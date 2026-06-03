"""BlockchainBlock ORM model — enriched lightweight blockchain."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    AttackClassification,
    BlockEventType,
    RiskLevel,
    SecuritySeverity,
)
from app.models.base import Base, JSONVariant


class BlockchainBlock(Base):
    """
    Enriched blockchain block with 14 fields.

    Each block stores security context (trust snapshot, risk level, attack
    classification, severity) alongside the standard chain linkage fields.
    """

    __tablename__ = "blockchain_blocks"

    # ── Chain linkage ────────────────────────────────────────────────────
    index: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # ── Temporal ─────────────────────────────────────────────────────────
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Source ───────────────────────────────────────────────────────────
    device_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)

    # ── Event context ────────────────────────────────────────────────────
    event_type: Mapped[BlockEventType] = mapped_column(
        String(50), nullable=False, index=True
    )

    # ── Data integrity ───────────────────────────────────────────────────
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Security context ─────────────────────────────────────────────────
    trust_score_snapshot: Mapped[float] = mapped_column(
        Float, nullable=False, default=100.0
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        String(20), nullable=False, default=RiskLevel.NONE
    )
    attack_classification: Mapped[AttackClassification] = mapped_column(
        String(30), nullable=False, default=AttackClassification.NONE
    )
    security_severity: Mapped[SecuritySeverity] = mapped_column(
        String(20), nullable=False, default=SecuritySeverity.INFO
    )

    # ── Metadata ─────────────────────────────────────────────────────────
    event_metadata: Mapped[dict] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )

    # ── Block integrity ──────────────────────────────────────────────────
    nonce_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # ── Timestamp ────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<Block(#{self.index}, event={self.event_type!r}, "
            f"severity={self.security_severity!r})>"
        )
