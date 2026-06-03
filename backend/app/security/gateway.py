"""Security Gateway: 6-stage IoT request validation pipeline."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.config import get_settings
from app.core.enums import DeviceLifecycleStatus
from app.core.exceptions import (
    AuthenticationError,
    DeviceLifecycleError,
    RateLimitExceededError,
    ReplayAttackError,
    TimestampExpiredError,
)
from app.database.redis import get_redis
from app.models.device import Device
from app.security.crypto import verify_ecc_signature
from app.services.device_service import DeviceService


async def verify_device_request(
    request: Request,
    db: DbSession,
    redis: Annotated[Redis, Depends(get_redis)],
) -> Device:
    """
    Security Gateway Dependency.
    Executes the 6-stage validation pipeline for IoT requests.
    """
    settings = get_settings()
    
    # Extract headers
    device_id = request.headers.get("X-Device-ID")
    timestamp_str = request.headers.get("X-Timestamp")
    nonce = request.headers.get("X-Nonce")
    signature = request.headers.get("X-Signature")
    
    if not all([device_id, timestamp_str, nonce, signature]):
        raise AuthenticationError("Missing required security headers")

    # 1. Device Validation (Whitelist & Status)
    device = await DeviceService.get_by_device_id(db, device_id)
    if not device:
        raise AuthenticationError("Unknown device")
    if device.lifecycle_status != DeviceLifecycleStatus.ACTIVE:
        raise DeviceLifecycleError(device.lifecycle_status.value, device_id)

    # 2. Rate Limiting (Redis token bucket or simple counter)
    # Using a simple sliding window counter per minute
    rl_key = f"rate_limit:{device_id}"
    current_count = await redis.incr(rl_key)
    if current_count == 1:
        await redis.expire(rl_key, 60)
    if current_count > settings.rate_limit_device_max:
        raise RateLimitExceededError(device_id, limit=settings.rate_limit_device_max)

    # 3. Timestamp Validation (Prevent delayed/stale attacks)
    try:
        req_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_diff = abs((now - req_time).total_seconds())
        if time_diff > settings.jwt_access_token_expire_minutes * 60:  # e.g., 5 mins
            raise TimestampExpiredError(
                drift_seconds=time_diff, 
                max_drift=settings.jwt_access_token_expire_minutes * 60
            )
    except ValueError:
        raise AuthenticationError("Invalid timestamp format")

    # 4. Nonce Validation (Prevent exact replay attacks)
    nonce_key = f"nonce:{device_id}:{nonce}"
    # SETNX returns True if key was set (i.e. didn't exist)
    is_new_nonce = await redis.set(nonce_key, "1", nx=True, ex=300) # 5 min expiry
    if not is_new_nonce:
        raise ReplayAttackError(nonce, device_id)

    # 5. Mutual Auth / Signature Verification (ECC)
    # The payload to sign is: method + path + timestamp + nonce + body
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")
    
    payload_to_verify = f"{request.method}:{request.url.path}:{timestamp_str}:{nonce}:{body_str}"
    
    active_key = await DeviceService.get_active_key(db, str(device.id))
    if not active_key:
        raise AuthenticationError("No active key registered for device")
        
    is_valid = verify_ecc_signature(
        public_key_pem=active_key.ecc_public_key,
        payload=payload_to_verify,
        signature_b64=signature
    )
    
    if not is_valid:
        raise AuthenticationError("Invalid ECC signature")

    # 6. Return Validated Device
    return device


ValidatedDevice = Annotated[Device, Depends(verify_device_request)]
