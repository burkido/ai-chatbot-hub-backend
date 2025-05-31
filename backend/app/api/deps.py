from collections.abc import Generator
from typing import Annotated, Optional
import uuid

import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session, select
from fastapi import Request

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models.schemas.token import TokenPayload
from app.models.database.user import User
from app.models.database.application import Application
from app.core.i18n import get_language_from_request, get_translation

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def get_language(request: Request) -> str:
    """
    Dependency to extract the preferred language from the request.
    """
    return get_language_from_request(request)

SessionDep = Annotated[Session, Depends(get_db)]

def get_application_by_package_name(
    session: SessionDep, 
    x_application_key: Optional[str] = Header(None)
) -> Application:
    """
    Verify the application package name and return the corresponding application.
    """
    if not x_application_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Application-Key header is required",
        )
    
    application = session.exec(
        select(Application).where(
            Application.package_name == x_application_key,
            Application.is_active == True
        )
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive application key",
        )
    
    return application

TokenDep = Annotated[str, Depends(reusable_oauth2)]
LanguageDep = Annotated[str, Depends(get_language)]
ApplicationDep = Annotated[Application, Depends(get_application_by_package_name)]

def get_current_user(
    session: SessionDep,
    language: LanguageDep,
    token: TokenDep,
    current_application: ApplicationDep
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_translation("invalid_token", language),
        )
    
    # Validate that the token was issued for the current application
    if not token_data.app or str(current_application.id) != token_data.app:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_translation("invalid_token_for_application", language),
        )
    
    user = session.exec(
        select(User).where(
            User.id == token_data.sub,
            User.application_id == current_application.id
        )
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail=get_translation("user_not_found", language),
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail=get_translation("inactive_user", language),
        )
    
    return user


def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user",
        )
    return current_user


def get_current_verified_user(current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
    """Dependency for endpoints that require verified users (excludes anonymous users)"""
    if not current_user.is_verified and not current_user.is_anonymous:
        raise HTTPException(
            status_code=400,
            detail="Email verification required",
        )
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentVerifiedUser = Annotated[User, Depends(get_current_verified_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, 
            detail="The user doesn't have enough privileges"
        )
    return current_user