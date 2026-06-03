import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.ml_service import MLService
from app.core.enums import ModelType
from app.models.model_registry import ModelRegistry


@pytest.fixture
async def mock_models(db_session: AsyncSession) -> list[ModelRegistry]:
    models = [
        ModelRegistry(
            model_name="test_rf",
            model_display_name="Random Forest",
            model_type=ModelType.ENSEMBLE_BAGGING,
            file_path="dummy_path.pkl",
            accuracy=0.95,
            roc_auc=0.96,
            is_active=True
        ),
        ModelRegistry(
            model_name="test_xgb",
            model_display_name="XGBoost",
            model_type=ModelType.ENSEMBLE_BOOSTING,
            file_path="dummy_path2.pkl",
            accuracy=0.98,
            roc_auc=0.99,
            is_active=True
        ),
        ModelRegistry(
            model_name="test_lr",
            model_display_name="Logistic Regression",
            model_type=ModelType.LINEAR,
            file_path="dummy_path3.pkl",
            accuracy=0.85,
            roc_auc=0.88,
            is_active=False  # Inactive model
        )
    ]
    
    db_session.add_all(models)
    await db_session.commit()
    return models


@pytest.fixture
def mock_features() -> dict[str, float]:
    return {
        "WaterLevel": 10.5,
        "Temperature": 25.0,
        "Humidity": 60.0,
        "Ph": 6.5,
        "Rainfall": 12.0,
        "FertilizerApp": 0.0,
        "PesticideApp": 0.0,
        "SoilMoisture": 45.0,
        "LightIntensity": 1200.0,
        "WindSpeed": 5.0,
        "CO2Levels": 400.0,
        "PlantHeight": 15.0,
        "LeafAreaIndex": 2.5,
        "Yield": 0.0,
        "NDVI": 0.6,
        "SoilEC": 1.2,
        "SoilOrganicMatter": 3.5,
        "NitrogenLevel": 50.0,
        "PhosphorusLevel": 20.0,
        "PotassiumLevel": 30.0,
        "BatteryLevel": 95.0
    }


@pytest.mark.asyncio
async def test_get_active_models(db_session: AsyncSession, mock_models: list[ModelRegistry]):
    active_models = await MLService.get_active_models(db_session)
    assert len(active_models) == 2
    assert all(m.is_active for m in active_models)


@pytest.mark.asyncio
async def test_select_best_model(db_session: AsyncSession, mock_models: list[ModelRegistry]):
    # Should pick test_xgb because it has the highest roc_auc (0.99)
    best = await MLService.select_best_model(db_session)
    assert best.model_name == "test_xgb"
    
    # Should pick test_rf if we filter by type ENSEMBLE_BAGGING
    best_rf = await MLService.select_best_model(db_session, model_type=ModelType.ENSEMBLE_BAGGING.value)
    assert best_rf.model_name == "test_rf"


@pytest.mark.asyncio
async def test_predict_single(db_session: AsyncSession, mock_models: list[ModelRegistry], mock_features: dict[str, float]):
    # Predict using the best model automatically
    res = await MLService.predict_single(db_session, mock_features)
    assert res.model_name == "test_xgb"
    assert res.prediction == 0
    assert res.label == "Normal"
    
    # Predict using a specific model
    res_rf = await MLService.predict_single(db_session, mock_features, model_name="test_rf")
    assert res_rf.model_name == "test_rf"
    assert res_rf.prediction == 0


@pytest.mark.asyncio
async def test_predict_all(db_session: AsyncSession, mock_models: list[ModelRegistry], mock_features: dict[str, float]):
    res = await MLService.predict_all(db_session, mock_features)
    
    # There are 2 active models
    assert len(res.predictions) == 2
    
    names = {p.model_name for p in res.predictions}
    assert "test_rf" in names
    assert "test_xgb" in names
    
    # Check consensus (since mock returns 0 always, it should be Normal)
    assert res.consensus["majority_vote"] == "Normal"
    assert res.consensus["agreement_ratio"] == 1.0
    assert res.recommended_model == "test_xgb"
