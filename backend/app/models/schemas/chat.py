from typing import List, Dict, Any
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Schema for chat messages"""
    role: str  # "system", "user", or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Schema for chat requests"""
    history: List[ChatMessage]  # Full conversation history
    message: str  # The new user message to be appended
    topic: str  # The title of the chat request
    namespace: str  # The namespace for the chat request
    assistant_type: str | None = None  # Optional type of assistant to use
    language: str | None = None  # Optional language code for the response


class ChatResponse(BaseModel):
    """Schema for chat responses"""
    content: str
    title: str | None = None
    sources: List[Dict[str, Any]] | None = None  # Metadata about sources
    remaining_credit: int | None = None
    is_credit_sufficient: bool = True