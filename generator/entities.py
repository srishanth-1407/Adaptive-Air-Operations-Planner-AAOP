"""
Deterministic entity generator for Bases, Resource Assets, Crews, and Tasks.
All generation is fully repeatable given a fixed random seed.
"""

from typing import List, Tuple
import numpy as np

from generator.schemas import (
    BaseSchema,
    ResourceAssetSchema,
    CrewSchema,
    TaskSchema,
    GeographyConfig,
    SizeConfig,
)

ASSET_TYPES = [
    "LIGHT_TRANSPORT",
    "HEAVY_CARGO",
    "PATROL_RECON",
    "RESCUE_ROTARY",
]

TASK_TYPES = [
    "urgent",
    "patrol",
    "surveillance",
    "logistics",
]


def generate_bases(
    size_config: SizeConfig,
    geo_config: GeographyConfig,
    rng: np.random.Generator,
) -> List[BaseSchema]:
    """Generates synthetic bases within geographical bounds."""
    bases: List[BaseSchema] = []
    num_bases = size_config.num_bases

    for i in range(num_bases):
        base_id = f"BASE-{i + 1:03d}"
        lat = float(rng.uniform(geo_config.lat_min + 0.5, geo_config.lat_max - 0.5))
        lon = float(rng.uniform(geo_config.lon_min + 0.5, geo_config.lon_max - 0.5))
        capacity = int(rng.integers(10, 50))
        bases.append(
            BaseSchema(
                base_id=base_id,
                name=f"Forward Operating Base {i + 1}",
                latitude=round(lat, 4),
                longitude=round(lon, 4),
                capacity=capacity,
            )
        )
    return bases


def generate_assets(
    size_config: SizeConfig,
    bases: List[BaseSchema],
    rng: np.random.Generator,
) -> List[ResourceAssetSchema]:
    """Generates synthetic resource assets linked to bases."""
    assets: List[ResourceAssetSchema] = []
    base_ids = [b.base_id for b in bases]

    for i in range(size_config.num_assets):
        asset_id = f"A-{i + 1:04d}"
        asset_type = str(rng.choice(ASSET_TYPES))
        base_id = str(rng.choice(base_ids))

        age = float(round(rng.uniform(0.5, 15.0), 2))
        hours_since_maint = float(round(rng.uniform(5.0, 150.0), 1))
        endurance = float(round(rng.uniform(4.0, 12.0), 1))
        utilization = float(round(rng.uniform(0.0, 0.7), 2))
        availability = 1.0

        # Latent fragility is unobserved variable (0.0 to 1.0)
        latent_fragility = float(round(rng.beta(2, 5), 3))

        assets.append(
            ResourceAssetSchema(
                asset_id=asset_id,
                asset_type=asset_type,
                base_id=base_id,
                status="AVAILABLE",
                age=age,
                hours_since_maintenance=hours_since_maint,
                endurance=endurance,
                utilization=utilization,
                availability=availability,
                latent_fragility=latent_fragility,
            )
        )
    return assets


def generate_crews(
    size_config: SizeConfig,
    bases: List[BaseSchema],
    rng: np.random.Generator,
) -> List[CrewSchema]:
    """Generates synthetic crew/operators."""
    crews: List[CrewSchema] = []
    base_ids = [b.base_id for b in bases]

    for i in range(size_config.num_crews):
        crew_id = f"CREW-{i + 1:04d}"
        qualification = str(rng.choice(ASSET_TYPES))
        duty_hours_left = float(round(rng.uniform(4.0, 12.0), 1))
        base_id = str(rng.choice(base_ids))

        crews.append(
            CrewSchema(
                crew_id=crew_id,
                qualification=qualification,
                duty_hours_left=duty_hours_left,
                status="AVAILABLE",
                base_id=base_id,
            )
        )
    return crews


def generate_tasks(
    size_config: SizeConfig,
    geo_config: GeographyConfig,
    duration_hours: float,
    rng: np.random.Generator,
) -> List[TaskSchema]:
    """Generates synthetic operational tasks."""
    tasks: List[TaskSchema] = []

    for i in range(size_config.num_tasks):
        task_id = f"T-{i + 1:04d}"
        task_type = str(rng.choice(TASK_TYPES))

        if task_type == "urgent":
            priority = int(rng.choice([4, 5]))
            duration = float(round(rng.uniform(1.0, 3.0), 1))
        elif task_type == "patrol":
            priority = int(rng.choice([2, 3]))
            duration = float(round(rng.uniform(2.0, 6.0), 1))
        elif task_type == "surveillance":
            priority = int(rng.choice([3, 4]))
            duration = float(round(rng.uniform(3.0, 8.0), 1))
        else:
            priority = int(rng.choice([1, 2]))
            duration = float(round(rng.uniform(2.0, 5.0), 1))

        lat = float(rng.uniform(geo_config.lat_min, geo_config.lat_max))
        lon = float(rng.uniform(geo_config.lon_min, geo_config.lon_max))

        earliest = float(round(rng.uniform(0.0, max(1.0, duration_hours - duration - 2.0)), 1))
        latest = float(round(earliest + rng.uniform(duration + 1.0, 12.0), 1))

        required_resource_type = str(rng.choice(ASSET_TYPES))

        tasks.append(
            TaskSchema(
                task_id=task_id,
                task_type=task_type,
                priority=priority,
                latitude=round(lat, 4),
                longitude=round(lon, 4),
                earliest_time=earliest,
                latest_time=latest,
                duration=duration,
                required_resource_type=required_resource_type,
            )
        )
    return tasks
