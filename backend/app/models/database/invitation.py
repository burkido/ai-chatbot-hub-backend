import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class Invitation(SQLModel, table=True):
    """Database model for user invitations"""
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    inviter_id: uuid.UUID = Field(index=True)
    email_to: str = Field(index=True)
    code: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    is_used: bool = Field(default=False)
    used_at: Optional[datetime] = Field(default=None)

    def is_expired(self) -> bool:
        """Check if the invitation has expired"""
        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > self.expires_at

    def consume(self) -> None:
        """Mark the invitation as used"""
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)