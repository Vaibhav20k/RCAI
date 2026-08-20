# Stress and Concurrency Tests for Investigation Pipeline
import time
import pytest
from simulator.services.runner import InProcessCluster
from tools.registry import create_default_investigation_tools
from backend.incidents.models import AgentIncidentView, IncidentSeverity, IncidentStatus
from agent.investigator.concurrent import ConcurrentInvestigatorPool
from observability.cache import TelemetryCache

@pytest.fixture
def cluster_and_tools():
    c = InProcessCluster()
    tools = create_default_investigation_tools(c)
    yield c, tools
    c.clear_all_faults()

def test_telemetry_cache_ttl():
    cache = TelemetryCache(ttl_seconds=0.1)
    cache.set("order-service:metrics", {"cpu": 80.0})
    assert cache.get("order-service:metrics") == {"cpu": 80.0}
    time.sleep(0.15)
    assert cache.get("order-service:metrics") is None

def test_concurrent_investigator_pool_throughput(cluster_and_tools):
    cluster, tools = cluster_and_tools
    pool = ConcurrentInvestigatorPool(tool_registry=tools, max_workers=4)

    # Create batch of 8 concurrent incident investigations
    incidents = [
        AgentIncidentView(
            incident_id=f"inc_stress_{i}",
            scenario_id="scenario_db_regression_order",
            started_at=1000.0,
            detected_at=1060.0,
            severity=IncidentSeverity.HIGH,
            service="order-service",
            symptom="Order DB query latency regression",
            status=IncidentStatus.DETECTED,
            incident_window={"start_ts": 900.0, "end_ts": 1060.0}
        )
        for i in range(8)
    ]

    t0 = time.perf_counter()
    reports = pool.investigate_batch(incidents)
    elapsed = time.perf_counter() - t0

    assert len(reports) == 8
    # Ensure average investigation latency is fast under concurrent threads
    assert (elapsed / 8.0) < 0.20 # Under 200ms per investigation
