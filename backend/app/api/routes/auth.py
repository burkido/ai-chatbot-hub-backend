from datetime import timedelta, datetime, timezone  # Add timezone import
from typing import Annotated, Any, List
from uuid import UUID
import uuid  # Add this import to fix the NameError

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Body

import jwt
from sqlmodel import select  # Add this import

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.token import Message, Token, RefreshTokenRequest, NewPassword
from app.models.user import UserPublic, UserCreate, UserGoogleLogin, UserGoogleRegister
from app.models.otp import OTP, OTPVerify, OTPResponse, RenewOTP
from app.models.invitation import Invitation, InviteCreate, InviteResponse, InviteCheck, InviteConsumeResponse  # Updated import

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
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    elif not user.is_verified:
        # Check if there's an existing non-expired OTP
        statement = (
            select(OTP)
            .where(OTP.email == form_data.username)
            .order_by(OTP.created_at.desc())
        )
        existing_otp = session.exec(statement).first()
        
        # Reuse existing OTP if it's not expired, otherwise create a new one
        if existing_otp and not existing_otp.is_expired():
            otp = existing_otp
        else:
            # Create a new OTP for verification
            otp = OTP.generate(email=form_data.username)
            session.add(otp)
            session.commit()
        
        # Send verification email
        email_data = generate_email_verification_otp(
            email_to=form_data.username, 
            otp=otp.code,
            deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}"
        )
        send_email(
            email_to=form_data.username,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        
        raise HTTPException(
            status_code=403, 
            detail="Account not verified. A verification code has been sent to your email."
        )
    
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
    session: SessionDep, user_google: UserGoogleLogin
) -> Token:
    """
    Google login
    """
    user = crud.get_user_by_email(session=session, email=user_google.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    elif not user.is_verified:
        # Create and send a new OTP for verification since login failed due to unverified account
        otp = OTP.generate(email=user_google.email)
        session.add(otp)
        session.commit()
        
        # Send verification email
        email_data = generate_email_verification_otp(
            email_to=user_google.email, 
            otp=otp.code,
            deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}"
        )
        send_email(
            email_to=user_google.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        
        raise HTTPException(
            status_code=403, 
            detail="Account not verified. A new verification code has been sent to your email."
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
    session: SessionDep, token_request: RefreshTokenRequest
) -> Token:
    """
    Refresh access token
    """
    try:
        payload = jwt.decode(token_request.refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = crud.get_user_by_id(session=session, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    elif not user.is_verified:
        # Create and send a new OTP for verification since token refresh failed due to unverified account
        otp = OTP.generate(email=user.email)
        session.add(otp)
        session.commit()
        
        # Send verification email
        email_data = generate_email_verification_otp(
            email_to=user.email, 
            otp=otp.code,
            deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}"
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        
        raise HTTPException(
            status_code=403, 
            detail="Account not verified. A new verification code has been sent to your email."
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
    invite_code: str | None = None,
    inviter_id: str | None = None
) -> Message:
    """
    Register a new user with optional invite logic
    """
    user = crud.get_user_by_email(session=session, email=user_create.email)
    if user:
        raise HTTPException(
            status_code=409,
            detail="The user with this email already exists in the system.",
        )
    
    # If invited, validate the invitation code
    if invite_code and inviter_id:
        # Find the invitation
        statement = (
            select(Invitation)
            .where(Invitation.code == invite_code)
            .where(Invitation.inviter_id == UUID(inviter_id))  # Changed from uuid.UUID to UUID
        )
        invitation = session.exec(statement).first()
        
        if not invitation:
            raise HTTPException(status_code=404, detail="Invalid invitation code")
        
        if invitation.is_used:
            raise HTTPException(status_code=400, detail="Invitation code already used")
        
        if invitation.is_expired():
            raise HTTPException(status_code=400, detail="Invitation code has expired")
        
        # Mark invitation as used using the consume method
        invitation.consume()
        session.add(invitation)
        
        # Add bonus credits for invited user
        user_create.credit = 30

    # Create the new user
    new_user = crud.create_user(session=session, user_create=user_create)

    # Give credits to inviter if invitation is valid
    if invite_code and inviter_id:
        inviter_user = crud.get_user_by_id(session=session, user_id=inviter_id)
        if inviter_user:
            inviter_user.credit += 20
            session.add(inviter_user)
    
    # Create and send OTP for email verification
    otp = OTP.generate(email=user_create.email)
    session.add(otp)
    session.commit()
    
    # Send verification email
    email_data = generate_email_verification_otp(
        email_to=user_create.email, 
        otp=otp.code,
        deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}"
    )
    send_email(
        email_to=user_create.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return Message(message="Registration successful. Please verify your email address.")

@router.post("/register-google")
def google_register(
    session: SessionDep,
    user_google: UserGoogleRegister,
    invite_code: str | None = None,
    inviter_id: str | None = None
) -> Message:
    """
    Google register
    """
    user = crud.get_user_by_google_id(session=session, google_id=user_google.google_id)
    if user:
        raise HTTPException(
            status_code=409,
            detail="The user with this email already exists in the system.",
        )
    
    # If invited, validate the invitation code
    if invite_code and inviter_id:
        # Find the invitation
        statement = (
            select(Invitation)
            .where(Invitation.code == invite_code)
            .where(Invitation.inviter_id == UUID(inviter_id))  # Changed from uuid.UUID to UUID
        )
        invitation = session.exec(statement).first()
        
        if not invitation:
            raise HTTPException(status_code=404, detail="Invalid invitation code")
        
        if invitation.is_used:
            raise HTTPException(status_code=400, detail="Invitation code already used")
        
        if invitation.is_expired():
            raise HTTPException(status_code=400, detail="Invitation code has expired")
        
        # Mark invitation as used using the consume method
        invitation.consume()
        session.add(invitation)
        
        # Add bonus credits for invited user 
        user_google.credit = 30

    # Create the new user
    new_user = crud.create_user(session=session, user_google=user_google)

    # Give credits to inviter if invitation is valid
    if invite_code and inviter_id:
        inviter_user = crud.get_user_by_id(session=session, user_id=inviter_id)
        if inviter_user:
            inviter_user.credit += 20  # Make sure the field name is consistent
            session.add(inviter_user)
    
    # Create and send OTP for email verification
    otp = OTP.generate(email=user_google.email)
    session.add(otp)
    session.commit()
    
    # Send verification email
    email_data = generate_email_verification_otp(
        email_to=user_google.email, 
        otp=otp.code,
        deeplink=f"https://assistlyai.space/doctor/verify/{otp.code}"
    )
    send_email(
        email_to=user_google.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return Message(message="Registration successful. Please verify your email address.")

@router.post("/verify-email", response_model=OTPResponse)
def verify_email(session: SessionDep, verification_data: OTPVerify) -> OTPResponse:
    """
    Verify email using OTP
    """
    # Get the latest OTP for this email
    statement = (
        select(OTP)
        .where(OTP.email == verification_data.email)
        .order_by(OTP.created_at.desc())
    )
    otp_record = session.exec(statement).first()
    
    if not otp_record:
        raise HTTPException(status_code=404, detail="No verification code found for this email")
    
    if otp_record.is_expired():
        raise HTTPException(status_code=400, detail="Verification code has expired")
    
    if otp_record.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
    
    if otp_record.code != verification_data.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Mark OTP as verified
    otp_record.is_verified = True
    session.add(otp_record)
    
    # Mark user as verified
    user = crud.get_user_by_email(session=session, email=verification_data.email)
    if user:
        user.is_verified = True
        session.add(user)
    
    # Ensure changes are committed to the database
    session.commit()
    
    return OTPResponse(
        message="Email successfully verified", 
        expires_at=otp_record.expires_at
    )

@router.post("/renew-otp")
def renew_otp(session: SessionDep, renew: RenewOTP) -> Message:
    """
    Renew OTP code, delete the previous one, generate a new one, and send an email to the user
    """
    user = crud.get_user_by_email(session=session, email=renew.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If user is already verified, don't create a new OTP
    if user.is_verified:
        return Message(message="Your account is already verified. You can log in directly.")
    
    # Delete previous OTPs
    statement = select(OTP).where(OTP.email == renew.email)
    otps = session.exec(statement).all()
    for otp in otps:
        session.delete(otp)
    
    # Generate new OTP
    new_otp = OTP.generate(email=renew.email)
    session.add(new_otp)
    session.commit()
    
    # Send verification email
    email_data = generate_email_verification_otp(
        email_to=renew.email, 
        otp=new_otp.code,
        deeplink=f"https://assistlyai.space/doctor/verify/{new_otp.code}"
    )
    send_email(
        email_to=renew.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    
    return Message(message="New OTP generated and sent to your email")

@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token,
        deeplink=f"https://assistlyai.space/doctor/reset-password/{password_reset_token}"
    )
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Password recovery email sent")


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    hashed_password = get_password_hash(password=body.new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    return Message(message="Password updated successfully")

@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token,
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
) -> Any:
    """
    Invite a friend to register on the platform
    """
    # Check if the user is already registered
    invited_user = crud.get_user_by_email(session=session, email=invite_create.email_to)
    if invited_user:
        raise HTTPException(
            status_code=409,
            detail="The invited user with this email already exists in the system.",
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
    
    # Send invitation email
    email_data = generate_invite_friend_email(
        email_to=invite_create.email_to,
        username=current_user.email,
        inviter_name=current_user.email,
        deeplink=deeplink
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
) -> Any:
    """
    Get all invitations sent by a user.
    """
    # Ensure the user can only see their own invitations unless they're an admin
    if str(current_user.id) != str(user_id) and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
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
