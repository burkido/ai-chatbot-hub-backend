import os

from fastapi import APIRouter, HTTPException, Depends

from app import crud
from app.api.deps import SessionDep, CurrentUser
from app.models.user import User
from app.models.chat import ChatMessage, ChatRequest, ChatResponse

from typing import List

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

router = APIRouter()

# it can adapt for managing multiple indexes
index_name = "langchain-retrieval-augmentation"

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
    if user.credit < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    crud.decrease_user_credit(session=session, user=user, amount=1)
    
    response = chat(chat_request.message, chat_request.namespace, chat_model, chat_request.history, vectorstore)
    
    # Generate title if this is the first message
    title = None
    if len(chat_request.history) == 0:
        title = generate_title(chat_request.message, chat_model)
        
    return ChatResponse(content=response, title=title)

def augment_prompt(
        query: str,
        namespace: str,
        vectorstore: PineconeVectorStore
):
    # get top 3 results from knowledge base
    results = vectorstore.similarity_search(query=query, k=10, namespace=namespace)
    # get the text from the results
    source_knowledge = "\n".join([x.page_content for x in results])
    # feed into an augmented prompt
    augmented_prompt = f"""Using the contexts below, answer the query. Answer according to prompted langugage. If you don't know the answer, you can say "I don't know. If you want to notify the problem, please send us a message by clicking the menu item ontop right of the screen."

    Contexts:
    {source_knowledge}

    Query: {query}"""
    return augmented_prompt

def chat(
        new_message: str,
        namespace: str,
        chat_model: ChatOpenAI,
        history: List[ChatMessage],
        vectorstore: PineconeVectorStore
) -> str:
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

    # Augment the prompt with RAG
    augmented_prompt = augment_prompt(new_message, namespace, vectorstore)
    langchain_messages.append(HumanMessage(content=augmented_prompt))

    # Get the assistant's response
    response = chat_model(langchain_messages)
    
    return response.content

def generate_title(message: str, chat_model: ChatOpenAI) -> str:
    prompt = HumanMessage(content=f"Create a very brief title (4 words max) for this message: '{message}'")
    response = chat_model([prompt])
    return response.content.strip()