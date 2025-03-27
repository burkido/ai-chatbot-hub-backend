import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from pydantic import BaseModel, EmailStr
from uuid import UUID

class Invitation(SQLModel, table=True):
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

    @classmethod
    def generate(cls, email_to: str, inviter_id: uuid.UUID, expiry_hours: int = 72) -> "Invitation":
        """Generate a new invitation with a secure random code"""
        # Create a random 8-character alphanumeric code
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        code = ''.join(random.choice(chars) for _ in range(8))
        
        # Set expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        
        return cls(
            email_to=email_to,
            inviter_id=inviter_id,
            code=code,
            expires_at=expires_at
        )
    
    def is_expired(self) -> bool:
        """Check if the invitation has expired"""
        # Ensure the expires_at has timezone info before comparison
        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > self.expires_at
    
    def consume(self) -> None:
        """Mark the invitation as used"""
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)


class InviteCreate(BaseModel):
    email_to: EmailStr
    

class InviteResponse(BaseModel):
    id: UUID
    inviter_id: UUID
    email_to: str
    code: str
    created_at: datetime
    expires_at: datetime
    is_used: bool
    used_at: Optional[datetime] = None


class InviteCheck(BaseModel):
    is_valid: bool
    message: str
    inviter_id: Optional[UUID] = None
    email_to: Optional[str] = None
    expires_at: Optional[datetime] = None


class InviteConsumeResponse(BaseModel):
    message: str
    success: bool