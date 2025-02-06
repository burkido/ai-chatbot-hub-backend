from sqlmodel import SQLModel
from typing import Optional

class CreditAdd(SQLModel):
    amount: int

class CreditResponse(SQLModel):
    current_credit: int