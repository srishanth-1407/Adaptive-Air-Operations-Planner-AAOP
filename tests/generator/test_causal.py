"""
Unit tests for Shared Causal Module (generator/causal.py).
"""

import numpy as np
import pytest
from generator.causal import (
    asset_failure_hazard,
    task_risk,
    environmental_stress,
    resource_utilization_stress,
)


def test_environmental_stress_bounds():
    s1 = environmental_stress(weather_severity=0.0, airspace_restriction_level=0.0)
    assert s1 == 0.0

    s2 = environmental_stress(weather_severity=1.0, airspace_restriction_level=1.0, terrain_complexity=1.0)
    assert 0.0 <= s2 <= 2.0


def test_resource_utilization_stress_bounds():
    s = resource_utilization_stress(utilization=0.5, hours_since_maintenance=50.0, duty_hours_left=6.0)
    assert s >= 0.0


def test_asset_failure_hazard_monotonicity():
    """Higher maintenance hours or higher stress should increase failure probability."""
    p_low_maint = asset_failure_hazard(
        hours_since_maintenance=10.0, utilization=0.1, age=2.0, env_stress=0.1, latent_fragility=0.1
    )
    p_high_maint = asset_failure_hazard(
        hours_since_maintenance=200.0, utilization=0.9, age=10.0, env_stress=1.5, latent_fragility=0.9
    )
    assert p_high_maint > p_low_maint
    assert 0.0 < p_low_maint < 1.0
    assert 0.0 < p_high_maint < 1.0


def test_task_risk_monotonicity():
    """Longer distance and higher weather severity should increase task risk."""
    r_low = task_risk(
        distance_km=10.0, weather_severity=0.1, env_stress=0.1, utilization=0.1, latent_fragility=0.1
    )
    r_high = task_risk(
        distance_km=500.0, weather_severity=0.9, env_stress=1.5, utilization=0.9, latent_fragility=0.9
    )
    assert r_high > r_low
    assert 0.0 < r_low < 1.0
    assert 0.0 < r_high < 1.0


def test_causal_stochastic_reproducibility():
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)

    p1 = asset_failure_hazard(50.0, 0.5, 5.0, 0.5, 0.5, rng=rng1)
    p2 = asset_failure_hazard(50.0, 0.5, 5.0, 0.5, 0.5, rng=rng2)

    assert p1 == p2
