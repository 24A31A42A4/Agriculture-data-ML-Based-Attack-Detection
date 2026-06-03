"""DeviceKey ORM model — ECC key management with rotation and revocation."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class DeviceKey(Base):
    """
    ECC key pair metadata for a device.

    - Public key stored in PEM format (database).
    - Private key stored as AES-256-encrypted file (key vault, referenced by path).
    - Key fingerprint = SHA-256 of DER-encoded public key.
    - Only one active key per device at any time.
    """

    __tablename__ = "device_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id"), nullable=False, index=True
    )

    # ── Key material ─────────────────────────────────────────────────────
    ecc_public_key: Mapped[str] = mapped_column(
        Text, nullable=False, comment="PEM-encoded SECP256R1 public key"
    )
    key_fingerprint: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
        comment="SHA-256 hex digest of DER-encoded public key"
    )
    private_key_vault_path: Mapped[str] = mapped_column(
        String(500), nullable=False,
        comment="Relative path inside key_vault/ directory"
    )

    # ── Versioning ───────────────────────────────────────────────────────
    key_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # ── Lifecycle ────────────────────────────────────────────────────────
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    device = relationship("Device", back_populates="keys")

    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return (
            f"<DeviceKey(fingerprint={self.key_fingerprint[:16]}..., "
            f"v{self.key_version}, {status})>"
        )
