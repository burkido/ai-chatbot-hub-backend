from datetime import datetime
from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class OTPCreate(SQLModel):
    """Schema for creating an OTP"""
    user_id: str


class OTPVerify(SQLModel):
    """Schema for verifying an OTP"""
    user_id: str
    code: str = Field(min_length=6, max_length=6)


class OTPResponse(SQLModel):
    """Schema for OTP response"""
    message: str
    expires_at: datetime


class RenewOTP(SQLModel):
    """Schema for renewing an OTP"""
    user_id: str