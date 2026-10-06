"""
Synthetic Historical Data Generator for ML Pipelines.
Uses shared causal module (generator/causal.py) to produce historical readiness and task-risk datasets.
Excludes unobserved latent variables from feature columns while incorporating them into target outcomes.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

from generator.schemas import ScenarioConfig
from generator.causal import (
    asset_failure_hazard,
    task_risk,
    environmental_stress,
    resource_utilization_stress,
)
from generator.entities import generate_bases, generate_assets, generate_tasks, ASSET_TYPES, TASK_TYPES
from optimize.scoring import haversine_distance_km
from generator import __version__ as generator_version


def generate_synthetic_history(
    config: ScenarioConfig,
    num_days: int = 180,
    output_dir: str = "data/synthetic_history",
    label_noise_rate: float = 0.05,
    horizon_hours: float = 4.0,
) -> Dict[str, Any]:
    """
    Generates 6 months (or custom duration) of synthetic historical operational datasets:
    1. Readiness Dataset: Asset features per hour -> target: went_down_within_horizon
    2. Task Risk Dataset: Resource-Task assignment features -> target: task_success
    """
    rng = np.random.default_rng(config.seed)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Generate Static World Entities
    bases = generate_bases(config.size, config.geography, rng)
    assets = generate_assets(config.size, bases, rng)
    base_map = {b.base_id: b for b in bases}

    # 2. Simulate Readiness History over time
    readiness_rows: List[Dict[str, Any]] = []
    task_risk_rows: List[Dict[str, Any]] = []

    total_hours = num_days * 24

    for hour in range(0, total_hours, 2):  # Sample every 2 hours
        timestamp = float(hour)
        weather_severity = float(round(rng.uniform(0.1, 0.9), 2))
        env_st = environmental_stress(weather_severity)

        for asset in assets:
            # Dynamic state drift
            hours_maint = float(round(asset.hours_since_maintenance + (hour % 150), 1))
            utilization = float(round(np.clip(asset.utilization + rng.uniform(-0.1, 0.1), 0.0, 1.0), 2))
            recent_failures = int(rng.poisson(0.1 + asset.latent_fragility))
            sorties_24h = int(rng.integers(0, 6))

            # Compute true underlying failure hazard using shared causal model (includes unobserved latent_fragility)
            p_fail_hourly = asset_failure_hazard(
                hours_since_maintenance=hours_maint,
                utilization=utilization,
                age=asset.age,
                env_stress=env_st,
                latent_fragility=asset.latent_fragility,
                hazard_params=config.hazard_parameters.model_dump(),
                rng=rng,
            )

            # Horizon probability over 4 hours
            p_fail_horizon = 1.0 - (1.0 - p_fail_hourly) ** horizon_hours
            true_went_down = int(rng.uniform(0.0, 1.0) < p_fail_horizon)

            # Apply 5% controlled label noise
            if rng.uniform(0.0, 1.0) < label_noise_rate:
                went_down_label = 1 - true_went_down
            else:
                went_down_label = true_went_down

            # OBSERVED FEATURES (Excludes latent_fragility!)
            readiness_rows.append(
                {
                    "timestamp": timestamp,
                    "asset_id": asset.asset_id,
                    "asset_type": asset.asset_type,
                    "base_id": asset.base_id,
                    "age": asset.age,
                    "hours_since_maintenance": hours_maint,
                    "sorties_last_24h": sorties_24h,
                    "utilization_last_24h": utilization,
                    "environmental_stress": env_st,
                    "weather_severity": weather_severity,
                    "recent_failure_count": recent_failures,
                    "current_status": "AVAILABLE",
                    "went_down_within_horizon": went_down_label,
                }
            )

            # Generate Task Risk pairs for this asset at this time
            if rng.uniform(0.0, 1.0) < 0.3:  # 30% sampling rate for task assignments
                task_id = f"HT-{len(task_risk_rows) + 1:06d}"
                t_type = str(rng.choice(TASK_TYPES))
                priority = int(rng.choice([1, 2, 3, 4, 5]))
                duration = float(round(rng.uniform(1.5, 5.0), 1))

                # Distance calculation from asset base
                b_obj = base_map[asset.base_id]
                t_lat = float(rng.uniform(config.geography.lat_min, config.geography.lat_max))
                t_lon = float(rng.uniform(config.geography.lon_min, config.geography.lon_max))
                dist_km = haversine_distance_km(b_obj.latitude, b_obj.longitude, t_lat, t_lon)

                time_slack = float(round(rng.uniform(0.5, 6.0), 1))

                # Compute true risk using shared causal task_risk function
                p_risk = task_risk(
                    distance_km=dist_km,
                    weather_severity=weather_severity,
                    env_stress=env_st,
                    utilization=utilization,
                    latent_fragility=asset.latent_fragility,
                    task_risk_params=config.task_risk_parameters.model_dump(),
                    rng=rng,
                )

                true_success = int(rng.uniform(0.0, 1.0) >= p_risk)
                if rng.uniform(0.0, 1.0) < label_noise_rate:
                    task_success_label = 1 - true_success
                else:
                    task_success_label = true_success

                task_risk_rows.append(
                    {
                        "timestamp": timestamp,
                        "task_id": task_id,
                        "asset_id": asset.asset_id,
                        "asset_type": asset.asset_type,
                        "task_type": t_type,
                        "priority": priority,
                        "distance_km": dist_km,
                        "estimated_duration": duration,
                        "time_slack": time_slack,
                        "weather_severity": weather_severity,
                        "environmental_stress": env_st,
                        "resource_utilization": utilization,
                        "task_success": task_success_label,
                    }
                )

    readiness_df = pd.DataFrame(readiness_rows)
    task_risk_df = pd.DataFrame(task_risk_rows)

    # Save to Parquet
    readiness_path = out_path / "readiness_history.parquet"
    task_risk_path = out_path / "task_risk_history.parquet"

    readiness_df.to_parquet(readiness_path, index=False)
    task_risk_df.to_parquet(task_risk_path, index=False)

    # Construct Manifest
    readiness_features = [c for c in readiness_df.columns if c != "went_down_within_horizon"]
    task_risk_features = [c for c in task_risk_df.columns if c != "task_success"]

    manifest = {
        "seed": config.seed,
        "generator_version": generator_version,
        "schema_version": 1,
        "num_days_simulated": num_days,
        "label_noise_rate": label_noise_rate,
        "prediction_horizon_hours": horizon_hours,
        "hidden_variable_policy": "latent_fragility included in causal ground truth but EXCLUDED from feature sets",
        "datasets": {
            "readiness": {
                "file": "readiness_history.parquet",
                "row_count": len(readiness_df),
                "features": readiness_features,
                "target": "went_down_within_horizon",
                "positive_class_ratio": round(float(readiness_df["went_down_within_horizon"].mean()), 4),
            },
            "task_risk": {
                "file": "task_risk_history.parquet",
                "row_count": len(task_risk_df),
                "features": task_risk_features,
                "target": "task_success",
                "positive_class_ratio": round(float(task_risk_df["task_success"].mean()), 4),
            },
        },
    }

    manifest_path = out_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest
