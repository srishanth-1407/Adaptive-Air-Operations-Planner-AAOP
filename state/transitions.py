"""
Deterministic state transition engine.
Applies incoming domain events to a StateSnapshot to produce a new StateSnapshot with incremented version.
"""

from copy import deepcopy
from typing import Tuple
from generator.schemas import EventSchema
from state.models import (
    StateSnapshot,
    StateVersion,
    AssetState,
    CrewState,
    TaskState,
    WeatherState,
    AirspaceState,
)


def apply_event(snapshot: StateSnapshot, event: EventSchema) -> StateSnapshot:
    """
    Applies a domain event deterministically to produce the next versioned StateSnapshot.
    """
    next_snapshot = deepcopy(snapshot)

    # Increment version
    next_version_num = snapshot.version.version + 1
    next_snapshot.version = StateVersion(
        version=next_version_num,
        timestamp=event.timestamp,
        last_event_id=event.event_id,
        last_event_kind=event.kind,
    )

    kind = event.kind
    payload = event.payload

    if kind == "ASSET_UNAVAILABLE":
        asset_id = payload.get("asset_id")
        if asset_id and asset_id in next_snapshot.assets:
            asset = next_snapshot.assets[asset_id]
            asset.status = "UNAVAILABLE"
            asset.availability = 0.0

            # Unassign tasks currently assigned to this failed asset
            for task in next_snapshot.tasks.values():
                if task.assigned_asset_id == asset_id:
                    task.assigned_asset_id = None
                    task.status = "UNASSIGNED"

    elif kind == "ASSET_AVAILABLE":
        asset_id = payload.get("asset_id")
        if asset_id and asset_id in next_snapshot.assets:
            asset = next_snapshot.assets[asset_id]
            asset.status = "AVAILABLE"
            asset.availability = 1.0

    elif kind == "NEW_TASK":
        task_id = payload.get("task_id")
        if task_id:
            next_snapshot.tasks[task_id] = TaskState(
                task_id=task_id,
                task_type=payload.get("task_type", "patrol"),
                priority=payload.get("priority", 3),
                latitude=payload.get("latitude", 0.0),
                longitude=payload.get("longitude", 0.0),
                duration=payload.get("duration", 2.0),
                required_resource_type=payload.get("required_resource_type", "LIGHT_TRANSPORT"),
                status="UNASSIGNED",
            )

    elif kind == "TASK_PRIORITY_CHANGE":
        task_id = payload.get("task_id")
        if task_id and task_id in next_snapshot.tasks:
            next_snapshot.tasks[task_id].priority = payload.get("new_priority", 3)

    elif kind == "WEATHER_UPDATE":
        wx_id = payload.get("weather_id")
        if wx_id and wx_id in next_snapshot.weather_cells:
            next_snapshot.weather_cells[wx_id].severity = payload.get("new_severity", 0.0)

    elif kind == "AIRSPACE_UPDATE":
        zone_id = payload.get("zone_id")
        if zone_id and zone_id in next_snapshot.airspace_zones:
            next_snapshot.airspace_zones[zone_id].restriction_level = payload.get(
                "new_restriction_level", 0.0
            )

    elif kind == "CREW_RESTRICTION":
        crew_id = payload.get("crew_id")
        if crew_id and crew_id in next_snapshot.crews:
            next_snapshot.crews[crew_id].status = "RESTING"

    elif kind == "CREW_AVAILABLE":
        crew_id = payload.get("crew_id")
        if crew_id and crew_id in next_snapshot.crews:
            next_snapshot.crews[crew_id].status = "AVAILABLE"

    return next_snapshot
