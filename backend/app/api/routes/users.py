import uuid
from typing import Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select, and_

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    LanguageDep,
    get_current_active_superuser,
    ApplicationDep,
)
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
# Updated imports to use specific directory paths
from app.models.database.user import User
from app.models.database.application import Application
from app.models.database.verification import Verification
from app.models.schemas.message import Message
from app.models.schemas.user import (
    UserCreate, UserPublic, UserRegister, UserUpdate, 
    UserUpdateMe, UsersPublic, UpdatePassword, CreditAddRequest,
    UserStatistics, ApplicationUserStats, UserStatPoint
)
from app.utils import generate_new_account_email, generate_email_verification_otp, send_email
from app.core.i18n import get_translation

router = APIRouter()

@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(
    session: SessionDep, 
    skip: int = 0, 
    limit: int = 100,
    application: ApplicationDep = None,
    application_key: str = None,
    show_all: bool = False
) -> Any:
    """
    Retrieve users.
    - If application_key is provided, filter by that specific package name
    - Otherwise, show users from all applications (behaves like show_all)
    """
    if application_key:
        # Find the application with this package_name
        app_statement = select(Application).where(Application.package_name == application_key)
        filtered_application = session.exec(app_statement).first()
        
        if filtered_application:
            # Get count with filtered application
            count_statement = select(func.count()).select_from(
                select(User).where(User.application_id == filtered_application.id).subquery()
            )
            count = session.exec(count_statement).one()

            # Get users with filtered application
            statement = select(User).where(User.application_id == filtered_application.id).offset(skip).limit(limit)
            users = session.exec(statement).all()
        else:
            # No application found with that package_name
            return UsersPublic(data=[], count=0)
    else:
        # By default, get all users across all applications (no filter = show all)
        # Get count of all users across all applications
        count_statement = select(func.count()).select_from(User)
        count = session.exec(count_statement).one()

        # Get all users across all applications
        statement = select(User).offset(skip).limit(limit)
        users = session.exec(statement).all()

    return UsersPublic(data=users, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(
    session: SessionDep, 
    language: LanguageDep, 
    user_in: UserCreate,
    application: ApplicationDep
) -> Any:
    """
    Create new user in the current application.
    """
    # For superusers creating users, we check within the current application
    user = crud.get_user_by_email(session=session, email=user_in.email, application_id=application.id)
    if user:
        raise HTTPException(
            status_code=400,
            detail=get_translation("user_with_email_exists", language),
        )
    
    user = crud.create_user(session=session, user_create=user_in, application_id=application.id)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, 
            username=user_in.email, 
            password=user_in.password, 
            deeplink=f"https://assistlyai.space/doctor/login",
            project_name=application.name if application.name else settings.PROJECT_NAME
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
            project_name=application.name if application.name else settings.PROJECT_NAME
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, language: LanguageDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email, application_id=current_user.application_id)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail=get_translation("user_with_email_exists", language)
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, language: LanguageDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail=get_translation("incorrect_password", language))
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, language: LanguageDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail=get_translation("superuser_delete_not_allowed", language)
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, language: LanguageDep, application: ApplicationDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email, application_id=application.id)
    if user:
        raise HTTPException(
            status_code=400,
            detail=get_translation("user_with_email_exists", language),
        )
    
    # Create a user_create object from the registration input
    user_create = UserCreate.model_validate(user_in)
    
    # Create user with application_id from the header
    user = crud.create_user(session=session, user_create=user_create, application_id=application.id)
    
    # Create and send Verification for email verification
    verification = Verification.generate(
        application_id=application.id,
        email=user_in.email, 
        user_id=str(user.id)
    )
    session.add(verification)
    session.commit()
    
    # Send verification email
    email_data = generate_email_verification_otp(
        email_to=user_in.email, 
        otp=verification.code,
        deeplink=f"{application.app_deeplink_url}/verify/{verification.code}",
        project_name=application.name if application.name else settings.PROJECT_NAME,
        language=language
    )
    send_email(
        email_to=user_in.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
        project_name=application.name if application.name else settings.PROJECT_NAME
    )
    
    return user

@router.post("/add-credit/ad", response_model=UserPublic)
def add_credit_from_ad(
    *, session: SessionDep, current_user: CurrentUser, credit_request: CreditAddRequest
) -> Any:
    """
    Add credits to the current user after watching an ad.
    """
    # Add the specified amount of credits
    current_user.credit += credit_request.amount
    
    # Save changes to database
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user

@router.get(
    "/user-statistics",
    response_model=UserStatistics,
)
def get_user_statistics(
    session: SessionDep,
    current_user: CurrentUser,
    application: ApplicationDep,
) -> Any:
    """
    Get all user statistics for the current user's application without time filtering.
    """
    # Get total users count for this application
    total_query = select(func.count()).select_from(User).where(User.application_id == application.id)
    total_users = session.exec(total_query).one()
    
    # Create result structure
    result = UserStatistics(total_users=total_users, by_application=[])
    
    # Get current user count for this application
    current_count_query = select(func.count()).select_from(User).where(User.application_id == application.id)
    current_count = session.exec(current_count_query).one()
    
    # Since we don't have created_at field, we'll just return the current count
    # without historical data points
    data_points = [
        UserStatPoint(date=datetime.now().isoformat(), count=current_count)
    ]
    
    # Add to results
    result.by_application.append(
        ApplicationUserStats(
            application_name=application.name,
            data_points=data_points,
            current_count=current_count
        )
    )
    
    return result


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, language: LanguageDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail=get_translation("superuser_access_required", language)
        )
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    language: LanguageDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail=get_translation("user_not_found", language),
        )
    
    if user_in.email:
        # Before checking for duplicate emails, extract the real email from the input
        # to prevent double prefixing in the crud.update_user function
        from app.utils import extract_real_email
        user_in_dict = user_in.model_dump(exclude_unset=True)
        original_email = user_in_dict.get("email")
        
        # Check if the email already exists for another user
        existing_user = crud.get_user_by_email(session=session, email=original_email, application_id=db_user.application_id)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail=get_translation("user_with_email_exists", language)
            )

    db_user = crud.update_user(session=session, db_obj=db_user, user_in=user_in)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, language: LanguageDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=get_translation("user_not_found", language))
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
