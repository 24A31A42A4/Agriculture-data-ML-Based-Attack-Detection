"""TrustEvent ORM model — trust score change history."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import TrustEventType
from app.models.base import Base, generate_uuid


class TrustEvent(Base):
    """
    Records every trust score change for a device.

    Stores before/after scores to enable trend analysis.
    """

    __tablename__ = "trust_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id"), nullable=False, index=True
    )
    event_type: Mapped[TrustEventType] = mapped_column(String(50), nullable=False)
    score_before: Mapped[float] = mapped_column(Float, nullable=False)
    score_change: Mapped[float] = mapped_column(Float, nullable=False)
    score_after: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    device = relationship("Device", back_populates="trust_events")

    def __repr__(self) -> str:
        return (
            f"<TrustEvent(type={self.event_type!r}, "
            f"delta={self.score_change:+.1f}, after={self.score_after:.1f})>"
        )
