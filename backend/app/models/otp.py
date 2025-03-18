import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from pydantic import EmailStr


class OTPBase(SQLModel):
    email: EmailStr = Field(index=True, max_length=255)
    expires_at: datetime
    is_verified: bool = False

    def is_expired(self) -> bool:
        """Check if the OTP has expired"""
        if self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > self.expires_at


class OTP(OTPBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(max_length=6)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def generate(cls, email: str, expiration_minutes: int = 10) -> "OTP":
        """Generate a new OTP for the given email with specified expiration time"""
        otp_code = ''.join(secrets.choice('0123456789') for _ in range(6))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
        
        return cls(
            email=email,
            code=otp_code,
            expires_at=expires_at
        )


class OTPCreate(SQLModel):
    email: EmailStr


class OTPVerify(SQLModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class OTPResponse(SQLModel):
    message: str
    expires_at: datetime

class RenewOTP(SQLModel):
    email: EmailStr