import uuid
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone


class Application(SQLModel, table=True):
    """Database model for client applications"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, max_length=255)
    package_name: str = Field(unique=True, index=True, max_length=255)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    default_user_credit: int = Field(default=10)
    default_anonymous_credit: int = Field(default=3)  # Lower credit for anonymous users
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Application specific settings
    app_deeplink_url: str = Field(default="https://example.com")