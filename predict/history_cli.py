"""
CLI tool for generating synthetic historical ML datasets (Readiness + Task Risk).
Usage:
  python -m predict.history_cli --config configs/small.yaml --days 30 --output data/synthetic_history
"""

import argparse
import sys
from pathlib import Path
from generator.scenario import load_config
from predict.history import generate_synthetic_history


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic operational history for ML modeling.")
    parser.add_argument("--config", type=str, required=True, help="Path to scenario config YAML")
    parser.add_argument("--days", type=int, default=60, help="Number of operational days to simulate")
    parser.add_argument("--output", type=str, default="data/synthetic_history", help="Output directory")
    parser.add_argument("--noise", type=float, default=0.05, help="Label noise rate (0.0 to 0.1)")

    args = parser.parse_args()

    try:
        config, _ = load_config(args.config)
        manifest = generate_synthetic_history(
            config=config,
            num_days=args.days,
            output_dir=args.output,
            label_noise_rate=args.noise,
        )

        print("==================================================")
        print("AAOP Synthetic History ML Dataset Generator")
        print("==================================================")
        print(f"Days Simulated:  {manifest['num_days_simulated']}")
        print(f"Seed:            {manifest['seed']}")
        print(f"Noise Rate:      {manifest['label_noise_rate']*100:.1f}%")
        print(f"Policy:          {manifest['hidden_variable_policy']}")
        print("--------------------------------------------------")
        print("DATASET 1: READINESS HISTORY")
        print(f"  Rows:          {manifest['datasets']['readiness']['row_count']}")
        print(f"  Target:        {manifest['datasets']['readiness']['target']}")
        print(f"  Pos Ratio:     {manifest['datasets']['readiness']['positive_class_ratio']*100:.2f}%")
        print("--------------------------------------------------")
        print("DATASET 2: TASK RISK HISTORY")
        print(f"  Rows:          {manifest['datasets']['task_risk']['row_count']}")
        print(f"  Target:        {manifest['datasets']['task_risk']['target']}")
        print(f"  Pos Ratio:     {manifest['datasets']['task_risk']['positive_class_ratio']*100:.2f}%")
        print("==================================================")
        print(f"Output Path:     {Path(args.output).resolve()}")
        print("==================================================")

    except Exception as e:
        print(f"History generation error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
