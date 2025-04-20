from datetime import timedelta, datetime, timezone
from typing import Annotated, Any, List
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Body

import jwt
from sqlmodel import select

from app import crud
from app.api.deps import CurrentUser, SessionDep, LanguageDep, ApplicationDep
from app.core import security
from app.core.config import settings
from app.core.i18n import get_translation
from app.core.security import get_password_hash
# Updated imports to use the new model structure
from app.models.database.user import User
from app.models.database.verification import Verification
from app.models.database.invitation import Invitation
from app.models.database.otp import OTP
from app.models.database.reset_password_token import ResetPasswordToken

from app.models.schemas.user import UserPublic, UserCreate, UserGoogleLogin, RegisterResponse, PasswordRecoveryRequest, UserGoogleRegister
from app.models.schemas.token import Token, RefreshTokenRequest, NewPassword
from app.models.schemas.message import Message
from app.models.schemas.verification import VerificationVerify, VerificationResponse, RenewVerification
from app.models.schemas.invitation import InviteCreate, InviteResponse, InviteCheck

from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    generate_invite_friend_email,
    generate_email_verification_otp,
    send_email,
    verify_password_reset_token,
    extract_real_email,
)

router = APIRouter()


@router.post("/login")
def login(
    session: SessionDep, 
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    language: LanguageDep,
    application: ApplicationDep
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password, application_id=application.id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_translation("incorrect_credentials", language),  
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation("account_inactive", language),  
        )

    if not user.is_verified:
        # Check if there's an existing non-expired OTP
        statement = select(OTP).where(OTP.user_id == str(user.id)).order_by(OTP.created_at.desc())
        existing_otp = session.exec(statement).first()
        
        # Handle OTP expiration
        if existing_otp and not existing_otp.is_expired():
            otp = existing_otp
        else:
            if existing_otp:
                session.delete(existing_otp)
                session.commit()
                
            # Extract real email for OTP generation
            real_email = extract_real_email(user.email)
            otp = OTP.generate(email=real_email, user_id=str(user.id))
            session.add(otp)
            session.commit()
            session.refresh(otp)

        # Send verification email with localized subject using real email
        real_email = extract_real_email(user.email)
        email_data = generate_email_verification_otp(
            email_to=real_email, 
            otp=otp.code,
            deeplink=f"{application.app_deeplink_url}/verify/{otp.code}",
            language=language  
        )
        send_email(
            email_to=real_email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=get_translation("account_not_verified", language)  
        )

    # Generate Tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    return Token(
        access_token=security.create_access_token(
            user.id, 
            application.id,
            expires_delta=access_token_expires
        ),
        refresh_token=security.create_refresh_token(
            user.id, 
            application.id,
            expires_delta=refresh_token_expires
        ),
        user_id=str(user.id),
        is_premium=user.is_premium,
        remaining_credit=user.credit
    )

@router.post("/login-google")
def google_login(
    session: SessionDep, 
    user_google: UserGoogleLogin,
    language: LanguageDep,
    application: ApplicationDep
) -> Token:
    """
    Google login
    """
    user = crud.get_user_by_email(
        session=session, 
        email=user_google.email, 
        application_id=application.id
    )
    
    # If user exists, verify their Google ID
    if user:
        # Check if user has a google_id and it matches
        if hasattr(user, 'google_id') and user.google_id and user.google_id != user_google.google_id:
            raise HTTPException(
                status_code=401, 
                detail=get_translation("invalid_google_credentials", language)  
            )
        # If user doesn't have a google_id yet, update it
        elif not hasattr(user, 'google_id') or not user.google_id:
            user.google_id = user_google.google_id
            session.add(user)
            session.commit()
            session.refresh(user)
    else:
        # Instead of returning an error, create a new account
        # Set credit to application default
        credit = application.default_user_credit
        
        # Create user with Google credentials - mark as verified immediately for direct login
        user = User(
            email=user_google.email,
            google_id=user_google.google_id,
            full_name=user_google.full_name if hasattr(user_google, 'full_name') else "",
            credit=credit,
            is_active=True,
            is_verified=True,  # Mark as verified immediately
            is_superuser=False,
            application_id=application.id
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    
    if not user.is_active:
        raise HTTPException(
            status_code=400, 
            detail=get_translation("inactive_user", language)  
        )
    
    # Always mark user as verified for Google login
    if not user.is_verified:
        user.is_verified = True
        session.add(user)
        session.commit()
        session.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return Token(
        access_token=security.create_access_token(
            user.id, 
            application.id,
            expires_delta=access_token_expires
        ),
        refresh_token=security.create_refresh_token(
            user.id, 
            application.id,
            expires_delta=refresh_token_expires
        ),
        user_id=str(user.id),
        is_premium=user.is_premium,
        remaining_credit=user.credit
    )

@router.post("/refresh-token")
def refresh_access_token(
    session: SessionDep, 
    token_request: RefreshTokenRequest,
    language: LanguageDep,
    application: ApplicationDep
) -> Token:
    """
    Refresh access token using refresh token.
    Application is identified by the X-Application-Key header automatically.
    """
    try:
        payload = jwt.decode(token_request.refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get("sub")
        token_app_id = payload.get("app")
        
        # Verify token is for the current application
        if token_app_id != str(application.id):
            raise HTTPException(
                status_code=401, 
                detail=get_translation("invalid_token_for_application", language)
            )
        
        if user_id is None:
            raise HTTPException(
                status_code=401, 
                detail=get_translation("invalid_token", language)
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail=get_translation("invalid_token", language)
        )
    except jwt.DecodeError:
        raise HTTPException(
            status_code=401, 
            detail=get_translation("invalid_token", language)
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401, 
            detail=get_translation("invalid_token", language)
        )

    user = crud.get_user_by_id(
        session=session, 
        user_id=user_id, 
        application_id=application.id
    )
    
    if not user:
        raise HTTPException(
            status_code=404, 
            detail=get_translation("user_not_found", language)
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=400, 
            detail=get_translation("inactive_user", language)
        )
    elif not user.is_verified:
        # Create and send a new Verification for verification since token refresh failed due to unverified account
        # Extract real email for verification
        real_email = extract_real_email(user.email)
        verification = Verification.generate(
            application_id=application.id,
            email=real_email, 
            user_id=str(user.id)
        )
        session.add(verification)
        session.commit()
        
        # Send verification email with localized subject
        email_data = generate_email_verification_otp(
            email_to=real_email, 
            otp=verification.code,
            deeplink=f"{application.app_deeplink_url}/verify/{verification.code}",
            language=language  
        )
        send_email(
            email_to=real_email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        
        raise HTTPException(
            status_code=403, 
            detail=get_translation("account_not_verified", language)
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return Token(
        access_token=security.create_access_token(
            str(user.id), 
            str(application.id),
            expires_delta=access_token_expires
        ),
        refresh_token=security.create_refresh_token(
            str(user.id), 
            str(application.id),
            expires_delta=refresh_token_expires
        ),
        user_id=str(user.id),
        is_premium=user.is_premium,
        remaining_credit=user.credit
    )

@router.post("/register")
def register(
    session: SessionDep,
    user_create: UserCreate,
    language: LanguageDep,
    application: ApplicationDep
) -> RegisterResponse:
    """
    Register a new user with optional invite logic
    """
    # Check if this email is already registered with this application
    user = crud.get_user_by_email(
        session=session, 
        email=user_create.email,
        application_id=application.id
    )
    
    if user:
        raise HTTPException(
            status_code=409,
            detail=get_translation("user_exists", language),
        )
    
    # If invited, validate the invitation code
    if user_create.invite_code and user_create.inviter_id:
        # Find the invitation
        statement = (
            select(Invitation)
            .where(Invitation.code == user_create.invite_code)
            .where(Invitation.inviter_id == UUID(user_create.inviter_id))
            .where(Invitation.application_id == application.id)
        )
        invitation = session.exec(statement).first()
        
        if not invitation:
            raise HTTPException(
                status_code=404, 
                detail=get_translation("invalid_token", language)
            )
        
        if invitation.is_used:
            raise HTTPException(
                status_code=400, 
                detail=get_translation("invitation_code_used", language)
            )
        
        if invitation.is_expired():
            raise HTTPException(
                status_code=400, 
                detail=get_translation("invitation_code_expired", language)
            )
        
        # Mark invitation as used using the consume method
        invitation.consume()
        session.add(invitation)
        
        # Add bonus credits for invited user
        user_create.credit = application.default_user_credit * 2  # Double the default credits for invited users

    # Set application_id on the user before creation
    # Ensure default credit comes from the application if not specifically set
    if user_create.credit == 10:  # This is the default from the model
        user_create.credit = application.default_user_credit
    
    # Store original email for sending verification
    real_email = user_create.email
    
    # Create the new user (the create_user function will handle email prefixing)
    new_user = crud.create_user(session=session, user_create=user_create, application_id=application.id)

    # Give credits to inviter if invitation is valid
    if user_create.invite_code and user_create.inviter_id:
        inviter_user = crud.get_user_by_id(
            session=session, 
            user_id=user_create.inviter_id,
            application_id=application.id
        )
        if inviter_user:
            inviter_user.credit += application.default_user_credit
            session.add(inviter_user)
    
    # Create and send Verification for email verification
    verification = Verification.generate(
        application_id=application.id,
        email=real_email,  # Use real email for the verification record
        user_id=str(new_user.id)
    )
    session.add(verification)
    session.commit()
    
    # Send verification email
    email_data = generate_email_verification_otp(
        email_to=real_email,  # Send to real email
        otp=verification.code,
        deeplink=f"{application.app_deeplink_url}/verify/{verification.code}",
        language=language  
    )
    send_email(
        email_to=real_email,  # Send to real email
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return RegisterResponse(id=str(new_user.id))

@router.post("/register-google", response_model=Token)
def google_register(
    session: SessionDep,
    user_google: UserGoogleRegister,
    language: LanguageDep,
    application: ApplicationDep
) -> Token:
    """
    Register a new user with Google credentials, optional invite logic, and returns a token for immediate login
    """
    # Check if this email is already registered with this application
    user = crud.get_user_by_email(
        session=session, 
        email=user_google.email,
        application_id=application.id
    )
    
    if user:
        raise HTTPException(
            status_code=409,
            detail=get_translation("user_exists", language),
        )
    
    # Set initial credit value to application default
    credit = application.default_user_credit
    
    # If invited, validate the invitation code
    if user_google.invite_code and user_google.inviter_id:
        # Find the invitation
        statement = (
            select(Invitation)
            .where(Invitation.code == user_google.invite_code)
            .where(Invitation.inviter_id == UUID(user_google.inviter_id))
            .where(Invitation.application_id == application.id)
        )
        invitation = session.exec(statement).first()
        
        if not invitation:
            raise HTTPException(
                status_code=404, 
                detail=get_translation("invalid_token", language)
            )
        
        if invitation.is_used:
            raise HTTPException(
                status_code=400, 
                detail=get_translation("invitation_code_used", language)
            )
        
        if invitation.is_expired():
            raise HTTPException(
                status_code=400, 
                detail=get_translation("invitation_code_expired", language)
            )
        
        # Mark invitation as used
        invitation.consume()
        session.add(invitation)
        
        # Double credits for invited users
        credit = application.default_user_credit * 2
    
    # Store original email for sending verification
    real_email = user_google.email
    
    # Create a UserCreate object from the Google registration data
    user_create = UserCreate(
        email=user_google.email,
        password="",  # No password needed for Google login
        full_name=user_google.full_name,
        is_active=True,
        is_verified=True,  # Google users are pre-verified
        credit=credit,
        invite_code=user_google.invite_code,
        inviter_id=user_google.inviter_id
    )
    
    # Create the user with the crud function that handles email prefixing
    new_user = crud.create_user(session=session, user_create=user_create, application_id=application.id)
    
    # Set the Google ID after creation
    new_user.google_id = user_google.google_id
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # Give credits to inviter if invitation is valid
    if user_google.invite_code and user_google.inviter_id:
        inviter_user = crud.get_user_by_id(
            session=session, 
            user_id=user_google.inviter_id,
            application_id=application.id
        )
        if inviter_user:
            inviter_user.credit += application.default_user_credit
            session.add(inviter_user)
            session.commit()
    
    # Generate tokens for immediate login
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return Token(
        access_token=security.create_access_token(
            new_user.id, 
            application.id,
            expires_delta=access_token_expires
        ),
        refresh_token=security.create_refresh_token(
            new_user.id, 
            application.id,
            expires_delta=refresh_token_expires
        ),
        user_id=str(new_user.id),
        is_premium=new_user.is_premium,
        remaining_credit=new_user.credit
    )

@router.post("/verify-email", response_model=VerificationResponse)
def verify_email(
    session: SessionDep, 
    verification_data: VerificationVerify,
    language: LanguageDep,
    application: ApplicationDep
) -> VerificationResponse:
    """
    Verify email using Verification with localized responses
    """
    # Get user first
    user = crud.get_user_by_id(
        session=session, 
        user_id=verification_data.user_id,
        application_id=application.id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=get_translation("user_not_found", language)
        )
    
    # Get the latest Verification for this user and application
    statement = (
        select(Verification)
        .where(Verification.user_id == verification_data.user_id)
        .where(Verification.application_id == application.id)
        .order_by(Verification.created_at.desc())
    )
    verification_record = session.exec(statement).first()
    
    if not verification_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=get_translation("no_verification_code", language)
        )

    if verification_record.is_expired():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=get_translation("verification_expired", language)  
        )

    if verification_record.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_translation("already_verified", language)  
        )

    if verification_record.code != verification_data.code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=get_translation("invalid_verification_code", language)  
        )
    
    # Mark Verification as verified
    verification_record.is_verified = True
    session.add(verification_record)
    
    # Mark user as verified
    user.is_verified = True
    session.add(user)
    
    # Ensure changes are committed to the database
    session.commit()
    
    return VerificationResponse(
        message=get_translation("email_successfully_verified", language),
        expires_at=verification_record.expires_at
    )

@router.post("/verify-email-resend")
def verify_email_resend(
    session: SessionDep, 
    renew: RenewVerification,
    language: LanguageDep,
    application: ApplicationDep
) -> Message:
    """
    Renew Verification code, delete the previous one, generate a new one, and send an email to the user
    """
    # Find user by ID and application
    user = crud.get_user_by_id(
        session=session, 
        user_id=renew.user_id,
        application_id=application.id
    )
    
    if not user:
        raise HTTPException(
            status_code=404, 
            detail=get_translation("user_not_found", language)
        )
    
    # Extract real email from user record
    real_email = extract_real_email(user.email)
    
    # If user is already verified, don't create a new Verification
    if user.is_verified:
        return Message(message=get_translation("account_already_verified", language))
    
    # Delete previous Verifications for this user and application
    statement = select(Verification).where(
        Verification.user_id == renew.user_id,
        Verification.application_id == application.id
    )
    verifications = session.exec(statement).all()
    for verification in verifications:
        session.delete(verification)
    
    # Generate new Verification
    new_verification = Verification.generate(
        application_id=application.id,
        email=real_email,  # Use real email
        user_id=renew.user_id
    )
    session.add(new_verification)
    session.commit()
    
    # Send verification email with localized subject
    email_data = generate_email_verification_otp(
        email_to=real_email,  # Send to real email
        otp=new_verification.code,
        deeplink=f"{application.app_deeplink_url}/verify/{new_verification.code}",
        language=language  
    )
    send_email(
        email_to=real_email,  # Send to real email
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return Message(message=get_translation("new_verification_sent", language))

@router.post("/password-recovery")
def recover_password(
    password_recovery_request: PasswordRecoveryRequest,
    session: SessionDep, 
    language: LanguageDep,
    application: ApplicationDep
) -> Message:
    """
    Password Recovery with 6-digit token
    """
    user = crud.get_user_by_email(
        session=session, 
        email=password_recovery_request.email,
        application_id=application.id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail=get_translation("user_not_found", language),
        )
    
    # Extract real email from user record
    real_email = extract_real_email(user.email)

    print(f"Real email: {real_email}")
    
    # Delete any existing unused reset tokens for this user
    statement = select(ResetPasswordToken).where(
        ResetPasswordToken.user_id == str(user.id),
        ResetPasswordToken.application_id == application.id,
        ResetPasswordToken.is_used == False
    )
    existing_tokens = session.exec(statement).all()
    for token in existing_tokens:
        session.delete(token)
    session.commit()
    
    # Generate new reset password token
    reset_token = ResetPasswordToken.generate(
        application_id=application.id,
        email=real_email,  # Use real email
        user_id=str(user.id),
        expiration_hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS
    )
    session.add(reset_token)
    session.commit()
    session.refresh(reset_token)
    
    # Generate email with reset token
    email_data = generate_reset_password_email(
        email_to=real_email,  # Send to real email
        email=real_email,  # Use real email in template
        token=reset_token.token,  # Use the 6-digit token
        deeplink=f"{application.app_deeplink_url}/reset-password/{reset_token.token}",
        language=language
    )
    
    send_email(
        email_to=real_email,  # Send to real email
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return Message(message="Password recovery email sent")

@router.post("/reset-password/")
def reset_password(
    session: SessionDep, 
    body: NewPassword,
    language: LanguageDep,
    application: ApplicationDep
) -> Message:
    """
    Reset password using 6-digit token
    """
    # Find token in the database
    statement = select(ResetPasswordToken).where(
        ResetPasswordToken.token == body.token,
        ResetPasswordToken.application_id == application.id,
        ResetPasswordToken.is_used == False
    )
    token_record = session.exec(statement).first()
    
    # Verify token exists and is valid
    if not token_record:
        raise HTTPException(
            status_code=400, 
            detail=get_translation("invalid_token", language)
        )
    
    # Check if token has expired
    if token_record.is_expired():
        raise HTTPException(
            status_code=400, 
            detail=get_translation("token_expired", language)
        )
    
    # Get the user associated with the token
    user = crud.get_user_by_id(
        session=session, 
        user_id=token_record.user_id,
        application_id=application.id
    )
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail=get_translation("user_not_found", language),
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=400, 
            detail=get_translation("inactive_user", language)
        )
    
    # Update the user's password
    hashed_password = get_password_hash(password=body.new_password)
    user.hashed_password = hashed_password
    
    # Mark the token as used
    token_record.is_used = True
    
    # Save changes
    session.add(user)
    session.add(token_record)
    session.commit()
    
    return Message(message=get_translation("password_updated", language))

@router.post(
    "/password-recovery-html-content/{user_id}",
    response_class=HTMLResponse,
)
def recover_password_html_content(
    user_id: str, 
    session: SessionDep, 
    language: LanguageDep,
    current_user: CurrentUser,
    application: ApplicationDep
) -> Any:
    """
    HTML Content for Password Recovery
    """
    # Check if current user is a superuser
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    
    # Find user by ID and application
    user = crud.get_user_by_id(
        session=session, 
        user_id=user_id,
        application_id=application.id
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail=get_translation("user_not_found", language),
        )
    
    # Extract real email from user record
    real_email = extract_real_email(user.email)
    
    password_reset_token = generate_password_reset_token(email=real_email)
    email_data = generate_reset_password_email(
        email_to=real_email,  # Use real email
        email=real_email,  # Use real email in template
        token=password_reset_token,
        deeplink=f"{application.app_deeplink_url}/reset-password/{password_reset_token}",
        language=language
    )

    return HTMLResponse(
        content=email_data.html_content, 
        headers={"subject:": email_data.subject}
    )

@router.post("/invite-friend", response_model=InviteResponse)
def invite_friend(
    session: SessionDep,
    invite_create: InviteCreate,
    current_user: CurrentUser,
    language: LanguageDep,
    application: ApplicationDep
) -> Any:
    """
    Invite a friend to register on the platform
    """
    # Check if the user is already registered with this application
    invited_user = crud.get_user_by_email(
        session=session, 
        email=invite_create.email_to,
        application_id=application.id
    )
    
    if invited_user:
        raise HTTPException(
            status_code=409,
            detail=get_translation("user_exists", language),
        )
    
    # Check if there's already an active invitation for this email in this application
    statement = (
        select(Invitation)
        .where(
            Invitation.email_to == invite_create.email_to,
            Invitation.application_id == application.id,
            Invitation.is_used == False,
            Invitation.expires_at > datetime.now(timezone.utc)
        )
    )
    existing_invite = session.exec(statement).first()
    
    if existing_invite:
        # Return the existing invitation instead of creating a new one
        return existing_invite
    
    # Extract real email from current user
    current_user_real_email = extract_real_email(current_user.email)
    
    # Create a new invitation
    invitation = Invitation.generate(
        application_id=application.id,
        email_to=invite_create.email_to,
        inviter_id=current_user.id
    )
    
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    
    # Generate the deeplink with the invitation code
    deeplink = f"{application.app_deeplink_url}/register/{current_user.id}/{invitation.code}"
    
    # Send invitation email with localized subject
    email_data = generate_invite_friend_email(
        email_to=invite_create.email_to,
        username=current_user_real_email,
        inviter_name=current_user_real_email,
        deeplink=deeplink,
        language=language  
    )
    send_email(
        email_to=invite_create.email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return invitation

@router.get("/invite/{code}", response_model=InviteCheck)
def check_invite(
    code: str,
    session: SessionDep,
    application: ApplicationDep
) -> Any:
    """
    Check if an invitation is valid for the current application.
    """
    invitation = session.exec(
        select(Invitation)
        .where(
            Invitation.code == code,
            Invitation.application_id == application.id
        )
    ).first()
    
    if not invitation:
        return InviteCheck(
            is_valid=False,
            message="Invitation not found"
        )
    
    if invitation.is_used:
        return InviteCheck(
            is_valid=False,
            message="Invitation has already been used"
        )
    
    if invitation.is_expired():
        return InviteCheck(
            is_valid=False,
            message="Invitation has expired"
        )
    
    return InviteCheck(
        is_valid=True,
        message="Invitation is valid",
        inviter_id=invitation.inviter_id,
        email_to=invitation.email_to,
        expires_at=invitation.expires_at
    )

@router.get("/invites/by-user/{user_id}", response_model=List[InviteResponse])
def get_user_invites(
    user_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
    language: LanguageDep,
    application: ApplicationDep
) -> Any:
    """
    Get all invitations sent by a user within the current application.
    """
    # Ensure the user can only see their own invitations unless they're an admin
    if str(current_user.id) != str(user_id) and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=get_translation("not_authorized", language)
        )
    
    invitations = session.exec(
        select(Invitation)
        .where(
            Invitation.inviter_id == user_id,
            Invitation.application_id == application.id
        )
    ).all()
    
    return invitations

@router.post("/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user
