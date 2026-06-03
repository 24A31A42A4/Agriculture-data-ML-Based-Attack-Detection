import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import async_session_factory
from app.services.attack_sim_service import AttackSimService
import traceback

async def run_test():
    async with async_session_factory() as db:
        device_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        try:
            res = await AttackSimService.simulate_ml_anomaly(db, device_id)
            print("RESULT DETAILS:")
            print(res.details)
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
