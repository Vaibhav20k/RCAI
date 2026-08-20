# Unit Tests for Telemetry Normalization and Evidence Provenance
import time
import pytest
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType
from observability.normalizer import TelemetryNormalizer
from observability.logs.collector import LogEntry
from observability.tracing.collector import Span
from observability.deployments.store import DeploymentRecord

def test_normalized_evidence_schema_and_provenance():
    ev = NormalizedEvidence.create(
        source=EvidenceSource.METRICS,
        evidence_type=EvidenceType.METRIC_SERIES,
        summary="API Gateway error rate spiked to 18%",
        data={"error_rate": 0.18, "threshold": 0.05},
        query="http_requests_total[5m]",
        collector="MetricsCollector",
        reliability=0.99
    )
    assert ev.evidence_id.startswith("ev_")
    assert ev.source == EvidenceSource.METRICS
    assert ev.provenance.collector == "MetricsCollector"
    assert len(ev.provenance.hash_signature) == 16
    assert ev.reliability == 0.99
    assert ev.data["error_rate"] == 0.18

def test_normalizer_log_entry():
    entry = LogEntry(
        timestamp=time.time(),
        service="payment-service",
        level="ERROR",
        event="db_connection_timeout",
        message="Database query timed out after 5000ms",
        request_id="req_9981",
        trace_id="trace_7721",
        version="1.2.0"
    )
    ev = TelemetryNormalizer.normalize_log_entry(entry)
    assert ev.source == EvidenceSource.LOGS
    assert ev.evidence_type == EvidenceType.LOG_RECORD
    assert "payment-service" in ev.summary
    assert ev.data["request_id"] == "req_9981"
    assert ev.data["trace_id"] == "trace_7721"

def test_normalizer_trace_span():
    span = Span(
        trace_id="trace_xyz",
        service_name="order-service",
        operation="POST /api/v1/orders",
        start_time=time.time() - 0.1,
        end_time=time.time(),
        duration_ms=120.5,
        status_code=200
    )
    ev = TelemetryNormalizer.normalize_trace_span(span)
    assert ev.source == EvidenceSource.TRACES
    assert ev.evidence_type == EvidenceType.TRACE_SPAN
    assert "duration=120.50ms" in ev.summary

def test_normalizer_deployment_record():
    rec = DeploymentRecord(
        deployment_id="dep_order_v2",
        service="order-service",
        version="2.0.0",
        previous_version="1.9.0",
        config_version="v2",
        deployed_at=time.time() - 600,
        change_description="Updated SQL query indexing"
    )
    ev = TelemetryNormalizer.normalize_deployment_record(rec)
    assert ev.source == EvidenceSource.DEPLOYMENTS
    assert ev.evidence_type == EvidenceType.DEPLOYMENT_EVENT
    assert ev.data["version"] == "2.0.0"
