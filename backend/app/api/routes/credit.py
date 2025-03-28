from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from app.api.deps import CurrentUser, SessionDep, LanguageDep
from app.models.credit import CreditAdd, CreditResponse
from app.core.i18n import get_translation

router = APIRouter()

@router.post("/add", response_model=CreditResponse)
def add_credit(
    *, 
    session: SessionDep,
    credit_in: CreditAdd,
    current_user: CurrentUser,
    language: LanguageDep  # Added language dependency
) -> Any:
    """
    Add credit to current user's account.
    """
    if credit_in.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail=get_translation("invalid_credit_amount", language)
        )
    
    current_user.credit += credit_in.amount
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return CreditResponse(current_credit=current_user.credit)