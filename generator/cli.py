"""
Command-Line Interface for Scenario Generation.
Usage:
  python -m generator.cli --config configs/small.yaml --output data/scenarios/run_001
"""

import argparse
import sys
from pathlib import Path
from generator.scenario import generate_scenario


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic aviation scenario entities and event streams."
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to configuration YAML file (e.g., configs/small.yaml)",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to output directory (e.g., data/scenarios/run_001)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Optional path to scenario definition file (e.g., scenarios/surge_attrition.yaml)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random seed",
    )

    args = parser.parse_args()

    try:
        manifest = generate_scenario(
            config_path=args.config,
            output_dir=args.output,
            scenario_path=args.scenario,
            override_seed=args.seed,
        )

        print("==================================================")
        print("AAOP Synthetic Scenario Generator - Run Complete")
        print("==================================================")
        print(f"Seed:           {manifest.seed}")
        print(f"Config Hash:    {manifest.config_hash[:12]}...")
        print(f"Bases:          {manifest.row_counts.get('bases', 0)}")
        print(f"Assets:         {manifest.row_counts.get('assets', 0)}")
        print(f"Crews:          {manifest.row_counts.get('crews', 0)}")
        print(f"Tasks:          {manifest.row_counts.get('tasks', 0)}")
        print(f"Weather cells:  {manifest.row_counts.get('weather_cells', 0)}")
        print(f"Airspace zones: {manifest.row_counts.get('airspace_zones', 0)}")
        print(f"Events:         {manifest.row_counts.get('events', 0)}")
        print(f"Output Path:    {Path(args.output).resolve()}")
        print("==================================================")

    except Exception as e:
        print(f"Error generating scenario: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
