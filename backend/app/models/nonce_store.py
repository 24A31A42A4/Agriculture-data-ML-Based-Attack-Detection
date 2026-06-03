"""NonceStore ORM model — fallback nonce storage (primary: Redis)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NonceStore(Base):
    """
    Nonce persistence for replay attack protection.
    Primary validation uses Redis; this table is a fallback/audit record.
    """

    __tablename__ = "nonce_store"

    nonce: Mapped[str] = mapped_column(String(100), primary_key=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id"), nullable=False, index=True
    )
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Nonce({self.nonce[:16]}..., used={self.used})>"
