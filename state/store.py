"""
Live State Store with Redis integration and in-memory fallback.
Manages current state snapshot, versioning, state transitions, and snapshot retrieval.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any
import pandas as pd

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
from state.transitions import apply_event
from state.versioning import HistoricalStateReconstructor


class LiveStateStore:
    """Live State Store providing versioned state access, snapshot persistence, and Redis support."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self._redis_client = None
        self._current_snapshot: Optional[StateSnapshot] = None
        self._reconstructor: Optional[HistoricalStateReconstructor] = None

        if redis_url:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(redis_url)
                self._redis_client.ping()
            except Exception:
                self._redis_client = None

    def initialize_from_tables(
        self,
        assets: Dict[str, AssetState],
        crews: Dict[str, CrewState],
        tasks: Dict[str, TaskState],
        weather_cells: Dict[str, WeatherState],
        airspace_zones: Dict[str, AirspaceState],
    ) -> StateSnapshot:
        """Initializes state snapshot at version 0 from explicit dicts."""
        initial_version = StateVersion(version=0, timestamp=0.0)
        self._current_snapshot = StateSnapshot(
            version=initial_version,
            assets=assets,
            crews=crews,
            tasks=tasks,
            weather_cells=weather_cells,
            airspace_zones=airspace_zones,
        )
        self._reconstructor = HistoricalStateReconstructor(self._current_snapshot)
        self._sync_redis()
        return self._current_snapshot

    def initialize_from_parquet_dir(self, parquet_dir: str) -> StateSnapshot:
        """Initializes state snapshot from Phase 1 generated scenario Parquet directory."""
        path = Path(parquet_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"Scenario directory not found: {parquet_dir}")

        assets_df = pd.read_parquet(path / "assets.parquet")
        crews_df = pd.read_parquet(path / "crews.parquet")
        tasks_df = pd.read_parquet(path / "tasks.parquet")
        weather_df = pd.read_parquet(path / "weather.parquet")
        airspace_df = pd.read_parquet(path / "airspace.parquet")

        assets = {
            row["asset_id"]: AssetState(
                asset_id=row["asset_id"],
                asset_type=row["asset_type"],
                base_id=row["base_id"],
                status=row["status"],
                age=float(row["age"]),
                hours_since_maintenance=float(row["hours_since_maintenance"]),
                endurance=float(row["endurance"]),
                utilization=float(row["utilization"]),
                availability=float(row["availability"]),
                latent_fragility=float(row["latent_fragility"]),
            )
            for _, row in assets_df.iterrows()
        }

        crews = {
            row["crew_id"]: CrewState(
                crew_id=row["crew_id"],
                qualification=row["qualification"],
                duty_hours_left=float(row["duty_hours_left"]),
                status=row["status"],
                base_id=row["base_id"],
            )
            for _, row in crews_df.iterrows()
        }

        tasks = {
            row["task_id"]: TaskState(
                task_id=row["task_id"],
                task_type=row["task_type"],
                priority=int(row["priority"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                earliest_time=float(row["earliest_time"]),
                latest_time=float(row["latest_time"]),
                duration=float(row["duration"]),
                required_resource_type=row["required_resource_type"],
                status="UNASSIGNED",
            )
            for _, row in tasks_df.iterrows()
        }

        weather_cells = {
            row["weather_id"]: WeatherState(
                weather_id=row["weather_id"],
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                radius_km=float(row["radius_km"]),
                severity=float(row["severity"]),
                start_time=float(row["start_time"]),
                end_time=float(row["end_time"]),
            )
            for _, row in weather_df.iterrows()
        }

        airspace_zones = {
            row["zone_id"]: AirspaceState(
                zone_id=row["zone_id"],
                geometry_wkt=row["geometry_wkt"],
                start_time=float(row["start_time"]),
                end_time=float(row["end_time"]),
                restriction_level=float(row["restriction_level"]),
            )
            for _, row in airspace_df.iterrows()
        }

        return self.initialize_from_tables(assets, crews, tasks, weather_cells, airspace_zones)

    def process_event(self, event: EventSchema) -> StateSnapshot:
        """Applies event to live store, increments version, and returns new StateSnapshot."""
        if self._current_snapshot is None or self._reconstructor is None:
            raise RuntimeError("LiveStateStore must be initialized before processing events.")

        self._current_snapshot = self._reconstructor.record_and_apply(event)
        self._sync_redis()
        return self._current_snapshot

    def get_current_state(self) -> StateSnapshot:
        if self._current_snapshot is None:
            raise RuntimeError("State store is uninitialized.")
        return self._current_snapshot

    def get_version(self) -> int:
        return self.get_current_state().version.version

    def get_snapshot_at_version(self, target_version: int) -> StateSnapshot:
        if self._reconstructor is None:
            raise RuntimeError("State store is uninitialized.")
        return self._reconstructor.reconstruct_at_version(target_version)

    def _sync_redis(self):
        """Persists state to Redis if Redis client is active."""
        if self._redis_client and self._current_snapshot:
            try:
                data = self._current_snapshot.model_dump_json()
                self._redis_client.set("airops:live_state", data)
                self._redis_client.set("airops:version", self._current_snapshot.version.version)
            except Exception:
                pass
