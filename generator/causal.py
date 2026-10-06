"""
Shared Causal Module (generator/causal.py).
Contains core causal functions for asset failure hazard, task risk, environmental stress,
and resource utilization stress.
All data generators (live events, synthetic history, evaluation, simulation) must use this shared logic.
"""

import math
from typing import Dict, Optional
import numpy as np


def environmental_stress(
    weather_severity: float,
    airspace_restriction_level: float = 0.0,
    terrain_complexity: float = 0.0,
) -> float:
    """
    Computes environmental stress index S_env in [0, 1+].
    """
    base = 0.6 * weather_severity + 0.3 * airspace_restriction_level + 0.1 * terrain_complexity
    return max(0.0, min(2.0, float(base)))


def resource_utilization_stress(
    utilization: float,
    hours_since_maintenance: float,
    duty_hours_left: float = 12.0,
) -> float:
    """
    Computes operational utilization stress S_util.
    """
    maint_factor = min(2.0, hours_since_maintenance / 100.0)
    duty_factor = max(0.0, (12.0 - duty_hours_left) / 12.0)
    return float(0.5 * utilization + 0.3 * maint_factor + 0.2 * duty_factor)


def asset_failure_hazard(
    hours_since_maintenance: float,
    utilization: float,
    age: float,
    env_stress: float,
    latent_fragility: float,
    hazard_params: Optional[Dict[str, float]] = None,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """
    Computes hourly failure probability p_fail for an asset using logistic causal formulation:

    logit(p) = intercept
             + b_hours_maint * hours_since_maintenance
             + b_utilization * utilization
             + b_age * age
             + b_environmental_stress * env_stress
             + b_latent_fragility * latent_fragility
             + noise
    p_fail = 1 / (1 + exp(-logit))
    """
    if hazard_params is None:
        hazard_params = {
            "intercept": -4.0,
            "b_hours_maint": 0.015,
            "b_utilization": 0.8,
            "b_age": 0.05,
            "b_environmental_stress": 1.2,
            "b_latent_fragility": 2.0,
            "stochastic_noise_std": 0.1,
        }

    intercept = hazard_params.get("intercept", -4.0)
    b_maint = hazard_params.get("b_hours_maint", 0.015)
    b_util = hazard_params.get("b_utilization", 0.8)
    b_age = hazard_params.get("b_age", 0.05)
    b_env = hazard_params.get("b_environmental_stress", 1.2)
    b_frag = hazard_params.get("b_latent_fragility", 2.0)
    noise_std = hazard_params.get("stochastic_noise_std", 0.1)

    noise = 0.0
    if rng is not None and noise_std > 0.0:
        noise = float(rng.normal(0.0, noise_std))

    logit = (
        intercept
        + b_maint * hours_since_maintenance
        + b_util * utilization
        + b_age * age
        + b_env * env_stress
        + b_frag * latent_fragility
        + noise
    )

    # Sigmoid function for probability
    p_fail = 1.0 / (1.0 + math.exp(-logit))
    return float(p_fail)


def task_risk(
    distance_km: float,
    weather_severity: float,
    env_stress: float,
    utilization: float,
    latent_fragility: float,
    task_risk_params: Optional[Dict[str, float]] = None,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """
    Computes failure/attrition risk for a given task-asset assignment:

    logit(p) = intercept
             + b_distance * distance_km
             + b_weather_severity * weather_severity
             + b_environmental_stress * env_stress
             + b_utilization * utilization
             + b_asset_fragility * latent_fragility
             + noise
    """
    if task_risk_params is None:
        task_risk_params = {
            "intercept": -3.0,
            "b_distance": 0.005,
            "b_weather_severity": 2.5,
            "b_environmental_stress": 1.5,
            "b_utilization": 0.5,
            "b_asset_fragility": 1.8,
            "stochastic_noise_std": 0.1,
        }

    intercept = task_risk_params.get("intercept", -3.0)
    b_dist = task_risk_params.get("b_distance", 0.005)
    b_weather = task_risk_params.get("b_weather_severity", 2.5)
    b_env = task_risk_params.get("b_environmental_stress", 1.5)
    b_util = task_risk_params.get("b_utilization", 0.5)
    b_frag = task_risk_params.get("b_asset_fragility", 1.8)
    noise_std = task_risk_params.get("stochastic_noise_std", 0.1)

    noise = 0.0
    if rng is not None and noise_std > 0.0:
        noise = float(rng.normal(0.0, noise_std))

    logit = (
        intercept
        + b_dist * distance_km
        + b_weather * weather_severity
        + b_env * env_stress
        + b_util * utilization
        + b_frag * latent_fragility
        + noise
    )

    p_risk = 1.0 / (1.0 + math.exp(-logit))
    return float(p_risk)
