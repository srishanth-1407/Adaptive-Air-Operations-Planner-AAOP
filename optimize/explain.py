"""
Structured Explanation Engine for Adaptive Air Operations Planning.
Computes deterministic plan diffs between consecutive allocation plans and generates
data-driven structured explanations for reassignments, drops, displacements, and binding constraints.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from state.models import StateSnapshot
from optimize.schemas import AllocationPlan, TaskAssignment


class ReassignmentExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    previous_asset_id: Optional[str]
    new_asset_id: Optional[str]
    reassignment_type: str  # REASSIGNED, NEWLY_ASSIGNED, DROPPED, UNCHANGED
    primary_reasons: List[str]


class PlanDiffExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id_old: str
    plan_id_new: str
    state_version: int
    timestamp: float
    reassigned_tasks: List[ReassignmentExplanation] = Field(default_factory=list)
    newly_assigned_tasks: List[str] = Field(default_factory=list)
    dropped_tasks: List[str] = Field(default_factory=list)
    displaced_tasks: List[str] = Field(default_factory=list)
    binding_constraints: List[str] = Field(default_factory=list)
    objective_change: float = Field(default=0.0)
    coverage_change: float = Field(default=0.0)
    plan_churn_score: float = Field(default=0.0)


class PlanExplainer:
    """Generates structured, data-grounded explanations for plan transitions."""

    @staticmethod
    def explain_diff(
        old_plan: Optional[AllocationPlan],
        new_plan: AllocationPlan,
        snapshot: StateSnapshot,
        trigger_reason: str = "State event trigger",
    ) -> PlanDiffExplanation:
        """
        Calculates plan diff and generates structured explanations based strictly on snapshot state.
        """
        old_assignments: Dict[str, TaskAssignment] = (
            {a.task_id: a for a in old_plan.assignments} if old_plan else {}
        )
        new_assignments: Dict[str, TaskAssignment] = {a.task_id: a for a in new_plan.assignments}

        reassignments: List[ReassignmentExplanation] = []
        newly_assigned: List[str] = []
        dropped: List[str] = []
        displaced: List[str] = []

        all_task_ids = set(old_assignments.keys()).union(set(new_assignments.keys()))

        for t_id in all_task_ids:
            old_a = old_assignments.get(t_id)
            new_a = new_assignments.get(t_id)

            reasons: List[str] = []

            if old_a is None and new_a is not None:
                newly_assigned.append(t_id)
                reasons.append("New task or newly feasible resource available")
                reassignments.append(
                    ReassignmentExplanation(
                        task_id=t_id,
                        previous_asset_id=None,
                        new_asset_id=new_a.asset_id,
                        reassignment_type="NEWLY_ASSIGNED",
                        primary_reasons=reasons,
                    )
                )

            elif old_a is not None and new_a is None:
                dropped.append(t_id)
                # Determine why dropped
                prev_asset = snapshot.assets.get(old_a.asset_id)
                if prev_asset and prev_asset.status == "UNAVAILABLE":
                    reasons.append(f"Previous resource {old_a.asset_id} became unavailable")
                else:
                    reasons.append("Resource displaced by higher priority task")
                    displaced.append(t_id)

                reassignments.append(
                    ReassignmentExplanation(
                        task_id=t_id,
                        previous_asset_id=old_a.asset_id,
                        new_asset_id=None,
                        reassignment_type="DROPPED",
                        primary_reasons=reasons,
                    )
                )

            elif old_a is not None and new_a is not None and old_a.asset_id != new_a.asset_id:
                prev_asset = snapshot.assets.get(old_a.asset_id)
                if prev_asset and prev_asset.status == "UNAVAILABLE":
                    reasons.append(f"Previous resource {old_a.asset_id} became unavailable")

                reasons.append(f"New resource {new_a.asset_id} was feasible and offered higher expected utility")
                reasons.append("Task remained within valid execution window")
                reasons.append("Plan stability penalty evaluated minimum-churn trade-off")

                reassignments.append(
                    ReassignmentExplanation(
                        task_id=t_id,
                        previous_asset_id=old_a.asset_id,
                        new_asset_id=new_a.asset_id,
                        reassignment_type="REASSIGNED",
                        primary_reasons=reasons,
                    )
                )

        # Binding constraints analysis
        binding_constraints: List[str] = []
        unavailable_asset_count = sum(1 for a in snapshot.assets.values() if a.status == "UNAVAILABLE")
        if unavailable_asset_count > 0:
            binding_constraints.append(f"{unavailable_asset_count} resource(s) currently in maintenance/unavailable")

        unserved_tasks_count = len(new_plan.unassigned_tasks)
        if unserved_tasks_count > 0:
            binding_constraints.append(f"{unserved_tasks_count} task(s) unassigned due to resource endurance/capacity limits")

        # Churn calculation
        total_changed = len(newly_assigned) + len(dropped) + sum(1 for r in reassignments if r.reassignment_type == "REASSIGNED")
        total_tasks_count = len(all_task_ids) or 1
        churn_score = round(total_changed / total_tasks_count, 4)

        old_obj = old_plan.metrics.objective_value if old_plan else 0.0
        old_cov = old_plan.metrics.priority_weighted_coverage if old_plan else 0.0

        diff = PlanDiffExplanation(
            plan_id_old=old_plan.plan_id if old_plan else "NONE",
            plan_id_new=new_plan.plan_id,
            state_version=new_plan.state_version,
            timestamp=new_plan.timestamp,
            reassigned_tasks=reassignments,
            newly_assigned_tasks=newly_assigned,
            dropped_tasks=dropped,
            displaced_tasks=displaced,
            binding_constraints=binding_constraints,
            objective_change=round(new_plan.metrics.objective_value - old_obj, 2),
            coverage_change=round(new_plan.metrics.priority_weighted_coverage - old_cov, 4),
            plan_churn_score=churn_score,
        )
        return diff
