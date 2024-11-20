from fastapi import APIRouter, HTTPException, Form, Depends
from pydantic import BaseModel
from app.api.deps import ChatEngineDep
from app import crud
from app.api.deps import SessionDep, CurrentUser
from app.models.user import User
from app.models.chat import ChatMessage, ChatRequest
from typing import List
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import os

router = APIRouter()

# Dependency for ChatOpenAI instance
def get_chat_openai() -> ChatOpenAI:
    return ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7,
        model="gpt-4o"
    )

def chat(new_message: str, chat_model: ChatOpenAI, history: List[ChatMessage]) -> str:
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

    # Get the assistant's response
    response = chat_model(langchain_messages)
    
    return response.content

@router.post("/", response_model=str)
def chat_endpoint(
    chat_request: ChatRequest,
    session: SessionDep,
    current_user: CurrentUser,
    chat_model: ChatOpenAI = Depends(get_chat_openai)
) -> str:
    """
    Chat with the assistant and decrease the user's credit.
    """
    # Get the current user from the database
    user = session.get(User, current_user.id)

    # Check if the user has enough credits
    if user.credit < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    # Decrease the user's credit
    crud.decrease_user_credit(session=session, user=user, amount=1)
    
    # Get the chat response
    response = chat(chat_request.message, chat_model, chat_request.history)
    
    return response