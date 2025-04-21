from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
from sqlmodel import Field, SQLModel


class FeedbackCreate(SQLModel):
    """Schema for creating feedback"""
    content: str = Field(max_length=500)


class FeedbackResponse(SQLModel):
    """Schema for feedback response"""
    id: UUID
    user_id: UUID
    application_id: UUID
    content: str
    created_at: datetime
    resolved: bool
    contact_made: bool


class FeedbackUpdate(SQLModel):
    """Schema for updating feedback status"""
    resolved: Optional[bool] = None
    contact_made: Optional[bool] = None


class FeedbacksResponse(SQLModel):
    """Schema for list of feedback responses"""
    data: List[FeedbackResponse]
    count: int


class FeedbackDelete(BaseModel):
    """Schema for feedback deletion response"""
    message: str