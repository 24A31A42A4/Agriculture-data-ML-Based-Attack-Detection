"""Device management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession, ResearcherUser
from app.core.enums import DeviceLifecycleStatus
from app.schemas.device import (
    DeviceCreate,
    DeviceKeyCreate,
    DeviceKeyResponse,
    DeviceResponse,
    DeviceUpdate,
)
from app.services.device_service import DeviceService

router = APIRouter()


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    db: DbSession,
    device_in: DeviceCreate,
    current_user: ResearcherUser,
) -> DeviceResponse:
    """
    Register a new IoT device. Requires Admin or Researcher role.
    """
    # Check if device_id already exists
    existing = await DeviceService.get_by_device_id(db, device_id=device_in.device_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A device with this ID already exists.",
        )
        
    device = await DeviceService.create(
        db, obj_in=device_in, registered_by=current_user.id
    )
    return device


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    status_filter: DeviceLifecycleStatus | None = None,
) -> list[DeviceResponse]:
    """
    List registered devices.
    """
    devices = await DeviceService.get_multi(
        db, skip=skip, limit=limit, status=status_filter
    )
    return devices


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> DeviceResponse:
    """
    Get device details by ID.
    """
    device = await DeviceService.get(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_in: DeviceUpdate,
    db: DbSession,
    current_user: ResearcherUser,
) -> DeviceResponse:
    """
    Update a device. Requires Admin or Researcher role.
    """
    device = await DeviceService.get(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        
    device = await DeviceService.update(db, db_obj=device, obj_in=device_in)
    return device


@router.post("/{device_id}/reset-trust", response_model=DeviceResponse)
async def reset_device_trust(
    device_id: str,
    db: DbSession,
    current_user: ResearcherUser,
) -> DeviceResponse:
    """
    Reset a device's trust score to 100.0 for simulation purposes.
    """
    device = await DeviceService.get(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        
    device.trust_score = 100.0
    device.lifecycle_status = DeviceLifecycleStatus.REGISTERED
    await db.commit()
    await db.refresh(device)
    
    return device


@router.post("/{device_id}/keys", response_model=DeviceKeyResponse)
async def register_device_key(
    device_id: str,
    key_in: DeviceKeyCreate,
    db: DbSession,
    current_user: ResearcherUser,
) -> DeviceKeyResponse:
    """
    Register a new ECC public key for a device.
    This will deactivate any currently active key for this device.
    """
    device = await DeviceService.get(db, device_id=device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        
    key = await DeviceService.register_key(db, device_id=device_id, obj_in=key_in)
    return key


@router.get("/{device_id}/keys/active", response_model=DeviceKeyResponse)
async def get_active_device_key(
    device_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> DeviceKeyResponse:
    """
    Get the currently active public key for a device.
    """
    key = await DeviceService.get_active_key(db, device_id=device_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active key found for device")
    return key
