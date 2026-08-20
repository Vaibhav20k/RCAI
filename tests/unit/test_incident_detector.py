# Unit Tests for Deterministic Incident Detector
import pytest
from simulator.services.runner import InProcessCluster
from observability.metrics.collector import MetricsCollector
from backend.incidents.detector import IncidentDetector
from simulator.faults.models import FaultConfig, FaultType

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_incident_detector_clean_state(cluster):
    metrics = MetricsCollector(cluster)
    detector = IncidentDetector(metrics)
    
    # Clean cluster produces no incidents
    incidents = detector.detect_incidents_from_metrics()
    assert len(incidents) == 0

def test_incident_detector_detects_anomaly(cluster):
    metrics = MetricsCollector(cluster)
    detector = IncidentDetector(metrics)
    
    # Inject fault on payment service
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0
    )
    cluster.payment_service.fault_injector.set_fault(fault)

    for _ in range(5):
        cluster.payment_client.get("/health")

    incidents = detector.detect_incidents_from_metrics(scenario_id="test_run")
    assert len(incidents) > 0
    inc = incidents[0]
    assert inc.service == "payment-service"
    assert "error rate" in inc.symptom.lower() or "anomaly" in inc.symptom.lower()
