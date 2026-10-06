"""
ML Model Inference Engine.
Loads saved model artifacts and produces calibrated prediction probabilities for state features.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import joblib
import numpy as np
import pandas as pd


class MLInferenceEngine:
    """Loads trained ML models and executes probability inference for live assets & tasks."""

    def __init__(self, model_path: str):
        path = Path(model_path)
        if not path.is_file():
            raise FileNotFoundError(f"Model artifact not found: {model_path}")

        artifact = joblib.load(path)
        self.model = artifact["model"]
        self.pipeline = artifact["pipeline"]
        self.target_col = artifact["target_col"]

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms input feature dataframe and returns predicted positive class probabilities."""
        X = self.pipeline.transform(df)
        probs = self.model.predict_proba(X)[:, 1]
        return probs
