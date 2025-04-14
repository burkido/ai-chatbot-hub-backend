from datetime import datetime
from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class VerificationCreate(SQLModel):
    """Schema for creating a verification code"""
    user_id: str


class VerificationVerify(SQLModel):
    """Schema for verifying a verification code"""
    user_id: str
    code: str = Field(min_length=6, max_length=6)


class VerificationResponse(SQLModel):
    """Schema for verification response"""
    message: str
    expires_at: datetime


class RenewVerification(SQLModel):
    """Schema for renewing a verification code"""
    user_id: str