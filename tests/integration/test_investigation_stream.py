# Integration Tests for Live Investigation Streaming API
import pytest
from starlette.testclient import TestClient
from backend.api.app import app, incidents_db, seed_inc

def test_investigation_stream_endpoint():
    client = TestClient(app)
    resp = client.get(f"/api/investigate/stream/{seed_inc.incident_id}")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "data:" in text
    assert "START" in text
    assert "COMPLETE" in text
