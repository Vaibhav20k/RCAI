# Integration Tests for Stage C: Zero-Friction Install Experience
import subprocess
import sys
from pathlib import Path
import pytest
import yaml
from discovery.registry import reset_active_topology

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

@pytest.fixture(autouse=True)
def clean_topology():
    reset_active_topology()
    yield
    reset_active_topology()

def test_docker_compose_snippet_syntax_and_security_guarantees():

    """
    Validates docker-compose.snippet.yml:
    - Parses as valid YAML
    - Mounts /var/run/docker.sock with mandatory :ro flag
    - Sets RCAI_DISCOVERY_MODE=docker
    - Configures rcai and optional rcai-prometheus services
    """
    snippet_path = REPO_ROOT / "docker-compose.snippet.yml"
    assert snippet_path.is_file(), "docker-compose.snippet.yml must exist in repo root"

    content = yaml.safe_load(snippet_path.read_text(encoding="utf-8"))
    assert "services" in content
    services = content["services"]

    # 1. RCAI Service
    assert "rcai" in services
    rcai_svc = services["rcai"]

    # Check environment variables
    env = rcai_svc.get("environment", [])
    env_str = " ".join(str(e) for e in env)
    assert "RCAI_DISCOVERY_MODE=docker" in env_str
    assert "DOCKER_SOCKET_PATH=/var/run/docker.sock" in env_str

    # Check mandatory read-only socket mount
    volumes = rcai_svc.get("volumes", [])
    socket_mount = next((v for v in volumes if "/var/run/docker.sock" in str(v)), None)
    assert socket_mount is not None, "Docker socket must be mounted into RCAI container"
    assert socket_mount.endswith(":ro"), f"Docker socket mount MUST be read-only (:ro), got: {socket_mount}"

    # 2. Bundled Prometheus service
    assert "rcai-prometheus" in services
    prom_svc = services["rcai-prometheus"]
    assert "prom/prometheus" in prom_svc.get("image", "")

def test_compose_manifest_inspector_on_sample_app():
    """
    Tests scripts/inspect_compose.py against a sample 3-service compose file:
    - Detects all 3 services [web, api, postgres]
    - Classifies postgres as DB-related
    - Classifies web and api as non-DB
    - Identifies metrics candidate
    """
    from scripts.inspect_compose import analyze_compose, generate_prometheus_yaml

    sample_compose = REPO_ROOT / "examples" / "sample-app" / "docker-compose.yml"
    assert sample_compose.is_file()

    analysis = analyze_compose(sample_compose)
    assert analysis["total_services"] == 3
    assert set(analysis["services"]) == {"web", "api", "postgres"}
    assert "postgres" in analysis["db_services"]
    assert "web" not in analysis["db_services"]
    assert "api" not in analysis["db_services"]

    scrape_yaml = generate_prometheus_yaml(analysis)
    assert "job_name: 'api'" in scrape_yaml
    assert "job_name: 'postgres'" in scrape_yaml
    assert "job_name: 'web'" in scrape_yaml

def test_install_script_dry_run_execution():
    """
    Tests install.sh with --dry-run against sample-app:
    - Returns exit code 0
    - Outputs expected discovery report
    - Generates prometheus scrape file
    """
    install_script = REPO_ROOT / "install.sh"
    sample_compose = REPO_ROOT / "examples" / "sample-app" / "docker-compose.yml"

    cmd = [str(install_script), "-f", str(sample_compose), "--dry-run"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))

    assert proc.returncode == 0, f"install.sh failed: {proc.stderr}"
    stdout = proc.stdout
    assert "Discovered 3 services: [web, api, postgres]" in stdout
    assert "Database-like services detected: [postgres]" in stdout
    assert "[DRY-RUN] Discovery completed" in stdout

def test_install_script_auto_confirm_flag():
    """
    Tests install.sh with -y flag:
    - Verifies non-interactive execution proceeds without prompting user
    """
    install_script = REPO_ROOT / "install.sh"
    sample_compose = REPO_ROOT / "examples" / "sample-app" / "docker-compose.yml"

    cmd = [str(install_script), "-f", str(sample_compose), "-y"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))

    # Should exit cleanly (either launching if docker is present, or gracefully warning)
    assert proc.returncode == 0, f"install.sh with -y failed: {proc.stderr}"
    assert "Discovered 3 services: [web, api, postgres]" in proc.stdout

def test_topology_scrape_config_api_endpoint():
    """
    Tests GET /api/topology/scrape-config endpoint on FastAPI app.
    """
    from starlette.testclient import TestClient
    from backend.api.app import app

    client = TestClient(app)
    resp = client.get("/api/topology/scrape-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "discovery_mode" in data
    assert "scrape_config_yaml" in data
    assert "scrape_configs:" in data["scrape_config_yaml"]

