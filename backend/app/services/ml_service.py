"""
ML Inference Service.

Handles model loading, pre-processing, inference, dynamic model selection,
and benchmarking multiple models against each other.
"""

import logging
import time
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_registry import ModelRegistry
from app.schemas.ml import ComparePredictionResponse, PredictionResult

logger = logging.getLogger(__name__)

# In a real environment, we would use joblib or pickle to load actual models.
# For this research framework implementation, we simulate the loaded model registry.
_LOADED_MODELS: dict[str, Any] = {}


import numpy as np

class DynamicModel:
    """A mathematically valid simulated model using genuine scikit-learn."""
    def __init__(self, name: str, m_type: str):
        self.name = name
        self.m_type = m_type
        
        # Initialize real models
        if "Stack" in name:
            from sklearn.linear_model import LogisticRegression
            self.model = LogisticRegression(random_state=42)
        elif "Random Forest" in name:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        elif "XGBoost" in name:
            try:
                from xgboost import XGBClassifier
                self.model = XGBClassifier(n_estimators=10, random_state=42)
            except ImportError:
                from sklearn.ensemble import GradientBoostingClassifier
                self.model = GradientBoostingClassifier(n_estimators=10, random_state=42)
        elif "LightGBM" in name:
            try:
                from lightgbm import LGBMClassifier
                self.model = LGBMClassifier(n_estimators=10, random_state=42)
            except ImportError:
                from sklearn.ensemble import HistGradientBoostingClassifier
                self.model = HistGradientBoostingClassifier(random_state=42)
        else:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(n_estimators=5, random_state=42)
            
        # Fit on synthetic distribution (21 features)
        # Normal data: mean=0, std=1. Attack data: mean=5, std=2
        # This guarantees predict_proba returns mathematically derived probabilities
        np.random.seed(42 + len(name))
        X_normal = np.random.normal(0, 1, (200, 21))
        y_normal = np.zeros(200)
        
        X_attack = np.random.normal(5, 2, (100, 21))
        y_attack = np.ones(100)
        
        X_train = np.vstack([X_normal, X_attack])
        y_train = np.concatenate([y_normal, y_attack])
        
        self.model.fit(X_train, y_train)
        
        self.feature_names = [
            "WaterLevel", "Temperature", "Humidity", "Ph", "Rainfall",
            "FertilizerApp", "PesticideApp", "SoilMoisture", "LightIntensity",
            "WindSpeed", "CO2Levels", "PlantHeight", "LeafAreaIndex", "Yield",
            "NDVI", "SoilEC", "SoilOrganicMatter", "NitrogenLevel",
            "PhosphorusLevel", "PotassiumLevel", "BatteryLevel"
        ]
        
    def predict(self, X: list[list[float]]) -> list[int]:
        return self.model.predict(X).tolist()
        
    def predict_proba(self, X: list[list[float]]) -> list[list[float]]:
        return self.model.predict_proba(X).tolist()
        
    def get_feature_importances(self) -> list[float]:
        if hasattr(self.model, "feature_importances_"):
            return self.model.feature_importances_.tolist()
        elif hasattr(self.model, "coef_"):
            return np.abs(self.model.coef_[0]).tolist()
        return [1.0/21] * 21


class MLService:
    """Service for ML predictions and model management."""

    @staticmethod
    async def get_active_models(db: AsyncSession) -> list[ModelRegistry]:
        """Fetch all active models from the database."""
        stmt = select(ModelRegistry).where(ModelRegistry.is_active == True)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def select_best_model(
        db: AsyncSession, criterion: str = "roc_auc", model_type: str | None = None
    ) -> ModelRegistry:
        """Select best active model by criterion, optionally filtered by type."""
        query = select(ModelRegistry).where(ModelRegistry.is_active == True)
        if model_type:
            query = query.where(ModelRegistry.model_type == model_type)
        
        # Prevent SQL injection by checking criterion
        valid_criteria = ["accuracy", "roc_auc", "f1_score", "mcc"]
        if criterion not in valid_criteria:
            criterion = "roc_auc"
            
        query = query.order_by(desc(getattr(ModelRegistry, criterion)))
        result = await db.execute(query)
        best_model = result.scalars().first()
        
        if not best_model:
            raise ValueError("No active models found in registry.")
            
        return best_model

    @staticmethod
    def _load_model_from_disk(model_name: str, model_type: str) -> Any:
        """Lazy-load a model from disk. Uses MockModel for dev environment."""
        if model_name not in _LOADED_MODELS:
            logger.info("Loading ML model into memory: %s", model_name)
            # In production:
            # path = f"app/ml/models/{model_name}.pkl"
            # _LOADED_MODELS[model_name] = joblib.load(path)
            
            # Dev dynamic sklearn model:
            _LOADED_MODELS[model_name] = DynamicModel(model_name, model_type)
            
        return _LOADED_MODELS[model_name]

    @staticmethod
    def _preprocess_features(features: dict[str, float]) -> list[list[float]]:
        """Preprocess features matching the Jupyter notebook pipeline."""
        # The 21 features in exact order used by the models
        feature_order = [
            "WaterLevel", "Temperature", "Humidity", "Ph", "Rainfall",
            "FertilizerApp", "PesticideApp", "SoilMoisture", "LightIntensity",
            "WindSpeed", "CO2Levels", "PlantHeight", "LeafAreaIndex", "Yield",
            "NDVI", "SoilEC", "SoilOrganicMatter", "NitrogenLevel",
            "PhosphorusLevel", "PotassiumLevel", "BatteryLevel"
        ]
        
        vector = [features.get(f, 0.0) for f in feature_order]
        
        # Scaling would be applied here using a loaded StandardScaler (.pkl)
        # return scaler.transform([vector])
        return [vector]

    @staticmethod
    async def predict_single(
        db: AsyncSession, features: dict[str, float], model_name: str | None = None
    ) -> PredictionResult:
        """Run inference using a specific model or the best available."""
        if model_name:
            stmt = select(ModelRegistry).where(ModelRegistry.model_name == model_name)
            result = await db.execute(stmt)
            model_info = result.scalar_one_or_none()
            if not model_info:
                raise ValueError(f"Model {model_name} not found.")
        else:
            model_info = await MLService.select_best_model(db)
            
        m_type = model_info.model_type.value if hasattr(model_info.model_type, "value") else model_info.model_type
        model = MLService._load_model_from_disk(model_info.model_name, m_type)
        X = MLService._preprocess_features(features)
        
        start_time = time.perf_counter()
        
        # Prediction
        prediction = model.predict(X)[0]
        
        # Probability if available
        probability = None
        confidence = None
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)[0]
            probability = probs[1] # Probability of class 1 (Attack)
            confidence = max(probs)
            
        feature_importances = None
        top_features = None
        if hasattr(model, "get_feature_importances"):
            importances = model.get_feature_importances()
            feature_importances = importances
            
            names = getattr(model, "feature_names", [])
            if names and len(names) == len(importances):
                paired = sorted(zip(names, importances), key=lambda x: x[1], reverse=True)
                top_features = [{"feature": k, "importance": float(v)} for k, v in paired[:3]]
                
        inference_time_ms = (time.perf_counter() - start_time) * 1000
                
        return PredictionResult(
            model_name=model_info.model_name,
            model_type=model_info.model_type.value if hasattr(model_info.model_type, "value") else model_info.model_type,
            prediction=int(prediction),
            label="Anomaly" if prediction == 1 else "Normal",
            probability=probability,
            confidence=confidence,
            inference_time_ms=inference_time_ms,
            accuracy=model_info.accuracy,
            roc_auc=model_info.roc_auc,
            feature_importances=feature_importances,
            top_features=top_features
        )

    @staticmethod
    async def predict_all(
        db: AsyncSession, features: dict[str, float]
    ) -> ComparePredictionResponse:
        """Run inference across all active models and determine a consensus."""
        active_models = await MLService.get_active_models(db)
        if not active_models:
            raise ValueError("No active models found in registry.")
            
        X = MLService._preprocess_features(features)
        
        predictions = []
        votes_for_anomaly = 0
        best_model_name = ""
        highest_auc = -1.0
        
        for m_info in active_models:
            m_type = m_info.model_type.value if hasattr(m_info.model_type, "value") else m_info.model_type
            model = MLService._load_model_from_disk(m_info.model_name, m_type)
            start_time = time.perf_counter()
            
            pred = model.predict(X)[0]
            if pred == 1:
                votes_for_anomaly += 1
                
            probability = None
            confidence = None
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(X)[0]
                probability = probs[1]
                confidence = max(probs)
                
            feature_importances = None
            top_features = None
            if hasattr(model, "get_feature_importances"):
                importances = model.get_feature_importances()
                feature_importances = importances
                
                names = getattr(model, "feature_names", [])
                if names and len(names) == len(importances):
                    paired = sorted(zip(names, importances), key=lambda x: x[1], reverse=True)
                    top_features = [{"feature": k, "importance": float(v)} for k, v in paired[:3]]
            
            inference_time = (time.perf_counter() - start_time) * 1000
            
            predictions.append(
                PredictionResult(
                    model_name=m_info.model_name,
                    model_type=m_info.model_type.value if hasattr(m_info.model_type, "value") else m_info.model_type,
                    prediction=int(pred),
                    label="Anomaly" if pred == 1 else "Normal",
                    probability=probability,
                    confidence=confidence,
                    inference_time_ms=inference_time,
                    accuracy=m_info.accuracy,
                    roc_auc=m_info.roc_auc,
                    feature_importances=feature_importances,
                    top_features=top_features
                )
            )
            
            if m_info.roc_auc > highest_auc:
                highest_auc = m_info.roc_auc
                best_model_name = m_info.model_name
                
        # Consensus: Simple majority voting
        total = len(predictions)
        ratio = votes_for_anomaly / total
        consensus_label = "Anomaly" if ratio > 0.5 else "Normal"
        agreement = ratio if ratio > 0.5 else (1.0 - ratio)
        
        return ComparePredictionResponse(
            input_features=features,
            predictions=predictions,
            consensus={
                "majority_vote": consensus_label,
                "agreement_ratio": agreement
            },
            recommended_model=best_model_name
        )
