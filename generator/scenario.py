"""
Scenario Generator Pipeline.
Loads YAML configuration, generates static entities and environment, executes Poisson event generator,
serializes event stream to JSONL, exports synthetic data tables to Parquet, and writes manifest.json.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import yaml
import numpy as np
import pandas as pd

from generator.schemas import (
    ScenarioConfig,
    ManifestSchema,
    BaseSchema,
    ResourceAssetSchema,
    CrewSchema,
    TaskSchema,
    WeatherCellSchema,
    AirspaceZoneSchema,
    EventSchema,
)
from generator.entities import (
    generate_bases,
    generate_assets,
    generate_crews,
    generate_tasks,
)
from generator.environment import (
    generate_weather_cells,
    generate_airspace_zones,
)
from generator.events import generate_event_stream
from generator import __version__


def load_config(config_path: str) -> Tuple[ScenarioConfig, str]:
    """Loads configuration YAML file and computes SHA256 content hash."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw_text = path.read_text(encoding="utf-8")
    config_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    data = yaml.safe_load(raw_text)
    config = ScenarioConfig(**data)
    return config, config_hash


def load_scenario_def(scenario_path: str) -> Dict[str, Any]:
    """Loads scenario definition YAML file."""
    path = Path(scenario_path)
    if not path.is_file():
        raise FileNotFoundError(f"Scenario definition file not found: {scenario_path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


def generate_scenario(
    config_path: str,
    output_dir: str,
    scenario_path: Optional[str] = None,
    override_seed: Optional[int] = None,
) -> ManifestSchema:
    """
    Executes full scenario generation pipeline and outputs Parquet, JSONL, and manifest.json.
    """
    config, config_hash = load_config(config_path)

    scripted_events = []
    if scenario_path:
        scen_def = load_scenario_def(scenario_path)
        scripted_events = scen_def.get("scripted_events", [])
        if "seed" in scen_def and override_seed is None:
            config.seed = scen_def["seed"]

    if override_seed is not None:
        config.seed = override_seed

    rng = np.random.default_rng(config.seed)

    # 1. Generate Static Entities
    bases = generate_bases(config.size, config.geography, rng)
    assets = generate_assets(config.size, bases, rng)
    crews = generate_crews(config.size, bases, rng)
    tasks = generate_tasks(config.size, config.geography, config.simulation.duration_hours, rng)

    # 2. Generate Environment
    weather_cells = generate_weather_cells(config.size, config.geography, config.simulation.duration_hours, rng)
    airspace_zones = generate_airspace_zones(config.size, config.geography, config.simulation.duration_hours, rng)

    # 3. Generate Event Stream
    events = generate_event_stream(
        config=config,
        assets=assets,
        crews=crews,
        tasks=tasks,
        weather_cells=weather_cells,
        airspace_zones=airspace_zones,
        scripted_events=scripted_events,
        rng=rng,
    )

    # 4. Prepare Output Directories
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Export entities to Parquet
    bases_df = pd.DataFrame([b.model_dump() for b in bases])
    assets_df = pd.DataFrame([a.model_dump() for a in assets])
    crews_df = pd.DataFrame([c.model_dump() for c in crews])
    tasks_df = pd.DataFrame([t.model_dump() for t in tasks])
    weather_df = pd.DataFrame([w.model_dump() for w in weather_cells])
    airspace_df = pd.DataFrame([z.model_dump() for z in airspace_zones])

    bases_df.to_parquet(out_path / "bases.parquet", index=False)
    assets_df.to_parquet(out_path / "assets.parquet", index=False)
    crews_df.to_parquet(out_path / "crews.parquet", index=False)
    tasks_df.to_parquet(out_path / "tasks.parquet", index=False)
    weather_df.to_parquet(out_path / "weather.parquet", index=False)
    airspace_df.to_parquet(out_path / "airspace.parquet", index=False)

    # Export event stream to JSONL
    events_jsonl_path = out_path / "events.jsonl"
    with open(events_jsonl_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event.model_dump()) + "\n")

    # Build and export Manifest
    row_counts = {
        "bases": len(bases),
        "assets": len(assets),
        "crews": len(crews),
        "tasks": len(tasks),
        "weather_cells": len(weather_cells),
        "airspace_zones": len(airspace_zones),
        "events": len(events),
    }

    date_range = {
        "start_time": config.simulation.start_time,
        "duration_hours": config.simulation.duration_hours,
    }

    manifest = ManifestSchema(
        seed=config.seed,
        config_hash=config_hash,
        generator_version=__version__,
        schema_version=1,
        row_counts=row_counts,
        date_range=date_range,
    )

    manifest_path = out_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(), indent=2), encoding="utf-8")

    return manifest
