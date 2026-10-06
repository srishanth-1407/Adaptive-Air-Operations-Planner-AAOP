"""
ML Evaluation Engine for Classification Models.
Computes ROC-AUC, PR-AUC, Precision, Recall, F1, Brier Score, ECE, and Calibration Curves.
"""

from typing import Dict, Any, Tuple, List
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    confusion_matrix,
)
from sklearn.calibration import calibration_curve


def compute_expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE)."""
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="uniform")
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)

    for i in range(n_bins):
        in_bin = (y_prob >= bin_boundaries[i]) & (y_prob < bin_boundaries[i + 1])
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(y_true[in_bin])
            avg_confidence_in_bin = np.mean(y_prob[in_bin])
            ece += np.abs(accuracy_in_bin - avg_confidence_in_bin) * prop_in_bin

    return round(float(ece), 4)


def evaluate_binary_classifier(
    y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Evaluates binary classification predictions and returns comprehensive metric report.
    """
    y_pred = (y_prob >= threshold).astype(int)

    # ROC-AUC & PR-AUC
    try:
        roc_auc = round(float(roc_auc_score(y_true, y_prob)), 4)
    except Exception:
        roc_auc = 0.5

    try:
        pr_auc = round(float(average_precision_score(y_true, y_prob)), 4)
    except Exception:
        pr_auc = 0.0

    prec = round(float(precision_score(y_true, y_pred, zero_division=0)), 4)
    rec = round(float(recall_score(y_true, y_pred, zero_division=0)), 4)
    f1 = round(float(f1_score(y_true, y_pred, zero_division=0)), 4)
    brier = round(float(brier_score_loss(y_true, y_prob)), 4)
    ece = compute_expected_calibration_error(y_true, y_prob)

    cm = confusion_matrix(y_true, y_pred).tolist()

    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "brier_score": brier,
        "ece": ece,
        "confusion_matrix": cm,
        "calibration_curve": {
            "prob_true": [round(float(x), 4) for x in prob_true],
            "prob_pred": [round(float(x), 4) for x in prob_pred],
        },
    }
