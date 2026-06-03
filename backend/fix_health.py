import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models.device import Device
from app.models.device_health import DeviceHealth
from app.services.device_health_service import DeviceHealthService

async def fix_health():
    engine = create_async_engine("sqlite+aiosqlite:///c:/Users/Alisha/Desktop/Agri_another/Agriculture-data-ML-Based-Attack-Detection/backend/agri_iot.db")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as db:
        devices = (await db.execute(select(Device))).scalars().all()
        for d in devices:
            health = await DeviceHealthService.get_or_create_health(db, d.id)
            await DeviceHealthService._recompute_health_score(db, health)
        await db.commit()
        print(f"Created/updated health records for {len(devices)} devices.")

if __name__ == "__main__":
    asyncio.run(fix_health())
