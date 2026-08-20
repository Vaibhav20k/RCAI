# Benchmark Incident Scenario Registry - RCAI v2 Expanded Suite
from typing import Dict, List, Optional
from benchmark.scenarios.models import ScenarioDefinition
from simulator.faults.models import FaultConfig, FaultType
from backend.incidents.models import GroundTruth, IncidentSeverity

# --- Original Baseline Scenarios (1-5) ---
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
    name="Async Worker Queue Consumer Starvation",
    description="Worker process failure prevents order fulfillment background processing",
    service="worker-service",
    severity=IncidentSeverity.MEDIUM,
    symptom_description="Order fulfillment async queue depth growing monotonically",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        parameters={"queue_depth_increment": 50}
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Async worker task queue message accumulation",
        injected_fault_config={"queue_depth_increment": 50},
        expected_remediation="scale_worker_replicas",
        verification_criteria={"max_queue_depth": 5}
    )
)

# --- Expanded Scenarios (6-20) ---
# DATABASE VARIANTS
SCENARIO_DB_POOL_EXHAUSTION = ScenarioDefinition(
    scenario_id="scenario_db_pool_exhaustion",
    name="Order Service DB Connection Pool Starvation",
    description="Leaked database connections lead to pool exhaustion and connection timeouts",
    service="order-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Database connection checkout timeout exceeded in order-service",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        db_query_delay_ms=150.0,
        parameters={"pool_exhausted": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="database_regression",
        description="Database connection pool exhaustion on order-service",
        injected_fault_config={"pool_exhausted": True, "db_query_delay_ms": 150.0},
        expected_remediation="optimize_db_index",
        verification_criteria={"max_p95_latency_ms": 30.0}
    )
)

SCENARIO_DB_LOCK_CONTENTION = ScenarioDefinition(
    scenario_id="scenario_db_lock_contention",
    name="Payment Service Row-Level DB Lock Contention",
    description="Concurrent ledger update lock contention on account balances",
    service="payment-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Transaction commit lock wait timeouts on payment-service",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        db_query_delay_ms=110.0,
        parameters={"lock_contention": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="database_regression",
        description="Database row-level lock contention on payment-service",
        injected_fault_config={"lock_contention": True},
        expected_remediation="optimize_db_index",
        verification_criteria={"max_p95_latency_ms": 35.0}
    )
)

# DEPLOYMENT VARIANTS
SCENARIO_DEPLOY_PARTIAL_CANARY = ScenarioDefinition(
    scenario_id="scenario_deploy_partial_canary",
    name="Order Service Canary Release Error Regression",
    description="Canary deployment v1.8.0 throws intermittent deserialization exceptions",
    service="order-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Elevated error rate 40% on order placement following release",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.40,
        parameters={"http_status": 502}
    ),
    deployment_event={
        "deployment_id": "dep_order_v180",
        "service": "order-service",
        "version": "1.8.0",
        "previous_version": "1.7.9",
        "change_description": "Order payload schema update v1.8.0"
    },
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="bad_deployment",
        description="Buggy canary deployment v1.8.0 in order-service",
        injected_fault_config={"version": "1.8.0", "error_rate": 0.40},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_DEPLOY_CONFIG_DRIFT = ScenarioDefinition(
    scenario_id="scenario_deploy_config_drift",
    name="API Gateway Configuration Drift Deployment",
    description="Bad routing configuration deployment routes traffic to invalid upstream",
    service="api-gateway",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="API Gateway routing table config failure causing 503 Bad Gateway",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.80,
        parameters={"http_status": 503}
    ),
    deployment_event={
        "deployment_id": "dep_gw_cfg_v3",
        "service": "api-gateway",
        "version": "3.1.0",
        "previous_version": "3.0.9",
        "change_description": "Upstream routing rule modernization"
    },
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="bad_deployment",
        description="Configuration drift deployment in api-gateway",
        injected_fault_config={"version": "3.1.0", "error_rate": 0.80},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

# DEPENDENCY VARIANTS
SCENARIO_DEPENDENCY_TIMEOUT = ScenarioDefinition(
    scenario_id="scenario_dependency_timeout",
    name="Partner Bank Verification Total Timeout",
    description="Partner bank endpoint unreachable resulting in connection timeout cascade",
    service="dependency-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Downstream partner bank HTTP connection timeouts > 200ms",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=250.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Third-party bank API connection timeout",
        injected_fault_config={"latency_ms": 250.0},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 50.0}
    )
)

SCENARIO_DEPENDENCY_503_FLAP = ScenarioDefinition(
    scenario_id="scenario_dependency_503_flap",
    name="Partner Bank Intermittent Flapping Failures",
    description="Intermittent HTTP 503 upstream error responses from downstream partner bank",
    service="dependency-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Downstream partner bank 503 Service Unavailable flapping error rate 60%",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        error_rate=0.60,
        parameters={"http_status": 503}
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Downstream partner bank gateway flapping failures",
        injected_fault_config={"error_rate": 0.60},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_error_rate": 0.05}
    )
)

# RESOURCE VARIANTS
SCENARIO_RESOURCE_MEMORY_LEAK = ScenarioDefinition(
    scenario_id="scenario_resource_memory_leak",
    name="Payment Service Memory Pressure and GC Pauses",
    description="Unbounded object retention causes high memory pressure and severe GC pause latency",
    service="payment-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Stop-the-world garbage collection latency spikes on payment-service",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=80.0,
        parameters={"memory_pressure": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="resource_saturation",
        description="Memory pressure and garbage collection pause in payment-service",
        injected_fault_config={"cpu_burn_ms": 80.0},
        expected_remediation="restart_workers",
        verification_criteria={"max_p95_latency_ms": 30.0}
    )
)

SCENARIO_RESOURCE_THREAD_STARVATION = ScenarioDefinition(
    scenario_id="scenario_resource_thread_starvation",
    name="Order Service Worker Thread Starvation",
    description="Async event loop thread starvation blocks incoming order HTTP workers",
    service="order-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Async event loop thread starvation on order-service",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=95.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="resource_saturation",
        description="Worker thread starvation in order-service",
        injected_fault_config={"cpu_burn_ms": 95.0},
        expected_remediation="restart_workers",
        verification_criteria={"max_p95_latency_ms": 30.0}
    )
)

# QUEUE VARIANTS
SCENARIO_QUEUE_POISON_PILL = ScenarioDefinition(
    scenario_id="scenario_queue_poison_pill",
    name="Worker Service Poison Pill Message Blockage",
    description="Malformed queue message crashes worker thread and blocks consumer partition",
    service="worker-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Worker partition consumer stuck in restart crash loop with queue lag",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        parameters={"poison_pill": True, "queue_depth_increment": 80}
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Poison pill message consumer blockage on worker-service",
        injected_fault_config={"poison_pill": True},
        expected_remediation="scale_workers",
        verification_criteria={"max_queue_depth": 5}
    )
)

SCENARIO_QUEUE_BURST_BACKLOG = ScenarioDefinition(
    scenario_id="scenario_queue_burst_backlog",
    name="Worker Service Flash Sale Producer Burst",
    description="Sudden order volume surge overwhelms background fulfillment throughput",
    service="worker-service",
    severity=IncidentSeverity.MEDIUM,
    symptom_description="Flash sale volume surge creates 120+ unconsumed queue jobs",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        parameters={"burst_multiplier": 4.0, "queue_depth_increment": 120}
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Flash sale traffic burst async queue accumulation",
        injected_fault_config={"queue_depth_increment": 120},
        expected_remediation="scale_workers",
        verification_criteria={"max_queue_depth": 5}
    )
)

# Registry containing all 14 benchmark scenarios (expanded in Phase 2)
ALL_SCENARIOS: List[ScenarioDefinition] = [
    SCENARIO_DB_REGRESSION_ORDER,
    SCENARIO_BAD_DEPLOY_PAYMENT,
    SCENARIO_DEPENDENCY_LATENCY_BANK,
    SCENARIO_RESOURCE_SATURATION_GATEWAY,
    SCENARIO_QUEUE_BACKLOG_WORKER,
    SCENARIO_DB_POOL_EXHAUSTION,
    SCENARIO_DB_LOCK_CONTENTION,
    SCENARIO_DEPLOY_PARTIAL_CANARY,
    SCENARIO_DEPLOY_CONFIG_DRIFT,
    SCENARIO_DEPENDENCY_TIMEOUT,
    SCENARIO_DEPENDENCY_503_FLAP,
    SCENARIO_RESOURCE_MEMORY_LEAK,
    SCENARIO_RESOURCE_THREAD_STARVATION,
    SCENARIO_QUEUE_POISON_PILL,
    SCENARIO_QUEUE_BURST_BACKLOG
]

SCENARIO_MAP: Dict[str, ScenarioDefinition] = {
    sc.scenario_id: sc for sc in ALL_SCENARIOS
}

def get_scenario_by_id(scenario_id: str) -> Optional[ScenarioDefinition]:
    return SCENARIO_MAP.get(scenario_id)

get_scenario = get_scenario_by_id
