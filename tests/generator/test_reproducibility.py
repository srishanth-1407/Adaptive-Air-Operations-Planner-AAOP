"""
Unit and integration tests for reproducibility, event stream ordering, and scenario generation outputs.
"""

import json
from pathlib import Path
import pytest
import pandas as pd

from generator.scenario import generate_scenario, load_config
from generator.schemas import EventSchema, ManifestSchema


@pytest.fixture
def small_config_path():
    return "configs/small.yaml"


def test_reproducibility_same_seed(small_config_path, tmp_path):
    out1 = tmp_path / "run_001"
    out2 = tmp_path / "run_002"

    manifest1 = generate_scenario(small_config_path, str(out1), override_seed=42)
    manifest2 = generate_scenario(small_config_path, str(out2), override_seed=42)

    assert manifest1.seed == manifest2.seed == 42
    assert manifest1.row_counts == manifest2.row_counts

    # Check that events files are identical
    events1 = (out1 / "events.jsonl").read_text()
    events2 = (out2 / "events.jsonl").read_text()
    assert events1 == events2

    # Check parquet data match
    assets1 = pd.read_parquet(out1 / "assets.parquet")
    assets2 = pd.read_parquet(out2 / "assets.parquet")
    pd.testing.assert_frame_equal(assets1, assets2)


def test_reproducibility_different_seed(small_config_path, tmp_path):
    out1 = tmp_path / "seed_42"
    out2 = tmp_path / "seed_999"

    generate_scenario(small_config_path, str(out1), override_seed=42)
    generate_scenario(small_config_path, str(out2), override_seed=999)

    events1 = (out1 / "events.jsonl").read_text()
    events2 = (out2 / "events.jsonl").read_text()
    assert events1 != events2


def test_event_chronology_and_schema_validation(small_config_path, tmp_path):
    out_dir = tmp_path / "chrono_test"
    generate_scenario(small_config_path, str(out_dir), override_seed=123)

    events_path = out_dir / "events.jsonl"
    assert events_path.exists()

    prev_timestamp = -1.0
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            event = EventSchema.model_validate(data)
            assert event.timestamp >= prev_timestamp, "Events are not chronologically ordered!"
            prev_timestamp = event.timestamp


def test_manifest_metadata(small_config_path, tmp_path):
    out_dir = tmp_path / "manifest_test"
    manifest = generate_scenario(small_config_path, str(out_dir), override_seed=77)

    manifest_file = out_dir / "manifest.json"
    assert manifest_file.exists()

    raw_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    validated_manifest = ManifestSchema.model_validate(raw_manifest)

    assert validated_manifest.seed == 77
    assert "assets" in validated_manifest.row_counts
    assert "events" in validated_manifest.row_counts
    assert validated_manifest.row_counts["assets"] == 20
    assert validated_manifest.row_counts["events"] > 0
