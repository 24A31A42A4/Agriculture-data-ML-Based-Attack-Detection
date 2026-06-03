"""Device and DeviceKey Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress

from app.core.enums import DeviceLifecycleStatus, DeviceType


# ── Shared Base ──────────────────────────────────────────────────────────────
class DeviceBase(BaseModel):
    """Shared device attributes."""
    device_id: str = Field(..., max_length=100)
    device_name: str = Field(..., min_length=2, max_length=255)
    device_type: DeviceType = Field(default=DeviceType.SOIL_MOISTURE)


# ── Create ───────────────────────────────────────────────────────────────────
class DeviceCreate(DeviceBase):
    """Properties to receive via API on creation."""
    pass


# ── Update ───────────────────────────────────────────────────────────────────
class DeviceUpdate(BaseModel):
    """Properties to receive via API on update."""
    device_name: str | None = Field(None, min_length=2, max_length=255)
    lifecycle_status: DeviceLifecycleStatus | None = None
    is_whitelisted: bool | None = None


# ── Response ─────────────────────────────────────────────────────────────────
class DeviceResponse(DeviceBase):
    """Properties to return via API."""
    id: uuid.UUID
    lifecycle_status: DeviceLifecycleStatus
    is_whitelisted: bool
    trust_score: float
    registered_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Device Key Schemas ───────────────────────────────────────────────────────
class DeviceKeyCreate(BaseModel):
    """Properties to receive for registering a device public key."""
    public_key_pem: str = Field(..., description="ECC secp256r1 public key in PEM format")


class DeviceKeyResponse(BaseModel):
    """Properties to return for device keys."""
    id: uuid.UUID
    device_id: str
    public_key_pem: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
