"""
SQLAlchemy declarative base and shared mixins.

All ORM models inherit from Base and optionally use TimestampMixin
for automatic created_at / updated_at columns.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

# Cross-database JSON type (JSONB on Postgres, JSON on SQLite)
JSONVariant = JSON().with_variant(JSONB, "postgresql")

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns.

    - created_at: Set once at row insertion (server default).
    - updated_at: Updated automatically on every UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID4 for use as a primary key default."""
    return uuid.uuid4()
