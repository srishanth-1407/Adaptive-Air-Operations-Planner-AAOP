"""
Unit and integration tests for Monte Carlo benchmarking framework (eval/monte_carlo.py).
"""

import json
from pathlib import Path
import pytest
import pandas as pd

from eval.monte_carlo import run_single_seed_benchmark, aggregate_monte_carlo_results
from eval.benchmarks import run_monte_carlo_suite


@pytest.fixture
def benchmark_dir(tmp_path):
    out_dir = tmp_path / "mc_test_benchmarks"
    return str(out_dir)


def test_single_seed_benchmark(benchmark_dir):
    records = run_single_seed_benchmark(
        config_path="configs/small.yaml",
        seed=101,
        tmp_output_dir=benchmark_dir,
        time_limit_sec=0.5,
    )

    assert len(records) == 3  # Greedy, CP-SAT, CP-SAT+ML
    solvers = {r["solver"] for r in records}
    assert solvers == {"Greedy", "CP-SAT", "CP-SAT+ML"}

    for r in records:
        assert 0.0 <= r["priority_weighted_coverage"] <= 1.0
        assert r["runtime_ms"] >= 0.0


def test_monte_carlo_suite_and_aggregation(benchmark_dir):
    manifest = run_monte_carlo_suite(
        config_path="configs/small.yaml",
        num_seeds=3,
        output_dir=benchmark_dir,
        time_limit_sec=0.5,
    )

    out_path = Path(benchmark_dir)
    assert (out_path / "benchmark_results.parquet").exists()
    assert (out_path / "manifest.json").exists()

    assert manifest["num_seeds"] == 3
    assert "Greedy" in manifest["solver_comparison"]
    assert "CP-SAT" in manifest["solver_comparison"]
    assert "CP-SAT+ML" in manifest["solver_comparison"]

    df = pd.read_parquet(out_path / "benchmark_results.parquet")
    assert len(df) == 9  # 3 seeds * 3 solvers
