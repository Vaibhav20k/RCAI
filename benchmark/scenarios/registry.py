# Benchmark Incident Scenario Registry
from typing import Dict, List, Optional
from benchmark.scenarios.models import ScenarioDefinition
from simulator.faults.models import FaultConfig, FaultType
from backend.incidents.models import GroundTruth, IncidentSeverity

SCENARIO_DB_REGRESSION_ORDER = ScenarioDefinition(
    scenario_id="scenario_db_regression_order",
    name="Order Service Database Query Latency Regression",
    description="Unindexed database queries in Order Service create severe query latency degradation under traffic",
    service="order-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="API Gateway orders endpoint p95 latency spiked above 80ms (normal < 20ms)",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        db_query_delay_ms=90.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="database_regression",
        description="Database query latency regression in order_service",
        injected_fault_config={"db_query_delay_ms": 90.0},
        expected_remediation="rebuild_order_table_index",
        verification_criteria={"max_p95_latency_ms": 30.0}
    )
)

SCENARIO_BAD_DEPLOY_PAYMENT = ScenarioDefinition(
    scenario_id="scenario_bad_deploy_payment",
    name="Payment Service Buggy Deployment Release",
    description="New deployment v2.4.1 in Payment Service introduces unhandled runtime exceptions on UPI payments",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Payment processing endpoint error rate spiked to 100% with HTTP 500 responses",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0,
        parameters={"http_status": 500}
    ),
    deployment_event={
        "deployment_id": "dep_pay_bad_v241",
        "service": "payment-service",
        "version": "2.4.1",
        "previous_version": "2.4.0",
        "change_description": "Payment processor pipeline optimization v2.4.1"
    },
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Buggy deployment v2.4.1 in payment-service causing 100% failure rate",
        injected_fault_config={"version": "2.4.1", "error_rate": 1.0},
        expected_remediation="rollback_payment_service_v2.4.0",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_DEPENDENCY_LATENCY_BANK = ScenarioDefinition(
    scenario_id="scenario_dependency_latency_bank",
    name="Downstream Bank Gateway Latency Spikes",
    description="Third-party bank verification service experiences severe response latency",
    service="dependency-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Payment service downstream bank verification calls taking > 100ms",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=120.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Downstream partner bank gateway latency degradation",
        injected_fault_config={"latency_ms": 120.0},
        expected_remediation="enable_bank_gateway_circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

SCENARIO_RESOURCE_SATURATION_GATEWAY = ScenarioDefinition(
    scenario_id="scenario_resource_saturation_gateway",
    name="API Gateway CPU Saturation and Thread Burn",
    description="High CPU consumption in API Gateway middleware causes connection timeouts",
    service="api-gateway",
    severity=IncidentSeverity.HIGH,
    symptom_description="API Gateway response latency elevated due to CPU exhaustion",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=60.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="CPU burn spinlock in api-gateway",
        injected_fault_config={"cpu_burn_ms": 60.0},
        expected_remediation="restart_gateway_workers",
        verification_criteria={"max_p95_latency_ms": 25.0}
    )
)

SCENARIO_QUEUE_BACKLOG_WORKER = ScenarioDefinition(
    scenario_id="scenario_queue_backlog_worker",
    name="Async Worker Queue Consumer Backlog",
    description="Worker service background task queue accumulates unprocessed messages",
    service="worker-service",
    severity=IncidentSeverity.MEDIUM,
    symptom_description="Worker background queue depth increased significantly above baseline",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Asynchronous worker consumption backlog",
        injected_fault_config={},
        expected_remediation="scale_worker_replicas",
        verification_criteria={"max_queue_depth": 2}
    )
)

ALL_SCENARIOS = [
    SCENARIO_DB_REGRESSION_ORDER,
    SCENARIO_BAD_DEPLOY_PAYMENT,
    SCENARIO_DEPENDENCY_LATENCY_BANK,
    SCENARIO_RESOURCE_SATURATION_GATEWAY,
    SCENARIO_QUEUE_BACKLOG_WORKER,
]

SCENARIO_MAP: Dict[str, ScenarioDefinition] = {s.scenario_id: s for s in ALL_SCENARIOS}

def get_scenario(scenario_id: str) -> Optional[ScenarioDefinition]:
    return SCENARIO_MAP.get(scenario_id)
