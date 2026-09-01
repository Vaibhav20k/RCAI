# Integration Tests for Live Prometheus Telemetry Ingestion Layer
import os
import time
import pytest
from unittest.mock import patch, MagicMock
import httpx
from backend.config import Settings, get_settings, reset_settings
from observability.models import EvidenceSource, EvidenceType, NormalizedEvidence
from observability.live.client import PrometheusLiveClient
from observability.live.adapter import LivePrometheusAdapter, LiveTelemetryNormalizer
from tools.metrics.query_metrics import QueryMetricsTool
from tools.database.query_db import QueryDatabaseMetricsTool
from tools.registry import create_default_investigation_tools, ToolRegistry
from tools.base import ToolExecutionStatus
from backend.incidents.models import AgentIncidentView, IncidentSeverity, IncidentStatus
from agent.investigator.loop import ActiveInvestigator
from agent.verification.engine import RootCauseVerifier

@pytest.fixture(autouse=True)
def clean_settings():
    reset_settings()
    yield
    reset_settings()

def test_prometheus_live_client_auth_headers():
    # Test Bearer token authentication
    client_bearer = PrometheusLiveClient(
        base_url="http://prom.internal:9090",
        bearer_token="secret_bearer_token_123"
    )
    assert client_bearer._headers["Authorization"] == "Bearer secret_bearer_token_123"
    assert "X-API-Key" not in client_bearer._headers

    # Test API Key authentication
    client_api_key = PrometheusLiveClient(
        base_url="http://prom.internal:9090",
        api_key="secret_api_key_456"
    )
    assert client_api_key._headers["X-API-Key"] == "secret_api_key_456"
    assert "Authorization" not in client_api_key._headers

def test_prometheus_live_client_query_instant_success():
    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"__name__": "http_requests_total", "service": "order-service"},
                    "value": [1700000000.0, "250.0"]
                }
            ]
        }
    }
    
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        client = PrometheusLiveClient(base_url="http://localhost:9090")
        res = client.query_instant('sum(http_requests_total{service="order-service"})')
        
        assert res["status"] == "success"
        assert res["data"]["result"][0]["value"][1] == "250.0"

def test_prometheus_live_client_connection_error_handling():
    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Connection refused")):
        client = PrometheusLiveClient(base_url="http://unreachable-host:9090")
        res = client.query_instant('sum(http_requests_total)')
        assert res["status"] == "error"
        assert res["errorType"] == "connection_error"
        assert "Failed to connect to Prometheus" in res["error"]

def test_live_telemetry_normalizer_sha256_provenance():
    ev = LiveTelemetryNormalizer.normalize_prometheus_metric(
        service="payment-service",
        metric_name="error_rate",
        metric_value=0.85,
        unit="ratio",
        query="prometheus.query(service=payment-service,metric=error_rate)"
    )

    assert ev.source == EvidenceSource.METRICS
    assert ev.evidence_type == EvidenceType.METRIC_SERIES
    assert ev.data["service"] == "payment-service"
    assert ev.data["value"] == 0.85
    assert ev.provenance.collector == "PrometheusLiveCollector"
    assert len(ev.provenance.hash_signature) == 16
    assert "Live Prometheus metric error_rate on payment-service: 0.85 ratio" in ev.summary

def test_live_prometheus_adapter_service_health_stats():
    adapter = LivePrometheusAdapter()
    
    # Mock client query_service_metrics output
    mocked_metrics = {
        "total_requests": 1500.0,
        "error_requests": 300.0,
        "error_rate": 0.20,
        "p95_latency_ms": 45.5,
        "cpu_burn_ms": 0.0,
        "active_faults_count": 0.0
    }
    
    with patch.object(adapter.client, "query_service_metrics", return_value=mocked_metrics):
        stats = adapter.calculate_service_health_stats("order-service")
        assert stats["service"] == "order-service"
        assert stats["total_requests"] == 1500.0
        assert stats["error_rate"] == 0.20
        assert stats["p95_latency_ms"] == 45.5
        assert stats["is_live_telemetry"] is True

        # Test scraping evidence
        evidence = adapter.scrape_service_evidence("order-service")
        assert len(evidence) == 3
        assert all(isinstance(e, NormalizedEvidence) for e in evidence)
        assert all(e.provenance.collector == "PrometheusLiveCollector" for e in evidence)

def test_query_metrics_tool_with_live_adapter():
    adapter = LivePrometheusAdapter()
    mocked_metrics = {
        "total_requests": 800.0,
        "error_requests": 0.0,
        "error_rate": 0.0,
        "p95_latency_ms": 12.0,
        "cpu_burn_ms": 80.0,
        "active_faults_count": 1.0
    }

    with patch.object(adapter.client, "query_service_metrics", return_value=mocked_metrics):
        tool = QueryMetricsTool(metrics_collector=adapter)
        result = tool.execute(service="api-gateway")

        assert result.status == ToolExecutionStatus.SUCCESS
        assert len(result.evidence) == 3
        assert result.raw_output["has_resource_anomaly"] is True
        assert result.raw_output["total_requests"] == 800.0
        
        cpu_ev = next(e for e in result.evidence if e.data.get("metric") == "cpu_burn_ms")
        assert cpu_ev.data["value"] == 80.0
        assert cpu_ev.provenance.collector == "PrometheusLiveCollector"

def test_query_db_metrics_tool_with_live_adapter():
    adapter = LivePrometheusAdapter()
    mocked_metrics = {
        "total_requests": 500.0,
        "active_faults_count": 1.0,
        "cpu_burn_ms": 0.0
    }

    with patch.object(adapter.client, "query_service_metrics", return_value=mocked_metrics):
        tool = QueryDatabaseMetricsTool(metrics_collector=adapter)
        result = tool.execute(service="order-service")

        assert result.status == ToolExecutionStatus.SUCCESS
        assert len(result.evidence) == 1
        assert result.raw_output["has_db_anomaly"] is True
        assert result.evidence[0].provenance.collector == "PrometheusLiveCollector"

def test_end_to_end_investigator_with_live_prometheus_telemetry():
    adapter = LivePrometheusAdapter()
    mocked_metrics = {
        "total_requests": 1200.0,
        "error_requests": 960.0,
        "error_rate": 0.80,
        "p95_latency_ms": 95.0,
        "cpu_burn_ms": 0.0,
        "active_faults_count": 1.0
    }

    with patch.object(adapter.client, "query_service_metrics", return_value=mocked_metrics):
        reg = ToolRegistry()
        reg.register_tool(QueryMetricsTool(metrics_collector=adapter))
        reg.register_tool(QueryDatabaseMetricsTool(metrics_collector=adapter))

        investigator = ActiveInvestigator(tool_registry=reg, max_tool_calls=5)
        now = time.time()
        incident = AgentIncidentView(
            incident_id="inc_live_prom_01",
            scenario_id="live_prometheus_test",
            started_at=now - 60,
            detected_at=now,
            severity=IncidentSeverity.CRITICAL,
            service="order-service",
            symptom="High error rate observed in live Prometheus alerts",
            status=IncidentStatus.DETECTED,
            incident_window={"start_ts": now - 300, "end_ts": now}
        )

        state = investigator.start_investigation(incident)
        state = investigator.step(state)

        assert len(state.action_history) > 0
        last_action = state.action_history[-1]
        assert last_action.tool_name in ["query_db_metrics", "query_metrics"]
        assert len(last_action.evidence_ids) > 0
        
        # Verify evidence provenance
        for ev_id in last_action.evidence_ids:
            ev = state.evidence_store[ev_id]
            assert ev.provenance.collector == "PrometheusLiveCollector"
            assert len(ev.provenance.hash_signature) == 16

        # Generate report and verify SHA256 audit trail
        verifier = RootCauseVerifier()
        report = verifier.generate_incident_report(state)
        assert report.report_id.startswith("rep_")
        assert len(report.evidence_trail) > 0
        assert report.evidence_trail[0]["collector"] == "PrometheusLiveCollector"

def test_data_source_configuration_toggle():
    # Simulator mode
    with patch.dict(os.environ, {"DATA_SOURCE": "simulator"}):
        reset_settings()
        s1 = get_settings()
        assert s1.is_live_mode() is False
        assert s1.DATA_SOURCE == "simulator"
        tools_sim = create_default_investigation_tools()
        qm_sim = tools_sim.get_tool("query_metrics")
        assert qm_sim is not None

    # Live mode
    with patch.dict(os.environ, {"DATA_SOURCE": "live"}):
        reset_settings()
        s2 = get_settings()
        assert s2.is_live_mode() is True
        assert s2.DATA_SOURCE == "live"
        tools_live = create_default_investigation_tools()
        qm_live = tools_live.get_tool("query_metrics")
        assert qm_live is not None
        assert isinstance(qm_live._collector, LivePrometheusAdapter)
