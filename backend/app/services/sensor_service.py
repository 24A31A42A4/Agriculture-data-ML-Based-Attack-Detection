import json
import logging
from datetime import datetime, timezone
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.config import get_settings
from app.models.device import Device
from app.models.sensor_data import SensorData
from app.schemas.sensor_data import SensorDataIngest
from app.security.crypto import get_device_symmetric_key, decrypt_aes_gcm
from app.core.exceptions import AgriIoTError

logger = logging.getLogger(__name__)


class SensorDataService:
    """Service for handling sensor data ingestion and querying."""

    @staticmethod
    async def ingest_data(
        db: AsyncSession,
        redis_client,
        device: Device,
        payload: SensorDataIngest,
        signature: str,
        nonce: str,
        timestamp: str
    ) -> SensorData:
        """
        Process incoming encrypted sensor data.
        
        1. Derives symmetric key for device.
        2. Decrypts AES-GCM payload.
        3. Verifies data hash.
        4. Saves record to DB.
        5. Caches latest reading in Redis.
        """
        settings = get_settings()
        
        # 1. Decrypt payload
        aes_key = get_device_symmetric_key(settings.vault_master_secret, device.device_id)
        raw_json_bytes = decrypt_aes_gcm(aes_key, payload.encrypted_payload)
        
        # 2. Verify data hash
        computed_hash = hashlib.sha256(raw_json_bytes).hexdigest()
        if computed_hash != payload.data_hash:
            raise AgriIoTError("Data integrity check failed: Hash mismatch")
            
        # 3. Parse JSON
        try:
            raw_data = json.loads(raw_json_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            raise AgriIoTError("Decrypted payload is not valid JSON")
            
        # 4. Save to Database
        try:
            sensor_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            sensor_time = datetime.now(timezone.utc)
            
        db_obj = SensorData(
            device_id=device.id,
            raw_data=raw_data,
            encrypted_payload=payload.encrypted_payload,
            data_hash=payload.data_hash,
            signature=signature,
            nonce=nonce,
            sensor_timestamp=sensor_time,
            integrity_verified=True,
            # ML Prediction fields will be filled later by ML service
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        # 5. Cache latest reading in Redis for dashboards
        cache_key = f"latest_sensor:{device.device_id}"
        cache_data = {
            "id": str(db_obj.id),
            "device_id": str(db_obj.device_id),
            "timestamp": sensor_time.isoformat(),
            "data": raw_data,
        }
        await redis_client.set(cache_key, json.dumps(cache_data), ex=3600)  # 1 hour expiry
        
        return db_obj
