"""
Unit and integration tests for ML Feature Pipeline, Training, Evaluation, and Inference (predict/train.py).
"""

import pytest
import numpy as np
import pandas as pd

from generator.scenario import load_config
from predict.history import generate_synthetic_history
from predict.train import train_and_evaluate_models
from predict.inference import MLInferenceEngine


@pytest.fixture
def synthetic_data(tmp_path):
    config, _ = load_config("configs/small.yaml")
    out_dir = tmp_path / "ml_test_data"
    generate_synthetic_history(config, num_days=10, output_dir=str(out_dir))
    return str(out_dir)


def test_ml_training_pipeline_readiness(synthetic_data, tmp_path):
    df = pd.read_parquet(f"{synthetic_data}/readiness_history.parquet")
    models_out = tmp_path / "models"

    results = train_and_evaluate_models(
        df=df,
        target_col="went_down_within_horizon",
        categorical_cols=["asset_type", "base_id", "current_status"],
        numerical_cols=["age", "hours_since_maintenance", "utilization_last_24h", "environmental_stress"],
        output_dir=str(models_out),
    )

    assert "Trivial_Baseline" in results
    assert "Logistic_Regression" in results
    assert "XGBoost" in results
    assert "LightGBM" in results

    # Verify metrics structure
    for m_name, m in results.items():
        assert "roc_auc" in m
        assert "pr_auc" in m
        assert "f1" in m
        assert "brier_score" in m
        assert "ece" in m
        assert 0.0 <= m["roc_auc"] <= 1.0
        assert 0.0 <= m["brier_score"] <= 1.0


def test_ml_inference_engine(synthetic_data, tmp_path):
    df = pd.read_parquet(f"{synthetic_data}/readiness_history.parquet")
    models_out = tmp_path / "inference_models"

    train_and_evaluate_models(
        df=df,
        target_col="went_down_within_horizon",
        categorical_cols=["asset_type", "base_id", "current_status"],
        numerical_cols=["age", "hours_since_maintenance", "utilization_last_24h", "environmental_stress"],
        output_dir=str(models_out),
    )

    model_file = str(models_out / "xgboost_went_down_within_horizon.joblib")
    engine = MLInferenceEngine(model_file)

    sample_sub = df.head(10)
    probs = engine.predict_proba(sample_sub)

    assert len(probs) == 10
    assert np.all((probs >= 0.0) & (probs <= 1.0))
