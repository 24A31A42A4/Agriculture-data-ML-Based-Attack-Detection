"""Pydantic schemas for audit log API requests and responses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import AuditEventType, SecuritySeverity


class AuditLogResponse(BaseModel):
    """Response schema for an audit log entry."""

    id: uuid.UUID
    event_type: str
    severity: str
    device_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    source_ip: str | None = None
    event_details: dict[str, Any]
    blockchain_block_index: int | None = None
    correlation_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditEventCreate(BaseModel):
    """Schema for manually creating an audit event (admin use)."""

    event_type: AuditEventType
    device_id: uuid.UUID | None = None
    source_ip: str | None = None
    event_details: dict[str, Any] = {}
    correlation_id: str | None = None
