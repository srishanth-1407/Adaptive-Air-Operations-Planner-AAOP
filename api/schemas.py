"""
API Pydantic Request and Response Schemas.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from state.models import StateSnapshot, AssetState, TaskState
from optimize.schemas import AllocationPlan, PlanMetrics
from optimize.explain import PlanDiffExplanation


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    version: str = "0.1.0"
    state_version: int = 0


class StateVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    timestamp: float
    last_event_id: Optional[str] = None
    last_event_kind: Optional[str] = None


class ReplanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    solver_type: str = Field(default="CP_SAT_ML")  # GREEDY, CP_SAT, CP_SAT_ML
    time_limit_sec: float = Field(default=2.0, gt=0.0)


class ReplanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = True
    plan: AllocationPlan
    explanation: Optional[PlanDiffExplanation] = None


class WhatIfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remove_asset_id: Optional[str] = None
    add_task: Optional[Dict[str, Any]] = None
    weather_severity_increase: Optional[Dict[str, float]] = None  # weather_id -> new_severity
    time_limit_sec: float = Field(default=2.0, gt=0.0)


class WhatIfResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_plan_metrics: PlanMetrics
    whatif_plan_metrics: PlanMetrics
    objective_difference: float
    coverage_difference: float
    new_unassigned_tasks: List[str]
    plan_churn_score: float
    whatif_plan: AllocationPlan


class SimulationStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    running: bool
    speed_factor: float
    current_time: float
    total_events_processed: int
    consumer_lag: int


class SimulationControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_path: Optional[str] = "data/scenarios/run_001"
    speed_factor: float = Field(default=1.0, ge=0.0)


class MetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_version: int
    total_assets: int
    available_assets: int
    total_tasks: int
    assigned_tasks: int
    unassigned_tasks: int
    consumer_lag: int
    latest_event_timestamp: float
    throughput_eps: float
