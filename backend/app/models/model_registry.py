"""ModelRegistry ORM model — ML model metadata and versioning."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ModelType
from app.models.base import Base, TimestampMixin, generate_uuid


class ModelRegistry(Base, TimestampMixin):
    """
    Persistent registry of trained ML models with full evaluation metrics.
    """

    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    model_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    model_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[ModelType] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # ── Evaluation metrics ───────────────────────────────────────────────
    accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    precision_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    f1_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    roc_auc: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mcc: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    specificity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Performance metrics ──────────────────────────────────────────────
    feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=21)
    training_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_inference_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_size_bytes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # ── Lifecycle ────────────────────────────────────────────────────────
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return (
            f"<ModelRegistry(name={self.model_name!r}, "
            f"acc={self.accuracy:.4f}, v{self.model_version})>"
        )
