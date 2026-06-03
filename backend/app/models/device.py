"""Device ORM model — lifecycle-managed IoT device registry."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DeviceLifecycleStatus, DeviceType
from app.models.base import Base, TimestampMixin, generate_uuid


class Device(Base, TimestampMixin):
    """
    IoT device with 5-state lifecycle management.

    Lifecycle: registered → active → suspended → revoked → recovered → active
    """

    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    device_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(String(50), nullable=False)

    # ── Lifecycle ────────────────────────────────────────────────────────
    lifecycle_status: Mapped[DeviceLifecycleStatus] = mapped_column(
        String(50), nullable=False, default=DeviceLifecycleStatus.REGISTERED
    )
    is_whitelisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Trust ────────────────────────────────────────────────────────────
    trust_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)

    # ── Ownership ────────────────────────────────────────────────────────
    registered_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )

    # ── Lifecycle timestamps ─────────────────────────────────────────────
    suspension_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────
    registered_by_user = relationship("User", back_populates="devices")
    keys = relationship("DeviceKey", back_populates="device", lazy="selectin")
    health = relationship(
        "DeviceHealth", back_populates="device", uselist=False, lazy="selectin"
    )
    sensor_data = relationship("SensorData", back_populates="device", lazy="noload")
    trust_events = relationship("TrustEvent", back_populates="device", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<Device(device_id={self.device_id!r}, "
            f"status={self.lifecycle_status!r}, "
            f"trust={self.trust_score:.1f})>"
        )
