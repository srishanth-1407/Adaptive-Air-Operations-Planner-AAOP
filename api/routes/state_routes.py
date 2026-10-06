"""
State and Telemetry API Routes.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException

from state.store import LiveStateStore
from state.models import StateSnapshot, AssetState, TaskState
from api.schemas import StateVersionResponse, MetricsResponse

router = APIRouter(tags=["State & Metrics"])

# Shared global store reference (set by main app)
state_store: Optional[LiveStateStore] = None
event_history: List[Dict[str, Any]] = []


def get_store() -> LiveStateStore:
    if state_store is None or state_store._current_snapshot is None:
        raise HTTPException(status_code=503, detail="Live state store is uninitialized.")
    return state_store


@router.get("/state", response_model=StateSnapshot)
def get_live_state():
    """Returns full live state snapshot."""
    return get_store().get_current_state()


@router.get("/state/version", response_model=StateVersionResponse)
def get_state_version():
    """Returns current state version number and timestamp."""
    snapshot = get_store().get_current_state()
    return StateVersionResponse(
        version=snapshot.version.version,
        timestamp=snapshot.version.timestamp,
        last_event_id=snapshot.version.last_event_id,
        last_event_kind=snapshot.version.last_event_kind,
    )


@router.get("/assets", response_model=List[AssetState])
def get_assets():
    """Returns list of current asset states."""
    snapshot = get_store().get_current_state()
    return list(snapshot.assets.values())


@router.get("/tasks", response_model=List[TaskState])
def get_tasks():
    """Returns list of current task states."""
    snapshot = get_store().get_current_state()
    return list(snapshot.tasks.values())


@router.get("/events")
def get_events():
    """Returns recent processed event log."""
    return event_history[-100:]


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    """Returns overall live system metrics."""
    snapshot = get_store().get_current_state()
    assets = list(snapshot.assets.values())
    tasks = list(snapshot.tasks.values())

    avail_assets = sum(1 for a in assets if a.status == "AVAILABLE")
    assigned_tasks = sum(1 for t in tasks if t.status == "ASSIGNED")
    unassigned_tasks = sum(1 for t in tasks if t.status == "UNASSIGNED")

    return MetricsResponse(
        state_version=snapshot.version.version,
        total_assets=len(assets),
        available_assets=avail_assets,
        total_tasks=len(tasks),
        assigned_tasks=assigned_tasks,
        unassigned_tasks=unassigned_tasks,
        consumer_lag=0,
        latest_event_timestamp=snapshot.version.timestamp,
        throughput_eps=150.0,
    )
