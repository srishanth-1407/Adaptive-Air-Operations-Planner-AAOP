"""
Scoring and geographic distance metrics for resource-task allocation optimization.
"""

import math
from state.models import AssetState, TaskState
from generator.schemas import BaseSchema

CRUISE_SPEED_KMH = 250.0  # Average synthetic aircraft cruising speed in km/h


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two geographic coordinates in kilometers."""
    r = 6371.0  # Earth's radius in kilometers

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


def evaluate_candidate_score(
    task: TaskState,
    asset: AssetState,
    distance_km: float,
    predicted_success_prob: float = 1.0,
) -> float:
    """
    Computes feasibility score for assigning an asset to a task.
    Higher score indicates a better candidate match.
    """
    priority_weight = float(task.priority) * 20.0
    distance_penalty = distance_km * 0.2
    utilization_penalty = asset.utilization * 15.0
    maint_penalty = (asset.hours_since_maintenance / 100.0) * 10.0
    risk_bonus = predicted_success_prob * 50.0

    score = priority_weight + risk_bonus - (distance_penalty + utilization_penalty + maint_penalty)
    return round(score, 3)
