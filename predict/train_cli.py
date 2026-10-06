"""
CLI tool for training and evaluating ML models (Trivial, Logistic Regression, XGBoost, LightGBM).
Usage:
  python -m predict.train_cli --data_dir data/synthetic_history
"""

import argparse
import sys
import pandas as pd
from predict.train import train_and_evaluate_models


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate ML models on synthetic operational history.")
    parser.add_argument("--data_dir", type=str, default="data/synthetic_history", help="Synthetic history directory")
    parser.add_argument("--output_dir", type=str, default="predict/models", help="Model artifact directory")

    args = parser.parse_args()

    try:
        readiness_path = f"{args.data_dir}/readiness_history.parquet"
        task_risk_path = f"{args.data_dir}/task_risk_history.parquet"

        readiness_df = pd.read_parquet(readiness_path)
        task_risk_df = pd.read_parquet(task_risk_path)

        print("==================================================")
        print("AAOP Predictive ML Model Training & Evaluation")
        print("==================================================")

        # 1. READINESS MODEL TRAINING
        cat_readiness = ["asset_type", "base_id", "current_status"]
        num_readiness = [
            "age",
            "hours_since_maintenance",
            "sorties_last_24h",
            "utilization_last_24h",
            "environmental_stress",
            "weather_severity",
            "recent_failure_count",
        ]

        print("\n--- MODEL SET 1: ASSET READINESS (went_down_within_horizon) ---")
        res_readiness = train_and_evaluate_models(
            df=readiness_df,
            target_col="went_down_within_horizon",
            categorical_cols=cat_readiness,
            numerical_cols=num_readiness,
            output_dir=args.output_dir,
        )

        print(f"{'MODEL':<22} | {'ROC-AUC':<8} | {'PR-AUC':<8} | {'F1':<8} | {'BRIER':<8} | {'ECE':<8}")
        print("-" * 75)
        for m_name, m in res_readiness.items():
            print(
                f"{m_name:<22} | {m['roc_auc']:<8.4f} | {m['pr_auc']:<8.4f} | {m['f1']:<8.4f} | {m['brier_score']:<8.4f} | {m['ece']:<8.4f}"
            )

        # 2. TASK RISK MODEL TRAINING
        cat_task = ["asset_type", "task_type"]
        num_task = [
            "priority",
            "distance_km",
            "estimated_duration",
            "time_slack",
            "weather_severity",
            "environmental_stress",
            "resource_utilization",
        ]

        print("\n--- MODEL SET 2: TASK SUCCESS RISK (task_success) ---")
        res_task = train_and_evaluate_models(
            df=task_risk_df,
            target_col="task_success",
            categorical_cols=cat_task,
            numerical_cols=num_task,
            output_dir=args.output_dir,
        )

        print(f"{'MODEL':<22} | {'ROC-AUC':<8} | {'PR-AUC':<8} | {'F1':<8} | {'BRIER':<8} | {'ECE':<8}")
        print("-" * 75)
        for m_name, m in res_task.items():
            print(
                f"{m_name:<22} | {m['roc_auc']:<8.4f} | {m['pr_auc']:<8.4f} | {m['f1']:<8.4f} | {m['brier_score']:<8.4f} | {m['ece']:<8.4f}"
            )

        print("==================================================")
        print("Model training completed successfully.")
        print("==================================================")

    except Exception as e:
        print(f"ML training error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
