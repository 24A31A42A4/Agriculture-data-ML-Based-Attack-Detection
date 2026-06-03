"""AuditLog ORM model — security event log with 5-tier severity."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AuditEventType, SecuritySeverity
from app.models.base import Base, JSONVariant, generate_uuid


class AuditLog(Base):
    """
    Immutable security audit log entry.

    Every security-relevant event is logged with a severity classification,
    optional device/user context, and an optional blockchain anchor.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    event_type: Mapped[AuditEventType] = mapped_column(
        String(50), nullable=False, index=True
    )
    severity: Mapped[SecuritySeverity] = mapped_column(
        String(20), nullable=False, index=True, default=SecuritySeverity.INFO
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("devices.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True, index=True
    )
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    event_details: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    blockchain_block_index: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("blockchain_blocks.index"), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(event={self.event_type!r}, severity={self.severity!r})>"
