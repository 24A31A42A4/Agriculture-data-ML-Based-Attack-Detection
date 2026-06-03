"""
ML Inference API endpoints.

Provides endpoints for querying the model registry, running inference
with specific models, and running comparative multi-model evaluations.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, require_role
from app.core.enums import UserRole
from app.schemas.ml import ComparePredictionResponse, ModelRegistryResponse, PredictionResult, PredictRequest
from app.services.ml_service import MLService

router = APIRouter()

AnyAuthenticated = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER, UserRole.FARMER, UserRole.SECURITY_ANALYST]))
ResearcherOrAdmin = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))


@router.get(
    "/models",
    response_model=list[ModelRegistryResponse],
    summary="List Active ML Models",
    description="Get metadata and evaluation metrics for all active models in the registry.",
    dependencies=[AnyAuthenticated],
)
async def list_models(db: DbSession):
    """List all active models from the registry."""
    return await MLService.get_active_models(db)


@router.post(
    "/predict",
    response_model=PredictionResult,
    summary="Predict Anomaly (Single Model)",
    description="Run inference using the best available model or a specifically requested one.",
    dependencies=[AnyAuthenticated],
)
async def predict_single(
    request: PredictRequest,
    db: DbSession,
    model_name: str | None = Query(None, description="Optional specific model to use"),
):
    """Run inference using a single model."""
    features = request.model_dump()
    return await MLService.predict_single(db, features, model_name=model_name)


@router.post(
    "/predict/all",
    response_model=ComparePredictionResponse,
    summary="Predict using all models (Ensemble Consensus)",
    description="Run inference across all active models and return a consensus decision. Useful for research comparisons.",
    dependencies=[AnyAuthenticated],
)
async def predict_all(
    request: PredictRequest,
    db: DbSession,
):
    """Run inference using all active models and return consensus."""
    features = request.model_dump()
    return await MLService.predict_all(db, features)


@router.post(
    "/compare",
    response_model=ComparePredictionResponse,
    summary="Compare Model Predictions",
    description="Alias for /predict/all intended for researchers.",
    dependencies=[ResearcherOrAdmin],
)
async def compare_predictions(
    request: PredictRequest,
    db: DbSession,
):
    """Alias for predict_all intended for detailed comparison."""
    features = request.model_dump()
    return await MLService.predict_all(db, features)
