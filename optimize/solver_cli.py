"""
CLI tool comparing Greedy Baseline vs OR-Tools CP-SAT Optimizer.
Usage:
  python -m optimize.solver_cli --scenario data/scenarios/run_001 --time_limit 2.0
"""

import argparse
import sys
from state.store import LiveStateStore
from optimize.greedy import GreedyAllocator
from optimize.solver import CPSatOptimizer, OptimizerConfig


def main():
    parser = argparse.ArgumentParser(description="Benchmark Greedy Baseline vs CP-SAT Optimizer.")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario directory")
    parser.add_argument("--time_limit", type=float, default=2.0, help="CP-SAT time limit in seconds")

    args = parser.parse_args()

    try:
        store = LiveStateStore()
        snapshot = store.initialize_from_parquet_dir(args.scenario)

        # 1. Greedy Baseline
        greedy = GreedyAllocator()
        plan_greedy = greedy.solve(snapshot)

        # 2. CP-SAT Optimizer
        config = OptimizerConfig(time_limit_sec=args.time_limit)
        cpsat = CPSatOptimizer(config=config)
        plan_cpsat = cpsat.solve(snapshot)

        print("==================================================")
        print("AAOP Optimization Comparison Benchmark")
        print("==================================================")
        print(f"Scenario:                   {args.scenario}")
        print(f"State Version:              {snapshot.version.version}")
        print(f"Total Tasks:                {len(snapshot.tasks)}")
        print(f"Total Assets:               {len(snapshot.assets)}")
        print("--------------------------------------------------")
        print("METRIC                        | GREEDY    | CP-SAT")
        print("--------------------------------------------------")
        print(f"Tasks Served                  | {plan_greedy.metrics.tasks_served:<9} | {plan_cpsat.metrics.tasks_served:<9}")
        print(f"Tasks Unserved                | {plan_greedy.metrics.tasks_unserved:<9} | {plan_cpsat.metrics.tasks_unserved:<9}")
        print(f"Priority-Weighted Coverage    | {plan_greedy.metrics.priority_weighted_coverage*100:6.2f}%   | {plan_cpsat.metrics.priority_weighted_coverage*100:6.2f}%")
        print(f"High-Priority Coverage        | {plan_greedy.metrics.high_priority_coverage*100:6.2f}%   | {plan_cpsat.metrics.high_priority_coverage*100:6.2f}%")
        print(f"Resource Utilization          | {plan_greedy.metrics.resource_utilization*100:6.2f}%   | {plan_cpsat.metrics.resource_utilization*100:6.2f}%")
        print(f"Objective Value               | {plan_greedy.metrics.objective_value:<9.2f} | {plan_cpsat.metrics.objective_value:<9.2f}")
        print(f"Solver Runtime (ms)           | {plan_greedy.metrics.runtime_ms:<9.2f} | {plan_cpsat.metrics.runtime_ms:<9.2f}")
        print("==================================================")

    except Exception as e:
        print(f"Solver comparison error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
