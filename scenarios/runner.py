"""
Demonstration Scenario Runner.
Executes repeatable, deterministic scenario demonstrations (baseline_day, surge_attrition, degraded_base),
simulating dynamic event streaming, state fusion, replan triggers, CP-SAT optimization, and explanation diffs.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List

from generator.scenario import generate_scenario
from ingest.replay import EventReplayer
from state.store import LiveStateStore
from optimize.replan import DynamicReplanner
from optimize.explain import PlanExplainer


def run_demo_scenario(scenario_config_file: str, scenario_def_file: str, output_dir: str) -> Dict[str, Any]:
    """
    Executes full scenario flow, logging state version updates, replans, plan diffs, and explanations.
    """
    print("==================================================")
    print(f"AAOP Scenario Demo Runner: {Path(scenario_def_file).stem}")
    print("==================================================")

    # 1. Generate Scenario Data & Event Stream
    manifest = generate_scenario(
        config_path=scenario_config_file,
        output_dir=output_dir,
        scenario_path=scenario_def_file,
    )

    print(f"Seed:               {manifest.seed}")
    print(f"Duration:           {manifest.date_range['duration_hours']} hours")
    print(f"Total Stream Events:{manifest.row_counts['events']}")
    print("==================================================")

    # 2. Initialize State Store & Dynamic Replanner
    store = LiveStateStore()
    store.initialize_from_parquet_dir(output_dir)

    replanner = DynamicReplanner(store=store)
    replayer = EventReplayer(f"{output_dir}/events.jsonl")

    prev_plan = None
    replans_log: List[Dict[str, Any]] = []

    for event in replayer.replay(speed_factor=0):
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

            log_entry = {
                "timestamp": event.timestamp,
                "event_kind": event.kind,
                "trigger_reason": res["replan_reason"],
                "state_version": snapshot.version.version,
                "objective_change": explanation.objective_change,
                "coverage_change": explanation.coverage_change,
                "plan_churn_score": explanation.plan_churn_score,
                "binding_constraints": explanation.binding_constraints,
                "reassignments_count": len(explanation.reassigned_tasks),
            }
            replans_log.append(log_entry)

            print(
                f"[{event.timestamp:5.2f}h | Version {snapshot.version.version:4d}] "
                f"REPLAN: {res['replan_reason']} | "
                f"Obj Delta: {explanation.objective_change:+.2f} | "
                f"Churn: {explanation.plan_churn_score*100:.1f}%"
            )

            prev_plan = curr_plan

    print("==================================================")
    print(f"Scenario Demo Complete: {len(replans_log)} replans executed.")
    print("==================================================")

    return {
        "manifest": manifest.model_dump(),
        "replans_count": len(replans_log),
        "replans_log": replans_log,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Repeatable AAOP Scenario Demonstration.")
    parser.add_argument("--config", type=str, default="configs/medium.yaml", help="Path to config YAML")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario definition YAML")
    parser.add_argument("--output", type=str, default="data/scenarios/demo_run", help="Output directory")

    args = parser.parse_args()

    try:
        run_demo_scenario(args.config, args.scenario, args.output)
    except Exception as e:
        print(f"Scenario demo error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
