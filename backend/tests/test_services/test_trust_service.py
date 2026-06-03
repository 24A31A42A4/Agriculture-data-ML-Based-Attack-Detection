import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.trust_service import TrustService
from app.core.enums import TrustEventType, DeviceLifecycleStatus
from app.models.device import Device
from app.models.user import User


@pytest.fixture
async def mock_device(db_session: AsyncSession) -> Device:
    user = User(
        email="test_trust@example.com",
        hashed_password="hash",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    device = Device(
        device_id=f"dev_{uuid.uuid4().hex[:8]}",
        device_name="Test Device",
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
async def test_adjust_trust_score_success(db_session: AsyncSession, mock_device: Device):
    # Base score is 100. A failure drops it by 10
    updated_device, trust_event = await TrustService.adjust_trust_score(
        db=db_session,
        device_id=mock_device.id,
        event_type=TrustEventType.AUTH_FAILURE
    )
    
    assert updated_device.trust_score == 90.0
    assert trust_event.score_change == -10.0
    assert trust_event.score_after == 90.0
    assert trust_event.event_type == TrustEventType.AUTH_FAILURE.value
    
    # Another success increases it by 1
    updated_device, trust_event2 = await TrustService.adjust_trust_score(
        db=db_session,
        device_id=mock_device.id,
        event_type=TrustEventType.AUTH_SUCCESS
    )
    
    assert updated_device.trust_score == 91.0
    assert trust_event2.score_change == +1.0


@pytest.mark.asyncio
async def test_adjust_trust_score_clamping(db_session: AsyncSession, mock_device: Device):
    # Score shouldn't exceed 100
    updated_device, _ = await TrustService.adjust_trust_score(
        db=db_session,
        device_id=mock_device.id,
        event_type=TrustEventType.AUTH_SUCCESS
    )
    assert updated_device.trust_score == 100.0
    
    # Score shouldn't drop below 0
    # Apply severe penalties
    for _ in range(5):
        updated_device, _ = await TrustService.adjust_trust_score(
            db=db_session,
            device_id=mock_device.id,
            event_type=TrustEventType.FAKE_SENSOR  # -25
        )
    
    assert updated_device.trust_score == 0.0


@pytest.mark.asyncio
async def test_auto_suspend_lifecycle(db_session: AsyncSession, mock_device: Device):
    # Drop below 50
    # Currently 100.
    await TrustService.adjust_trust_score(
        db=db_session, device_id=mock_device.id, event_type=TrustEventType.DOS_BEHAVIOR # -30 -> 70
    )
    updated_device, _ = await TrustService.adjust_trust_score(
        db=db_session, device_id=mock_device.id, event_type=TrustEventType.DOS_BEHAVIOR # -30 -> 40
    )
    
    assert updated_device.trust_score == 40.0
    assert updated_device.lifecycle_status == DeviceLifecycleStatus.SUSPENDED.value
    assert updated_device.suspended_at is not None


@pytest.mark.asyncio
async def test_auto_revoke_lifecycle(db_session: AsyncSession, mock_device: Device):
    # Drop below 20
    # Currently 100.
    for _ in range(3):
        updated_device, _ = await TrustService.adjust_trust_score(
            db=db_session, device_id=mock_device.id, event_type=TrustEventType.DOS_BEHAVIOR # -30
        )
    
    assert updated_device.trust_score == 10.0
    assert updated_device.lifecycle_status == DeviceLifecycleStatus.REVOKED.value
    assert updated_device.revoked_at is not None


@pytest.mark.asyncio
async def test_frozen_trust_score(db_session: AsyncSession, mock_device: Device):
    # Suspend device
    mock_device.lifecycle_status = DeviceLifecycleStatus.SUSPENDED
    mock_device.trust_score = 45.0
    await db_session.commit()
    
    # Try to adjust score
    updated_device, trust_event = await TrustService.adjust_trust_score(
        db=db_session, device_id=mock_device.id, event_type=TrustEventType.AUTH_SUCCESS
    )
    
    # Score should remain frozen at 45.0
    assert updated_device.trust_score == 45.0
    assert trust_event.score_change == 0.0
    assert trust_event.score_after == 45.0
