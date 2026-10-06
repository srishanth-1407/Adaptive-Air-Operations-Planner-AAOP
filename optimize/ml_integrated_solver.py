"""
Integrated ML + CP-SAT Optimizer.
Incorporates predicted asset readiness probabilities and predicted task success risks
from trained ML models into the CP-SAT objective function.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from state.models import StateSnapshot, AssetState, TaskState
from generator.schemas import BaseSchema
from optimize.schemas import AllocationPlan
from optimize.solver import CPSatOptimizer, OptimizerConfig
from optimize.scoring import haversine_distance_km
from predict.inference import MLInferenceEngine


class MLIntegratedOptimizer:
    """Predictive ML-guided CP-SAT Optimizer."""

    def __init__(
        self,
        readiness_model_path: Optional[str] = "predict/models/xgboost_went_down_within_horizon.joblib",
        task_risk_model_path: Optional[str] = "predict/models/xgboost_task_success.joblib",
        solver_config: Optional[OptimizerConfig] = None,
        bases: Optional[Dict[str, BaseSchema]] = None,
    ):
        self.bases = bases or {}
        self.solver_config = solver_config or OptimizerConfig()
        self.cpsat_solver = CPSatOptimizer(config=self.solver_config, bases=self.bases)

        self.readiness_engine: Optional[MLInferenceEngine] = None
        self.task_risk_engine: Optional[MLInferenceEngine] = None

        if readiness_model_path and Path(readiness_model_path).is_file():
            try:
                self.readiness_engine = MLInferenceEngine(readiness_model_path)
            except Exception:
                self.readiness_engine = None

        if task_risk_model_path and Path(task_risk_model_path).is_file():
            try:
                self.task_risk_engine = MLInferenceEngine(task_risk_model_path)
            except Exception:
                self.task_risk_engine = None

    def compute_predicted_success_probabilities(
        self, snapshot: StateSnapshot, active_bases: Dict[str, BaseSchema]
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculates predicted success probability for every feasible (task_id, asset_id) pair
        using ML model inference.
        """
        predicted_probs: Dict[Tuple[str, str], float] = {}

        tasks = [t for t in snapshot.tasks.values() if t.status != "COMPLETED"]
        assets = [a for a in snapshot.assets.values() if a.status == "AVAILABLE" and a.availability > 0.0]

        if not tasks or not assets:
            return predicted_probs

        # 1. Evaluate Readiness Predictions if ML model active
        readiness_probs: Dict[str, float] = {}
        if self.readiness_engine:
            readiness_rows = []
            asset_order = []
            for a in assets:
                readiness_rows.append(
                    {
                        "timestamp": snapshot.version.timestamp,
                        "asset_id": a.asset_id,
                        "asset_type": a.asset_type,
                        "base_id": a.base_id,
                        "age": a.age,
                        "hours_since_maintenance": a.hours_since_maintenance,
                        "sorties_last_24h": 2,
                        "utilization_last_24h": a.utilization,
                        "environmental_stress": 0.5,
                        "weather_severity": 0.3,
                        "recent_failure_count": 0,
                        "current_status": a.status,
                    }
                )
                asset_order.append(a.asset_id)
            readiness_df = pd.DataFrame(readiness_rows)
            p_fail_4h = self.readiness_engine.predict_proba(readiness_df)
            for a_id, p_f in zip(asset_order, p_fail_4h):
                readiness_probs[a_id] = float(np.clip(1.0 - p_f, 0.05, 1.0))
        else:
            for a in assets:
                readiness_probs[a.asset_id] = 1.0

        # 2. Evaluate Task Risk Predictions if ML model active
        task_risk_rows = []
        pair_order = []

        for task in tasks:
            for asset in assets:
                if asset.asset_type != task.required_resource_type:
                    continue

                base = active_bases.get(asset.base_id)
                base_lat = base.latitude if base else task.latitude
                base_lon = base.longitude if base else task.longitude

                dist_km = haversine_distance_km(base_lat, base_lon, task.latitude, task.longitude)

                task_risk_rows.append(
                    {
                        "timestamp": snapshot.version.timestamp,
                        "task_id": task.task_id,
                        "asset_id": asset.asset_id,
                        "asset_type": asset.asset_type,
                        "task_type": task.task_type,
                        "priority": task.priority,
                        "distance_km": dist_km,
                        "estimated_duration": task.duration,
                        "time_slack": 2.0,
                        "weather_severity": 0.3,
                        "environmental_stress": 0.5,
                        "resource_utilization": asset.utilization,
                    }
                )
                pair_order.append((task.task_id, asset.asset_id))

        if self.task_risk_engine and task_risk_rows:
            tr_df = pd.DataFrame(task_risk_rows)
            task_success_probs = self.task_risk_engine.predict_proba(tr_df)
            for (t_id, a_id), p_succ in zip(pair_order, task_success_probs):
                r_prob = readiness_probs.get(a_id, 1.0)
                # Combined ML probability = Task Success Prob * Asset Readiness Prob
                combined_prob = round(float(np.clip(p_succ * r_prob, 0.05, 1.0)), 4)
                predicted_probs[(t_id, a_id)] = combined_prob
        else:
            for (t_id, a_id) in pair_order:
                r_prob = readiness_probs.get(a_id, 1.0)
                predicted_probs[(t_id, a_id)] = round(float(r_prob), 4)

        return predicted_probs

    def solve(
        self,
        snapshot: StateSnapshot,
        bases: Optional[Dict[str, BaseSchema]] = None,
        previous_plan: Optional[AllocationPlan] = None,
    ) -> AllocationPlan:
        """
        Runs ML probability inference and feeds risk-aware utility expectations into CP-SAT solver.
        """
        active_bases = bases or self.bases

        # Run ML Inference to compute predicted success probabilities
        predicted_probs = self.compute_predicted_success_probabilities(snapshot, active_bases)

        # Run CP-SAT solver with ML probabilities
        plan = self.cpsat_solver.solve(
            snapshot=snapshot,
            bases=active_bases,
            previous_plan=previous_plan,
            predicted_success_probs=predicted_probs,
        )

        plan.solver_type = "CP_SAT + ML (Predictive)"
        return plan
