"""
Schemas for task assignments, plan metrics, and optimization allocation plans.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    asset_id: str
    crew_id: Optional[str] = None
    base_id: str
    distance_km: float = Field(..., ge=0.0)
    estimated_travel_hours: float = Field(..., ge=0.0)
    start_time: float = Field(..., ge=0.0)
    completion_time: float = Field(..., ge=0.0)
    candidate_score: float = Field(default=0.0)


class PlanMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority_weighted_coverage: float = Field(..., ge=0.0, le=1.0)
    high_priority_coverage: float = Field(..., ge=0.0, le=1.0)
    tasks_served: int = Field(..., ge=0)
    tasks_unserved: int = Field(..., ge=0)
    resource_utilization: float = Field(..., ge=0.0, le=1.0)
    runtime_ms: float = Field(..., ge=0.0)
    objective_value: float = Field(default=0.0)


class AllocationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    state_version: int = Field(default=0, ge=0)
    timestamp: float = Field(default=0.0, ge=0.0)
    solver_type: str = Field(default="GREEDY")
    assignments: List[TaskAssignment] = Field(default_factory=list)
    unassigned_tasks: List[str] = Field(default_factory=list)
    metrics: PlanMetrics
