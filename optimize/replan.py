"""
Dynamic Replanning Engine and Trigger Evaluator.
Evaluates state changes and incoming domain events to decide when replanning is required,
executes dynamic replanning using Greedy baseline and CP-SAT Optimizer, and tracks end-to-end latencies.
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from generator.schemas import EventSchema
from state.models import StateSnapshot
from state.store import LiveStateStore
from generator.schemas import BaseSchema
from optimize.schemas import AllocationPlan
from optimize.greedy import GreedyAllocator
from optimize.solver import CPSatOptimizer, OptimizerConfig


class ReplanTriggerEvaluator:
    """Evaluates whether an incoming event requires triggering a dynamic replan."""

    @staticmethod
    def should_replan(event: EventSchema, snapshot: StateSnapshot) -> Tuple[bool, str]:
        kind = event.kind
        payload = event.payload

        if kind == "ASSET_UNAVAILABLE":
            asset_id = payload.get("asset_id")
            # If failed asset was assigned to any active task, MUST replan
            for task in snapshot.tasks.values():
                if task.assigned_asset_id == asset_id:
                    return True, f"Assigned asset {asset_id} became unavailable"
            return True, f"Asset {asset_id} became unavailable"

        elif kind == "NEW_TASK":
            priority = int(payload.get("priority", 1))
            if priority >= 3:
                return True, f"New high-priority task {payload.get('task_id')} arrived (priority {priority})"

        elif kind == "TASK_PRIORITY_CHANGE":
            new_p = int(payload.get("new_priority", 1))
            if new_p >= 4:
                return True, f"Task {payload.get('task_id')} priority escalated to {new_p}"

        elif kind == "WEATHER_UPDATE":
            new_sev = float(payload.get("new_severity", 0.0))
            if new_sev >= 0.7:
                return True, f"Weather severity spike ({new_sev}) in zone {payload.get('weather_id')}"

        elif kind == "AIRSPACE_UPDATE":
            new_rest = float(payload.get("new_restriction_level", 0.0))
            if new_rest >= 0.8:
                return True, f"Airspace restriction elevated to {new_rest} in zone {payload.get('zone_id')}"

        elif kind == "CREW_RESTRICTION":
            crew_id = payload.get("crew_id")
            # If crew was assigned, trigger replan
            return True, f"Crew restriction for {crew_id}"

        return False, "No critical replan trigger met"


class DynamicReplanner:
    """Executes dynamic replanning pipeline and measures event-to-plan latencies."""

    def __init__(
        self,
        store: LiveStateStore,
        bases: Optional[Dict[str, BaseSchema]] = None,
        solver_config: Optional[OptimizerConfig] = None,
    ):
        self.store = store
        self.bases = bases or {}
        self.evaluator = ReplanTriggerEvaluator()
        self.greedy_allocator = GreedyAllocator(self.bases)
        self.cpsat_optimizer = CPSatOptimizer(config=solver_config, bases=self.bases)

        self.current_plan: Optional[AllocationPlan] = None
        self.replan_history: List[Dict[str, Any]] = []

    def handle_event(self, event: EventSchema) -> Dict[str, Any]:
        """
        Executes end-to-end event-driven state update and dynamic replanning loop:
        Event -> Update State -> Evaluate Trigger -> Solve Greedy & CP-SAT -> Update Plan -> Report Latency
        """
        start_event_time = time.time()

        # 1. Update State & Increment Version
        state_start = time.time()
        snapshot = self.store.process_event(event)
        state_update_ms = (time.time() - state_start) * 1000.0

        # 2. Evaluate Replan Trigger
        trigger_replan, reason = self.evaluator.should_replan(event, snapshot)

        greedy_plan = None
        cpsat_plan = None
        replan_executed = False

        greedy_ms = 0.0
        cpsat_ms = 0.0

        if trigger_replan:
            replan_executed = True

            # Run Greedy Baseline
            t_g = time.time()
            greedy_plan = self.greedy_allocator.solve(snapshot, self.bases)
            greedy_ms = (time.time() - t_g) * 1000.0

            # Run CP-SAT Optimizer with Plan Stability Churn Penalty against current_plan
            t_cp = time.time()
            cpsat_plan = self.cpsat_optimizer.solve(
                snapshot=snapshot,
                bases=self.bases,
                previous_plan=self.current_plan,
            )
            cpsat_ms = (time.time() - t_cp) * 1000.0

            # Update current plan
            self.current_plan = cpsat_plan

        total_event_to_plan_ms = (time.time() - start_event_time) * 1000.0

        record = {
            "event_id": event.event_id,
            "event_kind": event.kind,
            "timestamp": event.timestamp,
            "state_version": snapshot.version.version,
            "replan_triggered": trigger_replan,
            "replan_reason": reason,
            "replan_executed": replan_executed,
            "state_update_ms": round(state_update_ms, 3),
            "greedy_runtime_ms": round(greedy_ms, 3),
            "cpsat_solve_time_ms": round(cpsat_ms, 3),
            "event_to_plan_latency_ms": round(total_event_to_plan_ms, 3),
            "current_plan": self.current_plan,
        }

        self.replan_history.append(record)
        return record
