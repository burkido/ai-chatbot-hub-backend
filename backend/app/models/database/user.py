import uuid
from typing import Optional
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Database model for user table"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    full_name: str | None = Field(default=None, max_length=255)
    credit: int = Field(default=10, ge=0)
    google_id: str | None = Field(default=None, index=True)
    is_premium: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    hashed_password: Optional[str] = None