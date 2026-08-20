# Integration Tests for Multimodal Telemetry Observation
import time
import pytest
from simulator.services.runner import InProcessCluster
from simulator.faults.models import FaultConfig, FaultType
from observability.logs.collector import global_log_collector
from observability.tracing.collector import global_trace_collector
from observability.deployments.store import global_deployment_store, DeploymentRecord
from observability.metrics.collector import MetricsCollector
from observability.normalizer import TelemetryNormalizer

@pytest.fixture
def cluster():
    c = InProcessCluster()
    global_log_collector.clear()
    global_trace_collector.clear()
    yield c
    c.clear_all_faults()
    global_log_collector.clear()
    global_trace_collector.clear()

def test_incident_observable_across_metrics_logs_traces_and_deployments(cluster):
    # 1. Record deployment event
    deploy_record = DeploymentRecord(
        deployment_id="dep_pay_bad_v241",
        service="payment-service",
        version="2.4.1",
        previous_version="2.4.0",
        config_version="v2",
        deployed_at=time.time() - 30,
        change_description="Optimized bank routing logic"
    )
    global_deployment_store.record_deployment(deploy_record)
    ev_deploy = TelemetryNormalizer.normalize_deployment_record(deploy_record)
    assert ev_deploy.data["version"] == "2.4.1"

    # 2. Inject Bad Deployment error rate
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0,
        parameters={"http_status": 500}
    )
    cluster.payment_service.fault_injector.set_fault(fault)

    # 3. Send requests through Gateway
    custom_trace_id = "trace_incident_multimodal_1"
    resp = cluster.gateway_client.post(
        "/api/payments",
        json={"order_id": "ord_9901", "user_id": "usr_99", "amount": 100.0},
        headers={"X-Trace-ID": custom_trace_id}
    )
    assert resp.status_code == 500

    # 4. Verify Metrics evidence
    metrics_collector = MetricsCollector(cluster)
    health_stats = metrics_collector.calculate_service_health_stats("payment-service")
    assert health_stats["error_rate"] > 0.0
    ev_metric = TelemetryNormalizer.normalize_metric_summary(
        service_name="payment-service",
        metric_name="error_rate",
        metric_value=health_stats["error_rate"],
        unit="ratio"
    )
    assert ev_metric.data["value"] > 0.0

    # 5. Verify Logs evidence
    logs = global_log_collector.query_logs(service="payment-service", level="ERROR")
    assert len(logs) > 0
    ev_log = TelemetryNormalizer.normalize_log_entry(logs[0])
    assert ev_log.data["level"] == "ERROR"

    # 6. Verify Traces evidence
    spans = global_trace_collector.get_trace(custom_trace_id)
    assert len(spans) > 0
    error_spans = [s for s in spans if s.status_code >= 400]
    assert len(error_spans) > 0
    ev_trace = TelemetryNormalizer.normalize_trace_span(error_spans[0])
    assert ev_trace.data["status_code"] == 500

    # All 4 modalities grounded and normalized with strict provenance
    for ev in [ev_deploy, ev_metric, ev_log, ev_trace]:
        assert ev.provenance.hash_signature is not None
        assert ev.reliability > 0.9
