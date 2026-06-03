"""
Block construction and hashing for the lightweight private blockchain.

Implements the enriched 14-field BlockV2 schema with deterministic SHA-256
hash computation. The hash covers ALL fields (except current_hash itself)
in a strict, canonical order to guarantee tamper-evidence.

Research context:
    This module provides the cryptographic backbone for an immutable audit trail
    specifically designed for IoT security event logging in agricultural networks.
    The enriched block schema captures security metadata (trust snapshots, risk
    levels, attack classifications) that enables post-hoc temporal analysis of
    security posture — a key contribution of the research.

References:
    - SHA-256: FIPS PUB 180-4
    - Block structure inspired by Bitcoin's simplified block header
    - Enriched with IoT-specific security context fields
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.enums import (
    AttackClassification,
    BlockEventType,
    RiskLevel,
    SecuritySeverity,
)


@dataclass
class BlockData:
    """
    Immutable data container for block construction.

    This dataclass captures all 14 fields of the enriched BlockV2 schema
    before persisting to the database. It separates block *construction*
    from block *storage* (ORM model), following clean architecture principles.

    Attributes:
        index: Sequential block number (0 = genesis).
        previous_hash: SHA-256 hash of the preceding block.
        timestamp: UTC timestamp of block creation.
        device_id: UUID of the source device (None for system events).
        event_type: Category of the recorded event.
        data_hash: SHA-256 of the event payload being recorded.
        signature: ECC signature over data_hash for non-repudiation.
        trust_score_snapshot: Device trust score at block creation time.
        risk_level: Assessed risk level of the event.
        attack_classification: ML or rule-based attack label.
        security_severity: 5-tier severity classification.
        event_metadata: Structured JSON payload with event-specific context.
        nonce_value: Reserved for optional proof-of-work (default 0).
    """

    index: int
    previous_hash: str
    timestamp: datetime
    device_id: uuid.UUID | None
    event_type: BlockEventType
    data_hash: str
    signature: str
    trust_score_snapshot: float = 100.0
    risk_level: RiskLevel = RiskLevel.NONE
    attack_classification: AttackClassification = AttackClassification.NONE
    security_severity: SecuritySeverity = SecuritySeverity.INFO
    event_metadata: dict[str, Any] = field(default_factory=dict)
    nonce_value: int = 0


def compute_block_hash(block: BlockData) -> str:
    """
    Compute the deterministic SHA-256 hash of a block.

    The hash covers all 13 fields (everything except current_hash) in a
    strict canonical order. This ensures:
      - Tamper-evidence: any modification changes the hash.
      - Determinism: same data always produces the same hash.
      - Chain integrity: previous_hash links blocks cryptographically.

    The canonical form concatenates fields as strings with a pipe delimiter
    to prevent ambiguous concatenation attacks.

    Args:
        block: The BlockData to hash.

    Returns:
        64-character lowercase hex digest of SHA-256.
    """
    # Canonical string representation — pipe-delimited for unambiguity
    content = (
        f"{block.index}|"
        f"{block.previous_hash}|"
        f"{block.timestamp.isoformat()}|"
        f"{str(block.device_id) if block.device_id else 'SYSTEM'}|"
        f"{block.event_type.value}|"
        f"{block.data_hash}|"
        f"{block.signature}|"
        f"{block.trust_score_snapshot:.4f}|"
        f"{block.risk_level.value}|"
        f"{block.attack_classification.value}|"
        f"{block.security_severity.value}|"
        f"{json.dumps(block.event_metadata, sort_keys=True, separators=(',', ':'))}|"
        f"{block.nonce_value}"
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_data_hash(data: dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of an arbitrary event payload.

    Uses sorted keys and compact separators for deterministic output.

    Args:
        data: Dictionary to hash.

    Returns:
        64-character lowercase hex digest.
    """
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_genesis_block() -> BlockData:
    """
    Create the genesis block (index 0) for the blockchain.

    The genesis block has a zeroed previous_hash and is a SYSTEM_EVENT.
    It serves as the immutable root of the entire chain.

    Returns:
        BlockData for the genesis block with computed hash-ready fields.
    """
    return BlockData(
        index=0,
        previous_hash="0" * 64,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        device_id=None,
        event_type=BlockEventType.SYSTEM_EVENT,
        data_hash=compute_data_hash({"event": "genesis", "message": "Chain initialized"}),
        signature="GENESIS",
        trust_score_snapshot=100.0,
        risk_level=RiskLevel.NONE,
        attack_classification=AttackClassification.NONE,
        security_severity=SecuritySeverity.INFO,
        event_metadata={"event": "genesis", "message": "Chain initialized"},
        nonce_value=0,
    )


def compute_merkle_root(hashes: list[str]) -> str:
    """
    Compute the Merkle root of a list of SHA-256 hashes.

    This enables efficient verification of block subsets within an epoch.
    If the list is empty, returns a hash of an empty string.
    If the list has an odd number, the last hash is duplicated.

    Research context:
        Merkle trees allow O(log n) proof that a specific event is included
        in a set of blocks, which is useful for lightweight IoT devices that
        cannot store the full chain but need to verify specific records.

    Args:
        hashes: List of hex-encoded SHA-256 hashes.

    Returns:
        64-character hex digest of the Merkle root.
    """
    if not hashes:
        return hashlib.sha256(b"").hexdigest()

    # Work with a mutable copy
    current_level = list(hashes)

    while len(current_level) > 1:
        next_level = []
        # Duplicate last element if odd count
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            next_level.append(
                hashlib.sha256(combined.encode("utf-8")).hexdigest()
            )
        current_level = next_level

    return current_level[0]
