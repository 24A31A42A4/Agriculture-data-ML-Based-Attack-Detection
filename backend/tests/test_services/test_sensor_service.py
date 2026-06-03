import base64
import json
import os
import uuid
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AgriIoTError, DecryptionError
from app.models.device import Device
from app.schemas.sensor_data import SensorDataIngest
from app.security.crypto import get_device_symmetric_key
from app.services.sensor_service import SensorDataService
from app.core.enums import DeviceLifecycleStatus, DeviceType


@pytest.fixture
def sample_device(db_session: AsyncSession) -> Device:
    """Fixture providing a mock device for testing."""
    device = Device(
        id=uuid.uuid4(),
        device_id="sensor-001",
        device_name="Test Sensor",
        device_type=DeviceType.SOIL_MOISTURE,
        lifecycle_status=DeviceLifecycleStatus.ACTIVE,
        registered_by=uuid.uuid4()
    )
    db_session.add(device)
    # Don't commit yet, we will flush in the test if needed or wait for session to do it.
    return device


@pytest.mark.asyncio
async def test_ingest_data_success(db_session: AsyncSession, redis_client, sample_device):
    await db_session.commit()
    await db_session.refresh(sample_device)

    # Prepare payload
    settings = get_settings()
    aes_key = get_device_symmetric_key(settings.vault_master_secret, sample_device.device_id)
    raw_data = {"temp": 24.5, "hum": 65}
    raw_bytes = json.dumps(raw_data).encode("utf-8")
    
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, raw_bytes, None)
    encrypted_payload = base64.b64encode(nonce + ciphertext).decode("utf-8")
    
    import hashlib
    data_hash = hashlib.sha256(raw_bytes).hexdigest()
    
    payload = SensorDataIngest(
        encrypted_payload=encrypted_payload,
        data_hash=data_hash
    )
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Run service
    record = await SensorDataService.ingest_data(
        db=db_session,
        redis_client=redis_client,
        device=sample_device,
        payload=payload,
        signature="mock_sig",
        nonce="mock_nonce",
        timestamp=timestamp
    )
    
    # Assertions
    assert record.device_id == sample_device.id
    assert record.raw_data == raw_data
    assert record.data_hash == data_hash
    assert record.signature == "mock_sig"
    assert record.integrity_verified is True
    
    # Check cache
    cache_key = f"latest_sensor:{sample_device.device_id}"
    cached_val = await redis_client.get(cache_key)
    assert cached_val is not None
    cached_data = json.loads(cached_val)
    assert cached_data["data"] == raw_data


@pytest.mark.asyncio
async def test_ingest_data_hash_mismatch(db_session: AsyncSession, redis_client, sample_device):
    await db_session.commit()
    
    settings = get_settings()
    aes_key = get_device_symmetric_key(settings.vault_master_secret, sample_device.device_id)
    raw_data = {"temp": 24.5}
    raw_bytes = json.dumps(raw_data).encode("utf-8")
    
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, raw_bytes, None)
    encrypted_payload = base64.b64encode(nonce + ciphertext).decode("utf-8")
    
    payload = SensorDataIngest(
        encrypted_payload=encrypted_payload,
        data_hash="invalid_hash"
    )
    
    with pytest.raises(AgriIoTError, match="Data integrity check failed: Hash mismatch"):
        await SensorDataService.ingest_data(
            db=db_session,
            redis_client=redis_client,
            device=sample_device,
            payload=payload,
            signature="mock_sig",
            nonce="mock_nonce",
            timestamp=datetime.now(timezone.utc).isoformat()
        )


@pytest.mark.asyncio
async def test_ingest_data_decryption_failure(db_session: AsyncSession, redis_client, sample_device):
    await db_session.commit()
    
    # Wrong key or corrupted payload
    payload = SensorDataIngest(
        encrypted_payload=base64.b64encode(b"0" * 12 + b"corrupted_data").decode("utf-8"),
        data_hash="dummy"
    )
    
    with pytest.raises(DecryptionError):
        await SensorDataService.ingest_data(
            db=db_session,
            redis_client=redis_client,
            device=sample_device,
            payload=payload,
            signature="mock_sig",
            nonce="mock_nonce",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
