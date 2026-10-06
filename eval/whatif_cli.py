"""
CLI tool for running automated What-If analysis stress tests on scenario snapshots.
Usage:
  python -m eval.whatif_cli --scenario data/scenarios/run_001 --remove_asset A-0001
"""

import argparse
import sys
from state.store import LiveStateStore
from optimize.solver import CPSatOptimizer
from eval.whatif_engine import WhatIfEngine, WhatIfHypothesis


def main():
    parser = argparse.ArgumentParser(description="Run What-If Analysis Stress Test on scenario snapshot.")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario directory")
    parser.add_argument("--remove_asset", type=str, default=None, help="Asset ID to remove hypothetically")
    parser.add_argument("--inject_urgent_task", action="store_true", help="Inject priority 5 urgent task")

    args = parser.parse_args()

    try:
        store = LiveStateStore()
        snapshot = store.initialize_from_parquet_dir(args.scenario)

        solver = CPSatOptimizer()
        current_plan = solver.solve(snapshot)

        hypothesis = WhatIfHypothesis(
            remove_asset_id=args.remove_asset,
            add_task={
                "task_id": "T-HYPO-999",
                "priority": 5,
                "task_type": "urgent",
                "required_resource_type": "LIGHT_TRANSPORT",
            }
            if args.inject_urgent_task
            else None,
            time_limit_sec=2.0,
        )

        engine = WhatIfEngine()
        result = engine.evaluate_hypothesis(snapshot, current_plan, hypothesis)

        print("==================================================")
        print("AAOP What-If Hypothetical Stress Test Analysis")
        print("==================================================")
        print(f"Scenario:                    {args.scenario}")
        print(f"Baseline Plan ID:            {result.baseline_plan_id}")
        print(f"What-If Plan ID:             {result.whatif_plan_id}")
        print("Hypothesis Summary:")
        for s in result.hypothesis_summary:
            print(f"  - {s}")
        print("--------------------------------------------------")
        print(f"Baseline Objective Score:    {result.current_metrics.objective_value:.2f}")
        print(f"What-If Objective Score:     {result.whatif_metrics.objective_value:.2f}")
        print(f"Objective Difference:        {result.objective_difference:+.2f}")
        print(f"Coverage Difference:         {result.coverage_difference*100:+.2f}%")
        print(f"Resource Utilization Delta:  {result.resource_utilization_difference*100:+.2f}%")
        print(f"Plan Churn Score:            {result.plan_churn_score*100:.1f}%")
        print(f"Newly Infeasible Tasks:      {len(result.new_infeasibilities)}")
        for t_id in result.new_infeasibilities:
            print(f"  * {t_id}")
        print("==================================================")

    except Exception as e:
        print(f"What-If CLI error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
