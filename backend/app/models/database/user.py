import uuid
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import UniqueConstraint


class User(SQLModel, table=True):
    """Database model for user table"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(index=True, foreign_key="application.id")
    email: str = Field(unique=True, index=True, max_length=255)  # Restored unique constraint
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    full_name: str | None = Field(default=None, max_length=255)
    credit: int = Field(default=10, ge=0)
    google_id: str | None = Field(default=None, index=True)
    is_premium: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    is_anonymous: bool = Field(default=False)
    hashed_password: Optional[str] = None

    # Adding a UniqueConstraint via SQLAlchemy (using correct tuple syntax)
    __table_args__ = (
        UniqueConstraint("application_id", "email", name="uix_user_application_email"),
    )