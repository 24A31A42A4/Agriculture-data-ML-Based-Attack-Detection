"""
Trust and Risk API endpoints.

Provides read-only access to trust scores, trust event histories,
and system-wide trust analytics.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, require_role
from app.core.enums import UserRole
from app.models.device import Device
from app.schemas.trust import TrustAnalyticsResponse, TrustEventResponse, TrustScoreResponse
from app.services.trust_service import TrustService

router = APIRouter()

# Authentication dependencies
ResearcherOrAdmin = Depends(require_role([UserRole.RESEARCHER, UserRole.ADMIN]))
AnyAuthenticated = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER, UserRole.FARMER, UserRole.SECURITY_ANALYST]))


@router.get(
    "/scores",
    response_model=list[TrustScoreResponse],
    summary="List All Device Trust Scores",
    description="Retrieve the current trust score and risk level for all devices.",
    dependencies=[AnyAuthenticated],
)
async def list_trust_scores(
    db: DbSession,
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
):
    """List all device trust scores."""
    stmt = select(Device).offset(skip).limit(limit)
    result = await db.execute(stmt)
    devices = result.scalars().all()
    
    return [
        await TrustService.get_device_trust_score(db, device.id)
        for device in devices
    ]


@router.get(
    "/device/{device_id}/history",
    response_model=list[TrustEventResponse],
    summary="Get Device Trust History",
    description="Retrieve the chronological history of trust score changes for a specific device.",
    dependencies=[ResearcherOrAdmin],
)
async def get_device_trust_history(
    device_id: uuid.UUID,
    db: DbSession,
    limit: int = Query(50, ge=1, le=500),
):
    """Get the trust event history for a device."""
    return await TrustService.get_trust_history(db, device_id, limit)


@router.post(
    "/recalculate/{device_id}",
    response_model=TrustScoreResponse,
    summary="Force Recalculate Trust",
    description="Manually recalculate trust (admin only). Note: Normal operation adjusts trust incrementally.",
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
async def recalculate_trust(device_id: uuid.UUID, db: DbSession):
    """Force a recalculation of device trust score. Currently just returns the existing score in this v2 architecture."""
    return await TrustService.get_device_trust_score(db, device_id)


@router.get(
    "/analytics",
    response_model=TrustAnalyticsResponse,
    summary="Trust Analytics",
    description="Get system-wide trust analytics including average score, risk distribution, and event counts.",
    dependencies=[ResearcherOrAdmin],
)
async def get_trust_analytics(db: DbSession):
    """Get system-wide trust analytics."""
    analytics = await TrustService.get_system_analytics(db)
    return TrustAnalyticsResponse(**analytics)
