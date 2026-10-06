"""
Unit and integration tests for Performance Engineering & Profiler (eval/perf_profile.py).
"""

import pytest
from eval.perf_profile import profile_pipeline_scale


def test_performance_profiler_small(tmp_path):
    tmp_dir = tmp_path / "perf_test_data"
    profile = profile_pipeline_scale(
        config_path="configs/small.yaml",
        scale_name="small",
        num_events=10,
        tmp_dir=str(tmp_dir),
    )

    assert profile["scale_name"] == "small"
    assert profile["ingest_throughput_eps"] > 0.0
    assert profile["avg_state_update_ms"] >= 0.0
    assert profile["cpsat_runtime_ms"] >= 0.0
    assert profile["end_to_end_latency_ms"] >= 0.0
    assert profile["memory_mb"] > 0.0
    assert profile["primary_bottleneck"] in [
        "State Update",
        "Feature Gen",
        "ML Inference",
        "Greedy Solver",
        "CP-SAT Solver",
    ]
