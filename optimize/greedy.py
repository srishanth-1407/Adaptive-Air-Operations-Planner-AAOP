"""
Deterministic Greedy Baseline Allocator.
Fast priority-first greedy task assignment algorithm.
"""

import time
from typing import Dict, List, Optional, Set
from state.models import StateSnapshot
from generator.schemas import BaseSchema
from optimize.schemas import AllocationPlan, TaskAssignment, PlanMetrics
from optimize.scoring import haversine_distance_km, evaluate_candidate_score, CRUISE_SPEED_KMH


class GreedyAllocator:
    """Deterministic Greedy Allocator for resource-task assignment."""

    def __init__(self, bases: Optional[Dict[str, BaseSchema]] = None):
        self.bases = bases or {}

    def solve(
        self,
        snapshot: StateSnapshot,
        bases: Optional[Dict[str, BaseSchema]] = None,
    ) -> AllocationPlan:
        """
        Executes priority-sorted greedy allocation on live state snapshot.
        """
        start_time = time.time()
        active_bases = bases or self.bases

        # Extract tasks and sort by priority descending, then earliest_time
        tasks_to_assign = [t for t in snapshot.tasks.values() if t.status != "COMPLETED"]
        tasks_to_assign.sort(key=lambda t: (-t.priority, t.earliest_time))

        assigned_assets: Set[str] = set()
        assigned_crews: Set[str] = set()

        assignments: List[TaskAssignment] = []
        unassigned_task_ids: List[str] = []

        total_priority_all = sum(t.priority for t in tasks_to_assign) or 1
        high_priority_tasks = [t for t in tasks_to_assign if t.priority >= 4]
        total_high_priority = len(high_priority_tasks) or 1

        assigned_priority_sum = 0
        assigned_high_priority_count = 0
        total_objective = 0.0

        for task in tasks_to_assign:
            best_candidate: Optional[TaskAssignment] = None
            best_score: float = -1e9

            # Evaluate all available assets
            for asset in snapshot.assets.values():
                if asset.status != "AVAILABLE" or asset.availability <= 0.0:
                    continue
                if asset.asset_id in assigned_assets:
                    continue
                if asset.asset_type != task.required_resource_type:
                    continue

                # Locate base coordinates
                base = active_bases.get(asset.base_id)
                base_lat = base.latitude if base else task.latitude
                base_lon = base.longitude if base else task.longitude

                dist_km = haversine_distance_km(base_lat, base_lon, task.latitude, task.longitude)
                travel_hours = round(dist_km / CRUISE_SPEED_KMH, 2)
                total_flight_time = travel_hours * 2.0 + task.duration

                # Capability check: endurance
                if total_flight_time > asset.endurance:
                    continue

                # Find available crew at same base with matching qualification
                matching_crew_id: Optional[str] = None
                for crew in snapshot.crews.values():
                    if crew.status == "AVAILABLE" and crew.crew_id not in assigned_crews:
                        if crew.base_id == asset.base_id or crew.qualification == asset.asset_type:
                            matching_crew_id = crew.crew_id
                            break

                score = evaluate_candidate_score(
                    task=task,
                    asset=asset,
                    distance_km=dist_km,
                )

                if score > best_score:
                    best_score = score
                    start_t = max(task.earliest_time, snapshot.version.timestamp + travel_hours)
                    best_candidate = TaskAssignment(
                        task_id=task.task_id,
                        asset_id=asset.asset_id,
                        crew_id=matching_crew_id,
                        base_id=asset.base_id,
                        distance_km=dist_km,
                        estimated_travel_hours=travel_hours,
                        start_time=round(start_t, 2),
                        completion_time=round(start_t + task.duration, 2),
                        candidate_score=score,
                    )

            if best_candidate:
                assignments.append(best_candidate)
                assigned_assets.add(best_candidate.asset_id)
                if best_candidate.crew_id:
                    assigned_crews.add(best_candidate.crew_id)

                assigned_priority_sum += task.priority
                if task.priority >= 4:
                    assigned_high_priority_count += 1
                total_objective += best_score
            else:
                unassigned_task_ids.append(task.task_id)

        elapsed_ms = (time.time() - start_time) * 1000.0

        p_weighted_cov = round(assigned_priority_sum / total_priority_all, 4)
        h_priority_cov = round(assigned_high_priority_count / total_high_priority, 4)
        avg_util = (
            round(
                sum(snapshot.assets[a.asset_id].utilization for a in assignments)
                / max(1, len(assignments)),
                4,
            )
            if assignments
            else 0.0
        )

        metrics = PlanMetrics(
            priority_weighted_coverage=p_weighted_cov,
            high_priority_coverage=h_priority_cov,
            tasks_served=len(assignments),
            tasks_unserved=len(unassigned_task_ids),
            resource_utilization=avg_util,
            runtime_ms=round(elapsed_ms, 2),
            objective_value=round(total_objective, 2),
        )

        plan = AllocationPlan(
            plan_id=f"PLAN-GREEDY-V{snapshot.version.version}",
            state_version=snapshot.version.version,
            timestamp=snapshot.version.timestamp,
            solver_type="GREEDY",
            assignments=assignments,
            unassigned_tasks=unassigned_task_ids,
            metrics=metrics,
        )
        return plan
