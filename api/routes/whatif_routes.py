"""
What-If Branching Analysis API Routes.
Exempt from modifying actual live state.
"""

from copy import deepcopy
from typing import Optional
from fastapi import APIRouter, HTTPException

from state.store import LiveStateStore
from state.models import TaskState, StateSnapshot
from optimize.solver import CPSatOptimizer, OptimizerConfig
from optimize.explain import PlanExplainer
from api.schemas import WhatIfRequest, WhatIfResponse
from api.routes.plan_routes import get_current_plan

router = APIRouter(tags=["What-If Analysis"])

state_store: Optional[LiveStateStore] = None


def get_store() -> LiveStateStore:
    if state_store is None or state_store._current_snapshot is None:
        raise HTTPException(status_code=503, detail="Live state store is uninitialized.")
    return state_store


@router.post("/whatif", response_model=WhatIfResponse)
def evaluate_whatif(req: WhatIfRequest):
    """
    Executes hypothetical what-if scenario on a temporary branch state copy.
    DOES NOT modify live state.
    """
    base_snapshot = get_store().get_current_state()
    current_plan = get_current_plan()

    # 1. Create temporary deepcopy branch
    temp_snapshot: StateSnapshot = deepcopy(base_snapshot)

    # 2. Apply hypothetical modifications
    if req.remove_asset_id and req.remove_asset_id in temp_snapshot.assets:
        temp_snapshot.assets[req.remove_asset_id].status = "UNAVAILABLE"
        temp_snapshot.assets[req.remove_asset_id].availability = 0.0

    if req.add_task:
        t_data = req.add_task
        task_id = t_data.get("task_id", f"T-HYPO-{len(temp_snapshot.tasks)+1}")
        temp_snapshot.tasks[task_id] = TaskState(
            task_id=task_id,
            task_type=t_data.get("task_type", "urgent"),
            priority=int(t_data.get("priority", 5)),
            latitude=float(t_data.get("latitude", 34.0)),
            longitude=float(t_data.get("longitude", -115.0)),
            duration=float(t_data.get("duration", 3.0)),
            required_resource_type=t_data.get("required_resource_type", "LIGHT_TRANSPORT"),
            status="UNASSIGNED",
        )

    if req.weather_severity_increase:
        for wx_id, new_sev in req.weather_severity_increase.items():
            if wx_id in temp_snapshot.weather_cells:
                temp_snapshot.weather_cells[wx_id].severity = new_sev

    # 3. Run CP-SAT on hypothetical state
    config = OptimizerConfig(time_limit_sec=req.time_limit_sec)
    solver = CPSatOptimizer(config=config)
    whatif_plan = solver.solve(temp_snapshot, previous_plan=current_plan)

    explanation = PlanExplainer.explain_diff(
        old_plan=current_plan,
        new_plan=whatif_plan,
        snapshot=temp_snapshot,
        trigger_reason="What-if simulation branch",
    )

    obj_diff = round(whatif_plan.metrics.objective_value - current_plan.metrics.objective_value, 2)
    cov_diff = round(whatif_plan.metrics.priority_weighted_coverage - current_plan.metrics.priority_weighted_coverage, 4)
    new_unserved = [t_id for t_id in whatif_plan.unassigned_tasks if t_id not in current_plan.unassigned_tasks]

    return WhatIfResponse(
        current_plan_metrics=current_plan.metrics,
        whatif_plan_metrics=whatif_plan.metrics,
        objective_difference=obj_diff,
        coverage_difference=cov_diff,
        new_unassigned_tasks=new_unserved,
        plan_churn_score=explanation.plan_churn_score,
        whatif_plan=whatif_plan,
    )
