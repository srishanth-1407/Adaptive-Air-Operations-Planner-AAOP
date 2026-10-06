"""
Allocation Plan and Replanning API Routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException

from state.store import LiveStateStore
from optimize.schemas import AllocationPlan
from optimize.greedy import GreedyAllocator
from optimize.solver import CPSatOptimizer, OptimizerConfig
from optimize.ml_integrated_solver import MLIntegratedOptimizer
from optimize.explain import PlanExplainer
from api.schemas import ReplanRequest, ReplanResponse

router = APIRouter(tags=["Plan & Replanning"])

# Shared references
state_store: Optional[LiveStateStore] = None
current_active_plan: Optional[AllocationPlan] = None


def get_store() -> LiveStateStore:
    if state_store is None or state_store._current_snapshot is None:
        raise HTTPException(status_code=503, detail="Live state store is uninitialized.")
    return state_store


@router.get("/plan", response_model=AllocationPlan)
def get_current_plan():
    """Returns current active allocation plan."""
    global current_active_plan
    if current_active_plan is None:
        # Generate initial plan using Greedy
        snapshot = get_store().get_current_state()
        greedy = GreedyAllocator()
        current_active_plan = greedy.solve(snapshot)
    return current_active_plan


@router.post("/replan", response_model=ReplanResponse)
def trigger_replan(req: ReplanRequest):
    """Triggers dynamic replanning using specified solver algorithm."""
    global current_active_plan
    snapshot = get_store().get_current_state()

    config = OptimizerConfig(time_limit_sec=req.time_limit_sec)

    if req.solver_type == "GREEDY":
        solver = GreedyAllocator()
        new_plan = solver.solve(snapshot)
    elif req.solver_type == "CP_SAT":
        solver = CPSatOptimizer(config=config)
        new_plan = solver.solve(snapshot, previous_plan=current_active_plan)
    else:  # CP_SAT_ML
        solver = MLIntegratedOptimizer(solver_config=config)
        new_plan = solver.solve(snapshot, previous_plan=current_active_plan)

    explanation = PlanExplainer.explain_diff(
        old_plan=current_active_plan,
        new_plan=new_plan,
        snapshot=snapshot,
        trigger_reason="API /replan request",
    )

    current_active_plan = new_plan

    return ReplanResponse(
        success=True,
        plan=new_plan,
        explanation=explanation,
    )
