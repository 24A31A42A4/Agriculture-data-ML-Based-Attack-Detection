"""
Feature Drift Monitoring Service.

Calculates Population Stability Index (PSI) and runs Kolmogorov-Smirnov (KS)
tests to detect data distribution shifts in incoming sensor data.
"""

import logging
import uuid
from datetime import datetime, timezone

import numpy as np
from scipy.stats import ks_2samp

from app.schemas.drift import DriftCheckResponse, FeatureDriftResult

logger = logging.getLogger(__name__)


class DriftService:
    """Service to monitor and detect feature drift in ML models."""

    @staticmethod
    def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
        """
        Calculate the Population Stability Index (PSI) for a continuous variable.
        """
        def scale_range(input, min_val, max_val):
            input += -(np.min(input))
            input /= np.max(input) / (max_val - min_val)
            input += min_val
            return input

        if len(expected) == 0 or len(actual) == 0:
            return 0.0

        breakpoints = np.arange(0, buckets + 1) / (buckets) * 100
        breakpoints = np.percentile(expected, breakpoints)

        expected_percents = np.histogram(expected, breakpoints)[0] / len(expected)
        actual_percents = np.histogram(actual, breakpoints)[0] / len(actual)

        # Avoid divide by zero
        expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
        actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)

        psi_value = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
        return float(psi_value)

    @staticmethod
    def evaluate_drift(feature_name: str, reference_data: list[float], current_data: list[float]) -> FeatureDriftResult:
        """
        Evaluate drift for a single feature using PSI and KS-test.
        """
        ref_arr = np.array(reference_data)
        cur_arr = np.array(current_data)
        
        # KS Test
        if len(ref_arr) == 0 or len(cur_arr) == 0:
            ks_stat, p_value = 0.0, 1.0
        else:
            ks_stat, p_value = ks_2samp(ref_arr, cur_arr)
            
        # PSI
        psi_score = DriftService.calculate_psi(ref_arr, cur_arr)
        
        # Severity evaluation
        # PSI < 0.1: No change
        # PSI >= 0.1 and < 0.25: Moderate change
        # PSI >= 0.25: Severe change
        is_drifting = False
        severity = "none"
        
        # Combine PSI and KS-test (p-value < 0.05 implies different distributions)
        if psi_score >= 0.25 or p_value < 0.01:
            is_drifting = True
            severity = "severe"
        elif psi_score >= 0.1 or p_value < 0.05:
            is_drifting = True
            severity = "moderate"
            
        return FeatureDriftResult(
            feature_name=feature_name,
            psi_score=round(float(psi_score), 4),
            ks_statistic=round(float(ks_stat), 4),
            ks_p_value=round(float(p_value), 4),
            is_drifting=is_drifting,
            drift_severity=severity
        )

    @staticmethod
    async def run_drift_check(reference_data_dict: dict[str, list[float]], current_data_dict: dict[str, list[float]]) -> DriftCheckResponse:
        """
        Run a full drift check across all provided features.
        
        In a real scenario, current_data_dict would be queried from the database 
        (e.g., recent sensor readings), and reference_data_dict would be loaded 
        from the reference baseline generated during training.
        """
        results = []
        drifting_count = 0
        max_severity = "none"
        
        for feature_name, ref_data in reference_data_dict.items():
            if feature_name not in current_data_dict:
                continue
                
            cur_data = current_data_dict[feature_name]
            result = DriftService.evaluate_drift(feature_name, ref_data, cur_data)
            results.append(result)
            
            if result.is_drifting:
                drifting_count += 1
                if result.drift_severity == "severe":
                    max_severity = "severe"
                elif result.drift_severity == "moderate" and max_severity == "none":
                    max_severity = "moderate"
                    
        overall_drift = drifting_count > 0
        
        recommendation = "No action needed."
        if max_severity == "severe":
            recommendation = "Severe drift detected. Model retraining is highly recommended."
        elif max_severity == "moderate":
            recommendation = "Moderate drift detected. Monitor closely; consider retraining soon."
            
        # Here we would normally record this check to the database and/or blockchain
            
        return DriftCheckResponse(
            check_id=f"chk_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc),
            overall_drift_detected=overall_drift,
            features_drifting_count=drifting_count,
            feature_results=results,
            severity=max_severity,
            recommendation=recommendation
        )
