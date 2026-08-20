# Unit Tests for Synthetic Traffic Generator
import pytest
from simulator.services.runner import InProcessCluster
from simulator.traffic.generator import TrafficGenerator

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_traffic_generator_reproducibility(cluster):
    gen1 = TrafficGenerator(client=cluster.gateway_client, seed=123)
    stats1 = gen1.generate_batch(count=15)
    
    assert stats1.total_requests == 15
    assert stats1.successful_requests == 15
    assert stats1.error_rate == 0.0
    assert stats1.p50_latency_ms > 0.0
    assert stats1.p95_latency_ms >= stats1.p50_latency_ms

def test_traffic_generator_captures_injected_fault_error_rate(cluster):
    from simulator.faults.models import FaultConfig, FaultType
    
    # Inject 50% error rate on gateway
    fault = FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.6
    )
    cluster.gateway_service.fault_injector.set_fault(fault)

    gen = TrafficGenerator(client=cluster.gateway_client, seed=999)
    stats = gen.generate_batch(count=20)
    
    assert stats.failed_requests > 0
    assert stats.error_rate > 0.0
