import uuid
from typing import Any, Dict, List, Optional, TypeVar, Union, cast

from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr
from sqlmodel import Session, SQLModel, select

from app.core.security import get_password_hash, verify_password
from app.models.database import User
from app.models.schemas import UserCreate, UserUpdate

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)

# User-related CRUD operations

def get_user(session: Session, user_id: str) -> Optional[User]:
    user = session.get(User, user_id)
    if user:
        return user
    return None

def get_user_by_email(session: Session, email: str) -> Optional[User]:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()

def get_user_by_google_id(session: Session, google_id: str) -> Optional[User]:
    statement = select(User).where(User.google_id == google_id)
    return session.exec(statement).first()

def get_user_by_id(session: Session, user_id: str) -> Optional[User]:
    return session.get(User, user_id)

def get_users(session: Session, skip: int = 0, limit: int = 100) -> List[User]:
    statement = select(User).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_user(*, session: Session, user_create: UserCreate) -> User:
    
    db_obj = User.model_validate(user_create, update={"hashed_password": get_password_hash(user_create.password)})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def update_user(session: Session, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]) -> User:
    obj_data = jsonable_encoder(db_obj)
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)
    
    # Handle password updates separately
    password = update_data.pop("password", None)
    if password is not None:
        update_data["hashed_password"] = get_password_hash(password)
    
    # Update all other fields
    for field in obj_data:
        if field in update_data:
            setattr(db_obj, field, update_data[field])
    
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def authenticate(session: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(session=session, email=email)
    if not user:
        return None
    if not verify_password(password, cast(str, user.hashed_password)):
        return None
    return user

def decrease_user_credit(*, session: Session, user: User, amount: int) -> User:
    user.credit -= amount
    session.add(user)
    session.commit()
    session.refresh(user)
    return user