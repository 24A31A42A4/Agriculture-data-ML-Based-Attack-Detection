"""Pydantic schemas for the Attack Simulation API."""

from pydantic import BaseModel, ConfigDict


from typing import Any

class SimulationStep(BaseModel):
    """A single step in the detailed attack simulation trace."""
    step_name: str
    description: str
    status: str  # "success", "warning", "error", "info"
    metadata: dict[str, Any] = {}

class AttackSimResult(BaseModel):
    """Result of an attack simulation."""

    attack_type: str
    target_device_id: str | None
    was_detected: bool
    detection_layer: str  # e.g., "Gateway", "Trust Engine", "ML IDS"
    trust_score_penalty: float
    blockchain_anchored: bool
    details: str
    attack_trace: list[SimulationStep] = []

    model_config = ConfigDict(from_attributes=True)
