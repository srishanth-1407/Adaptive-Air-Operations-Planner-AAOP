"""
Unit tests for deterministic state transition engine (state/transitions.py).
"""

import pytest
from generator.schemas import EventSchema
from state.models import (
    StateSnapshot,
    StateVersion,
    AssetState,
    TaskState,
    WeatherState,
    CrewState,
)
from state.transitions import apply_event


@pytest.fixture
def base_snapshot():
    v0 = StateVersion(version=0, timestamp=0.0)
    asset = AssetState(
        asset_id="A-0001",
        asset_type="LIGHT_TRANSPORT",
        base_id="BASE-001",
        status="AVAILABLE",
        availability=1.0,
    )
    task = TaskState(
        task_id="T-0001",
        task_type="patrol",
        priority=3,
        latitude=34.0,
        longitude=-115.0,
        required_resource_type="LIGHT_TRANSPORT",
        assigned_asset_id="A-0001",
        status="ASSIGNED",
    )
    weather = WeatherState(
        weather_id="WX-001",
        latitude=34.0,
        longitude=-115.0,
        severity=0.2,
    )
    crew = CrewState(
        crew_id="CREW-0001",
        qualification="LIGHT_TRANSPORT",
        status="AVAILABLE",
        base_id="BASE-001",
    )

    return StateSnapshot(
        version=v0,
        assets={"A-0001": asset},
        tasks={"T-0001": task},
        weather_cells={"WX-001": weather},
        crews={"CREW-0001": crew},
    )


def test_asset_unavailable_transition(base_snapshot):
    event = EventSchema(
        event_id="E-001",
        timestamp=2.5,
        kind="ASSET_UNAVAILABLE",
        payload={"asset_id": "A-0001", "reason": "engine breakdown"},
    )
    next_state = apply_event(base_snapshot, event)

    assert next_state.version.version == 1
    assert next_state.version.timestamp == 2.5
    assert next_state.assets["A-0001"].status == "UNAVAILABLE"
    assert next_state.assets["A-0001"].availability == 0.0

    # Task assigned to A-0001 must be unassigned
    assert next_state.tasks["T-0001"].assigned_asset_id is None
    assert next_state.tasks["T-0001"].status == "UNASSIGNED"


def test_asset_available_transition(base_snapshot):
    # Set asset to unavailable first
    base_snapshot.assets["A-0001"].status = "UNAVAILABLE"
    base_snapshot.assets["A-0001"].availability = 0.0

    event = EventSchema(
        event_id="E-002",
        timestamp=5.0,
        kind="ASSET_AVAILABLE",
        payload={"asset_id": "A-0001"},
    )
    next_state = apply_event(base_snapshot, event)

    assert next_state.version.version == 1
    assert next_state.assets["A-0001"].status == "AVAILABLE"
    assert next_state.assets["A-0001"].availability == 1.0


def test_new_task_transition(base_snapshot):
    event = EventSchema(
        event_id="E-003",
        timestamp=3.0,
        kind="NEW_TASK",
        payload={
            "task_id": "T-NEW-99",
            "task_type": "urgent",
            "priority": 5,
            "latitude": 33.5,
            "longitude": -116.0,
            "duration": 4.0,
            "required_resource_type": "HEAVY_CARGO",
        },
    )
    next_state = apply_event(base_snapshot, event)

    assert "T-NEW-99" in next_state.tasks
    t = next_state.tasks["T-NEW-99"]
    assert t.priority == 5
    assert t.status == "UNASSIGNED"


def test_task_priority_change_transition(base_snapshot):
    event = EventSchema(
        event_id="E-004",
        timestamp=4.0,
        kind="TASK_PRIORITY_CHANGE",
        payload={"task_id": "T-0001", "old_priority": 3, "new_priority": 5},
    )
    next_state = apply_event(base_snapshot, event)
    assert next_state.tasks["T-0001"].priority == 5


def test_weather_update_transition(base_snapshot):
    event = EventSchema(
        event_id="E-005",
        timestamp=4.5,
        kind="WEATHER_UPDATE",
        payload={"weather_id": "WX-001", "new_severity": 0.85},
    )
    next_state = apply_event(base_snapshot, event)
    assert next_state.weather_cells["WX-001"].severity == 0.85
