# Integration Tests for Investigation Console REST API
import pytest
from starlette.testclient import TestClient
from backend.api.app import app, incidents_db

@pytest.fixture
def client():
    return TestClient(app)

def test_api_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "UP"

def test_api_list_incidents(client):
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert "incident_id" in data[0]

def test_api_trigger_investigation_flow(client):
    # Get first incident
    inc_id = list(incidents_db.keys())[0]
    
    resp = client.post(f"/api/investigate/{inc_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_completed"] is True
    assert "top_hypothesis" in data
    assert "report" in data
    assert len(data["action_history"]) > 0

def test_api_remediation_flow(client):
    inc_id = list(incidents_db.keys())[0]
    
    resp = client.post("/api/remediate", json={
        "incident_id": inc_id,
        "action_type": "optimize_db_index",
        "target_service": "order-service",
        "rationale": "Clear DB latency regression"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "outcome" in data

def test_api_benchmark_summary(client):
    resp = client.get("/api/benchmark/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "benchmarks" in data
    assert "ablations" in data
