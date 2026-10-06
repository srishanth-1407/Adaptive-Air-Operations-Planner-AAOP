"""
OR-Tools CP-SAT Optimizer for Adaptive Air Operations Planning.
Implements constraint programming model with configurable objective weights and plan stability / churn penalties.
"""

import time
from typing import Dict, List, Optional, Set, Tuple
from ortools.sat.python import cp_model

from state.models import StateSnapshot
from generator.schemas import BaseSchema
from optimize.schemas import AllocationPlan, TaskAssignment, PlanMetrics
from optimize.scoring import haversine_distance_km, evaluate_candidate_score, CRUISE_SPEED_KMH
from optimize.greedy import GreedyAllocator


class OptimizerConfig:
    """Configurable weights for CP-SAT multi-objective optimization."""

    def __init__(
        self,
        weight_priority: float = 100.0,
        weight_utility: float = 50.0,
        weight_distance: float = 0.5,
        weight_churn_penalty: float = 80.0,
        time_limit_sec: float = 5.0,
        num_workers: int = 4,
    ):
        self.weight_priority = weight_priority
        self.weight_utility = weight_utility
        self.weight_distance = weight_distance
        self.weight_churn_penalty = weight_churn_penalty
        self.time_limit_sec = time_limit_sec
        self.num_workers = num_workers


class CPSatOptimizer:
    """OR-Tools CP-SAT solver implementation for resource-task allocation."""

    def __init__(
        self,
        config: Optional[OptimizerConfig] = None,
        bases: Optional[Dict[str, BaseSchema]] = None,
    ):
        self.config = config or OptimizerConfig()
        self.bases = bases or {}

    def solve(
        self,
        snapshot: StateSnapshot,
        bases: Optional[Dict[str, BaseSchema]] = None,
        previous_plan: Optional[AllocationPlan] = None,
        predicted_success_probs: Optional[Dict[Tuple[str, str], float]] = None,
    ) -> AllocationPlan:
        """
        Builds CP-SAT model and solves for optimal task-resource allocations.
        """
        start_time = time.time()
        active_bases = bases or self.bases

        # Extract previous plan assignments for churn penalty calculation
        prev_assignments: Dict[str, str] = {}  # task_id -> asset_id
        if previous_plan:
            for assign in previous_plan.assignments:
                prev_assignments[assign.task_id] = assign.asset_id

        # Extract candidate tasks and assets
        tasks = [t for t in snapshot.tasks.values() if t.status != "COMPLETED"]
        assets = [a for a in snapshot.assets.values() if a.status == "AVAILABLE" and a.availability > 0.0]

        model = cp_model.CpModel()
        x: Dict[Tuple[str, str], cp_model.IntVar] = {}  # (task_id, asset_id) -> BoolVar

        candidate_details: Dict[Tuple[str, str], Dict] = {}

        # 1. Build Decision Variables and Feasibility Constraints
        for task in tasks:
            for asset in assets:
                if asset.asset_type != task.required_resource_type:
                    continue

                base = active_bases.get(asset.base_id)
                base_lat = base.latitude if base else task.latitude
                base_lon = base.longitude if base else task.longitude

                dist_km = haversine_distance_km(base_lat, base_lon, task.latitude, task.longitude)
                travel_hours = round(dist_km / CRUISE_SPEED_KMH, 2)
                total_flight_time = travel_hours * 2.0 + task.duration

                if total_flight_time > asset.endurance:
                    continue

                # Get predicted success probability (default 1.0)
                pred_prob = 1.0
                if predicted_success_probs and (task.task_id, asset.asset_id) in predicted_success_probs:
                    pred_prob = predicted_success_probs[(task.task_id, asset.asset_id)]

                cand_score = evaluate_candidate_score(
                    task=task,
                    asset=asset,
                    distance_km=dist_km,
                    predicted_success_prob=pred_prob,
                )

                var_name = f"x_{task.task_id}_{asset.asset_id}"
                x[(task.task_id, asset.asset_id)] = model.NewBoolVar(var_name)

                candidate_details[(task.task_id, asset.asset_id)] = {
                    "distance_km": dist_km,
                    "travel_hours": travel_hours,
                    "pred_prob": pred_prob,
                    "cand_score": cand_score,
                    "base_id": asset.base_id,
                }

        # If no feasible candidate pairs exist, fallback to greedy baseline
        if not x:
            greedy = GreedyAllocator(active_bases)
            return greedy.solve(snapshot, active_bases)

        # 2. Hard Constraints:
        # Each task assigned to AT MOST ONE asset
        for task in tasks:
            task_vars = [x[(task.task_id, a.asset_id)] for a in assets if (task.task_id, a.asset_id) in x]
            if task_vars:
                model.Add(sum(task_vars) <= 1)

        # Each asset assigned to AT MOST ONE task
        for asset in assets:
            asset_vars = [x[(t.task_id, asset.asset_id)] for t in tasks if (t.task_id, asset.asset_id) in x]
            if asset_vars:
                model.Add(sum(asset_vars) <= 1)

        # 3. Objective Function Terms (Scaled to Integers for CP-SAT)
        objective_terms = []

        for (t_id, a_id), var in x.items():
            task_obj = next(t for t in tasks if t.task_id == t_id)
            details = candidate_details[(t_id, a_id)]

            # Priority Weight Term
            priority_val = int(task_obj.priority * self.config.weight_priority * 10)

            # Utility / Prediction Weight Term
            utility_val = int(details["pred_prob"] * self.config.weight_utility * 10)

            # Distance Penalty Term
            distance_cost = int(details["distance_km"] * self.config.weight_distance * 10)

            # Plan Stability / Churn Penalty Term
            churn_penalty = 0
            if t_id in prev_assignments:
                if prev_assignments[t_id] != a_id:
                    churn_penalty = int(self.config.weight_churn_penalty * 10)

            coef = priority_val + utility_val - distance_cost - churn_penalty
            objective_terms.append(coef * var)

        model.Maximize(cp_model.LinearExpr.Sum(objective_terms))

        # 4. Configure Solver Parameters
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.time_limit_sec
        solver.parameters.num_search_workers = self.config.num_workers

        status_code = solver.Solve(model)
        status_name = solver.StatusName(status_code)

        # Handle solver result
        assignments: List[TaskAssignment] = []
        assigned_task_ids: Set[str] = set()

        total_objective = 0.0
        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for (t_id, a_id), var in x.items():
                if solver.Value(var) == 1:
                    task_obj = next(t for t in tasks if t.task_id == t_id)
                    details = candidate_details[(t_id, a_id)]

                    # Find matching crew
                    matching_crew_id = None
                    for crew in snapshot.crews.values():
                        if crew.status == "AVAILABLE" and crew.base_id == details["base_id"]:
                            matching_crew_id = crew.crew_id
                            break

                    start_t = max(task_obj.earliest_time, snapshot.version.timestamp + details["travel_hours"])
                    assignment = TaskAssignment(
                        task_id=t_id,
                        asset_id=a_id,
                        crew_id=matching_crew_id,
                        base_id=details["base_id"],
                        distance_km=details["distance_km"],
                        estimated_travel_hours=details["travel_hours"],
                        start_time=round(start_t, 2),
                        completion_time=round(start_t + task_obj.duration, 2),
                        candidate_score=details["cand_score"],
                    )
                    assignments.append(assignment)
                    assigned_task_ids.add(t_id)
                    total_objective += details["cand_score"]

        unassigned_task_ids = [t.task_id for t in tasks if t.task_id not in assigned_task_ids]
        elapsed_ms = (time.time() - start_time) * 1000.0

        # Calculate Metrics
        total_priority_all = sum(t.priority for t in tasks) or 1
        high_priority_tasks = [t for t in tasks if t.priority >= 4]
        total_high_priority = len(high_priority_tasks) or 1

        assigned_priority_sum = sum(
            next(t.priority for t in tasks if t.task_id == a.task_id) for a in assignments
        )
        assigned_high_priority_count = sum(
            1 for a in assignments if next(t.priority for t in tasks if t.task_id == a.task_id) >= 4
        )

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
            plan_id=f"PLAN-CPSAT-V{snapshot.version.version}",
            state_version=snapshot.version.version,
            timestamp=snapshot.version.timestamp,
            solver_type=f"CP_SAT ({status_name})",
            assignments=assignments,
            unassigned_tasks=unassigned_task_ids,
            metrics=metrics,
        )
        return plan
