import os

from fastapi import APIRouter, HTTPException, Depends

from app import crud
from app.api.deps import SessionDep, CurrentUser
from app.models.user import User
from app.models.chat import ChatMessage, ChatRequest, ChatResponse

from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

router = APIRouter()

# it can adapt for managing multiple indexes
index_name = "assistant-ai"

# Dependency for ChatOpenAI instance
def get_chat_openai() -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7,
        model="gpt-4o"
    )

def get_vectorstore() -> PineconeVectorStore:
    return PineconeVectorStore(index_name=index_name, embedding=OpenAIEmbeddings())

@router.post("/", response_model=ChatResponse)
def chat_endpoint(
    chat_request: ChatRequest,
    session: SessionDep,
    current_user: CurrentUser,
    chat_model: ChatOpenAI = Depends(get_chat_openai),
    vectorstore: PineconeVectorStore = Depends(get_vectorstore)
) -> ChatResponse:
    user = session.get(User, current_user.id)
    if not user.is_premium:
        if user.credit < 1:
            raise HTTPException(status_code=402, detail="Insufficient credits")
        crud.decrease_user_credit(session=session, user=user, amount=1)
    
    response, sources = chat(
        chat_request.message, 
        chat_request.namespace,
        chat_request.topic,
        chat_model, 
        chat_request.history, 
        vectorstore
    )
    
    title = None
    if len(chat_request.history) == 0:
        title = generate_title(chat_request.message, chat_model)
        
    return ChatResponse(content=response, title=title, sources=sources)

def augment_prompt(
        query: str,
        namespace: str,
        topic: str,
        vectorstore: PineconeVectorStore
):
    # get top results from knowledge base
    results = vectorstore.similarity_search(
        query=query,
        k=10,
        filter={"topic": {"$eq": topic}},
        namespace=namespace
    )

    # Extract sources information - excluding page_content
    sources = []
    for doc in results:
        if hasattr(doc, 'metadata'):
            source_info = {
                "authors": doc.metadata.get("authors", "Unknown"),
                "book_title": doc.metadata.get("book_title", "Untitled"),
                "source": doc.metadata.get("source", ""),
            }
            sources.append(source_info)
    
    # get the text from the results (still need this for the AI to generate a response)
    source_knowledge = "\n".join([x.page_content for x in results])
    
    # feed into an augmented prompt
    augmented_prompt = f"""Using the contexts below, answer the query. Answer according to prompted langugage. If you don't know the answer, you can say "I don't know. If you want to notify the problem, please send us a message by clicking the menu item ontop right of the screen."

    Contexts:
    {source_knowledge}

    Query: {query}"""
    return augmented_prompt, sources

def chat(
        new_message: str,
        namespace: str,
        topic: str,
        chat_model: ChatOpenAI,
        history: List[ChatMessage],
        vectorstore: PineconeVectorStore
) -> tuple[str, List[Dict[str, Any]]]:
    langchain_messages = []
    for msg in history:
        if msg.role == "system":
            langchain_messages.append(SystemMessage(content=msg.content))
        elif msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
        else:
            raise ValueError(f"Unknown role: {msg.role}")
    
    # Add the new user message
    langchain_messages.append(HumanMessage(content=new_message))

    # Augment the prompt with RAG and get the sources
    augmented_prompt, sources = augment_prompt(new_message, namespace, topic, vectorstore)
    langchain_messages.append(HumanMessage(content=augmented_prompt))

    # Get the assistant's response
    response = chat_model(langchain_messages)
    
    return response.content, sources

def generate_title(message: str, chat_model: ChatOpenAI) -> str:
    prompt = HumanMessage(content=f"Create a very brief title (4 words max) for this message: '{message}'")
    response = chat_model([prompt])
    return response.content.strip()