"""Pydantic schemas for device health API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeviceHealthResponse(BaseModel):
    """Schema for individual device health metrics."""

    device_id: uuid.UUID
    health_score: float
    total_auth_attempts: int
    auth_success_rate: float
    auth_failure_rate: float
    consecutive_failures: int
    trust_trend: float
    last_successful_auth: datetime | None = None
    last_failed_auth: datetime | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceHealthSummaryResponse(BaseModel):
    """Schema for system-wide device health summary."""

    average_health_score: float
    healthy_devices_count: int  # score >= 80
    warning_devices_count: int  # 50 <= score < 80
    degraded_devices_count: int  # score < 50
    total_devices_evaluated: int
