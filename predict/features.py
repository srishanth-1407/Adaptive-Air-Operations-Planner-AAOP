"""
Feature Engineering and Dataset Splitting Pipeline for ML models.
Handles categorical encoding, numerical scaling, temporal train/val/test splits,
and seed holdout splits.
"""

from typing import Tuple, List, Dict, Any
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer


class FeaturePipeline:
    """Handles feature transformation, column encoding, and scaling."""

    def __init__(self, categorical_cols: List[str], numerical_cols: List[str]):
        self.categorical_cols = categorical_cols
        self.numerical_cols = numerical_cols
        self.preprocessor: Optional[ColumnTransformer] = None

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), self.numerical_cols),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), self.categorical_cols),
            ]
        )
        X = self.preprocessor.fit_transform(df[self.numerical_cols + self.categorical_cols])
        return np.asarray(X, dtype=np.float32)

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if self.preprocessor is None:
            raise RuntimeError("FeaturePipeline must be fit before transform.")
        X = self.preprocessor.transform(df[self.numerical_cols + self.categorical_cols])
        return np.asarray(X, dtype=np.float32)

    def get_feature_names(self) -> List[str]:
        if self.preprocessor is None:
            return []
        cat_encoder = self.preprocessor.named_transformers_["cat"]
        cat_features = list(cat_encoder.get_feature_names_out(self.categorical_cols))
        return self.numerical_cols + cat_features


def temporal_split(
    df: pd.DataFrame, time_col: str = "timestamp", train_frac: float = 0.7, val_frac: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Performs chronologically ordered temporal split:
    Earlier timestamps -> Train, Middle timestamps -> Val, Latest timestamps -> Test.
    """
    df_sorted = df.sort_values(by=time_col).reset_index(drop=True)
    n = len(df_sorted)

    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))

    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    return train_df, val_df, test_df
