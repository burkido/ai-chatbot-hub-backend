from sqlmodel import SQLModel


class CreditAdd(SQLModel):
    """Schema for adding credits"""
    amount: int


class CreditResponse(SQLModel):
    """Schema for credit response"""
    current_credit: int