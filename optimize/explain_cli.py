"""
CLI tool for demonstrating structured explanation generation during dynamic replanning.
Usage:
  python -m optimize.explain_cli --scenario data/scenarios/run_001
"""

import argparse
import sys
import json

from ingest.replay import EventReplayer
from state.store import LiveStateStore
from optimize.replan import DynamicReplanner
from optimize.explain import PlanExplainer


def main():
    parser = argparse.ArgumentParser(description="Demonstrate structured explanation engine during replanning.")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario directory")
    parser.add_argument("--max_events", type=int, default=15, help="Max events to process")

    args = parser.parse_args()

    try:
        store = LiveStateStore()
        store.initialize_from_parquet_dir(args.scenario)

        replanner = DynamicReplanner(store=store)
        replayer = EventReplayer(f"{args.scenario}/events.jsonl")

        print("==================================================")
        print("AAOP Explanation Engine - Replanning Demonstration")
        print("==================================================")

        prev_plan = None
        for event in replayer.replay(speed_factor=0, max_events=args.max_events):
            res = replanner.handle_event(event)

            if res["replan_triggered"]:
                curr_plan = res["current_plan"]
                snapshot = store.get_current_state()

                explanation = PlanExplainer.explain_diff(
                    old_plan=prev_plan,
                    new_plan=curr_plan,
                    snapshot=snapshot,
                    trigger_reason=res["replan_reason"],
                )

                print("\n--------------------------------------------------")
                print(f"REPLAN TRIGGERED at t={event.timestamp}h (Event: {event.kind})")
                print(f"Trigger Reason:    {res['replan_reason']}")
                print(f"State Version:     {explanation.state_version}")
                print(f"Objective Change:  {explanation.objective_change:+.2f}")
                print(f"Coverage Change:   {explanation.coverage_change*100:+.2f}%")
                print(f"Plan Churn Score:  {explanation.plan_churn_score*100:.1f}%")
                print("Binding Constraints:")
                for c in explanation.binding_constraints:
                    print(f"  - {c}")

                print("Reassignment Details (Sample):")
                for r in explanation.reassigned_tasks[:3]:
                    print(f"  * Task {r.task_id}: [{r.previous_asset_id} -> {r.new_asset_id}] ({r.reassignment_type})")
                    for reason in r.primary_reasons:
                        print(f"      - {reason}")

                prev_plan = curr_plan

        print("==================================================")

    except Exception as e:
        print(f"Explanation error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
