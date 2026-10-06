"""
Simulation Execution and Control API Routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException

from state.store import LiveStateStore
from api.schemas import SimulationControlRequest, SimulationStatusResponse

router = APIRouter(tags=["Simulation Control"])

# Simulation runtime flags
sim_running: bool = False
sim_speed: float = 1.0
sim_scenario_path: str = "data/scenarios/run_001"
state_store: Optional[LiveStateStore] = None


def get_store() -> LiveStateStore:
    if state_store is None or state_store._current_snapshot is None:
        raise HTTPException(status_code=503, detail="Live state store is uninitialized.")
    return state_store


@router.get("/simulation/status", response_model=SimulationStatusResponse)
def get_simulation_status():
    """Returns simulation status."""
    snapshot = get_store().get_current_state()
    return SimulationStatusResponse(
        running=sim_running,
        speed_factor=sim_speed,
        current_time=snapshot.version.timestamp,
        total_events_processed=snapshot.version.version,
        consumer_lag=0,
    )


@router.post("/simulation/start")
def start_simulation(req: SimulationControlRequest):
    """Starts / resumes simulation event streaming loop."""
    global sim_running, sim_speed, sim_scenario_path
    sim_running = True
    sim_speed = req.speed_factor
    if req.scenario_path:
        sim_scenario_path = req.scenario_path
    return {"message": "Simulation started", "speed_factor": sim_speed, "scenario": sim_scenario_path}


@router.post("/simulation/stop")
def stop_simulation():
    """Stops / pauses simulation event streaming loop."""
    global sim_running
    sim_running = False
    return {"message": "Simulation stopped"}


@router.post("/simulation/reset")
def reset_simulation(req: SimulationControlRequest):
    """Resets state store back to version 0 of target scenario."""
    global sim_running, sim_scenario_path
    sim_running = False
    scen_path = req.scenario_path or sim_scenario_path
    get_store().initialize_from_parquet_dir(scen_path)
    return {"message": "Simulation reset to version 0", "scenario": scen_path}
