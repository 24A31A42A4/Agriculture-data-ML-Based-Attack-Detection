"""Pydantic schemas for trust API requests and responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrustEventResponse(BaseModel):
    """Response schema for a trust event."""

    id: uuid.UUID
    device_id: uuid.UUID
    event_type: str
    score_before: float
    score_change: float
    score_after: float
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrustScoreResponse(BaseModel):
    """Response schema for a device's current trust score."""

    device_id: uuid.UUID
    trust_score: float
    risk_level: str
    last_updated: datetime | None = None


class TrustAnalyticsResponse(BaseModel):
    """Response schema for system-wide trust analytics."""

    average_trust_score: float
    device_count: int
    risk_distribution: dict[str, int]
    recent_events_count: int
