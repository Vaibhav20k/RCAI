# Unit Tests for Controlled Fault Injection
import time
import pytest
from simulator.services.runner import InProcessCluster
from simulator.faults.models import FaultConfig, FaultType

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_database_regression_fault(cluster):
    # Baseline
    t0 = time.perf_counter()
    resp_normal = cluster.order_client.post(
        "/api/v1/orders",
        json={"user_id": "usr_1", "total_amount": 50.0}
    )
    baseline_duration = time.perf_counter() - t0
    assert resp_normal.status_code == 200

    # Inject 80ms DB delay
    fault = FaultConfig(
        service_name="order-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        db_query_delay_ms=80.0
    )
    cluster.order_service.fault_injector.set_fault(fault)

    t1 = time.perf_counter()
    resp_slow = cluster.order_client.post(
        "/api/v1/orders",
        json={"user_id": "usr_1", "total_amount": 50.0}
    )
    slow_duration = time.perf_counter() - t1
    assert resp_slow.status_code == 200
    assert slow_duration >= 0.07  # Demonstrable delay

def test_bad_deployment_error_rate_fault(cluster):
    # Inject 100% error rate on payment-service
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0,
        parameters={"http_status": 500}
    )
    cluster.payment_service.fault_injector.set_fault(fault)

    resp = cluster.payment_client.post(
        "/api/v1/payments/process",
        json={"order_id": "ord_100", "user_id": "usr_2", "amount": 99.0}
    )
    assert resp.status_code == 500
    assert resp.json()["error"] == "InjectedFaultError"

def test_downstream_dependency_latency_fault(cluster):
    # Inject latency on dependency service
    fault = FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=75.0
    )
    cluster.dependency_service.fault_injector.set_fault(fault)

    t0 = time.perf_counter()
    resp = cluster.dep_client.post(
        "/api/v1/bank/verify",
        json={"account_id": "usr_2", "amount": 100.0}
    )
    duration = time.perf_counter() - t0
    assert resp.status_code == 200
    assert duration >= 0.065

def test_resource_saturation_cpu_burn_fault(cluster):
    # Inject CPU burn
    fault = FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=50.0
    )
    cluster.gateway_service.fault_injector.set_fault(fault)

    t0 = time.perf_counter()
    resp = cluster.gateway_client.get("/health")
    duration = time.perf_counter() - t0
    assert resp.status_code == 200
    assert duration >= 0.045

def test_clear_faults_restores_normal_behavior(cluster):
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0
    )
    cluster.payment_service.fault_injector.set_fault(fault)
    assert cluster.payment_client.get("/health").status_code == 500

    cluster.payment_service.fault_injector.clear_faults()
    assert cluster.payment_client.get("/health").status_code == 200
