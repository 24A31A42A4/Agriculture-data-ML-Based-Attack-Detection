"""SensorData ORM model — encrypted and verified sensor readings."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONVariant, generate_uuid


class SensorData(Base):
    """
    Ingested sensor data record.

    Each record stores both the encrypted payload and the raw data (after
    successful decryption and verification). ML predictions are attached
    inline for traceability.
    """

    __tablename__ = "sensor_data"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id"), nullable=False, index=True
    )

    # ── Data ─────────────────────────────────────────────────────────────
    raw_data: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Integrity ────────────────────────────────────────────────────────
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[str] = mapped_column(String(100), nullable=False)
    sensor_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    integrity_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # ── ML prediction ────────────────────────────────────────────────────
    is_attack: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    attack_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_by_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Blockchain linkage ───────────────────────────────────────────────
    blockchain_block_index: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("blockchain_blocks.index"), nullable=True
    )

    # ── Timestamp ────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    device = relationship("Device", back_populates="sensor_data")

    def __repr__(self) -> str:
        status = "attack" if self.is_attack else "normal"
        return f"<SensorData(device={self.device_id}, {status})>"
