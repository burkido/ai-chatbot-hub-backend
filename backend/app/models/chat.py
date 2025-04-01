from pydantic import BaseModel
from typing import List, Dict, Any
from sqlmodel import SQLModel, Field

class ChatMessage(BaseModel):
    role: str  # "system", "user", or "assistant"
    content: str

class ChatRequest(BaseModel):
    history: List[ChatMessage]  # Full conversation history, including user and assistant messages
    message: str  # The new user message to be appended
    topic: str  # The title of the chat request
    namespace: str  # The namespace for the chat request

class ChatResponse(BaseModel):
    content: str
    title: str | None = None
    sources: List[Dict[str, Any]] | None = None  # Add this field to hold metadata
    remaining_credit: int | None = None  # User's remaining credit after this operation
    is_credit_sufficient: bool = True  # Flag to indicate if user had enough credits