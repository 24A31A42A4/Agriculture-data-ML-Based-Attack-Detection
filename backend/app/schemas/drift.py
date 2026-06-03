"""Pydantic schemas for Feature Drift Monitoring API."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FeatureDriftResult(BaseModel):
    """Drift analysis result for a single feature."""
    feature_name: str
    psi_score: float
    ks_statistic: float
    ks_p_value: float
    is_drifting: bool
    drift_severity: str  # "none", "moderate", "severe"


class DriftCheckResponse(BaseModel):
    """Response from a manual or scheduled drift check."""
    check_id: str
    timestamp: datetime
    overall_drift_detected: bool
    features_drifting_count: int
    feature_results: list[FeatureDriftResult]
    severity: str
    recommendation: str

    model_config = ConfigDict(from_attributes=True)
