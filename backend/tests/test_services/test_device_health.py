import pytest
import uuid
import numpy as np
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.device_health_service import DeviceHealthService
from app.services.trust_service import TrustService
from app.core.enums import DeviceLifecycleStatus, TrustEventType
from app.models.device import Device
from app.models.user import User


@pytest.fixture
async def mock_device_health(db_session: AsyncSession) -> Device:
    user = User(
        email="health_user@example.com",
        hashed_password="hash",
        full_name="Health User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    device = Device(
        device_id=f"dev_health_{uuid.uuid4().hex[:8]}",
        device_name="Test Device Health",
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
async def test_record_auth_event(db_session: AsyncSession, mock_device_health: Device):
    # Record success
    health = await DeviceHealthService.record_auth_event(
        db_session, mock_device_health.id, success=True
    )
    assert health.total_auth_attempts == 1
    assert health.auth_successes == 1
    assert health.auth_failures == 0
    assert health.auth_success_rate == 1.0
    assert health.consecutive_failures == 0
    
    # Record failure
    health = await DeviceHealthService.record_auth_event(
        db_session, mock_device_health.id, success=False
    )
    assert health.total_auth_attempts == 2
    assert health.auth_successes == 1
    assert health.auth_failures == 1
    assert health.auth_success_rate == 0.5
    assert health.consecutive_failures == 1


@pytest.mark.asyncio
async def test_compute_trust_trend(db_session: AsyncSession, mock_device_health: Device):
    # Base is 100. Let's create a declining trend
    for _ in range(5):
        await TrustService.adjust_trust_score(
            db_session, mock_device_health.id, TrustEventType.RATE_LIMIT_VIOLATION # -5
        )
        
    trend = await DeviceHealthService.compute_trust_trend(db_session, mock_device_health.id)
    # The trend should be negative (declining)
    assert trend < 0.0


@pytest.mark.asyncio
async def test_compute_health_score(db_session: AsyncSession, mock_device_health: Device):
    health = await DeviceHealthService.get_device_health(db_session, mock_device_health.id)
    # Brand new device, 0 auths. Auth component is neutral (50).
    # Trust is 100. Trend is 0 (norm to 50). Recency is 0.
    # Score = 0.4*50 + 0.3*100 + 0.2*50 + 0.1*0 = 20 + 30 + 10 + 0 = 60
    assert 59.0 <= health.health_score <= 61.0
    
    # Add successful auth to boost recency and auth component
    await DeviceHealthService.record_auth_event(db_session, mock_device_health.id, success=True)
    
    health = await DeviceHealthService.get_device_health(db_session, mock_device_health.id)
    # Auth rate = 100. Trust = 100. Trend = 0. Recency ~ 100.
    # Score = 0.4*100 + 0.3*100 + 0.2*50 + 0.1*100 = 40 + 30 + 10 + 10 = 90
    assert 89.0 <= health.health_score <= 91.0


@pytest.mark.asyncio
async def test_health_summary(db_session: AsyncSession, mock_device_health: Device):
    # Initialize health record
    await DeviceHealthService.get_device_health(db_session, mock_device_health.id)
    
    # Single device, health score should be ~60 initially
    summary = await DeviceHealthService.get_health_summary(db_session)
    
    assert summary["total_devices_evaluated"] >= 1
    # Check that keys exist
    assert "average_health_score" in summary
    assert "healthy_devices_count" in summary
    assert "warning_devices_count" in summary
    assert "degraded_devices_count" in summary


@pytest.mark.asyncio
async def test_degraded_devices(db_session: AsyncSession, mock_device_health: Device):
    # Intentionally degrade health by recording many failures
    for _ in range(10):
        await DeviceHealthService.record_auth_event(db_session, mock_device_health.id, success=False)
        
    degraded = await DeviceHealthService.get_degraded_devices(db_session)
    assert any(d.device_id == mock_device_health.id for d in degraded)
