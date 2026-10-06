"""
CLI tool to test state fusion and historical version reconstruction.
Usage:
  python -m state.cli --scenario data/scenarios/run_001
"""

import argparse
import sys
import time
from ingest.replay import EventReplayer
from state.store import LiveStateStore


def main():
    parser = argparse.ArgumentParser(description="Test state fusion and historical state reconstruction.")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario directory")

    args = parser.parse_args()

    try:
        store = LiveStateStore()
        init_snapshot = store.initialize_from_parquet_dir(args.scenario)
        replayer = EventReplayer(f"{args.scenario}/events.jsonl")

        print("==================================================")
        print("AAOP State Fusion Engine - Verification")
        print("==================================================")
        print(f"Scenario Dir:    {args.scenario}")
        print(f"Initial Version: {init_snapshot.version.version}")
        print(f"Initial Assets:  {len(init_snapshot.assets)}")
        print(f"Initial Tasks:   {len(init_snapshot.tasks)}")
        print("==================================================")

        start_time = time.time()
        for event in replayer.replay(speed_factor=0):
            store.process_event(event)

        elapsed = time.time() - start_time
        final_state = store.get_current_state()

        print(f"Final Version:   {final_state.version.version}")
        print(f"Elapsed Time:    {elapsed:.4f}s")
        print(f"Fusion Rate:     {len(replayer.events) / max(0.0001, elapsed):.2f} events/sec")

        # Test historical state reconstruction
        mid_version = len(replayer.events) // 2
        mid_state = store.get_snapshot_at_version(mid_version)
        print(f"Reconstructed Version {mid_version} successfully (Timestamp: {mid_state.version.timestamp})")
        print("==================================================")

    except Exception as e:
        print(f"State fusion error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
