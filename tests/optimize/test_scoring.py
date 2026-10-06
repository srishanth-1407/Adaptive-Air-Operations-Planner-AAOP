"""
Unit tests for distance metrics and candidate scoring (optimize/scoring.py).
"""

import pytest
from optimize.scoring import haversine_distance_km, evaluate_candidate_score
from state.models import TaskState, AssetState


def test_haversine_distance():
    # Distance between Los Angeles (34.0522, -118.2437) and San Diego (32.7157, -117.1611) ~180km
    dist = haversine_distance_km(34.0522, -118.2437, 32.7157, -117.1611)
    assert 170.0 <= dist <= 190.0


def test_candidate_score_higher_priority():
    asset = AssetState(asset_id="A-1", asset_type="PATROL_RECON", base_id="B-1", status="AVAILABLE")
    t_low = TaskState(task_id="T-1", task_type="patrol", priority=1, latitude=34.0, longitude=-118.0, required_resource_type="PATROL_RECON")
    t_high = TaskState(task_id="T-2", task_type="patrol", priority=5, latitude=34.0, longitude=-118.0, required_resource_type="PATROL_RECON")

    s_low = evaluate_candidate_score(t_low, asset, distance_km=10.0)
    s_high = evaluate_candidate_score(t_high, asset, distance_km=10.0)

    assert s_high > s_low
