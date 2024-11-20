from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models.token import TokenPayload
from app.models.user import User

from canopy.knowledge_base import KnowledgeBase
from canopy.context_engine import ContextEngine
from canopy.chat_engine import ChatEngine
from canopy.tokenizer import Tokenizer

Tokenizer.initialize()

INDEX_NAME = "quickstart-index"

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

class EngineSingleton:
    _chat_engine = None

    @classmethod
    def get_chat_engine(cls) -> ChatEngine:
        if cls._chat_engine is None:
            kb = KnowledgeBase(index_name=INDEX_NAME)
            kb.connect()
            context_engine = ContextEngine(kb)
            cls._chat_engine = ChatEngine(context_engine)
        return cls._chat_engine


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def get_chat_engine() -> ChatEngine:
    return EngineSingleton.get_chat_engine()
    

SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]
ChatEngineDep = Annotated[ChatEngine, Depends(get_chat_engine)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
