import uuid
from typing import Any, Dict, List, Optional, TypeVar, Union, cast

from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr
from sqlmodel import Session, SQLModel, select

from app.core.security import get_password_hash, verify_password
from app.models.database.user import User
from app.models.database.application import Application
from app.models.schemas.user import UserCreate, UserUpdate
from app.models.schemas.application import ApplicationCreate, ApplicationUpdate

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)

# User-related CRUD operations

def get_user(session: Session, user_id: str, application_id: uuid.UUID) -> Optional[User]:
    statement = select(User).where(User.id == user_id, User.application_id == application_id)
    return session.exec(statement).first()

def get_user_by_email(session: Session, email: str, application_id: uuid.UUID) -> Optional[User]:
    statement = select(User).where(User.email == email, User.application_id == application_id)
    return session.exec(statement).first()

def get_user_by_google_id(session: Session, google_id: str, application_id: uuid.UUID) -> Optional[User]:
    statement = select(User).where(User.google_id == google_id, User.application_id == application_id)
    return session.exec(statement).first()

def get_user_by_id(session: Session, user_id: str, application_id: uuid.UUID = None) -> Optional[User]:
    if application_id:
        statement = select(User).where(User.id == user_id, User.application_id == application_id)
        return session.exec(statement).first()
    else:
        return session.get(User, user_id)

def get_users(session: Session, application_id: uuid.UUID = None, skip: int = 0, limit: int = 100) -> List[User]:
    if application_id:
        statement = select(User).where(User.application_id == application_id).offset(skip).limit(limit)
    else:
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

def authenticate(session: Session, email: str, password: str, application_id: uuid.UUID) -> Optional[User]:
    user = get_user_by_email(session=session, email=email, application_id=application_id)
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

# Application-related CRUD operations

def create_application(*, session: Session, app_create: ApplicationCreate) -> Application:
    # Generate unique API key if not provided
    if not app_create.api_key:
        import secrets
        app_create.api_key = secrets.token_urlsafe(32)
        
    db_obj = Application.model_validate(app_create)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def get_application(session: Session, application_id: uuid.UUID) -> Optional[Application]:
    return session.get(Application, application_id)

def get_application_by_api_key(session: Session, api_key: str) -> Optional[Application]:
    statement = select(Application).where(Application.api_key == api_key)
    return session.exec(statement).first()

def get_applications(session: Session, skip: int = 0, limit: int = 100) -> List[Application]:
    statement = select(Application).offset(skip).limit(limit)
    return session.exec(statement).all()

def update_application(session: Session, db_obj: Application, obj_in: Union[ApplicationUpdate, Dict[str, Any]]) -> Application:
    obj_data = jsonable_encoder(db_obj)
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)
    
    # Update fields
    for field in obj_data:
        if field in update_data:
            setattr(db_obj, field, update_data[field])
    
    # Update the updated_at timestamp
    from datetime import datetime, timezone
    db_obj.updated_at = datetime.now(timezone.utc)
    
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj