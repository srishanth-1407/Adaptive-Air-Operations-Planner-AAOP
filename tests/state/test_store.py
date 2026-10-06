"""
Unit and integration tests for LiveStateStore (state/store.py).
"""

import pytest
from generator.scenario import generate_scenario
from state.store import LiveStateStore


@pytest.fixture
def scenario_dir(tmp_path):
    out_dir = tmp_path / "store_test_scenario"
    generate_scenario("configs/small.yaml", str(out_dir), override_seed=42)
    return str(out_dir)


def test_live_state_store_initialization(scenario_dir):
    store = LiveStateStore()
    snapshot = store.initialize_from_parquet_dir(scenario_dir)

    assert snapshot.version.version == 0
    assert len(snapshot.assets) == 20
    assert len(snapshot.crews) == 15
    assert len(snapshot.tasks) == 30
    assert len(snapshot.weather_cells) == 3
    assert len(snapshot.airspace_zones) == 2


def test_live_state_store_event_stream_processing(scenario_dir):
    from ingest.replay import EventReplayer

    store = LiveStateStore()
    store.initialize_from_parquet_dir(scenario_dir)

    replayer = EventReplayer(f"{scenario_dir}/events.jsonl")

    event_count = 0
    for event in replayer.replay(speed_factor=0):
        snapshot = store.process_event(event)
        event_count += 1
        assert snapshot.version.version == event_count

    assert store.get_version() == len(replayer.events)
