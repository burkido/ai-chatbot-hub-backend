from pydantic import BaseModel
from typing import List

class ChatMessage(BaseModel):
    role: str  # "system", "user", or "assistant"
    content: str

class ChatRequest(BaseModel):
    history: List[ChatMessage]  # Full conversation history, including user and assistant messages
    message: str  # The new user message to be appended
    namespace: str  # The namespace for the chat request