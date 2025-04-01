from sqlmodel import SQLModel
from typing import List
import uuid

class RedeemCodesPublic(SQLModel):
    """Schema for public redeem codes response"""
    data: List[uuid.UUID]  # Changed from the original to just use IDs
    count: int