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
from app.utils import prefix_email_with_package, extract_real_email

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)

# User-related CRUD operations

def get_user(session: Session, user_id: str, application_id: uuid.UUID) -> Optional[User]:
    statement = select(User).where(User.id == user_id, User.application_id == application_id)
    return session.exec(statement).first()

def get_user_by_email(session: Session, email: str, application_id: uuid.UUID) -> Optional[User]:
    # First try direct matching (for backward compatibility)
    statement = select(User).where(User.email == email, User.application_id == application_id)
    user = session.exec(statement).first()
    
    if user:
        return user
    
    # If not found, try to get the application's package_name
    application = session.get(Application, application_id)
    if not application:
        return None
        
    prefixed_email = prefix_email_with_package(email, application.package_name)
    print(f"Trying to find user with prefixed email: {prefixed_email}")
    statement = select(User).where(User.email == prefixed_email, User.application_id == application_id)
    return session.exec(statement).first()

def get_user_by_google_id(session: Session, google_id: str, application_id: uuid.UUID) -> Optional[User]:
    statement = select(User).where(User.google_id == google_id, User.application_id == application_id)
    return session.exec(statement).first()

def get_user_by_id(session: Session, user_id: str, application_id: uuid.UUID = None) -> Optional[User]:
    statement = select(User).where(User.id == user_id, User.application_id == application_id)
    return session.exec(statement).first()

def get_users(session: Session, application_id: uuid.UUID = None, skip: int = 0, limit: int = 100) -> List[User]:
    if application_id:
        statement = select(User).where(User.application_id == application_id).offset(skip).limit(limit)
    else:
        statement = select(User).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_user(*, session: Session, user_create: UserCreate, application_id: uuid.UUID) -> User:
    # Get the application for its package_name
    application = session.get(Application, application_id)
    if not application:
        raise ValueError("Application not found")
    
    # Store the real email
    real_email = user_create.email
    
    # Create the user object directly using the fields from UserCreate
    user = User(
        application_id=application_id,
        email=prefix_email_with_package(real_email, application.package_name),
        hashed_password=get_password_hash(user_create.password),
        is_active=user_create.is_active,
        is_superuser=user_create.is_superuser,
        is_verified=user_create.is_verified,
        full_name=user_create.full_name,
        credit=user_create.credit
    )
    
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

def update_user(session: Session, db_obj: User, user_in: Union[UserUpdate, Dict[str, Any]]) -> User:
    obj_data = jsonable_encoder(db_obj)
    if isinstance(user_in, dict):
        update_data = user_in
    else:
        update_data = user_in.model_dump(exclude_unset=True)
    
    # Handle password updates separately
    password = update_data.pop("password", None)
    if password is not None:
        update_data["hashed_password"] = get_password_hash(password)
    
    # Handle email updates with prefixing if needed
    email = update_data.pop("email", None)
    if email is not None:
        # Get the application for its package_name
        application = session.get(Application, db_obj.application_id)
        if application:
            # Check if this is already a prefixed email (contains package_name+)
            if email.startswith(f"{application.package_name}+"):
                # Use as is - already prefixed
                update_data["email"] = email
            else:
                # Prefix the email
                update_data["email"] = prefix_email_with_package(email, application.package_name)
    
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
    # Generate unique package name if not provided
    if not app_create.package_name:
        import secrets
        app_create.package_name = secrets.token_urlsafe(32)
        
    db_obj = Application.model_validate(app_create)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def get_application(session: Session, application_id: uuid.UUID) -> Optional[Application]:
    return session.get(Application, application_id)

def get_application_by_package_name(session: Session, package_name: str) -> Optional[Application]:
    statement = select(Application).where(Application.package_name == package_name)
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