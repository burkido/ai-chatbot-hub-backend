from sqlmodel import SQLModel

class Message(SQLModel):
    """Generic message schema"""
    message: str