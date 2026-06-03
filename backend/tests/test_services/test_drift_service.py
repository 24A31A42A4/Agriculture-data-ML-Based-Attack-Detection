import pytest
import numpy as np
from app.services.drift_service import DriftService


def test_calculate_psi_no_drift():
    # Same distribution
    np.random.seed(42)
    expected = np.random.normal(0, 1, 1000)
    actual = np.random.normal(0, 1, 1000)
    
    psi = DriftService.calculate_psi(expected, actual)
    assert psi < 0.1  # Less than 0.1 is considered no drift


def test_calculate_psi_moderate_drift():
    # Slight shift in mean
    np.random.seed(42)
    expected = np.random.normal(0, 1, 1000)
    actual = np.random.normal(0.3, 1, 1000)
    
    psi = DriftService.calculate_psi(expected, actual)
    assert 0.1 <= psi < 0.25  # Moderate drift


def test_calculate_psi_severe_drift():
    # Large shift in mean and variance
    np.random.seed(42)
    expected = np.random.normal(0, 1, 1000)
    actual = np.random.normal(2, 2, 1000)
    
    psi = DriftService.calculate_psi(expected, actual)
    assert psi >= 0.25  # Severe drift


def test_evaluate_drift_ks_test():
    np.random.seed(42)
    expected = np.random.normal(0, 1, 1000).tolist()
    actual = np.random.normal(0, 1, 1000).tolist()
    
    res = DriftService.evaluate_drift("feature1", expected, actual)
    assert res.feature_name == "feature1"
    assert res.is_drifting is False
    assert res.drift_severity == "none"
    assert res.ks_p_value > 0.05
    

@pytest.mark.asyncio
async def test_run_drift_check():
    np.random.seed(42)
    ref_dict = {
        "F1": np.random.normal(0, 1, 1000).tolist(),
        "F2": np.random.normal(10, 2, 1000).tolist(),
    }
    cur_dict = {
        "F1": np.random.normal(0, 1, 1000).tolist(),    # No drift
        "F2": np.random.normal(20, 2, 1000).tolist(),   # Severe drift
    }
    
    res = await DriftService.run_drift_check(ref_dict, cur_dict)
    
    assert res.overall_drift_detected is True
    assert res.features_drifting_count == 1
    assert res.severity == "severe"
    
    f1_res = next(f for f in res.feature_results if f.feature_name == "F1")
    assert f1_res.is_drifting is False
    
    f2_res = next(f for f in res.feature_results if f.feature_name == "F2")
    assert f2_res.is_drifting is True
    assert f2_res.drift_severity == "severe"
