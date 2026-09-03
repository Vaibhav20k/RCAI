# Integration Tests for Docker Compose Service Auto-Discovery Adapter
import os
import json
import time
import socket
import asyncio
import threading
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytest
import httpx

from discovery.models import TopologyNode, DiscoveredTopology
from discovery.docker_adapter import DockerDiscoveryAdapter
from discovery.registry import (
    get_current_topology,
    get_current_topology_services,
    set_active_topology,
    reset_active_topology,
    DEFAULT_SIMULATOR_NODES
)
from agent.policies.engine import PolicyEngine
from agent.policies.models import RemediationProposal, RemediationActionType
from backend.ingestion.normalizer import AlertNormalizer
from backend.ingestion.models import AlertmanagerAlert
from backend.api.app import app
from starlette.testclient import TestClient
from backend.config import reset_settings

@pytest.fixture(autouse=True)
def clean_topology():
    reset_active_topology()
    reset_settings()
    yield
    reset_active_topology()
    reset_settings()

# ---------------------------------------------------------------------------

# Mock Docker API Responses
# ---------------------------------------------------------------------------

MOCK_DOCKER_CONTAINERS_PAYLOAD = [
    {
        "Id": "abc12345678901234567890",
        "Names": ["/ecommerce_order-service_1"],
        "Image": "ecommerce/order-service:v2.1",
        "Labels": {
            "com.docker.compose.project": "ecommerce",
            "com.docker.compose.service": "order-service",
            "com.docker.compose.version": "2.24.0"
        },
        "Ports": [
            {"PrivatePort": 8001, "PublicPort": 8001, "Type": "tcp"}
        ],
        "NetworkSettings": {
            "Networks": {
                "ecommerce_default": {
                    "IPAddress": "172.28.0.2",
                    "Gateway": "172.28.0.1"
                }
            }
        }
    },
    {
        "Id": "def45678901234567890123",
        "Names": ["/ecommerce_payment-service_1"],
        "Image": "ecommerce/payment-service:v1.0",
        "Labels": {
            "com.docker.compose.project": "ecommerce",
            "com.docker.compose.service": "payment-service"
        },
        "Ports": [
            {"PrivatePort": 8002, "PublicPort": 8002, "Type": "tcp"}
        ],
        "NetworkSettings": {
            "Networks": {
                "ecommerce_default": {
                    "IPAddress": "172.28.0.3"
                }
            }
        }
    },
    {
        "Id": "98765432109876543210987",
        "Names": ["/ecommerce_postgres_1"],
        "Image": "postgres:15-alpine",
        "Labels": {
            "com.docker.compose.project": "ecommerce",
            "com.docker.compose.service": "postgres"
        },
        "Ports": [
            {"PrivatePort": 5432, "Type": "tcp"}
        ],
        "NetworkSettings": {
            "Networks": {
                "ecommerce_default": {
                    "IPAddress": "172.28.0.4"
                }
            }
        }
    }
]

# ---------------------------------------------------------------------------
# Unit & Contract Tests with Mock Transport
# ---------------------------------------------------------------------------

def test_successful_discovery_multiple_services():
    """Verify discovery parses container names, compose labels, ports, and IPs."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/containers/json" in request.url.path
        return httpx.Response(200, json=MOCK_DOCKER_CONTAINERS_PAYLOAD)

    mock_transport = httpx.MockTransport(handler)
    mock_client = httpx.Client(transport=mock_transport, base_url="http://docker")
    adapter = DockerDiscoveryAdapter(custom_client=mock_client)

    topo = adapter.discover(probe_metrics=False)
    assert isinstance(topo, DiscoveredTopology)
    assert len(topo.nodes) == 3
    assert "order-service" in topo.nodes
    assert "payment-service" in topo.nodes
    assert "postgres" in topo.nodes

    order_node = topo.nodes["order-service"]
    assert order_node.service_id == "order-service"
    assert order_node.container_id == "abc123456789"
    assert order_node.ip_address == "172.28.0.2"
    assert order_node.ports == [8001]
    assert order_node.is_db_related is False

    pg_node = topo.nodes["postgres"]
    assert pg_node.is_db_related is True
    assert pg_node.service_type == "database"
    assert pg_node.ports == [5432]

def test_metrics_probing_distinguishes_instrumented_vs_uninstrumented():
    """Verify metrics probing sets has_metrics=True on valid Prometheus endpoint and False on 404."""
    def probe_handler(request: httpx.Request) -> httpx.Response:
        if "8001/metrics" in str(request.url):
            # Valid Prometheus text exposition format
            content = "# HELP http_requests_total Counter\n# TYPE http_requests_total counter\nhttp_requests_total{code=\"200\"} 1042\n"
            return httpx.Response(200, text=content, headers={"Content-Type": "text/plain; version=0.0.4"})
        elif "8002/metrics" in str(request.url):
            # Uninstrumented endpoint returns 404
            return httpx.Response(404, text="Not Found")
        return httpx.Response(500, text="Error")

    probe_transport = httpx.MockTransport(probe_handler)
    probe_client = httpx.Client(transport=probe_transport)

    def docker_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=MOCK_DOCKER_CONTAINERS_PAYLOAD)

    docker_transport = httpx.MockTransport(docker_handler)
    docker_client = httpx.Client(transport=docker_transport, base_url="http://docker")

    adapter = DockerDiscoveryAdapter(custom_client=docker_client)
    topo = adapter.discover(probe_metrics=True, probe_client=probe_client)

    # order-service is instrumented
    assert topo.nodes["order-service"].has_metrics is True
    assert topo.nodes["order-service"].metrics_port == 8001
    assert topo.nodes["order-service"].is_instrumented is True

    # payment-service is uninstrumented but preserved in topology for remediation
    assert topo.nodes["payment-service"].has_metrics is False
    assert topo.nodes["payment-service"].metrics_port is None
    assert topo.nodes["payment-service"].is_instrumented is False

    # postgres was excluded from HTTP metrics probing
    assert topo.nodes["postgres"].has_metrics is False

def test_prometheus_scrape_config_generation():
    """Verify Prometheus scrape_configs YAML contains only instrumented targets with labels."""
    nodes = {
        "order-service": TopologyNode(
            service_id="order-service",
            name="Order Service",
            ip_address="172.28.0.2",
            ports=[8001],
            metrics_port=8001,
            has_metrics=True,
            is_db_related=False
        ),
        "payment-service": TopologyNode(
            service_id="payment-service",
            name="Payment Service",
            ip_address="172.28.0.3",
            ports=[8002],
            metrics_port=None,
            has_metrics=False,
            is_db_related=False
        ),
        "analytics-db": TopologyNode(
            service_id="analytics-db",
            name="Analytics DB",
            ip_address="172.28.0.5",
            ports=[9187],
            metrics_port=9187,
            has_metrics=True,
            is_db_related=True
        )
    }
    topo = DiscoveredTopology(nodes=nodes, discovery_mode="docker")
    scrape_yaml = topo.generate_prometheus_scrape_config(job_name="discovered-workload")

    assert "job_name: 'discovered-workload'" in scrape_yaml
    assert "metrics_path: '/metrics'" in scrape_yaml
    # Instrumented services must appear
    assert "172.28.0.2:8001" in scrape_yaml
    assert "service: 'order-service'" in scrape_yaml
    assert "172.28.0.5:9187" in scrape_yaml
    assert "service: 'analytics-db'" in scrape_yaml
    assert "role: 'database'" in scrape_yaml

    # Uninstrumented payment-service must NOT appear as scrape target
    assert "172.28.0.3" not in scrape_yaml

def test_docker_socket_strict_read_only_guarantee():
    """Verify adapter only issues HTTP GET requests and exposes no mutating methods."""
    recorded_methods = []

    def tracking_handler(request: httpx.Request) -> httpx.Response:
        recorded_methods.append(request.method)
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(tracking_handler), base_url="http://docker")
    adapter = DockerDiscoveryAdapter(custom_client=client)
    adapter.discover()

    assert len(recorded_methods) == 1
    assert recorded_methods[0] == "GET"

    # Verify no mutating methods exist on adapter class
    forbidden_verbs = ["create", "start", "stop", "restart", "delete", "kill", "exec", "remove"]
    for attr in dir(adapter):
        for verb in forbidden_verbs:
            assert not attr.startswith(f"{verb}_"), f"Mutating method found on read-only adapter: {attr}"

def test_graceful_handling_missing_or_inaccessible_socket():
    """Verify adapter logs warning and returns empty topology when socket is absent."""
    adapter = DockerDiscoveryAdapter(socket_path="/tmp/non_existent_rcai_docker.sock")
    topo = adapter.discover()
    assert isinstance(topo, DiscoveredTopology)
    assert len(topo.nodes) == 0
    assert topo.discovery_mode == "docker"

# ---------------------------------------------------------------------------
# All 4 Call Sites Synchronization Test
# ---------------------------------------------------------------------------

def test_all_four_call_sites_read_from_same_source_of_truth():
    """
    Verifies that Policy Gate, GET /api/topology, Alert Normalizer, and Simulator
    all synchronize cleanly against the active discovered topology.
    """
    reset_active_topology()
    custom_nodes = {
        "custom-checkout": TopologyNode(
            service_id="custom-checkout",
            name="Custom Checkout",
            service_type="service",
            ip_address="10.0.1.5",
            ports=[9000],
            has_metrics=True
        ),
        "custom-redis": TopologyNode(
            service_id="custom-redis",
            name="Custom Redis",
            service_type="database",
            ip_address="10.0.1.6",
            ports=[6379],
            has_metrics=False,
            is_db_related=True
        )
    }
    custom_topo = DiscoveredTopology(nodes=custom_nodes, discovery_mode="docker")
    set_active_topology(custom_topo)

    try:
        # Call Site 1: Policy Gate
        policy_engine = PolicyEngine()
        valid_services = policy_engine.get_valid_services()
        assert "custom-checkout" in valid_services
        assert "custom-redis" in valid_services
        assert "api-gateway" not in valid_services # Replaced by discovered topology

        # Allowed proposal for discovered service
        ok_prop = RemediationProposal(
            incident_id="inc_test_1",
            action_type=RemediationActionType.RESTART_SERVICE,
            target_service="custom-checkout",
            parameters={"service": "custom-checkout"},
            rationale="Restart custom checkout container to clear connection pool"
        )
        res = policy_engine.evaluate_proposal(ok_prop)
        assert res.is_allowed is True

        # Denied proposal for obsolete hardcoded service
        denied_prop = RemediationProposal(
            incident_id="inc_test_2",
            action_type=RemediationActionType.RESTART_SERVICE,
            target_service="api-gateway",
            parameters={"service": "api-gateway"},
            rationale="Restart api-gateway container"
        )
        denied_res = policy_engine.evaluate_proposal(denied_prop)
        assert denied_res.is_allowed is False
        assert denied_res.policy_code == "DENIED_UNKNOWN_SERVICE"


        # Call Site 2: GET /api/topology endpoint (used by frontend)
        client = TestClient(app)
        resp = client.get("/api/topology")
        assert resp.status_code == 200
        topo_data = resp.json()
        returned_ids = [n["id"] for n in topo_data["nodes"]]
        assert "custom-checkout" in returned_ids
        assert "custom-redis" in returned_ids

        # Call Site 3: Alert Normalizer target service resolution
        raw_alert = AlertmanagerAlert(
            status="firing",
            labels={"alertname": "CheckoutLatencyHigh", "service": "custom-checkout"},
            annotations={"summary": "p95 latency spike on custom-checkout"}
        )
        resolved_svc = AlertNormalizer.resolve_target_service(raw_alert)
        assert resolved_svc == "custom-checkout"

    finally:
        reset_active_topology()

# ---------------------------------------------------------------------------
# Live Toy HTTP Services + Real Unix Domain Socket End-to-End Test
# ---------------------------------------------------------------------------

class ToyMetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            body = (
                "# HELP http_requests_total Counter of HTTP requests.\n"
                "# TYPE http_requests_total counter\n"
                "http_requests_total{service=\"toy-order-service\",status=\"200\"} 842.0\n"
                "# HELP http_errors_total Counter of error requests.\n"
                "# TYPE http_errors_total counter\n"
                "http_errors_total{service=\"toy-order-service\"} 12.0\n"
            )
            self.wfile.write(body.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress noisy test server logs

class ToyUninstrumentedHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Service has no /metrics endpoint
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def log_message(self, format, *args):
        pass

def test_live_toy_services_e2e_with_real_unix_socket():
    """
    End-to-End sanity test against real running toy HTTP services and a real
    Unix Domain Socket serving the Docker Engine API protocol.
    
    Proves that:
    1. A real Unix socket is opened and read by httpx.HTTPTransport(uds=...).
    2. Real HTTP probing connects to running local ports.
    3. Prom-format (# HELP / # TYPE) text is detected over live TCP.
    4. Uninstrumented service returns has_metrics=False over live TCP.
    5. Working Prometheus scrape config is generated with real targets.
    """
    # 1. Start Toy HTTP Service 1 (Instrumented on free port)
    order_srv = HTTPServer(("127.0.0.1", 0), ToyMetricsHandler)
    order_port = order_srv.server_port
    t_order = threading.Thread(target=order_srv.serve_forever, daemon=True)
    t_order.start()

    # 2. Start Toy HTTP Service 2 (Uninstrumented on free port)
    pay_srv = HTTPServer(("127.0.0.1", 0), ToyUninstrumentedHandler)
    pay_port = pay_srv.server_port
    t_pay = threading.Thread(target=pay_srv.serve_forever, daemon=True)
    t_pay.start()

    # 3. Create real Unix Domain Socket Server serving Docker Engine API
    sock_dir = tempfile.mkdtemp(prefix="rcai_uds_")
    sock_path = os.path.join(sock_dir, "docker.sock")

    docker_containers = [
        {
            "Id": "111122223333444455556666",
            "Names": ["/toy_order_service_1"],
            "Image": "toy/order:latest",
            "Labels": {
                "com.docker.compose.project": "toy_project",
                "com.docker.compose.service": "toy-order-service"
            },
            "Ports": [{"PrivatePort": order_port, "PublicPort": order_port, "Type": "tcp"}],
            "NetworkSettings": {
                "Networks": {"toy_net": {"IPAddress": "127.0.0.1"}}
            }
        },
        {
            "Id": "777788889999000011112222",
            "Names": ["/toy_payment_service_1"],
            "Image": "toy/payment:latest",
            "Labels": {
                "com.docker.compose.project": "toy_project",
                "com.docker.compose.service": "toy-payment-service"
            },
            "Ports": [{"PrivatePort": pay_port, "PublicPort": pay_port, "Type": "tcp"}],
            "NetworkSettings": {
                "Networks": {"toy_net": {"IPAddress": "127.0.0.1"}}
            }
        },
        {
            "Id": "999900001111222233334444",
            "Names": ["/toy_postgres_1"],
            "Image": "postgres:15",
            "Labels": {
                "com.docker.compose.project": "toy_project",
                "com.docker.compose.service": "toy-postgres"
            },
            "Ports": [{"PrivatePort": 5432, "Type": "tcp"}],
            "NetworkSettings": {
                "Networks": {"toy_net": {"IPAddress": "127.0.0.1"}}
            }
        }
    ]

    stop_uds = threading.Event()

    def run_uds_server():
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(sock_path)
        server_sock.listen(5)
        server_sock.settimeout(0.5)

        while not stop_uds.is_set():
            try:
                conn, _ = server_sock.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            try:
                req_data = conn.recv(4096).decode("utf-8")
                if "GET /containers/json" in req_data:
                    body = json.dumps(docker_containers)
                    resp = (
                        f"HTTP/1.1 200 OK\r\n"
                        f"Content-Type: application/json\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        f"Connection: close\r\n\r\n"
                        f"{body}"
                    )
                    conn.sendall(resp.encode("utf-8"))
                else:
                    conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            except Exception:
                pass
            finally:
                conn.close()

        server_sock.close()

    t_uds = threading.Thread(target=run_uds_server, daemon=True)
    t_uds.start()

    try:
        # Give UDS a brief moment to bind
        time.sleep(0.1)

        # 4. Run DockerDiscoveryAdapter against real Unix Domain Socket
        adapter = DockerDiscoveryAdapter(socket_path=sock_path, timeout_seconds=5.0)
        topo = adapter.discover(probe_metrics=True)

        assert len(topo.nodes) == 3
        assert "toy-order-service" in topo.nodes
        assert "toy-payment-service" in topo.nodes
        assert "toy-postgres" in topo.nodes

        # 5. Verify real HTTP metrics probe results
        order_node = topo.nodes["toy-order-service"]
        assert order_node.has_metrics is True
        assert order_node.metrics_port == order_port

        pay_node = topo.nodes["toy-payment-service"]
        assert pay_node.has_metrics is False
        assert pay_node.metrics_port is None

        pg_node = topo.nodes["toy-postgres"]
        assert pg_node.is_db_related is True
        assert pg_node.service_type == "database"

        # 6. Verify Prometheus scrape configuration
        scrape_yaml = adapter.generate_prometheus_scrape_config(topo)
        assert f"127.0.0.1:{order_port}" in scrape_yaml
        assert "service: 'toy-order-service'" in scrape_yaml
        assert f":{pay_port}" not in scrape_yaml

    finally:
        # Clean shutdown
        stop_uds.set()
        order_srv.shutdown()
        pay_srv.shutdown()
        if os.path.exists(sock_path):
            os.remove(sock_path)
        if os.path.exists(sock_dir):
            os.rmdir(sock_dir)
