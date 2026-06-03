"""BenchmarkResult ORM model — evaluation framework results storage."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import BenchmarkType
from app.models.base import Base, JSONVariant, generate_uuid


class BenchmarkResult(Base):
    """
    Persistent storage for evaluation benchmark results.
    Grouped by run_id for batch queries.
    """

    __tablename__ = "benchmark_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    benchmark_type: Mapped[BenchmarkType] = mapped_column(
        String(20), nullable=False, index=True
    )
    benchmark_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONVariant, nullable=False, default=dict
    )
    run_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<BenchmarkResult(name={self.benchmark_name!r}, "
            f"value={self.value:.4f} {self.unit})>"
        )
