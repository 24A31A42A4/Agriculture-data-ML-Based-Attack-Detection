import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.attack_sim_service import AttackSimService
from app.services.trust_service import TrustService
from app.core.enums import DeviceLifecycleStatus
from app.models.device import Device
from app.models.user import User


@pytest.fixture
async def mock_device_attack(db_session: AsyncSession) -> Device:
    user = User(
        email="attack_user@example.com",
        hashed_password="hash",
        full_name="Attack User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    device = Device(
        device_id=f"dev_atk_{uuid.uuid4().hex[:8]}",
        device_name="Test Device Attack",
        device_type="temperature",
        lifecycle_status=DeviceLifecycleStatus.ACTIVE,
        trust_score=100.0,
        registered_by=user.id
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


@pytest.mark.asyncio
async def test_simulate_data_tampering(db_session: AsyncSession, mock_device_attack: Device):
    res = await AttackSimService.simulate_data_tampering(db_session, mock_device_attack.id)
    
    assert res.attack_type == "data_tampering"
    assert res.was_detected is True
    assert res.detection_layer == "Security Gateway"
    assert res.blockchain_anchored is True
    assert res.trust_score_penalty == -20.0
    
    # Check that trust score actually dropped
    await db_session.refresh(mock_device_attack)
    assert mock_device_attack.trust_score == 80.0


@pytest.mark.asyncio
async def test_simulate_fake_sensor(db_session: AsyncSession):
    res = await AttackSimService.simulate_fake_sensor(db_session)
    
    assert res.attack_type == "fake_sensor"
    assert res.was_detected is True
    assert res.detection_layer == "Security Gateway"
    assert res.trust_score_penalty == 0.0
    assert res.blockchain_anchored is True


@pytest.mark.asyncio
async def test_simulate_replay_attack(db_session: AsyncSession, mock_device_attack: Device):
    res = await AttackSimService.simulate_replay_attack(db_session, mock_device_attack.id)
    
    assert res.attack_type == "replay_attack"
    assert res.was_detected is True
    assert res.trust_score_penalty == -15.0


@pytest.mark.asyncio
async def test_simulate_dos_attack(db_session: AsyncSession, mock_device_attack: Device):
    res = await AttackSimService.simulate_dos_attack(db_session, mock_device_attack.id)
    
    assert res.attack_type == "dos_attack"
    assert res.was_detected is True
    assert res.trust_score_penalty == -30.0


@pytest.mark.asyncio
async def test_simulate_unauthorized_device(db_session: AsyncSession, mock_device_attack: Device):
    res = await AttackSimService.simulate_unauthorized_device(db_session, mock_device_attack.id)
    
    assert res.attack_type == "unauthorized_device"
    assert res.was_detected is True
    assert res.trust_score_penalty == -20.0
