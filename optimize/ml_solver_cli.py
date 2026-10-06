"""
CLI tool for 3-Way Ablation Benchmark: Greedy vs CP-SAT (Static Rules) vs CP-SAT + ML (Predictive Risk-Aware).
Usage:
  python -m optimize.ml_solver_cli --scenario data/scenarios/run_001
"""

import argparse
import sys
from state.store import LiveStateStore
from optimize.greedy import GreedyAllocator
from optimize.solver import CPSatOptimizer, OptimizerConfig
from optimize.ml_integrated_solver import MLIntegratedOptimizer


def main():
    parser = argparse.ArgumentParser(description="Run 3-Way Ablation Benchmark: Greedy vs CP-SAT vs CP-SAT + ML.")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario directory")
    parser.add_argument("--time_limit", type=float, default=2.0, help="CP-SAT time limit in seconds")

    args = parser.parse_args()

    try:
        store = LiveStateStore()
        snapshot = store.initialize_from_parquet_dir(args.scenario)

        # 1. Greedy Baseline
        greedy = GreedyAllocator()
        plan_g = greedy.solve(snapshot)

        # 2. CP-SAT Static Rules
        config = OptimizerConfig(time_limit_sec=args.time_limit)
        cpsat = CPSatOptimizer(config=config)
        plan_cp = cpsat.solve(snapshot)

        # 3. CP-SAT + ML Predictive Risk-Aware
        ml_solver = MLIntegratedOptimizer(solver_config=config)
        plan_ml = ml_solver.solve(snapshot)

        print("==========================================================================")
        print("AAOP 3-Way Optimization Ablation Benchmark")
        print("==========================================================================")
        print(f"Scenario:                   {args.scenario}")
        print(f"State Version:              {snapshot.version.version}")
        print(f"Total Tasks:                {len(snapshot.tasks)}")
        print(f"Total Assets:               {len(snapshot.assets)}")
        print("--------------------------------------------------------------------------")
        print("METRIC                        | GREEDY    | CP-SAT (Static) | CP-SAT + ML")
        print("--------------------------------------------------------------------------")
        print(
            f"Tasks Served                  | {plan_g.metrics.tasks_served:<9} | {plan_cp.metrics.tasks_served:<15} | {plan_ml.metrics.tasks_served:<9}"
        )
        print(
            f"Tasks Unserved                | {plan_g.metrics.tasks_unserved:<9} | {plan_cp.metrics.tasks_unserved:<15} | {plan_ml.metrics.tasks_unserved:<9}"
        )
        print(
            f"Priority-Weighted Coverage    | {plan_g.metrics.priority_weighted_coverage*100:6.2f}%   | {plan_cp.metrics.priority_weighted_coverage*100:6.2f}%          | {plan_ml.metrics.priority_weighted_coverage*100:6.2f}%"
        )
        print(
            f"High-Priority Coverage        | {plan_g.metrics.high_priority_coverage*100:6.2f}%   | {plan_cp.metrics.high_priority_coverage*100:6.2f}%          | {plan_ml.metrics.high_priority_coverage*100:6.2f}%"
        )
        print(
            f"Resource Utilization          | {plan_g.metrics.resource_utilization*100:6.2f}%   | {plan_cp.metrics.resource_utilization*100:6.2f}%          | {plan_ml.metrics.resource_utilization*100:6.2f}%"
        )
        print(
            f"Objective Value               | {plan_g.metrics.objective_value:<9.2f} | {plan_cp.metrics.objective_value:<15.2f} | {plan_ml.metrics.objective_value:<9.2f}"
        )
        print(
            f"Solver Runtime (ms)           | {plan_g.metrics.runtime_ms:<9.2f} | {plan_cp.metrics.runtime_ms:<15.2f} | {plan_ml.metrics.runtime_ms:<9.2f}"
        )
        print("==========================================================================")

    except Exception as e:
        print(f"3-Way ablation benchmark error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
