# Unit Tests for Microservice Base Endpoints and Header Propagation
import pytest
from simulator.services.runner import InProcessCluster

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_all_services_health_endpoints(cluster):
    services = cluster.get_service_map()
    clients = {
        "api-gateway": cluster.gateway_client,
        "order-service": cluster.order_client,
        "payment-service": cluster.payment_client,
        "dependency-service": cluster.dep_client,
        "worker-service": cluster.worker_client,
    }
    for name, client in clients.items():
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "UP"
        assert data["service"] == name
        assert "uptime_seconds" in data

def test_all_services_version_metadata(cluster):
    clients = {
        "api-gateway": cluster.gateway_client,
        "order-service": cluster.order_client,
        "payment-service": cluster.payment_client,
        "dependency-service": cluster.dep_client,
        "worker-service": cluster.worker_client,
    }
    for name, client in clients.items():
        resp = client.get("/version")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == name
        assert "version" in data
        assert "config_version" in data

def test_metrics_endpoint_exposes_prometheus_format(cluster):
    resp = cluster.order_client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text
    assert "db_query_duration_seconds" in resp.text

def test_request_id_and_trace_id_propagation(cluster):
    custom_req_id = "test-req-12345"
    custom_trace_id = "test-trace-67890"
    resp = cluster.gateway_client.post(
        "/api/orders",
        json={"user_id": "usr_99", "total_amount": 150.0},
        headers={"X-Request-ID": custom_req_id, "X-Trace-ID": custom_trace_id}
    )
    assert resp.headers.get("X-Request-ID") == custom_req_id
    assert resp.headers.get("X-Trace-ID") == custom_trace_id
