import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.database.session import async_session_factory
from app.models.user import User
from app.models.model_registry import ModelRegistry
from app.core.enums import UserRole, ModelType
from app.services.device_health_service import DeviceHealthService
from sqlalchemy import select

from app.models.base import Base
from app.database.session import engine

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def seed():
    await init_db()
    async with async_session_factory() as db:
        # Check if admin already exists
        result = await db.execute(select(User).where(User.email == "admin@example.com"))
        admin = result.scalars().first()
        
        if not admin:
            print("Creating admin user...")
            hashed_pw = pwd_context.hash("admin_password")
            admin = User(
                email="admin@example.com",
                hashed_password=hashed_pw,
                full_name="System Admin",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            await db.commit()
            print("Admin created: admin@example.com / admin_password")
        else:
            print("Admin user already exists.")

        # Check if models exist
        result = await db.execute(select(ModelRegistry))
        existing_models = result.scalars().all()
        if not existing_models:
            print("Creating dummy ML models...")
            models = [
                ModelRegistry(
                    model_name="rf_v1",
                    model_display_name="Random Forest Anomaly Detector",
                    model_type=ModelType.ENSEMBLE_BAGGING,
                    model_version="1.0.0",
                    file_path="models/rf_v1.pkl",
                    accuracy=0.995,
                    precision_score=0.991,
                    recall_score=0.996,
                    f1_score=0.993,
                    roc_auc=0.998,
                    mcc=0.990,
                    specificity=0.0,
                    feature_count=21,
                    training_time_seconds=0.0,
                    avg_inference_time_ms=1.2,
                    model_size_bytes=0,
                    is_active=True,
                ),
                ModelRegistry(
                    model_name="xgb_v1",
                    model_display_name="XGBoost Classifier",
                    model_type=ModelType.ENSEMBLE_BOOSTING,
                    model_version="1.0.0",
                    file_path="models/xgb_v1.pkl",
                    accuracy=0.997,
                    precision_score=0.995,
                    recall_score=0.998,
                    f1_score=0.996,
                    roc_auc=0.999,
                    mcc=0.994,
                    specificity=0.0,
                    feature_count=21,
                    training_time_seconds=0.0,
                    avg_inference_time_ms=1.5,
                    model_size_bytes=0,
                    is_active=True,
                ),
            ]
            db.add_all(models)
            await db.commit()
            print("Dummy models created.")
        else:
            print("Models already exist.")
            
        # Create dummy device for simulation
        from app.models.device import Device
        import uuid
        dummy_device_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = await db.execute(select(Device).where(Device.id == dummy_device_id))
        
        # Get admin user ID
        admin_user = await db.execute(select(User).where(User.email == "admin@example.com"))
        admin = admin_user.scalar_one_or_none()
        
        if not result.scalar_one_or_none():
            print("Creating dummy device...")
            dummy_device = Device(
                id=dummy_device_id,
                device_id="SIM-NODE-01",
                device_name="Simulation Node 01",
                device_type="soil_moisture",
                is_whitelisted=True,
                trust_score=100.0,
                registered_by=admin.id if admin else None
            )
            db.add(dummy_device)
            await db.commit()
            
            # Create associated health record
            health = await DeviceHealthService.get_or_create_health(db, dummy_device_id)
            await DeviceHealthService._recompute_health_score(db, health)
            await db.commit()
            
            print("Dummy device created.")
        else:
            print("Dummy device already exists.")

        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
