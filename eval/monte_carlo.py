"""
Monte Carlo Experiment Framework.
Runs multi-seed stochastic benchmark experiments across configurations (small, medium, large, degraded)
and compares Greedy, CP-SAT (Static), and CP-SAT + ML (Predictive) solvers.
"""

from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from generator.scenario import generate_scenario
from state.store import LiveStateStore
from optimize.greedy import GreedyAllocator
from optimize.solver import CPSatOptimizer, OptimizerConfig
from optimize.ml_integrated_solver import MLIntegratedOptimizer


def run_single_seed_benchmark(
    config_path: str,
    seed: int,
    tmp_output_dir: str,
    time_limit_sec: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Generates a scenario for a specific seed and runs all 3 solvers on initial state.
    """
    manifest = generate_scenario(config_path, tmp_output_dir, override_seed=seed)

    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(tmp_output_dir)

    results: List[Dict[str, Any]] = []
    config = OptimizerConfig(time_limit_sec=time_limit_sec)

    # 1. Greedy Baseline
    g_allocator = GreedyAllocator()
    g_plan = g_allocator.solve(snapshot)
    results.append({
        "seed": seed,
        "config_name": manifest.row_counts,
        "solver": "Greedy",
        "priority_weighted_coverage": g_plan.metrics.priority_weighted_coverage,
        "high_priority_coverage": g_plan.metrics.high_priority_coverage,
        "tasks_served": g_plan.metrics.tasks_served,
        "tasks_unserved": g_plan.metrics.tasks_unserved,
        "resource_utilization": g_plan.metrics.resource_utilization,
        "objective_value": g_plan.metrics.objective_value,
        "runtime_ms": g_plan.metrics.runtime_ms,
    })

    # 2. CP-SAT Static Rules
    cp_solver = CPSatOptimizer(config=config)
    cp_plan = cp_solver.solve(snapshot)
    results.append({
        "seed": seed,
        "config_name": manifest.row_counts,
        "solver": "CP-SAT",
        "priority_weighted_coverage": cp_plan.metrics.priority_weighted_coverage,
        "high_priority_coverage": cp_plan.metrics.high_priority_coverage,
        "tasks_served": cp_plan.metrics.tasks_served,
        "tasks_unserved": cp_plan.metrics.tasks_unserved,
        "resource_utilization": cp_plan.metrics.resource_utilization,
        "objective_value": cp_plan.metrics.objective_value,
        "runtime_ms": cp_plan.metrics.runtime_ms,
    })

    # 3. CP-SAT + ML Predictive
    ml_solver = MLIntegratedOptimizer(solver_config=config)
    ml_plan = ml_solver.solve(snapshot)
    results.append({
        "seed": seed,
        "config_name": manifest.row_counts,
        "solver": "CP-SAT+ML",
        "priority_weighted_coverage": ml_plan.metrics.priority_weighted_coverage,
        "high_priority_coverage": ml_plan.metrics.high_priority_coverage,
        "tasks_served": ml_plan.metrics.tasks_served,
        "tasks_unserved": ml_plan.metrics.tasks_unserved,
        "resource_utilization": ml_plan.metrics.resource_utilization,
        "objective_value": ml_plan.metrics.objective_value,
        "runtime_ms": ml_plan.metrics.runtime_ms,
    })

    return results


def aggregate_monte_carlo_results(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes statistical aggregations (mean, std, median, p50, p95) per solver.
    """
    summary: Dict[str, Any] = {}

    for solver_name, group in df.groupby("solver"):
        summary[solver_name] = {
            "num_seeds": len(group),
            "priority_weighted_coverage": {
                "mean": round(float(group["priority_weighted_coverage"].mean()), 4),
                "std": round(float(group["priority_weighted_coverage"].std()), 4),
                "median": round(float(group["priority_weighted_coverage"].median()), 4),
                "p50": round(float(np.percentile(group["priority_weighted_coverage"], 50)), 4),
                "p95": round(float(np.percentile(group["priority_weighted_coverage"], 95)), 4),
            },
            "high_priority_coverage": {
                "mean": round(float(group["high_priority_coverage"].mean()), 4),
                "std": round(float(group["high_priority_coverage"].std()), 4),
            },
            "tasks_served": {
                "mean": round(float(group["tasks_served"].mean()), 2),
                "std": round(float(group["tasks_served"].std()), 2),
            },
            "objective_value": {
                "mean": round(float(group["objective_value"].mean()), 2),
                "std": round(float(group["objective_value"].std()), 2),
            },
            "runtime_ms": {
                "mean": round(float(group["runtime_ms"].mean()), 2),
                "p50": round(float(np.percentile(group["runtime_ms"], 50)), 2),
                "p95": round(float(np.percentile(group["runtime_ms"], 95)), 2),
            },
        }

    return summary
