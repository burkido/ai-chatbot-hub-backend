from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select, func
from app.models.database.redeem_code import RedeemCode
from app.models.schemas.redeem_code import RedeemCodesPublic
from typing import Any
from app.api.deps import SessionDep, CurrentUser, LanguageDep, get_current_active_superuser
from app.models.database.user import User
from app.core.i18n import get_translation

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
def add_redeem_code(code: str, value: int, session: SessionDep, language: LanguageDep) -> Any:
    existing_code = session.exec(select(RedeemCode).where(RedeemCode.code == code)).first()
    if existing_code:
        raise HTTPException(status_code=400, detail=get_translation("redeem_code_exists", language))
    
    redeem_code = RedeemCode(code=code, value=value)
    session.add(redeem_code)
    session.commit()
    session.refresh(redeem_code)
    return redeem_code

@router.post("/use", response_model=User)
def use_redeem_code(code: str, user_id: str, session: SessionDep, language: LanguageDep) -> Any:
    redeem_code = session.exec(select(RedeemCode).where(RedeemCode.code == code)).first()
    if not redeem_code or redeem_code.is_used:
        raise HTTPException(status_code=400, detail=get_translation("redeem_code_invalid", language))
    
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail=get_translation("user_not_found", language))
    
    user.credit += redeem_code.value
    redeem_code.is_used = True
    session.commit()
    return user

@router.delete("/delete/{code}", response_model=dict, dependencies=[Depends(get_current_active_superuser)])
def delete_redeem_code(code: str, session: SessionDep, language: LanguageDep) -> Any:
    redeem_code = session.exec(select(RedeemCode).where(RedeemCode.code == code)).first()
    if not redeem_code:
        raise HTTPException(status_code=404, detail=get_translation("redeem_code_not_found", language))
    
    session.delete(redeem_code)
    session.commit()
    return {"detail": "Redeem code deleted successfully"}