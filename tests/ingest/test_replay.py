"""
Unit tests for event stream replay engine (ingest/replay.py).
"""

import time
import pytest
from generator.scenario import generate_scenario
from ingest.replay import EventReplayer


@pytest.fixture
def sample_events_file(tmp_path):
    out_dir = tmp_path / "replay_test"
    generate_scenario("configs/small.yaml", str(out_dir), override_seed=42)
    return out_dir / "events.jsonl"


def test_replayer_loads_all_events(sample_events_file):
    replayer = EventReplayer(str(sample_events_file))
    assert len(replayer.events) > 0


def test_replayer_max_throughput_mode(sample_events_file):
    replayer = EventReplayer(str(sample_events_file))
    start = time.time()
    replayed_events = list(replayer.replay(speed_factor=0))
    elapsed = time.time() - start

    assert len(replayed_events) == len(replayer.events)
    # Replay at max throughput should be almost instantaneous (<0.5s)
    assert elapsed < 0.5


def test_replayer_event_sequence_integrity(sample_events_file):
    replayer = EventReplayer(str(sample_events_file))
    replayed = list(replayer.replay(speed_factor=0))

    # Verify event timestamps are strictly non-decreasing
    for i in range(1, len(replayed)):
        assert replayed[i].timestamp >= replayed[i - 1].timestamp
