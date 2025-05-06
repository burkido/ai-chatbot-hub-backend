import uuid
from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, SQLModel


class AdBase(SQLModel):
    """Base schema for ad data"""
    name: str = Field(max_length=255)
    unit_id: str = Field(max_length=255)
    description: Optional[str] = None
    is_active: bool = True


class AdCreate(AdBase):
    """Schema for creating a new ad"""
    pass


class AdUpdate(SQLModel):
    """Schema for updating ad data"""
    name: Optional[str] = Field(default=None, max_length=255)
    unit_id: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AdPublic(AdBase):
    """Schema for public ad data"""
    id: uuid.UUID
    application_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class AdsPublic(SQLModel):
    """Schema for list of public ad data"""
    data: List[AdPublic]
    count: int


class AdResponse(SQLModel):
    """Schema for ad response"""
    ad_unit_id: str