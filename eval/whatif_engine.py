"""
What-If Branch Analysis Engine.
Executes hypothetical scenario evaluations on isolated state copies.
Ensures zero side-effects or mutations on live state store.
"""

from copy import deepcopy
from typing import Dict, List, Optional, Any
import numpy as np
from pydantic import BaseModel, Field, ConfigDict

from state.models import StateSnapshot, TaskState
from generator.schemas import BaseSchema
from optimize.schemas import AllocationPlan, PlanMetrics
from optimize.solver import CPSatOptimizer, OptimizerConfig
from optimize.ml_integrated_solver import MLIntegratedOptimizer
from optimize.explain import PlanExplainer


class WhatIfHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remove_asset_id: Optional[str] = None
    add_task: Optional[Dict[str, Any]] = None
    weather_severity_increase: Optional[Dict[str, float]] = None  # weather_id -> new_severity
    restrict_airspace_zone: Optional[Dict[str, float]] = None  # zone_id -> restriction_level
    reduce_crew_availability: Optional[List[str]] = None  # list of crew_ids to set RESTING
    use_ml_solver: bool = True
    time_limit_sec: float = 2.0


class WhatIfAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_plan_id: str
    whatif_plan_id: str
    state_version: int
    hypothesis_summary: List[str]
    current_metrics: PlanMetrics
    whatif_metrics: PlanMetrics
    objective_difference: float
    coverage_difference: float
    resource_utilization_difference: float
    plan_churn_score: float
    new_infeasibilities: List[str]
    explanation: Optional[Any] = None


class WhatIfEngine:
    """Executes hypothetical what-if scenario branching and comparative analysis."""

    def __init__(self, bases: Optional[Dict[str, BaseSchema]] = None):
        self.bases = bases or {}

    def evaluate_hypothesis(
        self,
        snapshot: StateSnapshot,
        current_plan: AllocationPlan,
        hypothesis: WhatIfHypothesis,
    ) -> WhatIfAnalysisResult:
        """
        Applies hypothesis to an isolated state deepcopy, computes new plan, and returns detailed delta report.
        """
        # 1. Isolated State Branching (Deepcopy ensures NO live state mutation!)
        branch_state: StateSnapshot = deepcopy(snapshot)
        summary: List[str] = []

        # Apply Resource Removal
        if hypothesis.remove_asset_id and hypothesis.remove_asset_id in branch_state.assets:
            branch_state.assets[hypothesis.remove_asset_id].status = "UNAVAILABLE"
            branch_state.assets[hypothesis.remove_asset_id].availability = 0.0
            summary.append(f"Removed resource {hypothesis.remove_asset_id}")

        # Apply Task Injection
        if hypothesis.add_task:
            t_data = hypothesis.add_task
            t_id = t_data.get("task_id", f"T-HYPO-{len(branch_state.tasks)+1:04d}")
            branch_state.tasks[t_id] = TaskState(
                task_id=t_id,
                task_type=t_data.get("task_type", "urgent"),
                priority=int(t_data.get("priority", 5)),
                latitude=float(t_data.get("latitude", 34.0)),
                longitude=float(t_data.get("longitude", -115.0)),
                duration=float(t_data.get("duration", 3.0)),
                required_resource_type=t_data.get("required_resource_type", "LIGHT_TRANSPORT"),
                status="UNASSIGNED",
            )
            summary.append(f"Injected high-priority task {t_id} (priority {t_data.get('priority', 5)})")

        # Apply Weather Escalation
        if hypothesis.weather_severity_increase:
            for wx_id, new_sev in hypothesis.weather_severity_increase.items():
                if wx_id in branch_state.weather_cells:
                    branch_state.weather_cells[wx_id].severity = float(np.clip(new_sev, 0.0, 1.0))
                    summary.append(f"Escalated weather severity in {wx_id} to {new_sev}")

        # Apply Airspace Restriction
        if hypothesis.restrict_airspace_zone:
            for z_id, new_rest in hypothesis.restrict_airspace_zone.items():
                if z_id in branch_state.airspace_zones:
                    branch_state.airspace_zones[z_id].restriction_level = float(np.clip(new_rest, 0.0, 1.0))
                    summary.append(f"Restricted airspace zone {z_id} to level {new_rest}")

        # Apply Crew Availability Reduction
        if hypothesis.reduce_crew_availability:
            for c_id in hypothesis.reduce_crew_availability:
                if c_id in branch_state.crews:
                    branch_state.crews[c_id].status = "RESTING"
                    summary.append(f"Reduced crew availability for {c_id}")

        # 2. Solve What-If Plan on Isolated Branch State
        solver_config = OptimizerConfig(time_limit_sec=hypothesis.time_limit_sec)

        if hypothesis.use_ml_solver:
            solver = MLIntegratedOptimizer(solver_config=solver_config, bases=self.bases)
        else:
            solver = CPSatOptimizer(config=solver_config, bases=self.bases)

        whatif_plan = solver.solve(snapshot=branch_state, bases=self.bases, previous_plan=current_plan)
        whatif_plan.plan_id = f"PLAN-WHATIF-V{branch_state.version.version}"

        # 3. Generate Diff Rationale & Metrics
        diff_explanation = PlanExplainer.explain_diff(
            old_plan=current_plan,
            new_plan=whatif_plan,
            snapshot=branch_state,
            trigger_reason="What-If Hypothesis Analysis",
        )

        curr_unassigned = set(current_plan.unassigned_tasks)
        whatif_unassigned = set(whatif_plan.unassigned_tasks)
        new_infeasible = list(whatif_unassigned - curr_unassigned)

        obj_diff = round(whatif_plan.metrics.objective_value - current_plan.metrics.objective_value, 2)
        cov_diff = round(whatif_plan.metrics.priority_weighted_coverage - current_plan.metrics.priority_weighted_coverage, 4)
        util_diff = round(whatif_plan.metrics.resource_utilization - current_plan.metrics.resource_utilization, 4)

        result = WhatIfAnalysisResult(
            baseline_plan_id=current_plan.plan_id,
            whatif_plan_id=whatif_plan.plan_id,
            state_version=snapshot.version.version,
            hypothesis_summary=summary,
            current_metrics=current_plan.metrics,
            whatif_metrics=whatif_plan.metrics,
            objective_difference=obj_diff,
            coverage_difference=cov_diff,
            resource_utilization_difference=util_diff,
            plan_churn_score=diff_explanation.plan_churn_score,
            new_infeasibilities=new_infeasible,
            explanation=diff_explanation.model_dump(),
        )
        return result
