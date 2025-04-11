import uuid
import secrets
from datetime import datetime, timedelta, timezone
from sqlmodel import Field, SQLModel


class OTP(SQLModel, table=True):
    """Database model for OTP (One-Time Password)"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_id: uuid.UUID = Field(index=True, foreign_key="application.id")
    email: str = Field(index=True, max_length=255)
    user_id: str = Field(index=True)
    code: str = Field(max_length=6)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    is_verified: bool = Field(default=False)

    def is_expired(self) -> bool:
        """Check if the OTP has expired"""
        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > self.expires_at
        
    @classmethod
    def generate(cls, application_id: uuid.UUID, email: str, user_id: str, expiration_minutes: int = 10) -> "OTP":
        """Generate a new OTP for the given email with specified expiration time"""
        otp_code = ''.join(secrets.choice('0123456789') for _ in range(6))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
        
        return cls(
            application_id=application_id,
            email=email,
            user_id=user_id,
            code=otp_code,
            expires_at=expires_at
        )