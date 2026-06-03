"""Pydantic schemas for ML Inference API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelRegistryResponse(BaseModel):
    """Schema for a registered ML model."""

    id: uuid.UUID
    model_name: str
    model_display_name: str
    model_type: str
    model_version: str
    is_active: bool
    accuracy: float
    precision_score: float
    recall_score: float
    f1_score: float
    roc_auc: float
    mcc: float
    avg_inference_time_ms: float
    trained_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictRequest(BaseModel):
    """Features required for model inference."""
    
    WaterLevel: float
    Temperature: float
    Humidity: float
    Ph: float
    Rainfall: float
    FertilizerApp: float
    PesticideApp: float
    SoilMoisture: float
    LightIntensity: float
    WindSpeed: float
    CO2Levels: float
    PlantHeight: float
    LeafAreaIndex: float
    Yield: float
    NDVI: float
    SoilEC: float
    SoilOrganicMatter: float
    NitrogenLevel: float
    PhosphorusLevel: float
    PotassiumLevel: float
    BatteryLevel: float


class PredictionResult(BaseModel):
    """Result from a single model prediction."""
    
    model_name: str
    model_type: str
    prediction: int  # 0 for Normal, 1 for Attack/Anomaly
    label: str
    probability: float | None = None
    confidence: float | None = None
    inference_time_ms: float
    accuracy: float
    roc_auc: float
    feature_importances: list[float] | None = None
    top_features: list[dict[str, str | float]] | None = None


class ComparePredictionResponse(BaseModel):
    """Response containing predictions from multiple models and consensus."""
    
    input_features: dict[str, float]
    predictions: list[PredictionResult]
    consensus: dict[str, str | float]
    recommended_model: str
