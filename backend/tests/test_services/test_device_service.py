"""Tests for device service CRUD operations."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DeviceLifecycleStatus, DeviceType, UserRole
from app.schemas.device import DeviceCreate, DeviceKeyCreate, DeviceUpdate
from app.schemas.user import UserCreate
from app.services.device_service import DeviceService
from app.services.user_service import UserService


@pytest.fixture
async def sample_admin(db_session: AsyncSession) -> uuid.UUID:
    """Fixture to create an admin user for device registration."""
    user_in = UserCreate(
        email="admin_device@example.com",
        password="SecurePassword123!",
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    user = await UserService.create(db_session, obj_in=user_in)
    return user.id


@pytest.fixture
def sample_device_data() -> dict:
    return {
        "device_id": "sensor-a1b2c3",
        "device_name": "Soil Sensor A1",
        "device_type": DeviceType.SOIL_MOISTURE.value,
    }


@pytest.fixture
def sample_ecc_public_key() -> str:
    """Sample valid secp256r1 public key in PEM format."""
    return (
        "-----BEGIN PUBLIC KEY-----\n"
        "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE7Z1+z0W/4E6p4r/W7gZg7Vq2Qc6j\n"
        "0bY+KqQ9uH3GvW2Hw/l1+d/O5x8y+X5f5X9y0g7b6R1p0Z1H5G9F2a6h5g==\n"
        "-----END PUBLIC KEY-----\n"
    )


@pytest.mark.asyncio
async def test_create_device(
    db_session: AsyncSession, sample_admin: uuid.UUID, sample_device_data: dict
):
    device_in = DeviceCreate(**sample_device_data)
    device = await DeviceService.create(db_session, obj_in=device_in, registered_by=sample_admin)
    
    assert device.id is not None
    assert device.device_name == sample_device_data["device_name"]
    assert device.device_id == sample_device_data["device_id"]
    assert device.lifecycle_status == DeviceLifecycleStatus.REGISTERED


@pytest.mark.asyncio
async def test_update_device(
    db_session: AsyncSession, sample_admin: uuid.UUID, sample_device_data: dict
):
    device_in = DeviceCreate(**sample_device_data)
    device = await DeviceService.create(db_session, obj_in=device_in, registered_by=sample_admin)
    
    update_data = DeviceUpdate(
        device_name="Updated Sensor", lifecycle_status=DeviceLifecycleStatus.SUSPENDED
    )
    updated_device = await DeviceService.update(db_session, db_obj=device, obj_in=update_data)
    
    assert updated_device.device_name == "Updated Sensor"
    assert updated_device.lifecycle_status == DeviceLifecycleStatus.SUSPENDED


@pytest.mark.asyncio
async def test_register_device_key(
    db_session: AsyncSession,
    sample_admin: uuid.UUID,
    sample_device_data: dict,
    sample_ecc_public_key: str,
):
    # 1. Create Device
    device_in = DeviceCreate(**sample_device_data)
    device = await DeviceService.create(db_session, obj_in=device_in, registered_by=sample_admin)
    
    # 2. Register Key
    key_in = DeviceKeyCreate(public_key_pem=sample_ecc_public_key)
    key = await DeviceService.register_key(db_session, device_id=device.id, obj_in=key_in)
    
    assert key.device_id == device.id
    assert key.ecc_public_key == sample_ecc_public_key
    assert key.is_active is True
    
    # 3. Verify device status updated to ACTIVE
    updated_device = await DeviceService.get(db_session, str(device.id))
    assert updated_device
    assert updated_device.lifecycle_status == DeviceLifecycleStatus.ACTIVE
    
    # 4. Register a second key (should deactivate the first)
    key_in_2 = DeviceKeyCreate(public_key_pem="-----BEGIN PUBLIC KEY-----\nNEWKEY\n-----END PUBLIC KEY-----\n")
    key_2 = await DeviceService.register_key(db_session, device_id=device.id, obj_in=key_in_2)
    
    assert key_2.is_active is True
    
    # Verify first key deactivated
    active_key = await DeviceService.get_active_key(db_session, device.id)
    assert active_key
    assert active_key.id == key_2.id
    assert active_key.ecc_public_key == key_in_2.public_key_pem
