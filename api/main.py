"""
Adaptive Air Operations Planner (AAOP) - FastAPI Main Server Application.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from state.store import LiveStateStore
from api.schemas import HealthResponse
from api.routes import state_routes, plan_routes, whatif_routes, simulation_routes
from generator.scenario import generate_scenario

# Global State Store
global_state_store = LiveStateStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes scenario data and state store on startup."""
    default_scen = "data/scenarios/run_001"
    if not Path(default_scen).is_dir():
        generate_scenario("configs/small.yaml", default_scen, override_seed=42)

    global_state_store.initialize_from_parquet_dir(default_scen)

    # Attach store to route modules
    state_routes.state_store = global_state_store
    plan_routes.state_store = global_state_store
    whatif_routes.state_store = global_state_store
    simulation_routes.state_store = global_state_store

    yield


app = FastAPI(
    title="Adaptive Air Operations Planner (AAOP) API",
    description="AI-Assisted Dynamic Resource Planning and Decision-Support Simulator Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check endpoint returning system status and current version."""
    v = global_state_store.get_version() if global_state_store._current_snapshot else 0
    return HealthResponse(status="ok", version="0.1.0", state_version=v)


# Include Routers
app.include_router(state_routes.router)
app.include_router(plan_routes.router)
app.include_router(whatif_routes.router)
app.include_router(simulation_routes.router)
