from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.redis import get_redis
from app.models.device import Device
from app.schemas.sensor_data import SensorDataIngest, SensorDataResponse
from app.security.gateway import verify_device_request
from app.services.sensor_service import SensorDataService

router = APIRouter()


@router.post(
    "/data",
    response_model=SensorDataResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Encrypted Sensor Data",
    description=(
        "IoT devices use this endpoint to submit AES-encrypted sensor readings. "
        "The request MUST pass the 6-stage Security Gateway (Whitelist, Rate Limiting, "
        "Timestamp drift, Nonce replay, and ECC Signature verification)."
    )
)
async def ingest_sensor_data(
    payload: SensorDataIngest,
    request: Request,
    x_signature: str = Header(..., description="Base64 encoded ECC signature"),
    x_nonce: str = Header(..., description="Unique one-time string"),
    x_timestamp: str = Header(..., description="ISO 8601 UTC timestamp"),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis),
    device: Device = Depends(verify_device_request),
):
    """
    Ingest data after it passes the Security Gateway middleware.
    """
    sensor_data = await SensorDataService.ingest_data(
        db=db,
        redis_client=redis_client,
        device=device,
        payload=payload,
        signature=x_signature,
        nonce=x_nonce,
        timestamp=x_timestamp
    )
    
    return sensor_data
