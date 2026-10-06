"""
Deterministic event generator using Poisson process sampling and explicit state tracking.
Manages repair states, dynamic task arrivals, crew restrictions, weather updates, and airspace restrictions.
All events are chronologically ordered and schema-validated.
"""

from typing import Dict, List, Optional, Any
import numpy as np

from generator.schemas import (
    EventSchema,
    ResourceAssetSchema,
    CrewSchema,
    TaskSchema,
    WeatherCellSchema,
    AirspaceZoneSchema,
    ScenarioConfig,
)
from generator.causal import asset_failure_hazard, environmental_stress


class EventGeneratorState:
    """Tracks state during event generation to enforce explicit persistence/repair dynamics."""

    def __init__(self, assets: List[ResourceAssetSchema], crews: List[CrewSchema]):
        self.asset_states: Dict[str, str] = {a.asset_id: a.status for a in assets}
        self.asset_repair_times: Dict[str, float] = {}  # asset_id -> timestamp when back available
        self.asset_objs: Dict[str, ResourceAssetSchema] = {a.asset_id: a for a in assets}

        self.crew_states: Dict[str, str] = {c.crew_id: c.status for c in crews}
        self.crew_return_times: Dict[str, float] = {}
        self.crew_objs: Dict[str, CrewSchema] = {c.crew_id: c for c in crews}


def generate_event_stream(
    config: ScenarioConfig,
    assets: List[ResourceAssetSchema],
    crews: List[CrewSchema],
    tasks: List[TaskSchema],
    weather_cells: List[WeatherCellSchema],
    airspace_zones: List[AirspaceZoneSchema],
    scripted_events: Optional[List[Dict[str, Any]]] = None,
    rng: Optional[np.random.Generator] = None,
) -> List[EventSchema]:
    """
    Generates a deterministic, chronologically ordered event stream over the simulation duration.
    Uses Poisson processes for stochastic events layered with explicit repair time tracking.
    """
    if rng is None:
        rng = np.random.default_rng(config.seed)

    events: List[EventSchema] = []
    state = EventGeneratorState(assets, crews)

    duration = config.simulation.duration_hours
    time_step = config.simulation.time_step_hours
    current_time = 0.0

    event_counter = 1

    # Add scripted events if present
    if scripted_events:
        for s_event in scripted_events:
            events.append(
                EventSchema(
                    event_id=f"E-{event_counter:05d}",
                    timestamp=float(s_event["timestamp"]),
                    kind=str(s_event["kind"]),
                    schema_version=1,
                    payload=dict(s_event.get("payload", {})),
                )
            )
            event_counter += 1

    # Event rate multipliers (can be dynamically altered by scripted events)
    task_rate_mult = 1.0
    failure_rate_mult = 1.0

    while current_time <= duration:
        # Check active scripted surge parameters at current_time
        for e in events:
            if e.kind == "SURGE_BEGIN" and e.timestamp <= current_time:
                task_rate_mult = float(e.payload.get("task_multiplier", 2.0))
                failure_rate_mult = float(e.payload.get("failure_multiplier", 2.0))
            elif e.kind == "SURGE_END" and e.timestamp <= current_time:
                task_rate_mult = 1.0
                failure_rate_mult = 1.0

        # 1. Process Asset Recovery / Repairs
        for asset_id, repair_end_time in list(state.asset_repair_times.items()):
            if repair_end_time <= current_time and state.asset_states[asset_id] != "AVAILABLE":
                state.asset_states[asset_id] = "AVAILABLE"
                del state.asset_repair_times[asset_id]
                events.append(
                    EventSchema(
                        event_id=f"E-{event_counter:05d}",
                        timestamp=round(current_time, 4),
                        kind="ASSET_AVAILABLE",
                        schema_version=1,
                        payload={"asset_id": asset_id, "reason": "Maintenance complete"},
                    )
                )
                event_counter += 1

        # 2. Process Crew Restrictions Recovery
        for crew_id, return_time in list(state.crew_return_times.items()):
            if return_time <= current_time and state.crew_states[crew_id] != "AVAILABLE":
                state.crew_states[crew_id] = "AVAILABLE"
                del state.crew_return_times[crew_id]
                events.append(
                    EventSchema(
                        event_id=f"E-{event_counter:05d}",
                        timestamp=round(current_time, 4),
                        kind="CREW_AVAILABLE",
                        schema_version=1,
                        payload={"crew_id": crew_id, "reason": "Rest period finished"},
                    )
                )
                event_counter += 1

        # 3. Sample Asset Failures using Shared Causal Model
        env_st = environmental_stress(weather_severity=0.3)
        for asset_id, asset in state.asset_objs.items():
            if state.asset_states[asset_id] == "AVAILABLE":
                p_fail_hourly = asset_failure_hazard(
                    hours_since_maintenance=asset.hours_since_maintenance,
                    utilization=asset.utilization,
                    age=asset.age,
                    env_stress=env_st,
                    latent_fragility=asset.latent_fragility,
                    hazard_params=config.hazard_parameters.model_dump(),
                    rng=rng,
                )
                # Failure hazard for time step dt
                p_fail_step = 1.0 - np.exp(-p_fail_hourly * time_step * failure_rate_mult * config.event_rates.poisson_failure_lambda)
                if rng.uniform(0.0, 1.0) < p_fail_step:
                    state.asset_states[asset_id] = "UNAVAILABLE"
                    repair_duration = float(
                        rng.uniform(config.repair.min_repair_hours, config.repair.max_repair_hours)
                    )
                    state.asset_repair_times[asset_id] = current_time + repair_duration
                    events.append(
                        EventSchema(
                            event_id=f"E-{event_counter:05d}",
                            timestamp=round(current_time, 4),
                            kind="ASSET_UNAVAILABLE",
                            schema_version=1,
                            payload={
                                "asset_id": asset_id,
                                "reason": "Mechanical fault detected",
                                "estimated_repair_hours": round(repair_duration, 2),
                            },
                        )
                    )
                    event_counter += 1

        # 4. Sample Dynamic Task Arrivals (Poisson Process)
        expected_tasks = config.event_rates.poisson_task_arrival_lambda * task_rate_mult * time_step
        num_new_tasks = rng.poisson(expected_tasks)
        for _ in range(num_new_tasks):
            t_idx = int(rng.integers(0, len(tasks)))
            base_t = tasks[t_idx]
            new_task_id = f"T-DYN-{event_counter:05d}"
            events.append(
                EventSchema(
                    event_id=f"E-{event_counter:05d}",
                    timestamp=round(current_time, 4),
                    kind="NEW_TASK",
                    schema_version=1,
                    payload={
                        "task_id": new_task_id,
                        "task_type": base_t.task_type,
                        "priority": int(rng.choice([1, 2, 3, 4, 5])),
                        "latitude": round(float(base_t.latitude + rng.uniform(-0.5, 0.5)), 4),
                        "longitude": round(float(base_t.longitude + rng.uniform(-0.5, 0.5)), 4),
                        "duration": base_t.duration,
                        "required_resource_type": base_t.required_resource_type,
                    },
                )
            )
            event_counter += 1

        # 5. Sample Task Priority Changes
        if rng.uniform(0.0, 1.0) < 0.05 * time_step:
            t_sample = tasks[int(rng.integers(0, len(tasks)))]
            new_priority = int(rng.choice([1, 2, 3, 4, 5]))
            events.append(
                EventSchema(
                    event_id=f"E-{event_counter:05d}",
                    timestamp=round(current_time, 4),
                    kind="TASK_PRIORITY_CHANGE",
                    schema_version=1,
                    payload={
                        "task_id": t_sample.task_id,
                        "old_priority": t_sample.priority,
                        "new_priority": new_priority,
                    },
                )
            )
            event_counter += 1

        # 6. Sample Weather Updates
        if rng.uniform(0.0, 1.0) < config.event_rates.poisson_weather_update_lambda * time_step:
            wx = weather_cells[int(rng.integers(0, len(weather_cells)))]
            new_sev = round(float(np.clip(wx.severity + rng.uniform(-0.2, 0.2), 0.0, 1.0)), 2)
            events.append(
                EventSchema(
                    event_id=f"E-{event_counter:05d}",
                    timestamp=round(current_time, 4),
                    kind="WEATHER_UPDATE",
                    schema_version=1,
                    payload={
                        "weather_id": wx.weather_id,
                        "old_severity": wx.severity,
                        "new_severity": new_sev,
                    },
                )
            )
            event_counter += 1

        # 7. Sample Airspace Restriction Updates
        if rng.uniform(0.0, 1.0) < config.event_rates.poisson_airspace_update_lambda * time_step:
            az = airspace_zones[int(rng.integers(0, len(airspace_zones)))]
            new_rest = round(float(np.clip(az.restriction_level + rng.uniform(-0.25, 0.25), 0.0, 1.0)), 2)
            events.append(
                EventSchema(
                    event_id=f"E-{event_counter:05d}",
                    timestamp=round(current_time, 4),
                    kind="AIRSPACE_UPDATE",
                    schema_version=1,
                    payload={
                        "zone_id": az.zone_id,
                        "old_restriction_level": az.restriction_level,
                        "new_restriction_level": new_rest,
                    },
                )
            )
            event_counter += 1

        # 8. Sample Crew Restrictions
        if rng.uniform(0.0, 1.0) < config.event_rates.poisson_crew_restriction_lambda * time_step:
            avail_crews = [c_id for c_id, st in state.crew_states.items() if st == "AVAILABLE"]
            if avail_crews:
                c_id = str(rng.choice(avail_crews))
                state.crew_states[c_id] = "RESTING"
                rest_duration = float(round(rng.uniform(4.0, 12.0), 1))
                state.crew_return_times[c_id] = current_time + rest_duration
                events.append(
                    EventSchema(
                        event_id=f"E-{event_counter:05d}",
                        timestamp=round(current_time, 4),
                        kind="CREW_RESTRICTION",
                        schema_version=1,
                        payload={
                            "crew_id": c_id,
                            "reason": "Mandatory duty rest cycle",
                            "rest_duration_hours": rest_duration,
                        },
                    )
                )
                event_counter += 1

        current_time += time_step

    # Sort events chronologically
    events.sort(key=lambda e: e.timestamp)
    return events
