"""
Model Training Pipeline for Trivial, Logistic Regression, XGBoost, and LightGBM models.
Supports temporal splits and seed holdout validation. Saves trained model artifacts.
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from predict.features import FeaturePipeline, temporal_split
from predict.evaluate import evaluate_binary_classifier


class PriorProbabilityClassifier:
    """Trivial baseline classifier predicting global class prior probability."""

    def __init__(self):
        self.prior_prob: float = 0.5

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.prior_prob = float(np.mean(y))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        probs = np.full((len(X), 2), 1.0 - self.prior_prob)
        probs[:, 1] = self.prior_prob
        return probs


def train_and_evaluate_models(
    df: pd.DataFrame,
    target_col: str,
    categorical_cols: List[str],
    numerical_cols: List[str],
    output_dir: str = "predict/models",
) -> Dict[str, Any]:
    """
    Trains Trivial, Logistic Regression, XGBoost, and LightGBM models on temporal splits.
    Returns comprehensive metric comparisons and saves model artifacts.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Temporal Train / Val / Test Split
    train_df, val_df, test_df = temporal_split(df, time_col="timestamp", train_frac=0.7, val_frac=0.15)

    # 2. Fit Feature Pipeline on Train Set
    pipeline = FeaturePipeline(categorical_cols, numerical_cols)
    X_train = pipeline.fit_transform(train_df)
    y_train = train_df[target_col].values.astype(int)

    X_val = pipeline.transform(val_df)
    y_val = val_df[target_col].values.astype(int)

    X_test = pipeline.transform(test_df)
    y_test = test_df[target_col].values.astype(int)

    feature_names = pipeline.get_feature_names()

    # 3. Model Definitions
    models = {
        "Trivial_Baseline": PriorProbabilityClassifier(),
        "Logistic_Regression": LogisticRegression(max_iter=1000, random_state=42),
        "XGBoost": XGBClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, eval_metric="logloss"
        ),
        "LightGBM": LGBMClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42, verbose=-1
        ),
    }

    results: Dict[str, Any] = {}

    for name, model in models.items():
        # Train
        model.fit(X_train, y_train)

        # Predict Test Set Probabilities
        y_prob = model.predict_proba(X_test)[:, 1]

        # Evaluate Metrics
        metrics = evaluate_binary_classifier(y_test, y_prob)

        # Feature Importance (if tree model)
        importances = {}
        if hasattr(model, "feature_importances_"):
            imp_vals = model.feature_importances_
            for fname, val in zip(feature_names, imp_vals):
                importances[fname] = round(float(val), 4)
            # Sort importances descending
            importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True)[:10])

        metrics["feature_importances"] = importances
        results[name] = metrics

        # Save artifact
        model_artifact_path = out_path / f"{name.lower()}_{target_col}.joblib"
        joblib.dump({"model": model, "pipeline": pipeline, "target_col": target_col}, model_artifact_path)

    return results
