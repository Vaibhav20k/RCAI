# Unit tests for LiveHttpCollector
import http.server
import threading
import socket
import pytest
from observability.live_http.collector import LiveHttpCollector

class MockServiceHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "commune-backend"}')
        elif self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            payload = (
                "# HELP http_requests_total Total HTTP requests\n"
                "# TYPE http_requests_total counter\n"
                "http_requests_total 42.0\n"
                "# HELP process_cpu_usage CPU usage fraction\n"
                "# TYPE process_cpu_usage gauge\n"
                "process_cpu_usage 0.15\n"
            )
            self.wfile.write(payload.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

@pytest.fixture(scope="module")
def mock_http_service():
    server = http.server.HTTPServer(("127.0.0.1", 0), MockServiceHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()
    server.server_close()

def test_service_liveness_probe_healthy(mock_http_service):
    port = mock_http_service
    collector = LiveHttpCollector(timeout_seconds=1.0)
    probe = collector.probe_service_liveness("commune-backend", ports=[port])
    assert probe.is_live is True
    assert probe.port == port
    assert probe.health_status_code == 200
    assert probe.has_metrics is True
    assert probe.error is None

def test_service_liveness_probe_unreachable():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    unused_port = sock.getsockname()[1]
    sock.close()

    collector = LiveHttpCollector(timeout_seconds=0.2)
    probe = collector.probe_service_liveness("commune-backend", ports=[unused_port])
    assert probe.is_live is False
    assert probe.error is not None

def test_live_http_collector_health_inspection(mock_http_service):
    port = mock_http_service
    collector = LiveHttpCollector(timeout_seconds=1.0)
    health = collector.query_service_health("127.0.0.1", port=port, health_path="/health")
    assert health["is_healthy"] is True
    assert health["status_code"] == 200
    assert health["body"] == {"status": "healthy", "service": "commune-backend"}
    assert health["is_live"] is True

def test_live_http_collector_metrics_inspection(mock_http_service):
    port = mock_http_service
    collector = LiveHttpCollector(timeout_seconds=1.0)
    metrics = collector.scrape_service_metrics("127.0.0.1", port=port, metrics_path="/metrics")
    assert metrics["status"] == "UP"
    assert metrics["is_live_telemetry"] is True
    assert metrics["counters"]["http_requests_total"] == 42.0
    assert metrics["gauges"]["process_cpu_usage"] == 0.15

def test_live_http_collector_unreachable_endpoint():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    unused_port = sock.getsockname()[1]
    sock.close()

    collector = LiveHttpCollector(timeout_seconds=0.2)
    health = collector.query_service_health("127.0.0.1", port=unused_port, health_path="/health")
    assert health["is_healthy"] is False
    assert health["status_code"] == 0
    assert "error" in health

def test_live_http_collector_normalize_evidence():
    collector = LiveHttpCollector()
    ev = collector.normalize_live_metric(
        service="commune-backend",
        metric_name="error_rate",
        metric_value=0.05,
        unit="%",
        query="http://127.0.0.1:8001/metrics"
    )
    assert ev.data["service"] == "commune-backend"
    assert ev.provenance.collector == "LiveHttpCollector"
    assert ev.provenance.hash_signature != ""
    assert ev.data["metric"] == "error_rate"
    assert ev.data["value"] == 0.05
