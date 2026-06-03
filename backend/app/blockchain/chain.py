"""
Chain manager for the lightweight private blockchain.

Manages the full lifecycle of the blockchain:
  - Genesis block creation and initialization
  - Block appending with automatic previous_hash linking
  - Full-chain integrity validation
  - Epoch-based Merkle root computation
  - Block querying by index, event type, device, and time range

Design rationale:
    This is a *private, permissioned, single-node* blockchain designed for
    IoT audit trails — NOT a distributed consensus chain. The chain provides:
      1. Tamper-evidence via SHA-256 hash chaining
      2. Temporal ordering via strictly sequential indices
      3. Non-repudiation via ECC signatures on data hashes
      4. Rich queryability via the enriched 14-field block schema

    The single-node design is intentional for lightweight IoT deployments
    where the primary threat model is post-hoc tampering of audit logs,
    not Byzantine fault tolerance.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.block import (
    BlockData,
    compute_block_hash,
    compute_data_hash,
    compute_merkle_root,
    create_genesis_block,
)
from app.core.enums import (
    AttackClassification,
    BlockEventType,
    RiskLevel,
    SecuritySeverity,
)
from app.core.exceptions import BlockValidationError, ChainIntegrityError
from app.models.blockchain import BlockchainBlock

logger = logging.getLogger(__name__)


class BlockchainManager:
    """
    Manages the lightweight private blockchain.

    Thread-safety: Each call receives its own AsyncSession, so concurrent
    appends are serialized by the database's transaction isolation.

    Usage:
        manager = BlockchainManager()
        await manager.initialize_chain(db)
        block = await manager.add_block(db, event_type=..., data_hash=..., ...)
    """

    # ── Initialization ────────────────────────────────────────────────────

    @staticmethod
    async def initialize_chain(db: AsyncSession) -> BlockchainBlock:
        """
        Initialize the blockchain with a genesis block if the chain is empty.

        This is idempotent: if the genesis block already exists, it is
        returned without modification.

        Returns:
            The genesis BlockchainBlock ORM object.
        """
        # Check if chain already exists
        stmt = select(BlockchainBlock).where(BlockchainBlock.index == 0)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info("Blockchain already initialized (genesis block exists)")
            return existing

        # Create genesis
        genesis_data = create_genesis_block()
        genesis_hash = compute_block_hash(genesis_data)

        genesis_block = BlockchainBlock(
            index=genesis_data.index,
            previous_hash=genesis_data.previous_hash,
            timestamp=genesis_data.timestamp,
            device_id=genesis_data.device_id,
            event_type=genesis_data.event_type,
            data_hash=genesis_data.data_hash,
            signature=genesis_data.signature,
            trust_score_snapshot=genesis_data.trust_score_snapshot,
            risk_level=genesis_data.risk_level,
            attack_classification=genesis_data.attack_classification,
            security_severity=genesis_data.security_severity,
            event_metadata=genesis_data.event_metadata,
            nonce_value=genesis_data.nonce_value,
            current_hash=genesis_hash,
        )

        db.add(genesis_block)
        await db.commit()
        await db.refresh(genesis_block)

        logger.info("Blockchain initialized with genesis block (hash=%s)", genesis_hash[:16])
        return genesis_block

    # ── Block Appending ───────────────────────────────────────────────────

    @staticmethod
    async def add_block(
        db: AsyncSession,
        event_type: BlockEventType,
        data_hash: str,
        signature: str,
        device_id: uuid.UUID | None = None,
        trust_score_snapshot: float = 100.0,
        risk_level: RiskLevel = RiskLevel.NONE,
        attack_classification: AttackClassification = AttackClassification.NONE,
        security_severity: SecuritySeverity = SecuritySeverity.INFO,
        event_metadata: dict[str, Any] | None = None,
    ) -> BlockchainBlock:
        """
        Append a new block to the chain.

        Automatically:
          - Determines the next index
          - Links to the previous block's hash
          - Computes the new block's SHA-256 hash
          - Persists to the database

        Args:
            db: Database session.
            event_type: Category of the event being recorded.
            data_hash: SHA-256 of the event payload.
            signature: ECC signature over data_hash.
            device_id: Source device UUID (None for system events).
            trust_score_snapshot: Device trust score at event time.
            risk_level: Assessed risk level.
            attack_classification: Attack type label.
            security_severity: 5-tier severity.
            event_metadata: Structured context payload.

        Returns:
            The newly created BlockchainBlock ORM object.
        """
        if event_metadata is None:
            event_metadata = {}

        # Get the latest block to link the chain
        stmt = select(BlockchainBlock).order_by(BlockchainBlock.index.desc()).limit(1)
        result = await db.execute(stmt)
        latest_block = result.scalar_one_or_none()

        if not latest_block:
            # Chain not initialized — initialize it first
            latest_block = await BlockchainManager.initialize_chain(db)

        # Construct the new block data
        new_index = latest_block.index + 1
        now = datetime.now(timezone.utc)

        block_data = BlockData(
            index=new_index,
            previous_hash=latest_block.current_hash,
            timestamp=now,
            device_id=device_id,
            event_type=event_type,
            data_hash=data_hash,
            signature=signature,
            trust_score_snapshot=trust_score_snapshot,
            risk_level=risk_level,
            attack_classification=attack_classification,
            security_severity=security_severity,
            event_metadata=event_metadata,
            nonce_value=0,
        )

        # Compute hash
        current_hash = compute_block_hash(block_data)

        # Create ORM object
        new_block = BlockchainBlock(
            index=new_index,
            previous_hash=latest_block.current_hash,
            timestamp=now,
            device_id=device_id,
            event_type=event_type,
            data_hash=data_hash,
            signature=signature,
            trust_score_snapshot=trust_score_snapshot,
            risk_level=risk_level,
            attack_classification=attack_classification,
            security_severity=security_severity,
            event_metadata=event_metadata,
            nonce_value=0,
            current_hash=current_hash,
        )

        db.add(new_block)
        await db.commit()
        await db.refresh(new_block)

        logger.info(
            "Block #%d added (event=%s, severity=%s, hash=%s)",
            new_index,
            event_type.value,
            security_severity.value,
            current_hash[:16],
        )

        return new_block

    # ── Chain Validation ──────────────────────────────────────────────────

    @staticmethod
    async def validate_chain(db: AsyncSession) -> dict[str, Any]:
        """
        Validate the integrity of the entire blockchain.

        Checks:
          1. Genesis block has correct previous_hash (all zeros).
          2. Each block's current_hash matches its recomputed hash.
          3. Each block's previous_hash matches the preceding block's current_hash.
          4. Indices are strictly sequential with no gaps.

        Returns:
            A validation report dictionary:
            {
                "is_valid": bool,
                "total_blocks": int,
                "blocks_validated": int,
                "errors": [{"block_index": int, "error": str}, ...],
                "merkle_root": str,
                "validated_at": str,
            }

        Raises:
            ChainIntegrityError: If critical integrity violations are found
                and raise_on_error=True.
        """
        stmt = select(BlockchainBlock).order_by(BlockchainBlock.index.asc())
        result = await db.execute(stmt)
        blocks = list(result.scalars().all())

        if not blocks:
            return {
                "is_valid": True,
                "total_blocks": 0,
                "blocks_validated": 0,
                "errors": [],
                "merkle_root": None,
                "validated_at": datetime.now(timezone.utc).isoformat(),
            }

        errors = []
        all_hashes = []

        for i, block in enumerate(blocks):
            # Reconstruct BlockData from ORM object
            block_data = BlockData(
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

            recomputed_hash = compute_block_hash(block_data)

            # Check 1: Genesis block validation
            if i == 0:
                if block.index != 0:
                    errors.append({
                        "block_index": block.index,
                        "error": f"First block has index {block.index}, expected 0",
                    })
                if block.previous_hash != "0" * 64:
                    errors.append({
                        "block_index": block.index,
                        "error": "Genesis block has non-zero previous_hash",
                    })

            # Check 2: Hash integrity
            if block.current_hash != recomputed_hash:
                errors.append({
                    "block_index": block.index,
                    "error": (
                        f"Hash mismatch: stored={block.current_hash[:16]}..., "
                        f"computed={recomputed_hash[:16]}..."
                    ),
                })

            # Check 3: Chain linkage (skip genesis)
            if i > 0:
                prev_block = blocks[i - 1]
                if block.previous_hash != prev_block.current_hash:
                    errors.append({
                        "block_index": block.index,
                        "error": (
                            f"Chain break: previous_hash does not match "
                            f"block #{prev_block.index} current_hash"
                        ),
                    })

                # Check 4: Sequential indices
                if block.index != prev_block.index + 1:
                    errors.append({
                        "block_index": block.index,
                        "error": (
                            f"Index gap: expected {prev_block.index + 1}, "
                            f"got {block.index}"
                        ),
                    })

            all_hashes.append(block.current_hash)

        # Compute Merkle root of all block hashes
        merkle = compute_merkle_root(all_hashes)

        report = {
            "is_valid": len(errors) == 0,
            "total_blocks": len(blocks),
            "blocks_validated": len(blocks),
            "errors": errors,
            "merkle_root": merkle,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

        if errors:
            logger.warning(
                "Chain validation FAILED: %d errors in %d blocks",
                len(errors),
                len(blocks),
            )
        else:
            logger.info(
                "Chain validation PASSED: %d blocks, merkle=%s",
                len(blocks),
                merkle[:16],
            )

        return report

    # ── Querying ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_block(db: AsyncSession, index: int) -> BlockchainBlock | None:
        """Get a single block by index."""
        stmt = select(BlockchainBlock).where(BlockchainBlock.index == index)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_latest_block(db: AsyncSession) -> BlockchainBlock | None:
        """Get the most recent block in the chain."""
        stmt = select(BlockchainBlock).order_by(BlockchainBlock.index.desc()).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_chain_length(db: AsyncSession) -> int:
        """Get the total number of blocks in the chain."""
        stmt = select(func.count()).select_from(BlockchainBlock)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def get_blocks_by_device(
        db: AsyncSession, device_id: uuid.UUID, limit: int = 50
    ) -> list[BlockchainBlock]:
        """Get all blocks associated with a specific device."""
        stmt = (
            select(BlockchainBlock)
            .where(BlockchainBlock.device_id == device_id)
            .order_by(BlockchainBlock.index.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_blocks_by_event_type(
        db: AsyncSession, event_type: BlockEventType, limit: int = 50
    ) -> list[BlockchainBlock]:
        """Get blocks filtered by event type."""
        stmt = (
            select(BlockchainBlock)
            .where(BlockchainBlock.event_type == event_type.value)
            .order_by(BlockchainBlock.index.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_blocks_by_severity(
        db: AsyncSession, severity: SecuritySeverity, limit: int = 50
    ) -> list[BlockchainBlock]:
        """Get blocks filtered by security severity."""
        stmt = (
            select(BlockchainBlock)
            .where(BlockchainBlock.security_severity == severity.value)
            .order_by(BlockchainBlock.index.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_blocks_in_range(
        db: AsyncSession,
        start_index: int,
        end_index: int,
    ) -> list[BlockchainBlock]:
        """Get blocks within an index range (inclusive)."""
        stmt = (
            select(BlockchainBlock)
            .where(
                BlockchainBlock.index >= start_index,
                BlockchainBlock.index <= end_index,
            )
            .order_by(BlockchainBlock.index.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def compute_epoch_merkle_root(
        db: AsyncSession,
        start_index: int,
        end_index: int,
    ) -> str:
        """
        Compute the Merkle root for a range of blocks (an "epoch").

        This is useful for:
          - Periodic integrity snapshots
          - Lightweight verification by IoT devices
          - Cross-referencing with external audit systems
        """
        blocks = await BlockchainManager.get_blocks_in_range(db, start_index, end_index)
        hashes = [block.current_hash for block in blocks]
        return compute_merkle_root(hashes)

    @staticmethod
    async def get_chain_statistics(db: AsyncSession) -> dict[str, Any]:
        """
        Compute comprehensive chain statistics for research analysis.

        Returns counts by event type, severity distribution, attack
        classification distribution, and average trust score over time.
        """
        blocks = await BlockchainManager.get_blocks_in_range(db, 0, 999999)

        if not blocks:
            return {"total_blocks": 0}

        # Event type distribution
        event_dist: dict[str, int] = {}
        severity_dist: dict[str, int] = {}
        attack_dist: dict[str, int] = {}
        trust_scores: list[float] = []

        for block in blocks:
            et = block.event_type if isinstance(block.event_type, str) else block.event_type.value
            event_dist[et] = event_dist.get(et, 0) + 1

            sv = block.security_severity if isinstance(block.security_severity, str) else block.security_severity.value
            severity_dist[sv] = severity_dist.get(sv, 0) + 1

            ac = block.attack_classification if isinstance(block.attack_classification, str) else block.attack_classification.value
            attack_dist[ac] = attack_dist.get(ac, 0) + 1

            trust_scores.append(block.trust_score_snapshot)

        avg_trust = sum(trust_scores) / len(trust_scores) if trust_scores else 0.0

        return {
            "total_blocks": len(blocks),
            "first_block_time": blocks[0].timestamp.isoformat() if blocks else None,
            "last_block_time": blocks[-1].timestamp.isoformat() if blocks else None,
            "event_type_distribution": event_dist,
            "severity_distribution": severity_dist,
            "attack_classification_distribution": attack_dist,
            "average_trust_score": round(avg_trust, 4),
            "min_trust_score": round(min(trust_scores), 4) if trust_scores else None,
            "max_trust_score": round(max(trust_scores), 4) if trust_scores else None,
        }
