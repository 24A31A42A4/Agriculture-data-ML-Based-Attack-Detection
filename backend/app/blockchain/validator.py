"""
Block-level integrity validator with configurable proof-of-work.

Provides standalone validation functions that can be used independently
of the chain manager for:
  - Single-block integrity checks
  - Proof-of-work verification (for future consensus extensions)
  - Block comparison and diff computation

Research context:
    The proof-of-work implementation uses a configurable difficulty parameter
    that can be tuned for IoT resource constraints. For agricultural sensor
    networks, difficulty=0 (no proof-of-work) is the default since the chain
    is private and the trust model relies on ECC signatures rather than
    computational puzzles. The PoW machinery is included for benchmarking
    purposes — measuring how computational overhead scales with difficulty
    provides data for the research evaluation chapter.
"""

import hashlib
import json
import logging
from typing import Any

from app.blockchain.block import BlockData, compute_block_hash
from app.core.enums import (
    AttackClassification,
    BlockEventType,
    RiskLevel,
    SecuritySeverity,
)
from app.models.blockchain import BlockchainBlock

logger = logging.getLogger(__name__)


def validate_block_integrity(block: BlockchainBlock) -> dict[str, Any]:
    """
    Validate the integrity of a single block by recomputing its hash.

    Returns:
        {
            "block_index": int,
            "is_valid": bool,
            "stored_hash": str,
            "computed_hash": str,
            "error": str | None,
        }
    """
    block_data = _orm_to_block_data(block)
    recomputed = compute_block_hash(block_data)

    is_valid = block.current_hash == recomputed
    return {
        "block_index": block.index,
        "is_valid": is_valid,
        "stored_hash": block.current_hash,
        "computed_hash": recomputed,
        "error": None if is_valid else "Hash mismatch — block may be tampered",
    }


def validate_block_linkage(
    block: BlockchainBlock, previous_block: BlockchainBlock
) -> dict[str, Any]:
    """
    Validate that a block correctly links to its predecessor.

    Checks:
      - block.previous_hash == previous_block.current_hash
      - block.index == previous_block.index + 1

    Returns:
        Validation result dictionary.
    """
    errors = []

    if block.previous_hash != previous_block.current_hash:
        errors.append(
            f"previous_hash mismatch: expected {previous_block.current_hash[:16]}..., "
            f"got {block.previous_hash[:16]}..."
        )

    if block.index != previous_block.index + 1:
        errors.append(
            f"Index discontinuity: expected {previous_block.index + 1}, got {block.index}"
        )

    return {
        "block_index": block.index,
        "previous_index": previous_block.index,
        "is_valid": len(errors) == 0,
        "errors": errors,
    }


def mine_block(block_data: BlockData, difficulty: int = 0) -> tuple[str, int]:
    """
    Apply proof-of-work mining to a block.

    The mining process increments the nonce_value until the resulting hash
    has `difficulty` leading zeros. With difficulty=0, this returns immediately.

    This is included for benchmarking purposes — measuring mining latency
    at various difficulty levels provides data on the computational overhead
    of different consensus configurations.

    Args:
        block_data: The block to mine (nonce_value will be mutated).
        difficulty: Number of required leading zeros in the hash.

    Returns:
        Tuple of (final_hash, nonce_value).
    """
    if difficulty == 0:
        return compute_block_hash(block_data), block_data.nonce_value

    target_prefix = "0" * difficulty
    nonce = 0
    max_iterations = 10_000_000  # Safety limit for IoT devices

    while nonce < max_iterations:
        block_data.nonce_value = nonce
        hash_result = compute_block_hash(block_data)
        if hash_result.startswith(target_prefix):
            logger.info(
                "Block mined: difficulty=%d, nonce=%d, hash=%s",
                difficulty, nonce, hash_result[:16],
            )
            return hash_result, nonce
        nonce += 1

    # Fallback — return best effort (shouldn't happen in practice)
    logger.warning(
        "Mining exceeded max iterations (%d) at difficulty=%d",
        max_iterations, difficulty,
    )
    return compute_block_hash(block_data), nonce


def compute_block_diff(
    block_a: BlockchainBlock, block_b: BlockchainBlock
) -> dict[str, Any]:
    """
    Compute a diff between two blocks for forensic analysis.

    Useful for detecting exactly which fields were tampered with
    when a chain integrity violation is detected.

    Returns:
        Dictionary of field names to (value_a, value_b) tuples
        for fields that differ.
    """
    fields_to_compare = [
        "index", "previous_hash", "timestamp", "device_id",
        "event_type", "data_hash", "signature",
        "trust_score_snapshot", "risk_level", "attack_classification",
        "security_severity", "event_metadata", "nonce_value", "current_hash",
    ]

    diff = {}
    for field_name in fields_to_compare:
        val_a = getattr(block_a, field_name, None)
        val_b = getattr(block_b, field_name, None)
        if val_a != val_b:
            diff[field_name] = {"block_a": str(val_a), "block_b": str(val_b)}

    return {
        "blocks_compared": [block_a.index, block_b.index],
        "fields_differing": len(diff),
        "diffs": diff,
    }


def _orm_to_block_data(block: BlockchainBlock) -> BlockData:
    """Convert an ORM BlockchainBlock to a BlockData dataclass."""
    return BlockData(
        index=block.index,
        previous_hash=block.previous_hash,
        timestamp=block.timestamp.replace(tzinfo=timezone.utc) if block.timestamp.tzinfo is None else block.timestamp,
        device_id=block.device_id,
        event_type=BlockEventType(block.event_type) if isinstance(block.event_type, str) else block.event_type,
        data_hash=block.data_hash,
        signature=block.signature,
        trust_score_snapshot=block.trust_score_snapshot,
        risk_level=RiskLevel(block.risk_level) if isinstance(block.risk_level, str) else block.risk_level,
        attack_classification=AttackClassification(block.attack_classification) if isinstance(block.attack_classification, str) else block.attack_classification,
        security_severity=SecuritySeverity(block.security_severity) if isinstance(block.security_severity, str) else block.security_severity,
        event_metadata=block.event_metadata or {},
        nonce_value=block.nonce_value,
    )
