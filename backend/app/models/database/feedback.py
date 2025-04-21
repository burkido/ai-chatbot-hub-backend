import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class Feedback(SQLModel, table=True):
    """Database model for user feedback"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(index=True, foreign_key="user.id")
    application_id: uuid.UUID = Field(index=True, foreign_key="application.id")
    content: str = Field(max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = Field(default=False)
    contact_made: bool = Field(default=False)