"""
CLI tool for running end-to-end dynamic replanning pipeline on scenario event streams.
Usage:
  python -m optimize.replan_cli --scenario data/scenarios/run_001
"""

import argparse
import sys
import numpy as np

from ingest.replay import EventReplayer
from state.store import LiveStateStore
from optimize.replan import DynamicReplanner


def main():
    parser = argparse.ArgumentParser(description="Run Dynamic Replanning Pipeline on scenario event stream.")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario directory")
    parser.add_argument("--max_events", type=int, default=None, help="Max events to process")

    args = parser.parse_args()

    try:
        store = LiveStateStore()
        store.initialize_from_parquet_dir(args.scenario)

        replanner = DynamicReplanner(store=store)
        replayer = EventReplayer(f"{args.scenario}/events.jsonl")

        print("==================================================")
        print("AAOP Dynamic Replanning Engine - Benchmark")
        print("==================================================")
        print(f"Scenario: {args.scenario}")
        print("==================================================")

        event_count = 0
        replans_count = 0

        event_to_plan_latencies = []
        state_update_latencies = []
        cpsat_solve_times = []

        for event in replayer.replay(speed_factor=0, max_events=args.max_events):
            event_count += 1
            res = replanner.handle_event(event)

            state_update_latencies.append(res["state_update_ms"])
            event_to_plan_latencies.append(res["event_to_plan_latency_ms"])

            if res["replan_triggered"]:
                replans_count += 1
                cpsat_solve_times.append(res["cpsat_solve_time_ms"])
                print(
                    f"[{res['timestamp']:5.2f}h | Version {res['state_version']:4d}] "
                    f"REPLAN TRIGGERED ({res['replan_reason']}) | "
                    f"CP-SAT: {res['cpsat_solve_time_ms']:.2f}ms | "
                    f"Event-to-Plan Latency: {res['event_to_plan_latency_ms']:.2f}ms"
                )

        p50_latency = float(np.percentile(event_to_plan_latencies, 50))
        p95_latency = float(np.percentile(event_to_plan_latencies, 95))
        avg_cpsat = float(np.mean(cpsat_solve_times)) if cpsat_solve_times else 0.0

        print("\nDynamic Replanning Benchmark Summary:")
        print(f"Total Events Processed:    {event_count}")
        print(f"Replans Triggered:         {replans_count} ({replans_count/max(1, event_count)*100:.1f}%)")
        print(f"Average State Update Time: {np.mean(state_update_latencies):.3f} ms")
        print(f"Average CP-SAT Solve Time: {avg_cpsat:.3f} ms")
        print(f"P50 Event-to-Plan Latency: {p50_latency:.3f} ms")
        print(f"P95 Event-to-Plan Latency: {p95_latency:.3f} ms")
        print("==================================================")

    except Exception as e:
        print(f"Replanning error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
