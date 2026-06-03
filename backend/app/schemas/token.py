"""Token Pydantic schemas for authentication responses."""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer")


class TokenPayload(BaseModel):
    """JWT token payload (claims)."""
    sub: str | None = None  # Subject (user ID)
    exp: int | None = None  # Expiration time
    role: str | None = None # User role
