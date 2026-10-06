"""
Integration tests for FastAPI backend routes (api/main.py).
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "state_version" in data


def test_get_state_and_version(client):
    res_state = client.get("/state")
    assert res_state.status_code == 200
    state_data = res_state.json()
    assert "version" in state_data
    assert "assets" in state_data

    res_v = client.get("/state/version")
    assert res_v.status_code == 200
    v_data = res_v.json()
    assert "version" in v_data


def test_get_assets_and_tasks(client):
    res_assets = client.get("/assets")
    assert res_assets.status_code == 200
    assert isinstance(res_assets.json(), list)

    res_tasks = client.get("/tasks")
    assert res_tasks.status_code == 200
    assert isinstance(res_tasks.json(), list)


def test_get_plan_and_replan(client):
    res_plan = client.get("/plan")
    assert res_plan.status_code == 200
    plan_data = res_plan.json()
    assert "plan_id" in plan_data

    res_replan = client.post("/replan", json={"solver_type": "GREEDY", "time_limit_sec": 1.0})
    assert res_replan.status_code == 200
    replan_data = res_replan.json()
    assert replan_data["success"] is True
    assert "plan" in replan_data


def test_get_metrics(client):
    res_m = client.get("/metrics")
    assert res_m.status_code == 200
    data = res_m.json()
    assert "total_assets" in data
    assert "total_tasks" in data


def test_whatif_analysis(client):
    payload = {
        "remove_asset_id": "A-0001",
        "time_limit_sec": 1.0,
    }
    res_whatif = client.post("/whatif", json=payload)
    assert res_whatif.status_code == 200
    data = res_whatif.json()
    assert "objective_difference" in data
    assert "whatif_plan" in data


def test_simulation_controls(client):
    res_status = client.get("/simulation/status")
    assert res_status.status_code == 200

    res_start = client.post("/simulation/start", json={"speed_factor": 2.0})
    assert res_start.status_code == 200

    res_stop = client.post("/simulation/stop")
    assert res_stop.status_code == 200
