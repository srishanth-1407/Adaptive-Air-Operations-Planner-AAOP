"""
Performance Engineering & Pipeline Bottleneck Profiler.
Measures latency breakdowns, event ingestion throughput, CPU/Memory footprint, and solver scaling
across Small, Medium, and Large configurations.
"""

import argparse
import sys
import time
import psutil
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

from generator.scenario import generate_scenario
from ingest.replay import EventReplayer
from ingest.producer import EventProducer
from ingest.consumer import EventConsumer
from state.store import LiveStateStore
from predict.inference import MLInferenceEngine
from optimize.greedy import GreedyAllocator
from optimize.solver import CPSatOptimizer, OptimizerConfig
from optimize.ml_integrated_solver import MLIntegratedOptimizer


def profile_pipeline_scale(
    config_path: str = "configs/small.yaml",
    scale_name: str = "small",
    num_events: int = 50,
    tmp_dir: str = "data/scenarios/perf_tmp",
) -> Dict[str, Any]:
    """
    Profiles latency breakdown across all pipeline stages for a given scenario scale.
    """
    process = psutil.Process()
    initial_mem_mb = process.memory_info().rss / (1024 * 1024)

    # 1. Measure Data Generation Latency
    t_gen_start = time.time()
    manifest = generate_scenario(config_path, tmp_dir, override_seed=42)
    gen_time_sec = time.time() - t_gen_start

    # 2. Measure Ingestion & Stream Replay Throughput
    replayer = EventReplayer(f"{tmp_dir}/events.jsonl")
    producer = EventProducer(topic=f"perf-{scale_name}")
    consumer = EventConsumer(topic=f"perf-{scale_name}")

    t_ingest_start = time.time()
    for event in replayer.events[:num_events]:
        producer.publish(event)
        consumer.poll_event(timeout=0.001)
    ingest_elapsed = time.time() - t_ingest_start
    ingest_throughput_eps = round(num_events / max(0.0001, ingest_elapsed), 2)

    # 3. Measure State Fusion Latency
    store = LiveStateStore()
    t_state_init = time.time()
    store.initialize_from_parquet_dir(tmp_dir)
    state_init_ms = (time.time() - t_state_init) * 1000.0

    state_update_times: List[float] = []
    for event in replayer.events[:num_events]:
        t0 = time.time()
        store.process_event(event)
        state_update_times.append((time.time() - t0) * 1000.0)

    avg_state_update_ms = float(np.mean(state_update_times))

    # 4. Measure Feature Generation & ML Inference Latency
    feature_gen_ms = 0.0
    ml_inference_ms = 0.0
    snapshot = store.get_current_state()

    readiness_model_file = "predict/models/xgboost_went_down_within_horizon.joblib"
    if Path(readiness_model_file).is_file():
        engine = MLInferenceEngine(readiness_model_file)
        assets = list(snapshot.assets.values())
        df_feats = pd.DataFrame([
            {
                "timestamp": snapshot.version.timestamp,
                "asset_id": a.asset_id,
                "asset_type": a.asset_type,
                "base_id": a.base_id,
                "age": a.age,
                "hours_since_maintenance": a.hours_since_maintenance,
                "sorties_last_24h": 2,
                "utilization_last_24h": a.utilization,
                "environmental_stress": 0.5,
                "weather_severity": 0.3,
                "recent_failure_count": 0,
                "current_status": a.status,
            }
            for a in assets
        ])

        t_feat = time.time()
        _ = engine.pipeline.transform(df_feats)
        feature_gen_ms = (time.time() - t_feat) * 1000.0

        t_inf = time.time()
        _ = engine.predict_proba(df_feats)
        ml_inference_ms = (time.time() - t_inf) * 1000.0

    # 5. Measure Solver Runtimes
    greedy = GreedyAllocator()
    t_g = time.time()
    _ = greedy.solve(snapshot)
    greedy_runtime_ms = (time.time() - t_g) * 1000.0

    config = OptimizerConfig(time_limit_sec=2.0)
    cpsat = CPSatOptimizer(config=config)
    t_cp = time.time()
    _ = cpsat.solve(snapshot)
    cpsat_runtime_ms = (time.time() - t_cp) * 1000.0

    # Measure Resource Footprint
    final_mem_mb = process.memory_info().rss / (1024 * 1024)
    cpu_percent = process.cpu_percent(interval=0.1)

    # Determine Bottleneck
    latencies = {
        "State Update": avg_state_update_ms,
        "Feature Gen": feature_gen_ms,
        "ML Inference": ml_inference_ms,
        "Greedy Solver": greedy_runtime_ms,
        "CP-SAT Solver": cpsat_runtime_ms,
    }
    primary_bottleneck = max(latencies, key=latencies.get)

    return {
        "scale_name": scale_name,
        "row_counts": manifest.row_counts,
        "gen_time_sec": round(gen_time_sec, 3),
        "ingest_throughput_eps": ingest_throughput_eps,
        "avg_state_update_ms": round(avg_state_update_ms, 3),
        "feature_gen_ms": round(feature_gen_ms, 3),
        "ml_inference_ms": round(ml_inference_ms, 3),
        "greedy_runtime_ms": round(greedy_runtime_ms, 3),
        "cpsat_runtime_ms": round(cpsat_runtime_ms, 3),
        "end_to_end_latency_ms": round(avg_state_update_ms + feature_gen_ms + ml_inference_ms + cpsat_runtime_ms, 3),
        "memory_mb": round(final_mem_mb, 2),
        "cpu_percent": round(cpu_percent, 1),
        "primary_bottleneck": primary_bottleneck,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Performance & Bottleneck Profiling Suite.")
    parser.add_argument("--config", type=str, default="configs/medium.yaml", help="Config YAML path")
    parser.add_argument("--scale", type=str, default="medium", help="Scale identifier (small, medium, large)")

    args = parser.parse_args()

    try:
        profile = profile_pipeline_scale(config_path=args.config, scale_name=args.scale)

        print("==================================================")
        print(f"AAOP Performance & Bottleneck Profile [{profile['scale_name'].upper()}]")
        print("==================================================")
        print(f"Entities:               {profile['row_counts']['assets']} assets, {profile['row_counts']['tasks']} tasks")
        print(f"Ingestion Throughput:   {profile['ingest_throughput_eps']} events/sec")
        print("--------------------------------------------------")
        print("STAGE LATENCY BREAKDOWN (ms):")
        print(f"  State Update:         {profile['avg_state_update_ms']:.3f} ms")
        print(f"  Feature Generation:   {profile['feature_gen_ms']:.3f} ms")
        print(f"  ML Inference:         {profile['ml_inference_ms']:.3f} ms")
        print(f"  Greedy Solver:        {profile['greedy_runtime_ms']:.3f} ms")
        print(f"  CP-SAT Solver:        {profile['cpsat_runtime_ms']:.3f} ms")
        print("--------------------------------------------------")
        print(f"End-to-End Latency:     {profile['end_to_end_latency_ms']:.3f} ms")
        print(f"Memory Footprint:       {profile['memory_mb']:.2f} MB")
        print(f"CPU Utilization:        {profile['cpu_percent']:.1f}%")
        print(f"PRIMARY BOTTLENECK:     {profile['primary_bottleneck']}")
        print("==================================================")

    except Exception as e:
        print(f"Profiling error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
