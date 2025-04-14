from typing import List, Dict, Optional
from datetime import datetime
from pydantic import EmailStr, BaseModel
from sqlmodel import Field, SQLModel
import uuid


class UserBase(SQLModel):
    """Base schema for user data"""
    email: str = Field(max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    credit: int = Field(default=10, ge=0)
    is_premium: bool = False
    is_verified: bool = False


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_superuser: bool = False
    is_active: bool = True
    is_verified: bool = False
    credit: int = 10
    invite_code: Optional[str] = None
    inviter_id: Optional[str] = None


class UserRegister(SQLModel):
    """Schema for user registration"""
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(UserBase):
    """Schema for updating user data"""
    email: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    """Schema for users updating their own data"""
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    """Schema for password update"""
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


class UpdateCredit(SQLModel):
    """Schema for credit update"""
    credit: int = Field(ge=0)


class UserPublic(UserBase):
    """Schema for public user data"""
    id: uuid.UUID


class UsersPublic(SQLModel):
    """Schema for list of public user data"""
    data: List[UserPublic]
    count: int


class UserGoogleLogin(SQLModel):
    """Schema for Google login"""
    email: EmailStr
    google_id: str


class RegisterResponse(SQLModel):
    """Schema for registration response"""
    id: str


class CreditAddRequest(SQLModel):
    """Schema for credit addition request"""
    amount: int = Field(gt=0, lt=10)

class PasswordRecovery(SQLModel):
    user_id: str

class PasswordRecoveryRequest(SQLModel):
    """Schema for password recovery request"""
    email: EmailStr

class UserStatPoint(SQLModel):
    """Schema for a single user statistics data point"""
    date: str
    count: int


class ApplicationUserStats(SQLModel):
    """Schema for user statistics for a single application"""
    application_name: str
    data_points: List[UserStatPoint]
    current_count: int


class UserStatistics(SQLModel):
    """Schema for user statistics response"""
    total_users: int
    by_application: List[ApplicationUserStats]