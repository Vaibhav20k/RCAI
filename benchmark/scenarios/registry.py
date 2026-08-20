# Benchmark Incident Scenario Registry - RCAI v2 Expanded Suite (25 Scenarios)
from typing import Dict, List, Optional
from benchmark.scenarios.models import ScenarioDefinition
from simulator.faults.models import FaultConfig, FaultType
from backend.incidents.models import GroundTruth, IncidentSeverity

# ==============================================================================
# 1. DATABASE FAMILY (5 Scenarios)
# ==============================================================================

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

SCENARIO_DB_POOL_EXHAUSTION = ScenarioDefinition(
    scenario_id="scenario_db_pool_exhaustion",
    name="Payment Service DB Connection Pool Exhaustion",
    description="Leaked connection handles exhaust the PostgreSQL connection pool",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Payment Service HTTP 500 error rate spiked to 80% with DB connection timeout",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        error_rate=0.80,
        parameters={"pool_exhausted": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="database_regression",
        description="Database connection pool exhaustion on payment_service",
        injected_fault_config={"pool_exhausted": True},
        expected_remediation="restart_workers",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_DB_LOCK_CONTENTION = ScenarioDefinition(
    scenario_id="scenario_db_lock_contention",
    name="Order Service Row-Level Lock Contention",
    description="Concurrent conflicting write transactions create exclusive lock queues on order records",
    service="order-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Order creation requests experiencing 90ms transaction commit latency lock waits",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        db_query_delay_ms=75.0,
        parameters={"lock_contention": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="database_regression",
        description="Row-level lock contention in order database",
        injected_fault_config={"lock_contention": True},
        expected_remediation="optimize_db_index",
        verification_criteria={"max_p95_latency_ms": 25.0}
    )
)

SCENARIO_DB_CONNECTION_TIMEOUT = ScenarioDefinition(
    scenario_id="scenario_db_connection_timeout",
    name="Payment DB Socket Connection Timeout",
    description="TCP socket connection handshake timeout to payment database primary",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Payment DB socket handshake timeout: 65% transactions failing with ECONNREFUSED",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        error_rate=0.65,
        parameters={"connection_timeout": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="database_regression",
        description="Database TCP socket connection timeout on payment-service",
        injected_fault_config={"connection_timeout": True},
        expected_remediation="restart_workers",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_DB_PARTIAL_DEGRADATION = ScenarioDefinition(
    scenario_id="scenario_db_partial_degradation",
    name="Order Read-Replica Partial Replication Lag",
    description="Asynchronous replication lag causes read-replica queries to stall and timeout",
    service="order-service",
    severity=IncidentSeverity.MEDIUM,
    symptom_description="Order query read-replica latency spiked to 60ms with stale read warnings",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        db_query_delay_ms=60.0,
        parameters={"replica_lag": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="database_regression",
        description="Database read-replica degradation in order_service",
        injected_fault_config={"replica_lag": True},
        expected_remediation="optimize_db_index",
        verification_criteria={"max_p95_latency_ms": 25.0}
    )
)

# ==============================================================================
# 2. DEPLOYMENT FAMILY (5 Scenarios)
# ==============================================================================

SCENARIO_BAD_DEPLOY_PAYMENT = ScenarioDefinition(
    scenario_id="scenario_bad_deploy_payment",
    name="Payment Service Buggy Release Deployment",
    description="Release v2.4.1 introduced a runtime exception causing complete failure of payment authorizations",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Payment Service HTTP 500 error rate spiked to 100% after release v2.4.1",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0
    ),
    deployment_event={
        "deployment_id": "dep_pay_241",
        "service": "payment-service",
        "version": "2.4.1",
        "previous_version": "2.4.0",
        "change_description": "Release v2.4.1: authorization pipeline rewrite"
    },
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Buggy deployment v2.4.1 in payment_service causing 100% failure rate",
        injected_fault_config={"version": "2.4.1", "error_rate": 1.0},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_DEPLOY_PARTIAL_CANARY = ScenarioDefinition(
    scenario_id="scenario_deploy_partial_canary",
    name="Payment Service Canary Release Partial Failure",
    description="Canary deployment v2.5.0-canary routed to 20% of traffic produces persistent 500 errors",
    service="payment-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Payment Service HTTP 500 error rate spiked to 20% following canary release",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.20
    ),
    deployment_event={
        "deployment_id": "dep_pay_canary",
        "service": "payment-service",
        "version": "2.5.0-canary",
        "previous_version": "2.4.0",
        "change_description": "Canary v2.5.0: partial traffic rollout"
    },
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Canary release v2.5.0 failure on payment_service",
        injected_fault_config={"version": "2.5.0-canary", "error_rate": 0.20},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_DEPLOY_CONFIG_DRIFT = ScenarioDefinition(
    scenario_id="scenario_deploy_config_drift",
    name="Order Service Config Drift & Bad Environment Variable",
    description="Configuration deployment injected missing database credentials causing auth failure",
    service="order-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Order Service 500 errors after config release: DB authentication rejected",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.75
    ),
    deployment_event={
        "deployment_id": "dep_order_cfg_drift",
        "service": "order-service",
        "version": "1.8.0",
        "previous_version": "1.7.9",
        "change_description": "Config release: rotated database connection strings"
    },
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="bad_deployment",
        description="Configuration drift deployment in order_service",
        injected_fault_config={"version": "1.8.0", "error_rate": 0.75},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_DEPLOY_FEATURE_FLAG = ScenarioDefinition(
    scenario_id="scenario_deploy_feature_flag_regression",
    name="Order Dynamic Feature Flag Regression",
    description="Enabling dynamic feature flag flag_instant_discount triggers unhandled exception",
    service="order-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Order creation error rate jumped to 50% following feature flag activation",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.50
    ),
    deployment_event={
        "deployment_id": "dep_order_ff_enable",
        "service": "order-service",
        "version": "1.8.1",
        "previous_version": "1.8.0",
        "change_description": "Feature flag enablement: flag_instant_discount=true"
    },
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="bad_deployment",
        description="Feature flag deployment regression in order-service",
        injected_fault_config={"version": "1.8.1", "error_rate": 0.50},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_DEPLOY_SCHEMA_MIGRATION = ScenarioDefinition(
    scenario_id="scenario_deploy_schema_migration_mismatch",
    name="Payment ORM Schema Migration Mismatch",
    description="Database migration dropped column expected by active payment worker model",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Payment Service 500 error spike: Unknown column merchant_tax_id in field list",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.90
    ),
    deployment_event={
        "deployment_id": "dep_pay_schema_mig",
        "service": "payment-service",
        "version": "2.4.2",
        "previous_version": "2.4.0",
        "change_description": "Migration rollout: altered payment_methods table"
    },
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Schema migration deployment mismatch on payment-service",
        injected_fault_config={"version": "2.4.2", "error_rate": 0.90},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

# ==============================================================================
# 3. DEPENDENCY FAMILY (5 Scenarios)
# ==============================================================================

SCENARIO_DEPENDENCY_LATENCY_BANK = ScenarioDefinition(
    scenario_id="scenario_dependency_latency_bank",
    name="Third-Party Bank Partner Network Latency Degradation",
    description="External banking partner API experiences severe network degradation, causing payment timeouts",
    service="dependency-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Payment API p95 latency spiked to 250ms due to upstream bank dependency delays",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=200.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Downstream partner bank network latency injected into dependency_service",
        injected_fault_config={"latency_ms": 200.0},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

SCENARIO_DEPENDENCY_TIMEOUT = ScenarioDefinition(
    scenario_id="scenario_dependency_timeout",
    name="External SMS / Notification Partner Gateway Timeout",
    description="External SMS verification gateway completely unresponsive leading to timeout cascades",
    service="dependency-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Dependency health check UNHEALTHY with 100% gateway timeout on dependency-service",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=300.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Hard timeout on external dependency_service partner",
        injected_fault_config={"latency_ms": 300.0},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

SCENARIO_DEPENDENCY_503_FLAP = ScenarioDefinition(
    scenario_id="scenario_dependency_503_flap",
    name="Intermittent 503 Flapping from Upstream Partner Bank",
    description="Upstream partner returns 503 Service Unavailable intermittently on 50% requests",
    service="dependency-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Downstream bank partner API flapping with 50% HTTP 503 error rate",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=150.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Flapping 503 errors from upstream dependency_service",
        injected_fault_config={"latency_ms": 150.0},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

SCENARIO_DEPENDENCY_RETRY_STORM = ScenarioDefinition(
    scenario_id="scenario_dependency_retry_storm",
    name="Partner API Degradation Triggering Client Retry Storm",
    description="Transient latency causes unjittered aggressive client retries, amplifying dependency overload",
    service="dependency-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Partner bank latency + 300% surge in retry request volume on dependency-service",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=220.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Downstream partner retry storm on dependency-service",
        injected_fault_config={"latency_ms": 220.0},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

SCENARIO_DEPENDENCY_CIRCUIT_BREAKER = ScenarioDefinition(
    scenario_id="scenario_dependency_circuit_breaker_open",
    name="Bank Route Outage Tripping Fast-Fail Circuit Breakers",
    description="Partner outage causes circuit breaker open state, failing fast on dependency-service",
    service="dependency-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Bank route dependency reports fast-fail circuit breaker open with high latency",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=180.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Dependency circuit breaker degradation on dependency-service",
        injected_fault_config={"latency_ms": 180.0},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

# ==============================================================================
# 4. RESOURCE FAMILY (5 Scenarios)
# ==============================================================================

SCENARIO_RESOURCE_SATURATION_GATEWAY = ScenarioDefinition(
    scenario_id="scenario_resource_saturation_gateway",
    name="API Gateway CPU Core Saturation & Throttling",
    description="High CPU burn in API Gateway proxy middleware induces latency and dropped connections",
    service="api-gateway",
    severity=IncidentSeverity.HIGH,
    symptom_description="API Gateway CPU utilization sustained at 100%, causing request queueing",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=80.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="CPU saturation on api_gateway proxy layer",
        injected_fault_config={"cpu_burn_ms": 80.0},
        expected_remediation="scale_workers",
        verification_criteria={"max_cpu_burn_ms": 0.0}
    )
)

SCENARIO_RESOURCE_MEMORY_LEAK = ScenarioDefinition(
    scenario_id="scenario_resource_memory_leak",
    name="API Gateway Heap Memory Leak & GC Thrashing",
    description="Unbounded request context buffer cache causes JVM/runtime GC pause times of 120ms",
    service="api-gateway",
    severity=IncidentSeverity.HIGH,
    symptom_description="API Gateway request latency elevated with 90MB/min memory growth rate",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=65.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="Memory pressure and GC pauses on api_gateway",
        injected_fault_config={"cpu_burn_ms": 65.0},
        expected_remediation="restart_workers",
        verification_criteria={"max_cpu_burn_ms": 0.0}
    )
)

SCENARIO_RESOURCE_THREAD_STARVATION = ScenarioDefinition(
    scenario_id="scenario_resource_thread_starvation",
    name="API Gateway Worker Thread Pool Starvation",
    description="Synchronous blocking operations exhaust the worker thread pool on API Gateway",
    service="api-gateway",
    severity=IncidentSeverity.HIGH,
    symptom_description="API Gateway thread pool active count 100/100, requests queuing on edge socket",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=70.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="Thread pool starvation in api_gateway",
        injected_fault_config={"cpu_burn_ms": 70.0},
        expected_remediation="scale_workers",
        verification_criteria={"max_cpu_burn_ms": 0.0}
    )
)

SCENARIO_RESOURCE_IO_THROTTLING = ScenarioDefinition(
    scenario_id="scenario_resource_io_throttling",
    name="API Gateway Storage / Access Log IOPS Throttling",
    description="Excessive synchronous logging throttles disk IOPS, inducing request processing stalls",
    service="api-gateway",
    severity=IncidentSeverity.MEDIUM,
    symptom_description="API Gateway access log write queue latency spiked to 55ms",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=50.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="Disk IOPS logging throttling on api_gateway",
        injected_fault_config={"cpu_burn_ms": 50.0},
        expected_remediation="scale_workers",
        verification_criteria={"max_cpu_burn_ms": 0.0}
    )
)

SCENARIO_RESOURCE_FD_EXHAUSTION = ScenarioDefinition(
    scenario_id="scenario_resource_fd_exhaustion",
    name="API Gateway Socket File Descriptor Leak",
    description="Unclosed upstream HTTP keep-alive connections leak file descriptors on API gateway",
    service="api-gateway",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="API Gateway rejecting connections with socket errno EMFILE: Too many open files",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=75.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="Socket file descriptor exhaustion on api_gateway",
        injected_fault_config={"cpu_burn_ms": 75.0},
        expected_remediation="restart_workers",
        verification_criteria={"max_cpu_burn_ms": 0.0}
    )
)

# ==============================================================================
# 5. QUEUE FAMILY (5 Scenarios)
# ==============================================================================

SCENARIO_QUEUE_BACKLOG_WORKER = ScenarioDefinition(
    scenario_id="scenario_queue_backlog_worker",
    name="Worker Service Background Job Processing Queue Backlog",
    description="Deadlock in background event processor causes unbounded queue backlog growth",
    service="worker-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Async payment notification queue depth exceeded 10,000 messages (normal < 100)",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.50
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Async worker processing queue backlog in worker_service",
        injected_fault_config={"error_rate": 0.50},
        expected_remediation="restart_workers",
        verification_criteria={"max_queue_depth": 100}
    )
)

SCENARIO_QUEUE_POISON_PILL = ScenarioDefinition(
    scenario_id="scenario_queue_poison_pill",
    name="Worker Service Poison-Pill Dead-Letter Loop",
    description="Malformed payload causes worker crash loop on dequeue, stalling the entire partition",
    service="worker-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Worker service crash-looping on unparseable JSON payload in webhook_events queue",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.85
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Poison pill payload crashing consumer in worker_service",
        injected_fault_config={"error_rate": 0.85},
        expected_remediation="restart_workers",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_QUEUE_BURST_BACKLOG = ScenarioDefinition(
    scenario_id="scenario_queue_burst_backlog",
    name="Webhook Event Producer 10x Burst Ingestion Spike",
    description="Sudden marketing campaign 10x traffic spike overwhelms standard worker concurrency",
    service="worker-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Worker queue backlog growing at 2,000 msg/sec with consumer lag exceeding 15s",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.40
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Sudden webhook producer burst causing worker queue lag",
        injected_fault_config={"error_rate": 0.40},
        expected_remediation="scale_workers",
        verification_criteria={"max_queue_depth": 200}
    )
)

SCENARIO_QUEUE_STUCK_CONSUMER = ScenarioDefinition(
    scenario_id="scenario_queue_stuck_consumer",
    name="Worker Consumer Thread Deadlock on Sync RPC",
    description="Worker consumer thread hangs indefinitely waiting on un-timed RPC, stalling message ack",
    service="worker-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Worker consumer throughput dropped to 0 msg/s; active messages stuck unacknowledged",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.70
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Consumer thread deadlock in worker_service",
        injected_fault_config={"error_rate": 0.70},
        expected_remediation="restart_workers",
        verification_criteria={"max_error_rate": 0.05}
    )
)

SCENARIO_QUEUE_PARTITION_LAG = ScenarioDefinition(
    scenario_id="scenario_queue_partition_lag",
    name="Asymmetric Kafka/Queue Partition Consumer Rebalance Lag",
    description="Consumer group rebalancing storm leaves partitions 2 and 4 unassigned and lagging",
    service="worker-service",
    severity=IncidentSeverity.MEDIUM,
    symptom_description="Asymmetric partition lag on worker consumer group with frequent rebalance alerts",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.35
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Consumer partition rebalance lag in worker_service",
        injected_fault_config={"error_rate": 0.35},
        expected_remediation="scale_workers",
        verification_criteria={"max_queue_depth": 150}
    )
)

# Registry containing all 25 benchmark scenarios (expanded in Gap A)
ALL_SCENARIOS: List[ScenarioDefinition] = [
    # Database
    SCENARIO_DB_REGRESSION_ORDER,
    SCENARIO_DB_POOL_EXHAUSTION,
    SCENARIO_DB_LOCK_CONTENTION,
    SCENARIO_DB_CONNECTION_TIMEOUT,
    SCENARIO_DB_PARTIAL_DEGRADATION,
    # Deployment
    SCENARIO_BAD_DEPLOY_PAYMENT,
    SCENARIO_DEPLOY_PARTIAL_CANARY,
    SCENARIO_DEPLOY_CONFIG_DRIFT,
    SCENARIO_DEPLOY_FEATURE_FLAG,
    SCENARIO_DEPLOY_SCHEMA_MIGRATION,
    # Dependency
    SCENARIO_DEPENDENCY_LATENCY_BANK,
    SCENARIO_DEPENDENCY_TIMEOUT,
    SCENARIO_DEPENDENCY_503_FLAP,
    SCENARIO_DEPENDENCY_RETRY_STORM,
    SCENARIO_DEPENDENCY_CIRCUIT_BREAKER,
    # Resource
    SCENARIO_RESOURCE_SATURATION_GATEWAY,
    SCENARIO_RESOURCE_MEMORY_LEAK,
    SCENARIO_RESOURCE_THREAD_STARVATION,
    SCENARIO_RESOURCE_IO_THROTTLING,
    SCENARIO_RESOURCE_FD_EXHAUSTION,
    # Queue
    SCENARIO_QUEUE_BACKLOG_WORKER,
    SCENARIO_QUEUE_POISON_PILL,
    SCENARIO_QUEUE_BURST_BACKLOG,
    SCENARIO_QUEUE_STUCK_CONSUMER,
    SCENARIO_QUEUE_PARTITION_LAG
]

SCENARIO_MAP: Dict[str, ScenarioDefinition] = {
    sc.scenario_id: sc for sc in ALL_SCENARIOS
}

def get_scenario_by_id(scenario_id: str) -> Optional[ScenarioDefinition]:
    return SCENARIO_MAP.get(scenario_id)

get_scenario = get_scenario_by_id
