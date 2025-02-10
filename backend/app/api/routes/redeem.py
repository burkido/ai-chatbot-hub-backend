from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, func
from app.models.redeem_code import RedeemCode, RedeemCodesPublic
from typing import Any

from app.api.deps import SessionDep, CurrentUser, get_current_active_superuser
from app.models.user import User

router = APIRouter()

@router.get("/list", response_model=RedeemCodesPublic)
def read_redeem_codes(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100
) -> Any:
    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(RedeemCode)
        count = session.exec(count_statement).one()
        statement = select(RedeemCode).offset(skip).limit(limit)
        redeem_codes = session.exec(statement).all()
    else:
        # No user-ownership field on RedeemCode, so this returns everything.
        count_statement = select(func.count()).select_from(RedeemCode)
        count = session.exec(count_statement).one()
        statement = select(RedeemCode).offset(skip).limit(limit)
        redeem_codes = session.exec(statement).all()

    return RedeemCodesPublic(data=redeem_codes, count=count)

@router.post("/add", response_model=RedeemCode, dependencies=[Depends(get_current_active_superuser)])
def add_redeem_code(code: str, value: int, session: SessionDep) -> Any:
    existing_code = session.exec(select(RedeemCode).where(RedeemCode.code == code)).first()
    if existing_code:
        raise HTTPException(status_code=400, detail="Redeem code already exists")
    
    redeem_code = RedeemCode(code=code, value=value)
    session.add(redeem_code)
    session.commit()
    session.refresh(redeem_code)
    return redeem_code

@router.post("/use", response_model=User)
def use_redeem_code(code: str, user_id: str, session: SessionDep) -> Any:
    redeem_code = session.exec(select(RedeemCode).where(RedeemCode.code == code)).first()
    if not redeem_code or redeem_code.is_used:
        raise HTTPException(status_code=400, detail="Invalid or already used redeem code")
    
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.credit += redeem_code.value
    redeem_code.is_used = True
    session.commit()
    return user

@router.delete("/delete/{code}", response_model=dict, dependencies=[Depends(get_current_active_superuser)])
def delete_redeem_code(code: str, session: SessionDep) -> Any:
    redeem_code = session.exec(select(RedeemCode).where(RedeemCode.code == code)).first()
    if not redeem_code:
        raise HTTPException(status_code=404, detail="Redeem code not found")
    
    session.delete(redeem_code)
    session.commit()
    return {"detail": "Redeem code deleted successfully"}