"""DeviceHealth ORM model — composite device health monitoring."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class DeviceHealth(Base):
    """
    Device health metrics — one row per device, updated in-place.

    Composite health score = weighted combination of:
        40% auth success rate
        30% trust score
        20% trust trend
        10% recency
    """

    __tablename__ = "device_health"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id"), unique=True, nullable=False, index=True
    )

    # ── Authentication metrics ───────────────────────────────────────────
    total_auth_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auth_successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auth_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auth_success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    auth_failure_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Trust trend ──────────────────────────────────────────────────────
    trust_trend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # ── Composite health ─────────────────────────────────────────────────
    health_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)

    # ── Timestamps ───────────────────────────────────────────────────────
    last_successful_auth: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failed_auth: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    device = relationship("Device", back_populates="health")

    def __repr__(self) -> str:
        return (
            f"<DeviceHealth(health={self.health_score:.1f}, "
            f"auth_rate={self.auth_success_rate:.2%})>"
        )
