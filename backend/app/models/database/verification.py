import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from app.utils import prefix_email_with_package


class Verification(SQLModel, table=True):
    """Database model for verification codes (One-Time Password)"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(index=True, foreign_key="application.id")
    email: str = Field(index=True, max_length=255)
    user_id: str = Field(index=True)
    code: str = Field(max_length=6)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    is_verified: bool = Field(default=False)

    def is_expired(self) -> bool:
        """Check if the verification code has expired"""
        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > self.expires_at
        
    @classmethod
    def generate(cls, application_id: uuid.UUID, email: str, user_id: str, expiration_minutes: int = 10, package_name: Optional[str] = None) -> "Verification":
        """Generate a new verification code for the given email with specified expiration time"""
        verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
        
        # Apply email prefixing if package_name is provided
        prefixed_email = prefix_email_with_package(email, package_name) if package_name else email
        
        return cls(
            application_id=application_id,
            email=prefixed_email,
            user_id=user_id,
            code=verification_code,
            expires_at=expires_at
        )