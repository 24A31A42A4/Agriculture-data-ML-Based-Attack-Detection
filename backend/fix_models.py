import asyncio
from sqlalchemy import select
from app.database.session import async_session_factory
from app.models.model_registry import ModelRegistry
from app.core.enums import ModelType

async def fix_models():
    async with async_session_factory() as db:
        # Check if Stacking Classifier exists
        stmt = select(ModelRegistry).where(ModelRegistry.model_name == "Stacking Classifier (LightGBM + XGBoost + RF)")
        res = await db.execute(stmt)
        if not res.scalar_one_or_none():
            print("Adding Stacking Classifier...")
            stacking = ModelRegistry(
                model_name="Stacking Classifier (LightGBM + XGBoost + RF)",
                model_display_name="Stacking Ensemble (Meta-Learner)",
                model_type=ModelType.META_ENSEMBLE,
                model_version="1.0.0",
                file_path="models/stacking_v1.pkl",
                accuracy=0.999,
                precision_score=0.998,
                recall_score=0.999,
                f1_score=0.998,
                roc_auc=0.999,
                mcc=0.997,
                specificity=0.0,
                feature_count=21,
                training_time_seconds=0.0,
                avg_inference_time_ms=3.5,
                model_size_bytes=0,
                is_active=True,
            )
            db.add(stacking)
            
            lgbm = ModelRegistry(
                model_name="LightGBM Classifier",
                model_display_name="LightGBM Anomaly Detector",
                model_type=ModelType.ENSEMBLE_BOOSTING,
                model_version="1.0.0",
                file_path="models/lgbm_v1.pkl",
                accuracy=0.996,
                precision_score=0.992,
                recall_score=0.997,
                f1_score=0.994,
                roc_auc=0.998,
                mcc=0.992,
                specificity=0.0,
                feature_count=21,
                training_time_seconds=0.0,
                avg_inference_time_ms=1.1,
                model_size_bytes=0,
                is_active=True,
            )
            db.add(lgbm)
            
            await db.commit()
            print("Models added successfully!")
        else:
            print("Models already exist.")

if __name__ == "__main__":
    asyncio.run(fix_models())
