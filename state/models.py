"""
Pydantic state models for live world snapshot, versioning, and event log.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from generator.schemas import EventSchema


class AssetState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    asset_type: str
    base_id: str
    status: str = Field(default="AVAILABLE")
    age: float = Field(default=1.0, ge=0.0)
    hours_since_maintenance: float = Field(default=0.0, ge=0.0)
    endurance: float = Field(default=8.0, gt=0.0)
    utilization: float = Field(default=0.0, ge=0.0, le=1.0)
    availability: float = Field(default=1.0, ge=0.0, le=1.0)
    latent_fragility: float = Field(default=0.1, ge=0.0, le=1.0)


class CrewState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crew_id: str
    qualification: str
    duty_hours_left: float = Field(default=12.0, ge=0.0)
    status: str = Field(default="AVAILABLE")
    base_id: str


class TaskState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_type: str
    priority: int = Field(default=3, ge=1, le=5)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    earliest_time: float = Field(default=0.0, ge=0.0)
    latest_time: float = Field(default=24.0, ge=0.0)
    duration: float = Field(default=2.0, gt=0.0)
    required_resource_type: str
    assigned_asset_id: Optional[str] = None
    status: str = Field(default="UNASSIGNED")  # UNASSIGNED, ASSIGNED, COMPLETED, FAILED


class WeatherState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weather_id: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_km: float = Field(default=20.0, gt=0.0)
    severity: float = Field(default=0.0, ge=0.0, le=1.0)
    start_time: float = Field(default=0.0, ge=0.0)
    end_time: float = Field(default=24.0, ge=0.0)


class AirspaceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str
    geometry_wkt: str
    start_time: float = Field(default=0.0, ge=0.0)
    end_time: float = Field(default=24.0, ge=0.0)
    restriction_level: float = Field(default=0.0, ge=0.0, le=1.0)


class StateVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=0, ge=0)
    timestamp: float = Field(default=0.0, ge=0.0)
    last_event_id: Optional[str] = None
    last_event_kind: Optional[str] = None


class StateSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: StateVersion
    assets: Dict[str, AssetState] = Field(default_factory=dict)
    crews: Dict[str, CrewState] = Field(default_factory=dict)
    tasks: Dict[str, TaskState] = Field(default_factory=dict)
    weather_cells: Dict[str, WeatherState] = Field(default_factory=dict)
    airspace_zones: Dict[str, AirspaceState] = Field(default_factory=dict)


class EventLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    event: EventSchema
