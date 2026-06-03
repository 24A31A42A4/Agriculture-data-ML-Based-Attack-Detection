import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.trust_service import TrustService
from app.services.risk_auth_service import RiskAuthService
from app.core.exceptions import AuthorizationError
from app.core.enums import DeviceLifecycleStatus, TrustEventType
from app.models.device import Device
from app.models.user import User


@pytest.fixture
async def mock_device_risk(db_session: AsyncSession) -> Device:
    user = User(
        email="test_risk@example.com",
        hashed_password="hash",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    
    device = Device(
        device_id=f"dev_risk_{uuid.uuid4().hex[:8]}",
        device_name="Test Device Risk",
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
async def test_risk_auth_full_access(db_session: AsyncSession, mock_device_risk: Device):
    # Score is 100
    decision = await RiskAuthService.evaluate_access(db_session, mock_device_risk.id)
    assert decision["access_granted"] is True
    assert decision["access_tier"] == "full"


@pytest.mark.asyncio
async def test_risk_auth_restricted_access(db_session: AsyncSession, mock_device_risk: Device):
    # Drop score to 70
    mock_device_risk.trust_score = 70.0
    await db_session.commit()
    
    decision = await RiskAuthService.evaluate_access(db_session, mock_device_risk.id)
    assert decision["access_granted"] is True
    assert decision["access_tier"] == "restricted"


@pytest.mark.asyncio
async def test_risk_auth_limited_access(db_session: AsyncSession, mock_device_risk: Device):
    # Drop score to 30
    mock_device_risk.trust_score = 30.0
    await db_session.commit()
    
    with pytest.raises(AuthorizationError) as exc:
        await RiskAuthService.evaluate_access(db_session, mock_device_risk.id)
    
    assert "Access limited" in str(exc.value)


@pytest.mark.asyncio
async def test_risk_auth_blocked_access(db_session: AsyncSession, mock_device_risk: Device):
    # Drop score to 10
    mock_device_risk.trust_score = 10.0
    await db_session.commit()
    
    with pytest.raises(AuthorizationError) as exc:
        await RiskAuthService.evaluate_access(db_session, mock_device_risk.id)
    
    assert "Access blocked" in str(exc.value)
