"""
Unit tests for state versioning and historical reconstruction (state/versioning.py).
"""

import pytest
from generator.schemas import EventSchema
from state.models import StateSnapshot, StateVersion, AssetState
from state.versioning import HistoricalStateReconstructor


@pytest.fixture
def initial_snapshot():
    v0 = StateVersion(version=0, timestamp=0.0)
    asset = AssetState(
        asset_id="A-0001",
        asset_type="PATROL_RECON",
        base_id="BASE-001",
        status="AVAILABLE",
    )
    return StateSnapshot(version=v0, assets={"A-0001": asset})


def test_monotonic_versioning_and_reconstruction(initial_snapshot):
    reconstructor = HistoricalStateReconstructor(initial_snapshot)

    e1 = EventSchema(
        event_id="E-001",
        timestamp=1.0,
        kind="ASSET_UNAVAILABLE",
        payload={"asset_id": "A-0001"},
    )
    e2 = EventSchema(
        event_id="E-002",
        timestamp=2.0,
        kind="ASSET_AVAILABLE",
        payload={"asset_id": "A-0001"},
    )

    s1 = reconstructor.record_and_apply(e1)
    assert s1.version.version == 1
    assert s1.assets["A-0001"].status == "UNAVAILABLE"

    s2 = reconstructor.record_and_apply(e2)
    assert s2.version.version == 2
    assert s2.assets["A-0001"].status == "AVAILABLE"

    # Reconstruct version 0 -> should be AVAILABLE
    rec_v0 = reconstructor.reconstruct_at_version(0)
    assert rec_v0.version.version == 0
    assert rec_v0.assets["A-0001"].status == "AVAILABLE"

    # Reconstruct version 1 -> should be UNAVAILABLE
    rec_v1 = reconstructor.reconstruct_at_version(1)
    assert rec_v1.version.version == 1
    assert rec_v1.assets["A-0001"].status == "UNAVAILABLE"

    # Reconstruct version 2 -> should be AVAILABLE
    rec_v2 = reconstructor.reconstruct_at_version(2)
    assert rec_v2.version.version == 2
    assert rec_v2.assets["A-0001"].status == "AVAILABLE"
