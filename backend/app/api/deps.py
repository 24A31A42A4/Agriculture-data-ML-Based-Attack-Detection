"""
FastAPI dependency injection for database sessions, authentication, and RBAC.

These dependencies are used across all API routers via Depends().
"""

import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db

# ── Type aliases for dependency injection ────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.config import get_settings
from app.core.enums import UserRole
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.user import User
from app.schemas.token import TokenPayload
from app.services.user_service import UserService

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().api_v1_str}/auth/login/access-token"
)

# ── Type aliases for dependency injection ────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]

async def get_current_user(
    db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    """Validate JWT token and return the current user."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        token_data = TokenPayload(**payload)
        if not token_data.sub:
            raise AuthenticationError("Token missing subject")
    except JWTError as e:
        raise AuthenticationError(f"Could not validate credentials: {str(e)}")

    user = await UserService.get(db, uuid.UUID(token_data.sub))
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("Inactive user")
        
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

def require_role(required_roles: list[UserRole]):
    """Dependency factory to restrict endpoints to specific roles."""
    def role_dependency(current_user: CurrentUser) -> User:
        if current_user.role not in required_roles:
            raise AuthorizationError(
                f"Requires one of roles: {[r.value for r in required_roles]}"
            )
        return current_user
    return role_dependency

AdminUser = Annotated[User, Depends(require_role([UserRole.ADMIN]))]
ResearcherUser = Annotated[User, Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))]
SecurityAnalystUser = Annotated[
    User, Depends(require_role([UserRole.ADMIN, UserRole.SECURITY_ANALYST]))
]
