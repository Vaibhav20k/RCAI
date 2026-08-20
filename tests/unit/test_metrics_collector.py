# Unit Tests for Metrics Collector
import pytest
from simulator.services.runner import InProcessCluster
from observability.metrics.collector import MetricsCollector
from simulator.faults.models import FaultConfig, FaultType

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_metrics_collector_scrape_and_stats(cluster):
    collector = MetricsCollector(cluster)
    
    # Generate 5 requests
    for _ in range(5):
        cluster.order_client.post("/api/v1/orders", json={"user_id": "usr_1", "total_amount": 50.0})
        
    stats = collector.calculate_service_health_stats("order-service")
    assert stats["service"] == "order-service"
    assert stats["total_requests"] >= 5.0
    assert stats["error_rate"] == 0.0

def test_metrics_collector_detects_error_rate(cluster):
    collector = MetricsCollector(cluster)
    
    # Inject 100% error rate on payment service
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0
    )
    cluster.payment_service.fault_injector.set_fault(fault)

    for _ in range(4):
        cluster.payment_client.get("/health")

    stats = collector.calculate_service_health_stats("payment-service")
    assert stats["error_rate"] == 1.0
    assert stats["active_faults"] == 1.0
