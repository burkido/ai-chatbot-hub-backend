import os

from fastapi import APIRouter, Depends

from app import crud
from app.api.deps import SessionDep, CurrentUser, LanguageDep
from app.models.database.user import User
from app.models.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.core.i18n import get_translation

from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings

router = APIRouter()

# it can adapt for managing multiple indexes
index_name = "assistant-ai"
#index_name = "canopy--ilmihal"

# Dependency for ChatOpenAI instance
def get_chat_openai() -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7,
        model="gpt-4o"
    )

def get_vectorstore() -> PineconeVectorStore:
    return PineconeVectorStore(index_name=index_name, embedding=OpenAIEmbeddings(model="text-embedding-3-small"))

@router.post("/", response_model=ChatResponse)
def chat_endpoint(
    chat_request: ChatRequest,
    session: SessionDep,
    current_user: CurrentUser,
    language: LanguageDep,  # Added language dependency
    chat_model: ChatOpenAI = Depends(get_chat_openai),
    vectorstore: PineconeVectorStore = Depends(get_vectorstore)
) -> ChatResponse:
    user = session.get(User, current_user.id)
    
    # Initialize credit status flags
    remaining_credit = user.credit
    is_credit_sufficient = True
    
    # Get response from chat function
    response, sources = chat(
        chat_request.message, 
        chat_request.namespace,
        chat_request.topic,
        chat_model, 
        chat_request.history, 
        vectorstore
    )
    
    # Handle credit deduction for non-premium users
    if not user.is_premium:
        # Calculate the credit cost based on whether sources were returned
        credit_cost = 2 if sources else 1
        
        if user.credit < credit_cost:
            # Mark as insufficient credit
            is_credit_sufficient = False
            
            # Decrease whatever credit is available if not already 0
            if user.credit > 0:
                crud.decrease_user_credit(session=session, user=user, amount=user.credit)
                remaining_credit = 0
        else:
            # User has sufficient credit, decrease the full amount
            crud.decrease_user_credit(session=session, user=user, amount=credit_cost)
            remaining_credit = user.credit
    
    title = None
    if len(chat_request.history) == 0:
        title = generate_title(chat_request.message, chat_model)
        
    return ChatResponse(
        content=response, 
        title=title, 
        sources=sources,
        remaining_credit=remaining_credit,
        is_credit_sufficient=is_credit_sufficient
    )

def augment_prompt(
        query: str,
        namespace: str,
        topic: str,
        vectorstore: PineconeVectorStore,
        similarity_threshold: float = 0.51  # Configurable threshold
):
    # get top results from knowledge base
    results = vectorstore.similarity_search_with_score(
        query=query,
        k=3,
        filter={"topic": {"$eq": topic}} if topic else None,
        namespace=namespace
    )

    print(f"Results: {results}")
    
    # Extract sources information - only from documents with sufficient score
    sources = []
    filtered_results = []
    
    for doc, score in results:
        print(f"Score for result: {score}")
        if score >= similarity_threshold:
            # Convert score to percentage (scores are typically between 0-1)
            similarity_percentage = round(score * 100, 2)
            source_info = {
                "authors": doc.metadata.get("authors", "Unknown"),
                "book_title": doc.metadata.get("book_title", "Untitled"),
                "source": doc.metadata.get("source", ""),
                "score": score,
                "similarity_percentage": similarity_percentage
            }
            sources.append(source_info)
            filtered_results.append((doc, score))
    
    # Join page_content only from documents that passed the threshold
    if filtered_results:
        source_knowledge = "\n".join([doc.page_content for doc, _ in filtered_results])
        
        augmented_prompt = f"""You are a kind and polite AI assistant with access to specific context from a book. When a user asks a question, use the provided context to generate accurate, helpful, and courteous answers. Always maintain a friendly, respectful tone in your responses.

        Contexts:
        {source_knowledge}

        Query: {query}"""
    else:
        # No results passed the threshold - use own knowledge but be transparent
        augmented_prompt = f"""You are a kind and polite AI assistant. The user has asked: "{query}" 

        I don't have specific information on this topic in my knowledge base. Please respond to the best of your ability using your own knowledge. Be honest that you're not using reference materials but still provide a helpful, friendly, and respectful response. Always maintain a supportive and courteous tone."""
    
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
    
    # Process history messages
    for msg in history:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            # If there are system messages in history, we'll include them too
            langchain_messages.append(SystemMessage(content=msg.content))
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