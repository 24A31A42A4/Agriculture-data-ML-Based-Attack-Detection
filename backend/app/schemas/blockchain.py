"""Pydantic schemas for blockchain API requests and responses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    AttackClassification,
    BlockEventType,
    RiskLevel,
    SecuritySeverity,
)


class BlockResponse(BaseModel):
    """Response schema for a single blockchain block."""

    index: int
    previous_hash: str
    timestamp: datetime
    device_id: uuid.UUID | None = None
    event_type: str
    data_hash: str
    signature: str
    trust_score_snapshot: float
    risk_level: str
    attack_classification: str
    security_severity: str
    event_metadata: dict[str, Any]
    nonce_value: int
    current_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChainValidationResponse(BaseModel):
    """Response schema for chain validation results."""

    is_valid: bool
    total_blocks: int
    blocks_validated: int
    errors: list[dict[str, Any]]
    merkle_root: str | None
    validated_at: str


class ChainStatisticsResponse(BaseModel):
    """Response schema for blockchain statistics."""

    total_blocks: int
    first_block_time: str | None = None
    last_block_time: str | None = None
    event_type_distribution: dict[str, int] = {}
    severity_distribution: dict[str, int] = {}
    attack_classification_distribution: dict[str, int] = {}
    average_trust_score: float = 0.0
    min_trust_score: float | None = None
    max_trust_score: float | None = None


class EpochMerkleRequest(BaseModel):
    """Request schema for computing epoch Merkle roots."""

    start_index: int = Field(..., ge=0, description="Start block index (inclusive)")
    end_index: int = Field(..., ge=0, description="End block index (inclusive)")


class EpochMerkleResponse(BaseModel):
    """Response schema for epoch Merkle root computation."""

    start_index: int
    end_index: int
    merkle_root: str
    block_count: int


class BlockIntegrityResponse(BaseModel):
    """Response schema for single-block integrity validation."""

    block_index: int
    is_valid: bool
    stored_hash: str
    computed_hash: str
    error: str | None = None
