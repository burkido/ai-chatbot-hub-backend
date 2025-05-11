"""
JWT token utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings

# JWT algorithm
ALGORITHM = "HS256"


def create_access_token(subject: str | Any, application_id: str | Any, expires_delta: timedelta) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (typically user ID)
        application_id: The application ID
        expires_delta: The expiration time delta
        
    Returns:
        str: The encoded JWT token
    """
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject), "app": str(application_id)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | Any, application_id: str | Any, expires_delta: timedelta) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: The subject of the token (typically user ID)
        application_id: The application ID
        expires_delta: The expiration time delta
        
    Returns:
        str: The encoded JWT token
    """
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject), "app": str(application_id)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
