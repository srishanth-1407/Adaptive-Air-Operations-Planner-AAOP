"""
Unit and integration tests for synthetic history generator (predict/history.py).
"""

import json
from pathlib import Path
import pytest
import pandas as pd

from generator.scenario import load_config
from predict.history import generate_synthetic_history


@pytest.fixture
def sample_config():
    config, _ = load_config("configs/small.yaml")
    return config


def test_synthetic_history_generation(sample_config, tmp_path):
    out_dir = tmp_path / "synthetic_history_test"
    manifest = generate_synthetic_history(
        config=sample_config,
        num_days=7,
        output_dir=str(out_dir),
        label_noise_rate=0.05,
    )

    readiness_file = out_dir / "readiness_history.parquet"
    task_risk_file = out_dir / "task_risk_history.parquet"
    manifest_file = out_dir / "manifest.json"

    assert readiness_file.exists()
    assert task_risk_file.exists()
    assert manifest_file.exists()

    readiness_df = pd.read_parquet(readiness_file)
    task_risk_df = pd.read_parquet(task_risk_file)

    assert len(readiness_df) > 0
    assert len(task_risk_df) > 0

    # ENFORCE HIDDEN VARIABLE POLICY: latent_fragility MUST NOT be a column in features!
    assert "latent_fragility" not in readiness_df.columns
    assert "latent_fragility" not in task_risk_df.columns

    # Verify target columns
    assert "went_down_within_horizon" in readiness_df.columns
    assert "task_success" in task_risk_df.columns

    assert set(readiness_df["went_down_within_horizon"].unique()).issubset({0, 1})
    assert set(task_risk_df["task_success"].unique()).issubset({0, 1})


def test_synthetic_history_manifest(sample_config, tmp_path):
    out_dir = tmp_path / "manifest_history_test"
    manifest = generate_synthetic_history(
        config=sample_config,
        num_days=3,
        output_dir=str(out_dir),
    )

    raw_manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert raw_manifest["seed"] == sample_config.seed
    assert "readiness" in raw_manifest["datasets"]
    assert "task_risk" in raw_manifest["datasets"]
    assert "latent_fragility" not in raw_manifest["datasets"]["readiness"]["features"]
