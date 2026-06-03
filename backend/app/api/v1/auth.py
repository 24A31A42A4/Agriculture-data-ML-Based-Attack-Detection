"""Authentication API endpoints."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DbSession
from app.config import get_settings
from app.core.exceptions import AuthenticationError
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.security.jwt import create_access_token, create_refresh_token
from app.security.password import verify_password
from app.services.user_service import UserService

router = APIRouter()


@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: DbSession, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await UserService.get_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthenticationError("Incorrect email or password")
    elif not user.is_active:
        raise AuthenticationError("Inactive user")

    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    access_token = create_access_token(
        subject=user.id, role=user.role, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(subject=user.id)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/register", response_model=UserResponse)
async def register_user(db: DbSession, user_in: UserCreate) -> User:
    """
    Register a new user.
    """
    user = await UserService.get_by_email(db, email=user_in.email)
    if user:
        raise AuthenticationError("User with this email already exists")
        
    user = await UserService.create(db, obj_in=user_in)
    return user


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: CurrentUser) -> User:
    """
    Get current user profile.
    """
    return current_user
