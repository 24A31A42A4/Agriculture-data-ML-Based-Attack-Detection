"""Device and DeviceKey business logic and CRUD operations."""

import secrets
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DeviceLifecycleStatus
from app.models.device import Device
from app.models.device_key import DeviceKey
from app.schemas.device import DeviceCreate, DeviceKeyCreate, DeviceUpdate


def generate_device_id() -> str:
    """Generate a unique string ID for a device (e.g., dev_a1b2c3d4)."""
    return f"dev_{secrets.token_hex(4)}"


class DeviceService:
    """Service for device and key management."""

    @staticmethod
    async def get(db: AsyncSession, device_id: str | uuid.UUID) -> Device | None:
        """Get a device by internal UUID."""
        if isinstance(device_id, str):
            device_id = uuid.UUID(device_id)
        stmt = select(Device).where(Device.id == device_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_device_id(db: AsyncSession, device_id: str) -> Device | None:
        """Get a device by its logical device_id."""
        stmt = select(Device).where(Device.device_id == device_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_multi(
        db: AsyncSession, skip: int = 0, limit: int = 100, status: DeviceLifecycleStatus | None = None
    ) -> Sequence[Device]:
        """Get multiple devices, optionally filtered by status."""
        stmt = select(Device).offset(skip).limit(limit)
        if status:
            stmt = stmt.where(Device.lifecycle_status == status)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, obj_in: DeviceCreate, registered_by: uuid.UUID) -> Device:
        """Register a new device."""
        db_obj = Device(
            device_id=obj_in.device_id,
            device_name=obj_in.device_name,
            device_type=obj_in.device_type,
            registered_by=registered_by,
            lifecycle_status=DeviceLifecycleStatus.REGISTERED,
            is_whitelisted=False,
            trust_score=100.0,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def update(db: AsyncSession, db_obj: Device, obj_in: DeviceUpdate) -> Device:
        """Update a device."""
        update_data = obj_in.model_dump(exclude_unset=True)
        if "ip_address" in update_data and update_data["ip_address"]:
            update_data["ip_address"] = str(update_data["ip_address"])
            
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    # ── Device Key Operations ────────────────────────────────────────────────

    @staticmethod
    async def get_active_key(db: AsyncSession, device_id: str | uuid.UUID) -> DeviceKey | None:
        """Get the currently active public key for a device internal UUID."""
        if isinstance(device_id, str):
            device_id = uuid.UUID(device_id)
        stmt = select(DeviceKey).where(
            DeviceKey.device_id == device_id, DeviceKey.is_active.is_(True)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def register_key(db: AsyncSession, device_id: str, obj_in: DeviceKeyCreate) -> DeviceKey:
        """
        Register a new public key for a device.
        Deactivates any existing active keys for the device.
        """
        # Deactivate current active keys
        stmt = select(DeviceKey).where(
            DeviceKey.device_id == device_id, DeviceKey.is_active.is_(True)
        )
        result = await db.execute(stmt)
        active_keys = result.scalars().all()
        for key in active_keys:
            key.is_active = False
            db.add(key)

        import hashlib
        fingerprint = hashlib.sha256(obj_in.public_key_pem.encode("utf-8")).hexdigest()
        
        if isinstance(device_id, str):
            device_id = uuid.UUID(device_id)
            
        # Add new key
        new_key = DeviceKey(
            device_id=device_id,
            ecc_public_key=obj_in.public_key_pem,
            key_fingerprint=fingerprint,
            private_key_vault_path=f"dummy/path/{fingerprint[:8]}.pem",
            is_active=True,
            key_version=len(active_keys) + 1,
        )
        db.add(new_key)
        
        # Mark device as active if it was just provisioned
        device = await DeviceService.get(db, device_id)
        if device and device.lifecycle_status == DeviceLifecycleStatus.REGISTERED:
            device.lifecycle_status = DeviceLifecycleStatus.ACTIVE
            db.add(device)

        await db.commit()
        await db.refresh(new_key)
        return new_key
