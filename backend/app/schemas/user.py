"""User Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import UserRole


# ── Shared Base ──────────────────────────────────────────────────────────────
class UserBase(BaseModel):
    """Shared user attributes."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = Field(default=UserRole.FARMER)


# ── Create ───────────────────────────────────────────────────────────────────
class UserCreate(UserBase):
    """Properties to receive via API on creation."""
    password: str = Field(..., min_length=8, max_length=128)


# ── Update ───────────────────────────────────────────────────────────────────
class UserUpdate(BaseModel):
    """Properties to receive via API on update."""
    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=2, max_length=100)
    password: str | None = Field(None, min_length=8, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None


# ── Response ─────────────────────────────────────────────────────────────────
class UserResponse(UserBase):
    """Properties to return via API."""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
