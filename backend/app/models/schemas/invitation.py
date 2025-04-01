from datetime import datetime
from typing import Optional
from pydantic import EmailStr, BaseModel
from uuid import UUID


class InviteCreate(BaseModel):
    """Schema for creating an invitation"""
    email_to: EmailStr


class InviteResponse(BaseModel):
    """Schema for invitation response"""
    id: UUID
    inviter_id: UUID
    email_to: str
    code: str
    created_at: datetime
    expires_at: datetime
    is_used: bool
    used_at: Optional[datetime] = None


class InviteCheck(BaseModel):
    """Schema for checking invitation status"""
    is_valid: bool
    message: str
    inviter_id: Optional[UUID] = None
    email_to: Optional[str] = None
    expires_at: Optional[datetime] = None


class InviteConsumeResponse(BaseModel):
    """Schema for invitation consumption response"""
    message: str
    success: bool