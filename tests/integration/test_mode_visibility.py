# Integration tests for Mode Visibility (LIVE, SIMULATED, UNREACHABLE)
import http.server
import threading
import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from discovery.registry import load_compose_topology, get_current_topology, reset_active_topology
from discovery.models import TopologyNode
from backend.ingestion.models import AlertmanagerAlert
from backend.ingestion.normalizer import AlertNormalizer
from backend.api.app import app

class MockHealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

@pytest.fixture(autouse=True)
def clean_topology_and_settings():
    from backend.config import reset_settings
    reset_active_topology()
    reset_settings()
    yield
    reset_active_topology()
    reset_settings()

@pytest.fixture(scope="module")
def mock_running_service():
    server = http.server.HTTPServer(("127.0.0.1", 0), MockHealthHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()
    server.server_close()

def test_docker_discovery_failure_raises_explicit_error():
    """Verify failed docker discovery raises an explicit error instead of silent fallback."""
    from backend.config import reset_settings
    with patch.dict(os.environ, {"RCAI_DISCOVERY_MODE": "docker", "RCAI_COMPOSE_FILE": ""}):
        reset_settings()
        with pytest.raises(RuntimeError) as excinfo:
            get_current_topology()
        assert "Docker discovery failed" in str(excinfo.value)


def test_compose_topology_detects_live_service(tmp_path, mock_running_service):
    port = mock_running_service
    compose_content = f"""
services:
  commune-backend:
    image: commune-backend:latest
    ports:
      - "{port}:8001"
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content)

    from backend.config import reset_settings
    with patch.dict(os.environ, {"DATA_SOURCE": "simulator"}):
        reset_settings()
        topo = load_compose_topology(compose_file)
        node = topo.nodes.get("commune-backend")
        assert node is not None
        assert node.mode == "LIVE"
        assert node.metrics_port == port or port in node.ports

def test_compose_topology_detects_simulated_when_port_offline(tmp_path):
    compose_content = """
services:
  commune-backend:
    image: commune-backend:latest
    ports:
      - "59999:8001"
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content)

    from backend.config import reset_settings
    with patch.dict(os.environ, {"DATA_SOURCE": "simulator"}):
        reset_settings()
        topo = load_compose_topology(compose_file)
        node = topo.nodes.get("commune-backend")
        assert node is not None
        assert node.mode == "SIMULATED"

def test_compose_topology_detects_unreachable_when_data_source_live(tmp_path):
    compose_content = """
services:
  commune-backend:
    image: commune-backend:latest
    ports:
      - "59999:8001"
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content)

    from backend.config import reset_settings
    with patch.dict(os.environ, {"DATA_SOURCE": "live"}):
        reset_settings()
        topo = load_compose_topology(compose_file)
        node = topo.nodes.get("commune-backend")
        assert node is not None
        assert node.mode == "UNREACHABLE"

def test_alert_normalizer_propagates_target_mode(tmp_path):
    compose_content = """
services:
  offline-svc:
    image: svc:latest
    ports:
      - "59998:8080"
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content)

    from backend.config import reset_settings
    with patch.dict(os.environ, {"DATA_SOURCE": "simulator"}):
        reset_settings()
        load_compose_topology(compose_file)
        alert = AlertmanagerAlert(
            labels={"alertname": "HighLatency", "service": "offline-svc", "severity": "critical"},
            annotations={"description": "High latency detected"}
        )
        inc = AlertNormalizer.normalize_alertmanager_alert(alert)
        assert inc.service == "offline-svc"
        assert inc.target_mode == "SIMULATED"
        assert inc.data_source == "simulated"

def test_api_topology_and_incidents_include_mode():
    client = TestClient(app)
    # Topology
    resp = client.get("/api/topology")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    for n in data["nodes"]:
        assert "mode" in n
        assert n["mode"] in ["LIVE", "SIMULATED", "UNREACHABLE"]

    # Inject scenario to guarantee incident presence
    sc_resp = client.get("/api/scenarios")
    assert sc_resp.status_code == 200
    sc_list = sc_resp.json()
    assert len(sc_list) > 0
    resp_inj = client.post(f"/api/scenarios/inject/{sc_list[0]['scenario_id']}")
    assert resp_inj.status_code == 200

    # Incidents list
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    incs = resp.json()
    assert len(incs) > 0
    for inc in incs:
        assert "target_mode" in inc
        assert "data_source" in inc

