"""
Attack Simulation API endpoints.

Provides endpoints to trigger different types of attack simulations
to test the security pipeline and monitor the responses.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, require_role
from app.core.enums import UserRole
from app.schemas.attack_sim import AttackSimResult
from app.services.attack_sim_service import AttackSimService

router = APIRouter()

ResearcherOrAdmin = Depends(require_role([UserRole.ADMIN, UserRole.RESEARCHER]))


@router.post(
    "/data-tampering/{device_id}",
    response_model=AttackSimResult,
    summary="Simulate Data Tampering",
    dependencies=[ResearcherOrAdmin],
)
async def simulate_data_tampering(device_id: uuid.UUID, db: DbSession):
    """Simulate a data payload modification attack."""
    return await AttackSimService.simulate_data_tampering(db, device_id)


@router.post(
    "/fake-sensor",
    response_model=AttackSimResult,
    summary="Simulate Fake Sensor",
    dependencies=[ResearcherOrAdmin],
)
async def simulate_fake_sensor(db: DbSession):
    """Simulate an unregistered device attempting data ingestion."""
    return await AttackSimService.simulate_fake_sensor(db)


@router.post(
    "/replay/{device_id}",
    response_model=AttackSimResult,
    summary="Simulate Replay Attack",
    dependencies=[ResearcherOrAdmin],
)
async def simulate_replay_attack(device_id: uuid.UUID, db: DbSession):
    """Simulate a replay attack using an old payload/nonce."""
    return await AttackSimService.simulate_replay_attack(db, device_id)


@router.post(
    "/dos/{device_id}",
    response_model=AttackSimResult,
    summary="Simulate DoS Attack",
    dependencies=[ResearcherOrAdmin],
)
async def simulate_dos_attack(device_id: uuid.UUID, db: DbSession):
    """Simulate a Denial of Service attack."""
    return await AttackSimService.simulate_dos_attack(db, device_id)


@router.post(
    "/unauthorized-device/{device_id}",
    response_model=AttackSimResult,
    summary="Simulate Unauthorized Device",
    dependencies=[ResearcherOrAdmin],
)
async def simulate_unauthorized_device(device_id: uuid.UUID, db: DbSession):
    """Simulate a registered device using an invalid ECC signature."""
    return await AttackSimService.simulate_unauthorized_device(db, device_id)


@router.post(
    "/ml-anomaly/{device_id}",
    response_model=AttackSimResult,
    summary="Simulate ML Behavioral Anomaly",
    dependencies=[ResearcherOrAdmin],
)
async def simulate_ml_anomaly(device_id: uuid.UUID, db: DbSession):
    """Simulate a behavioral anomaly detected by the ML IDS."""
    return await AttackSimService.simulate_ml_anomaly(db, device_id)
