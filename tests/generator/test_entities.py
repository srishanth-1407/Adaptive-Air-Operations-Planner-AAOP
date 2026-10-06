"""
Unit tests for entities generation, environment generation, and schema validation.
"""

import numpy as np
import pytest
from generator.schemas import ScenarioConfig, SizeConfig, GeographyConfig
from generator.entities import (
    generate_bases,
    generate_assets,
    generate_crews,
    generate_tasks,
    ASSET_TYPES,
)
from generator.environment import (
    generate_weather_cells,
    generate_airspace_zones,
    is_point_in_airspace,
)


@pytest.fixture
def sample_config():
    return ScenarioConfig.model_validate(
        {
            "seed": 42,
            "name": "test_small",
            "size": {
                "num_bases": 3,
                "num_assets": 20,
                "num_crews": 15,
                "num_tasks": 30,
                "num_weather_cells": 3,
                "num_airspace_zones": 2,
            },
            "simulation": {"start_time": 0.0, "duration_hours": 24.0, "time_step_hours": 0.25},
            "hazard_parameters": {},
            "task_risk_parameters": {},
            "event_rates": {},
            "geography": {"lat_min": 32.0, "lat_max": 36.0, "lon_min": -118.0, "lon_max": -112.0},
            "repair": {"min_repair_hours": 2.0, "max_repair_hours": 8.0},
        }
    )


def test_unique_ids(sample_config):
    rng = np.random.default_rng(sample_config.seed)
    bases = generate_bases(sample_config.size, sample_config.geography, rng)
    assets = generate_assets(sample_config.size, bases, rng)
    crews = generate_crews(sample_config.size, bases, rng)
    tasks = generate_tasks(sample_config.size, sample_config.geography, 24.0, rng)

    assert len({b.base_id for b in bases}) == len(bases)
    assert len({a.asset_id for a in assets}) == len(assets)
    assert len({c.crew_id for c in crews}) == len(crews)
    assert len({t.task_id for t in tasks}) == len(tasks)


def test_valid_coordinates_and_priorities(sample_config):
    rng = np.random.default_rng(sample_config.seed)
    bases = generate_bases(sample_config.size, sample_config.geography, rng)
    tasks = generate_tasks(sample_config.size, sample_config.geography, 24.0, rng)

    for b in bases:
        assert sample_config.geography.lat_min <= b.latitude <= sample_config.geography.lat_max
        assert sample_config.geography.lon_min <= b.longitude <= sample_config.geography.lon_max

    for t in tasks:
        assert sample_config.geography.lat_min <= t.latitude <= sample_config.geography.lat_max
        assert sample_config.geography.lon_min <= t.longitude <= sample_config.geography.lon_max
        assert 1 <= t.priority <= 5
        assert t.earliest_time <= t.latest_time
        assert t.required_resource_type in ASSET_TYPES


def test_crew_qualifications(sample_config):
    rng = np.random.default_rng(sample_config.seed)
    bases = generate_bases(sample_config.size, sample_config.geography, rng)
    crews = generate_crews(sample_config.size, bases, rng)

    for c in crews:
        assert c.qualification in ASSET_TYPES
        assert c.duty_hours_left > 0.0


def test_shapely_airspace_zones(sample_config):
    rng = np.random.default_rng(sample_config.seed)
    zones = generate_airspace_zones(sample_config.size, sample_config.geography, 24.0, rng)

    assert len(zones) == sample_config.size.num_airspace_zones
    for z in zones:
        assert z.geometry_wkt.startswith("POLYGON")
        assert 0.0 <= z.restriction_level <= 1.0
