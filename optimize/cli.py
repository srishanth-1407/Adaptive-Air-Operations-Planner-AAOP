"""
CLI Tool for benchmark execution of Greedy Allocator.
Usage:
  python -m optimize.cli --scenario data/scenarios/run_001
"""

import argparse
import sys
from state.store import LiveStateStore
from optimize.greedy import GreedyAllocator


def main():
    parser = argparse.ArgumentParser(description="Run Greedy Baseline Allocator on a scenario snapshot.")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario directory")

    args = parser.parse_args()

    try:
        store = LiveStateStore()
        snapshot = store.initialize_from_parquet_dir(args.scenario)

        allocator = GreedyAllocator()
        plan = allocator.solve(snapshot)

        print("==================================================")
        print("AAOP Greedy Baseline Allocator - Benchmark")
        print("==================================================")
        print(f"Scenario:                    {args.scenario}")
        print(f"State Version:               {plan.state_version}")
        print(f"Tasks Served:                {plan.metrics.tasks_served}")
        print(f"Tasks Unserved:              {plan.metrics.tasks_unserved}")
        print(f"Priority-Weighted Coverage:  {plan.metrics.priority_weighted_coverage * 100:.2f}%")
        print(f"High-Priority Coverage:      {plan.metrics.high_priority_coverage * 100:.2f}%")
        print(f"Resource Utilization:        {plan.metrics.resource_utilization * 100:.2f}%")
        print(f"Objective Value:             {plan.metrics.objective_value}")
        print(f"Solver Runtime:              {plan.metrics.runtime_ms:.2f} ms")
        print("==================================================")

    except Exception as e:
        print(f"Greedy optimization error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
