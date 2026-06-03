"""JWT generation and decoding utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError

from app.config import get_settings
from app.core.enums import UserRole
from app.core.exceptions import AuthenticationError


def create_access_token(
    subject: str | Any, role: UserRole, expires_delta: timedelta | None = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (e.g., user ID).
        role: The user's role.
        expires_delta: Optional custom expiration time.
        
    Returns:
        Encoded JWT token as a string.
    """
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    
    role_str = role.value if hasattr(role, "value") else role
    to_encode = {"exp": expire, "sub": str(subject), "role": role_str}
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: The subject of the token (e.g., user ID).
        expires_delta: Optional custom expiration time.
        
    Returns:
        Encoded JWT token as a string.
    """
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: The encoded JWT token.
        
    Returns:
        A dictionary containing the decoded payload.
        
    Raises:
        AuthenticationError: If the token is invalid or expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Could not validate credentials: {str(e)}")
