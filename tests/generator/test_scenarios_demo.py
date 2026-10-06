"""
Unit and integration tests for demonstration scenarios (scenarios/runner.py).
"""

import pytest
from scenarios.runner import run_demo_scenario


def test_baseline_day_scenario_demo(tmp_path):
    out_dir = tmp_path / "baseline_demo"
    res = run_demo_scenario(
        scenario_config_file="configs/small.yaml",
        scenario_def_file="scenarios/baseline_day.yaml",
        output_dir=str(out_dir),
    )

    assert res["manifest"]["seed"] == 42
    assert res["replans_count"] > 0


def test_surge_attrition_scenario_demo(tmp_path):
    out_dir = tmp_path / "surge_demo"
    res = run_demo_scenario(
        scenario_config_file="configs/small.yaml",
        scenario_def_file="scenarios/surge_attrition.yaml",
        output_dir=str(out_dir),
    )

    assert res["manifest"]["seed"] == 101
    assert res["replans_count"] > 0


def test_degraded_base_scenario_demo(tmp_path):
    out_dir = tmp_path / "degraded_demo"
    res = run_demo_scenario(
        scenario_config_file="configs/small.yaml",
        scenario_def_file="scenarios/degraded_base.yaml",
        output_dir=str(out_dir),
    )

    assert res["manifest"]["seed"] == 202
    assert res["replans_count"] > 0
