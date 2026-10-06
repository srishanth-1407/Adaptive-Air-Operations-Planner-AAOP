"""
Monte Carlo Benchmark Execution Engine & CLI.
Usage:
  python -m eval.benchmarks --config configs/small.yaml --seeds 30 --output data/benchmarks
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

from eval.monte_carlo import run_single_seed_benchmark, aggregate_monte_carlo_results


def run_monte_carlo_suite(
    config_path: str = "configs/small.yaml",
    num_seeds: int = 30,
    output_dir: str = "data/benchmarks",
    time_limit_sec: float = 1.0,
) -> Dict[str, Any]:
    """
    Runs multi-seed Monte Carlo benchmarks and exports summary stats & Parquet data.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    tmp_scratch = out_path / "scratch"

    all_records: List[Dict[str, Any]] = []

    print("==================================================")
    print(f"AAOP Monte Carlo Benchmark Suite ({num_seeds} Seeds)")
    print("==================================================")

    for i in range(num_seeds):
        seed = 1000 + i
        records = run_single_seed_benchmark(
            config_path=config_path,
            seed=seed,
            tmp_output_dir=str(tmp_scratch),
            time_limit_sec=time_limit_sec,
        )
        all_records.extend(records)
        if (i + 1) % 5 == 0 or (i + 1) == num_seeds:
            print(f"Completed {i + 1}/{num_seeds} seeds...")

    # Export full raw seed-level results to Parquet
    df = pd.DataFrame(all_records)
    # Convert config_name dict to string for parquet serialization
    df["config_name"] = df["config_name"].astype(str)
    parquet_path = out_path / "benchmark_results.parquet"
    df.to_parquet(parquet_path, index=False)

    # Compute Statistical Aggregation
    summary = aggregate_monte_carlo_results(df)

    manifest = {
        "num_seeds": num_seeds,
        "config_path": config_path,
        "solver_comparison": summary,
    }

    manifest_path = out_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("==================================================")
    print("Monte Carlo Benchmark Suite Complete!")
    print("==================================================")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Run Monte Carlo Benchmarking Suite.")
    parser.add_argument("--config", type=str, default="configs/small.yaml", help="Path to config YAML")
    parser.add_argument("--seeds", type=int, default=30, help="Number of random seeds (30-50 recommended)")
    parser.add_argument("--output", type=str, default="data/benchmarks", help="Output directory")
    parser.add_argument("--time_limit", type=float, default=1.0, help="CP-SAT time limit in seconds")

    args = parser.parse_args()

    try:
        manifest = run_monte_carlo_suite(
            config_path=args.config,
            num_seeds=args.seeds,
            output_dir=args.output,
            time_limit_sec=args.time_limit,
        )

        print("\nEmpirical Monte Carlo Statistical Summary:")
        print(f"{'SOLVER':<12} | {'COV MEAN':<10} | {'COV STD':<10} | {'COV P50':<10} | {'COV P95':<10} | {'TIME P50(ms)':<12}")
        print("-" * 75)
        for solver, stats in manifest["solver_comparison"].items():
            cov = stats["priority_weighted_coverage"]
            t_stats = stats["runtime_ms"]
            print(
                f"{solver:<12} | {cov['mean']*100:<9.2f}% | {cov['std']*100:<9.2f}% | {cov['p50']*100:<9.2f}% | {cov['p95']*100:<9.2f}% | {t_stats['p50']:<12.2f}"
            )
        print("==================================================")

    except Exception as e:
        print(f"Monte Carlo benchmark error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
