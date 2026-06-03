"""
Feature Drift Monitoring API endpoints.

Provides endpoints to trigger drift checks and view drift history.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np

from app.api.deps import DbSession, require_role
from app.core.enums import UserRole
from app.schemas.drift import DriftCheckResponse
from app.services.drift_service import DriftService

router = APIRouter()

ResearcherOrAdmin = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))


@router.post(
    "/check",
    response_model=DriftCheckResponse,
    summary="Trigger Manual Drift Check",
    description="Run a drift check comparing recent sensor data to the training baseline.",
    dependencies=[ResearcherOrAdmin],
)
async def check_drift(db: DbSession):
    """
    Trigger a manual feature drift check.
    
    In a fully operational environment, this would query recent SensorData 
    and compare it to a stored baseline distribution. For demonstration, 
    we simulate the baseline and current data distributions.
    """
    # Simulate Reference Data (Baseline) - e.g. normal distribution
    # Simulate Current Data (Recent) - e.g. drifted distribution
    np.random.seed(42)
    
    # Feature 1: No drift
    ref_f1 = np.random.normal(0, 1, 1000).tolist()
    cur_f1 = np.random.normal(0.05, 1, 1000).tolist()
    
    # Feature 2: Moderate drift
    ref_f2 = np.random.normal(10, 2, 1000).tolist()
    cur_f2 = np.random.normal(11, 2.5, 1000).tolist()
    
    # Feature 3: Severe drift
    ref_f3 = np.random.normal(50, 5, 1000).tolist()
    cur_f3 = np.random.normal(60, 5, 1000).tolist()

    reference_dict = {
        "Temperature": ref_f1,
        "Humidity": ref_f2,
        "SoilMoisture": ref_f3
    }
    
    current_dict = {
        "Temperature": cur_f1,
        "Humidity": cur_f2,
        "SoilMoisture": cur_f3
    }
    
    return await DriftService.run_drift_check(reference_dict, current_dict)
