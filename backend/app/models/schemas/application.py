import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel


class ApplicationBase(SQLModel):
    """Base schema for application data"""
    name: str = Field(max_length=255)
    description: str | None = Field(default=None)
    is_active: bool = True
    default_user_credit: int = Field(default=10, ge=0)
    deeplink_base_url: str = Field(default="https://example.com")


class ApplicationCreate(ApplicationBase):
    """Schema for creating a new application"""
    api_key: str | None = None  # Can be generated automatically


class ApplicationUpdate(SQLModel):
    """Schema for updating application data"""
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
    is_active: bool | None = None
    default_user_credit: int | None = Field(default=None, ge=0)
    deeplink_base_url: str | None = Field(default=None)


class ApplicationPublic(ApplicationBase):
    """Schema for public application data"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ApplicationsPublic(SQLModel):
    """Schema for list of public application data"""
    data: list[ApplicationPublic]
    count: int