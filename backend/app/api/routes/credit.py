from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from app.api.deps import CurrentUser, SessionDep
from app.models.credit import CreditAdd, CreditResponse

router = APIRouter()

@router.post("/add", response_model=CreditResponse)
def add_credit(
    *, 
    session: SessionDep,
    credit_in: CreditAdd,
    current_user: CurrentUser
) -> Any:
    """
    Add credit to current user's account.
    """
    if credit_in.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Credit amount must be positive"
        )
    
    current_user.credit += credit_in.amount
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return CreditResponse(current_credit=current_user.credit)