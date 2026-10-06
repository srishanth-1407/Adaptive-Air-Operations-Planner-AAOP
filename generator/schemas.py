"""
Pydantic schemas for entities, environment, events, configuration, and manifests.
"""

from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_id: str
    name: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    capacity: int = Field(..., ge=1)


class ResourceAssetSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    asset_type: str
    base_id: str
    status: str = Field(default="AVAILABLE")
    age: float = Field(..., ge=0.0)
    hours_since_maintenance: float = Field(..., ge=0.0)
    endurance: float = Field(..., gt=0.0)
    utilization: float = Field(default=0.0, ge=0.0, le=1.0)
    availability: float = Field(default=1.0, ge=0.0, le=1.0)
    latent_fragility: float = Field(..., ge=0.0, le=1.0)


class CrewSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crew_id: str
    qualification: str
    duty_hours_left: float = Field(..., ge=0.0)
    status: str = Field(default="AVAILABLE")
    base_id: str


class TaskSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_type: str
    priority: int = Field(..., ge=1, le=5)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    earliest_time: float = Field(..., ge=0.0)
    latest_time: float = Field(..., ge=0.0)
    duration: float = Field(..., gt=0.0)
    required_resource_type: str


class WeatherCellSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weather_id: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_km: float = Field(..., gt=0.0)
    severity: float = Field(..., ge=0.0, le=1.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., ge=0.0)


class AirspaceZoneSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str
    geometry_wkt: str
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., ge=0.0)
    restriction_level: float = Field(..., ge=0.0, le=1.0)


class EventSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    timestamp: float = Field(..., ge=0.0)
    kind: str
    schema_version: int = Field(default=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class ManifestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int
    config_hash: str
    generator_version: str
    schema_version: int = Field(default=1)
    row_counts: Dict[str, int]
    date_range: Dict[str, float]


# Config Models
class SizeConfig(BaseModel):
    num_bases: int
    num_assets: int
    num_crews: int
    num_tasks: int
    num_weather_cells: int
    num_airspace_zones: int


class SimulationConfig(BaseModel):
    start_time: float = 0.0
    duration_hours: float = 24.0
    time_step_hours: float = 0.25


class HazardParametersConfig(BaseModel):
    intercept: float = -4.0
    b_hours_maint: float = 0.015
    b_utilization: float = 0.8
    b_age: float = 0.05
    b_environmental_stress: float = 1.2
    b_latent_fragility: float = 2.0
    stochastic_noise_std: float = 0.1


class TaskRiskParametersConfig(BaseModel):
    intercept: float = -3.0
    b_distance: float = 0.005
    b_weather_severity: float = 2.5
    b_environmental_stress: float = 1.5
    b_utilization: float = 0.5
    b_asset_fragility: float = 1.8


class EventRatesConfig(BaseModel):
    poisson_failure_lambda: float = 0.5
    poisson_task_arrival_lambda: float = 1.0
    poisson_weather_update_lambda: float = 0.2
    poisson_airspace_update_lambda: float = 0.1
    poisson_crew_restriction_lambda: float = 0.15


class GeographyConfig(BaseModel):
    lat_min: float = 32.0
    lat_max: float = 36.0
    lon_min: float = -118.0
    lon_max: float = -112.0


class RepairConfig(BaseModel):
    min_repair_hours: float = 2.0
    max_repair_hours: float = 8.0


class ScenarioConfig(BaseModel):
    seed: int
    name: str
    description: str = ""
    size: SizeConfig
    simulation: SimulationConfig
    hazard_parameters: HazardParametersConfig
    task_risk_parameters: TaskRiskParametersConfig
    event_rates: EventRatesConfig
    geography: GeographyConfig
    repair: RepairConfig
