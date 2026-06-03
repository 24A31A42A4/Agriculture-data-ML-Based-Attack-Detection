from datetime import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict


class SensorDataIngest(BaseModel):
    """Payload received from the IoT device."""
    encrypted_payload: str
    data_hash: str


class SensorDataResponse(BaseModel):
    """Response returned to the dashboard."""
    id: uuid.UUID
    device_id: uuid.UUID
    raw_data: dict[str, Any] | None = None
    sensor_timestamp: datetime
    integrity_verified: bool
    is_attack: bool | None = None
    attack_probability: float | None = None
    predicted_by_model: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
