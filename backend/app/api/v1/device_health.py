"""
Device Health API endpoints.

Provides read-only access to composite device health scores,
authentication reliability, and trust trends.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, require_role
from app.core.enums import UserRole
from app.schemas.device_health import DeviceHealthResponse, DeviceHealthSummaryResponse
from app.services.device_health_service import DeviceHealthService

router = APIRouter()

AnyAuthenticated = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER, UserRole.FARMER, UserRole.SECURITY_ANALYST]))
AdminOrAnalyst = Depends(require_role([UserRole.ADMIN, UserRole.SECURITY_ANALYST]))


@router.get(
    "/health/summary",
    response_model=DeviceHealthSummaryResponse,
    summary="System-wide Device Health Summary",
    description="Get a high-level summary of all device health scores (healthy, warning, degraded).",
    dependencies=[AdminOrAnalyst],
)
async def get_health_summary(db: DbSession):
    """Get system-wide health summary."""
    summary = await DeviceHealthService.get_health_summary(db)
    return DeviceHealthSummaryResponse(**summary)


@router.get(
    "/health/degraded",
    response_model=list[DeviceHealthResponse],
    summary="List Degraded Devices",
    description="List all devices with a health score below 50.",
    dependencies=[AdminOrAnalyst],
)
async def get_degraded_devices(db: DbSession):
    """Get degraded devices."""
    devices = await DeviceHealthService.get_degraded_devices(db)
    return devices


@router.get(
    "/{device_id}/health",
    response_model=DeviceHealthResponse,
    summary="Get Device Health",
    description="Get the current health metrics and composite score for a specific device.",
    dependencies=[AnyAuthenticated],
)
async def get_device_health(device_id: uuid.UUID, db: DbSession):
    """Get health metrics for a specific device."""
    return await DeviceHealthService.get_device_health(db, device_id)
