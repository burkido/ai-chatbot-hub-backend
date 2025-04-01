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
from app.api.deps import CurrentUser, SessionDep, LanguageDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.core.i18n import get_translation
from app.core.security import get_password_hash
# Updated imports to use the new model structure
from app.models.database.user import User
from app.models.database.otp import OTP
from app.models.database.invitation import Invitation

from app.models.schemas.user import UserPublic, UserCreate, UserGoogleLogin, RegisterResponse
from app.models.schemas.token import Token, RefreshTokenRequest, NewPassword
from app.models.schemas.message import Message
from app.models.schemas.otp import OTPVerify, OTPResponse, RenewOTP
from app.models.schemas.invitation import InviteCreate, InviteResponse, InviteCheck

from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    generate_invite_friend_email,
    generate_email_verification_otp,
    send_email,
    verify_password_reset_token,
)

router = APIRouter()


@router.post("/login")
def login(
    session: SessionDep, 
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    language: LanguageDep
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
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
                
            otp = OTP.generate(email=form_data.username, user_id=str(user.id))
            session.add(otp)
            session.commit()
            session.refresh(otp)

        # Send verification email with localized subject
        email_data = generate_email_verification_otp(
            email_to=form_data.username, 
            otp=otp.code,
            deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}",
            language=language  
        )
        send_email(
            email_to=form_data.username,
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
        access_token=security.create_access_token(user.id, expires_delta=access_token_expires),
        refresh_token=security.create_refresh_token(user.id, expires_delta=refresh_token_expires),
        user_id=str(user.id),
        is_premium=user.is_premium,
        remaining_credit=user.credit
    )

@router.post("/login-google")
def google_login(
    session: SessionDep, 
    user_google: UserGoogleLogin,
    language: LanguageDep  
) -> Token:
    """
    Google login
    """
    user = crud.get_user_by_email(session=session, email=user_google.email)
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
        # Create and send a new OTP for verification since login failed due to unverified account
        otp = OTP.generate(email=user_google.email, user_id=str(user.id))
        session.add(otp)
        session.commit()
        
        # Send verification email with localized subject
        email_data = generate_email_verification_otp(
            email_to=user_google.email, 
            otp=otp.code,
            deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}",
            language=language  
        )
        send_email(
            email_to=user_google.email,
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
        access_token=security.create_access_token(user.id, expires_delta=access_token_expires),
        refresh_token=security.create_refresh_token(user.id, expires_delta=refresh_token_expires),
        user_id=user.id,
        is_premium=user.is_premium,
        remaining_credit=user.credit
    )

@router.post("/refresh-token")
def refresh_access_token(
    session: SessionDep, 
    token_request: RefreshTokenRequest,
    language: LanguageDep  
) -> Token:
    """
    Refresh access token
    """
    try:
        payload = jwt.decode(token_request.refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get("sub")
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

    user = crud.get_user_by_id(session=session, user_id=user_id)
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
        # Create and send a new OTP for verification since token refresh failed due to unverified account
        otp = OTP.generate(email=user.email, user_id=str(user.id))
        session.add(otp)
        session.commit()
        
        # Send verification email with localized subject
        email_data = generate_email_verification_otp(
            email_to=user.email, 
            otp=otp.code,
            deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}",
            language=language  
        )
        send_email(
            email_to=user.email,
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
            user.id, expires_delta=access_token_expires
        ),
        refresh_token=security.create_refresh_token(
            user.id, expires_delta=refresh_token_expires
        ),
        user_id=user.id,
        remaining_credit=user.credit
    )

@router.post("/register")
def register(
    session: SessionDep,
    user_create: UserCreate,
    language: LanguageDep
) -> RegisterResponse:
    """
    Register a new user with optional invite logic
    """
    user = crud.get_user_by_email(session=session, email=user_create.email)
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
        )
        invitation = session.exec(statement).first()
        
        if not invitation:
            raise HTTPException(status_code=404, detail=get_translation("invalid_token", language))
        
        if invitation.is_used:
            raise HTTPException(status_code=400, detail=get_translation("invitation_code_used", language))
        
        if invitation.is_expired():
            raise HTTPException(status_code=400, detail=get_translation("invitation_code_expired", language))
        
        # Mark invitation as used using the consume method
        invitation.consume()
        session.add(invitation)
        
        # Add bonus credits for invited user
        user_create.credit = 20

    # Create the new user
    new_user = crud.create_user(session=session, user_create=user_create)

    # Give credits to inviter if invitation is valid
    if user_create.invite_code and user_create.inviter_id:
        inviter_user = crud.get_user_by_id(session=session, user_id=user_create.inviter_id)
        if inviter_user:
            inviter_user.credit += 10
            session.add(inviter_user)
    
    # Create and send OTP for email verification
    otp = OTP.generate(email=user_create.email, user_id=str(new_user.id))
    session.add(otp)
    session.commit()
    
    # Send verification email
    email_data = generate_email_verification_otp(
        email_to=user_create.email, 
        otp=otp.code,
        deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}",
        language=language  
    )
    send_email(
        email_to=user_create.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return RegisterResponse(id=str(new_user.id))

@router.post("/verify-email", response_model=OTPResponse)
def verify_email(
    session: SessionDep, 
    verification_data: OTPVerify,
    language: LanguageDep
) -> OTPResponse:
    """
    Verify email using OTP with localized responses
    """
    # Get user first
    user = crud.get_user_by_id(session=session, user_id=verification_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=get_translation("user_not_found", language)
        )
    
    # Get the latest OTP for this user
    statement = (
        select(OTP)
        .where(OTP.user_id == verification_data.user_id)
        .order_by(OTP.created_at.desc())
    )
    otp_record = session.exec(statement).first()
    
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=get_translation("no_verification_code", language)
        )

    if otp_record.is_expired():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=get_translation("verification_expired", language)  
        )

    if otp_record.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_translation("already_verified", language)  
        )

    if otp_record.code != verification_data.code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=get_translation("invalid_verification_code", language)  
        )
    
    # Mark OTP as verified
    otp_record.is_verified = True
    session.add(otp_record)
    
    # Mark user as verified
    user.is_verified = True
    session.add(user)
    
    # Ensure changes are committed to the database
    session.commit()
    
    return OTPResponse(
        message=get_translation("email_successfully_verified", language),  # Localized success message
        expires_at=otp_record.expires_at
    )

@router.post("/verify-email-resend")
def verify_email_resend(
    session: SessionDep, 
    renew: RenewOTP,
    language: LanguageDep  
) -> Message:
    """
    Renew OTP code, delete the previous one, generate a new one, and send an email to the user
    """
    # Find user by ID
    user = crud.get_user_by_id(session=session, user_id=renew.user_id)
    if not user:
        raise HTTPException(
            status_code=404, 
            detail=get_translation("user_not_found", language)
        )
    
    # Get user's email from their record
    email = user.email
    
    # If user is already verified, don't create a new OTP
    if user.is_verified:
        return Message(message=get_translation("account_already_verified", language))
    
    # Delete previous OTPs
    statement = select(OTP).where(OTP.user_id == renew.user_id)
    otps = session.exec(statement).all()
    for otp in otps:
        session.delete(otp)
    
    # Generate new OTP
    new_otp = OTP.generate(email=email, user_id=renew.user_id)
    session.add(new_otp)
    session.commit()
    
    # Send verification email with localized subject
    email_data = generate_email_verification_otp(
        email_to=email, 
        otp=new_otp.code,
        deeplink=f"https://assistlyai.space/doctor/verify/{new_otp.code}",
        language=language  
    )
    send_email(
        email_to=email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return Message(message=get_translation("new_otp_sent", language))

@router.post("/password-recovery/{user_id}")
def recover_password(
    user_id: str, 
    session: SessionDep,
    language: LanguageDep  
) -> Message:
    """
    Password Recovery with localized messages
    """
    # Find user by ID instead of email
    user = crud.get_user_by_id(session=session, user_id=user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail=get_translation("user_not_found", language),  
        )
    
    email = user.email
    password_reset_token = generate_password_reset_token(email=email)
    
    # Generate email with localized subject
    email_data = generate_reset_password_email(
        email_to=email, 
        email=email, 
        token=password_reset_token,
        deeplink=f"https://assistlyai.space/doctor/verify/{password_reset_token}",
        language=language  
    )
    
    send_email(
        email_to=email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return Message(message=get_translation("password_recovery_sent", language))  # Localized success message

@router.post("/reset-password/")
def reset_password(
    session: SessionDep, 
    body: NewPassword,
    language: LanguageDep  
) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(
            status_code=400, 
            detail=get_translation("invalid_token", language)
        )
    user = crud.get_user_by_email(session=session, email=email)
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
    hashed_password = get_password_hash(password=body.new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    return Message(message=get_translation("password_updated", language))

@router.post(
    "/password-recovery-html-content/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(user_id: str, session: SessionDep, language: LanguageDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    # Find user by ID instead of email
    user = crud.get_user_by_id(session=session, user_id=user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail=get_translation("user_not_found", language),
        )
    
    email = user.email
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=email, email=email, token=password_reset_token,
        deeplink=f"https://assistlyai.space/doctor/reset-password/{password_reset_token}"
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )

@router.post("/invite-friend", response_model=InviteResponse)
def invite_friend(
    session: SessionDep,
    invite_create: InviteCreate,
    current_user: CurrentUser,
    language: LanguageDep  
) -> Any:
    """
    Invite a friend to register on the platform
    """
    # Check if the user is already registered
    invited_user = crud.get_user_by_email(session=session, email=invite_create.email_to)
    if invited_user:
        raise HTTPException(
            status_code=409,
            detail=get_translation("user_exists", language),
        )
    
    # Check if there's already an active invitation for this email
    statement = (
        select(Invitation)
        .where(Invitation.email_to == invite_create.email_to)
        .where(Invitation.is_used == False)
        .where(Invitation.expires_at > datetime.now(timezone.utc))
    )
    existing_invite = session.exec(statement).first()
    
    if existing_invite:
        # Return the existing invitation instead of creating a new one
        return existing_invite
    
    # Create a new invitation
    invitation = Invitation.generate(
        email_to=invite_create.email_to,
        inviter_id=current_user.id
    )
    
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    
    # Generate the deeplink with the invitation code
    deeplink = f"https://assistlyai.space/doctor/register/{current_user.id}/{invitation.code}"
    
    # Send invitation email with localized subject
    email_data = generate_invite_friend_email(
        email_to=invite_create.email_to,
        username=current_user.email,
        inviter_name=current_user.email,
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
) -> Any:
    """
    Check if an invitation is valid.
    """
    invitation = session.exec(select(Invitation).where(Invitation.code == code)).first()
    
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
    language: LanguageDep
) -> Any:
    """
    Get all invitations sent by a user.
    """
    # Ensure the user can only see their own invitations unless they're an admin
    if str(current_user.id) != str(user_id) and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=get_translation("not_authorized", language)
        )
    
    invitations = session.exec(
        select(Invitation).where(Invitation.inviter_id == user_id)
    ).all()
    
    return invitations

@router.post("/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user
