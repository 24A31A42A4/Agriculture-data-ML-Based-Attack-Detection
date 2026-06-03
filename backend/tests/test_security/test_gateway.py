"""Tests for the Security Gateway middleware."""

import base64
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DeviceLifecycleStatus, DeviceType

from app.core.exceptions import (
    AuthenticationError,
    DeviceLifecycleError,
    RateLimitExceededError,
    ReplayAttackError,
    TimestampExpiredError,
)
from app.models.device import Device
from app.models.device_key import DeviceKey
from app.security.gateway import verify_device_request


class MockRequest:
    def __init__(self, headers: dict, body: str):
        self.headers = headers
        self._body = body.encode("utf-8")
        self.method = "POST"
        
        class URL:
            path = "/api/v1/sensors/data"
        self.url = URL()
        
    async def body(self):
        return self._body


@pytest.fixture
def ecc_key_pair():
    """Generate an ephemeral secp256r1 key pair for testing."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.mark.asyncio
async def test_security_gateway_success(
    db_session: AsyncSession,
    redis_client,
    ecc_key_pair,
):
    private_key, public_key = ecc_key_pair
    from cryptography.hazmat.primitives import serialization
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    # 1. Setup mock device and key
    device_uuid = uuid.uuid4()
    device = Device(
        id=device_uuid,
        device_id="dev_mock_1", 
        lifecycle_status=DeviceLifecycleStatus.ACTIVE, 
        device_name="Mock", 
        device_type=DeviceType.SOIL_MOISTURE,
        registered_by=uuid.uuid4()
    )
    db_session.add(device)
    key = DeviceKey(
        device_id=device_uuid, 
        ecc_public_key=pub_pem, 
        key_fingerprint="mock_fingerprint",
        private_key_vault_path="mock/path.pem",
        is_active=True
    )
    db_session.add(key)
    await db_session.commit()

    # 2. Prepare payload and signature
    timestamp = datetime.now(timezone.utc).isoformat()
    nonce = "nonce-12345"
    body = '{"temp": 25.5}'
    
    payload_to_sign = f"POST:/api/v1/sensors/data:{timestamp}:{nonce}:{body}"
    signature = private_key.sign(
        payload_to_sign.encode("utf-8"),
        ec.ECDSA(hashes.SHA256())
    )
    sig_b64 = base64.b64encode(signature).decode("utf-8")

    # 3. Create request and test gateway
    headers = {
        "X-Device-ID": "dev_mock_1",
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": sig_b64,
    }
    request = MockRequest(headers, body)
    
    validated_device = await verify_device_request(request, db_session, redis_client)
    assert validated_device.device_id == "dev_mock_1"


@pytest.mark.asyncio
async def test_security_gateway_replay_attack(
    db_session: AsyncSession,
    redis_client,
):
    timestamp = datetime.now(timezone.utc).isoformat()
    nonce = "reused-nonce-42"
    headers = {
        "X-Device-ID": "dev_mock_1",
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": "dummy",
    }
    request = MockRequest(headers, "")
    
    # Manually set nonce in redis to simulate reuse
    await redis_client.set(f"nonce:dev_mock_1:{nonce}", "1")
    
    # Should fail timestamp/nonce
    device = Device(
        id=uuid.uuid4(),
        device_id="dev_mock_1", 
        lifecycle_status=DeviceLifecycleStatus.ACTIVE, 
        device_name="Mock", 
        device_type=DeviceType.SOIL_MOISTURE,
        registered_by=uuid.uuid4()
    )
    db_session.add(device)
    await db_session.commit()

    with pytest.raises(ReplayAttackError) as exc_info:
        await verify_device_request(request, db_session, redis_client)
        
    assert "Replay attack detected for device dev_mock_1" in exc_info.value.message


@pytest.mark.asyncio
async def test_security_gateway_expired_timestamp(
    db_session: AsyncSession,
    redis_client,
):
    # Timestamp 10 days in the past
    timestamp = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    headers = {
        "X-Device-ID": "dev_mock_1",
        "X-Timestamp": timestamp,
        "X-Nonce": "fresh-nonce-99",
        "X-Signature": "dummy",
    }
    request = MockRequest(headers, "")
    
    device = Device(
        id=uuid.uuid4(),
        device_id="dev_mock_1", 
        lifecycle_status=DeviceLifecycleStatus.ACTIVE, 
        device_name="Mock", 
        device_type=DeviceType.SOIL_MOISTURE,
        registered_by=uuid.uuid4()
    )
    db_session.add(device)
    await db_session.commit()

    with pytest.raises(TimestampExpiredError) as exc_info:
        await verify_device_request(request, db_session, redis_client)
        
    assert "Timestamp expired" in exc_info.value.message
