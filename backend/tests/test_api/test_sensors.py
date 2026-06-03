import base64
import json
import os
import uuid
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.enums import DeviceLifecycleStatus, DeviceType
from app.models.device import Device
from app.models.device_key import DeviceKey
from app.security.crypto import get_device_symmetric_key


@pytest.fixture
def ecc_key_pair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture
async def setup_device(db_session: AsyncSession, ecc_key_pair):
    private_key, public_key = ecc_key_pair
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    
    device_uuid = uuid.uuid4()
    device = Device(
        id=device_uuid,
        device_id="sensor-api-test",
        device_name="API Test Sensor",
        device_type=DeviceType.SOIL_MOISTURE,
        lifecycle_status=DeviceLifecycleStatus.ACTIVE,
        registered_by=uuid.uuid4()
    )
    db_session.add(device)
    
    key = DeviceKey(
        device_id=device_uuid,
        ecc_public_key=pub_pem,
        key_fingerprint="dummy_fp",
        private_key_vault_path="dummy.pem",
        is_active=True
    )
    db_session.add(key)
    await db_session.commit()
    
    return device, private_key


@pytest.mark.asyncio
async def test_api_ingest_sensor_data(client: AsyncClient, setup_device, redis_client):
    device, private_key = setup_device
    
    settings = get_settings()
    aes_key = get_device_symmetric_key(settings.vault_master_secret, device.device_id)
    
    raw_data = {"temperature": 22.5}
    raw_bytes = json.dumps(raw_data).encode("utf-8")
    
    import hashlib
    data_hash = hashlib.sha256(raw_bytes).hexdigest()
    
    aesgcm = AESGCM(aes_key)
    nonce_bytes = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce_bytes, raw_bytes, None)
    encrypted_payload = base64.b64encode(nonce_bytes + ciphertext).decode("utf-8")
    
    payload = {
        "encrypted_payload": encrypted_payload,
        "data_hash": data_hash
    }
    body_str = json.dumps(payload, separators=(',', ':'))
    
    timestamp = datetime.now(timezone.utc).isoformat()
    nonce = "api-test-nonce-1"
    
    payload_to_sign = f"POST:/api/v1/sensors/data:{timestamp}:{nonce}:{body_str}"
    signature = private_key.sign(
        payload_to_sign.encode("utf-8"),
        ec.ECDSA(hashes.SHA256())
    )
    sig_b64 = base64.b64encode(signature).decode("utf-8")
    
    headers = {
        "X-Device-ID": device.device_id,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": sig_b64,
        "Content-Type": "application/json"
    }
    
    response = await client.post("/api/v1/sensors/data", content=body_str.encode("utf-8"), headers=headers)
    assert response.status_code == 201
    
    data = response.json()
    assert data["device_id"] == str(device.id)
    assert data["integrity_verified"] is True
    assert data["raw_data"] == raw_data
