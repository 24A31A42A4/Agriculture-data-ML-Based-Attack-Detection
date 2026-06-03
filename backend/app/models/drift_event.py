"""DriftEvent ORM model — feature drift monitoring records."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import SecuritySeverity
from app.models.base import Base, JSONVariant, generate_uuid


class DriftEvent(Base):
    """
    Records feature distribution drift detected by the drift monitor.

    Each event compares a single feature's live distribution against
    the training reference distribution using PSI and KS-test.
    """

    __tablename__ = "drift_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    psi_score: Mapped[float] = mapped_column(Float, nullable=False)
    ks_statistic: Mapped[float] = mapped_column(Float, nullable=False)
    ks_p_value: Mapped[float] = mapped_column(Float, nullable=False)
    drift_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    severity: Mapped[SecuritySeverity] = mapped_column(
        String(20), nullable=False, default=SecuritySeverity.INFO
    )
    reference_distribution: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    current_distribution: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    blockchain_block_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        status = "DRIFT" if self.drift_detected else "stable"
        return f"<DriftEvent(feature={self.feature_name!r}, PSI={self.psi_score:.4f}, {status})>"
