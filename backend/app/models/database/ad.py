import uuid
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone


class Ad(SQLModel, table=True):
    """Database model for mobile app ads"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(index=True, foreign_key="application.id", ondelete="CASCADE")
    name: str = Field(index=True, max_length=255)
    unit_id: str = Field(max_length=255)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))