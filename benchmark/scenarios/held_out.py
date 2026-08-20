# Held-Out / Unseen Compositional Benchmark Scenarios for RCAI v2 Generalization (10 Scenarios)
from typing import List, Dict, Optional
from benchmark.scenarios.models import ScenarioDefinition
from benchmark.scenarios.taxonomy import (
    global_taxonomy,
    TaxonomyEntry,
    ScenarioFamily,
    ScenarioDifficulty,
    DatasetSplit
)
from simulator.faults.models import FaultConfig, FaultType
from backend.incidents.models import GroundTruth, IncidentSeverity

# 1. Compositional: Deployment Rollout + Concurrent DB Query Delay
SCENARIO_HELDOUT_DEPLOY_PLUS_DB = ScenarioDefinition(
    scenario_id="scenario_heldout_deploy_plus_db",
    name="Held-Out: Canary Release v3.0.0 Coupled with Table Lock Lag",
    description="Multi-factor incident: new deployment v3.0.0 exposes an unindexed foreign key query path under load",
    service="order-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Order Service latency spiked to 90ms following deployment v3.0.0 with DB query waits",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        db_query_delay_ms=85.0
    ),
    deployment_event={
        "deployment_id": "dep_order_300",
        "service": "order-service",
        "version": "3.0.0",
        "previous_version": "2.9.0",
        "change_description": "Release v3.0.0: new order checkout engine"
    },
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="database_regression",
        description="Unindexed database query path in order_service v3.0.0 release",
        injected_fault_config={"version": "3.0.0", "db_query_delay_ms": 85.0},
        expected_remediation="optimize_db_index",
        verification_criteria={"max_p95_latency_ms": 30.0}
    )
)

# 2. Compositional: Dependency Timeout + Worker Queue Backlog
SCENARIO_HELDOUT_DEP_TIMEOUT_PLUS_QUEUE = ScenarioDefinition(
    scenario_id="scenario_heldout_dep_timeout_plus_queue",
    name="Held-Out: Partner Bank Gateway Timeout Cascading to Async Worker Backlog",
    description="Downstream partner bank connection drop causes async payment worker queue to accumulate 5,000 retries",
    service="worker-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Worker Service queue depth spiked past 5,000 messages due to bank gateway timeout stalls",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.60
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Downstream partner bank latency cascading into worker_service queue backlog",
        injected_fault_config={"error_rate": 0.60},
        expected_remediation="restart_workers",
        verification_criteria={"max_queue_depth": 100}
    )
)

# 3. Compositional: Canary Release + Partial Route Degradation
SCENARIO_HELDOUT_CANARY_PLUS_ROUTE = ScenarioDefinition(
    scenario_id="scenario_heldout_canary_plus_route",
    name="Held-Out: Canary Release v3.1.0 with Degraded Bank Routing Config",
    description="Canary deployment routes UPI traffic to an uncertified bank route causing 40% transaction errors",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Payment Service 40% error rate on canary pod v3.1.0 with invalid routing headers",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.40
    ),
    deployment_event={
        "deployment_id": "dep_pay_310_canary",
        "service": "payment-service",
        "version": "3.1.0-canary",
        "previous_version": "3.0.5",
        "change_description": "Canary release v3.1.0: new bank router experiment"
    },
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Canary release v3.1.0 routing configuration regression on payment_service",
        injected_fault_config={"version": "3.1.0-canary", "error_rate": 0.40},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

# 4. Compositional: Webhook Retry Delay + Queue Consumer Backlog
SCENARIO_HELDOUT_WEBHOOK_DELAY_PLUS_QUEUE = ScenarioDefinition(
    scenario_id="scenario_heldout_webhook_delay_plus_queue",
    name="Held-Out: Webhook Network Latency Triggering Exponential Consumer Backlog",
    description="Merchant webhook endpoint latency causes worker timeout retries that saturate background threads",
    service="worker-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Worker Service consumer throughput dropped 80% due to merchant webhook retry backoff",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.55
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Merchant webhook retry backoff saturating worker_service consumers",
        injected_fault_config={"error_rate": 0.55},
        expected_remediation="scale_workers",
        verification_criteria={"max_queue_depth": 150}
    )
)

# 5. Compositional: Gateway CPU Saturation + Database Connection Pool Pressure
SCENARIO_HELDOUT_CPU_PLUS_DB_PRESSURE = ScenarioDefinition(
    scenario_id="scenario_heldout_cpu_plus_db_pressure",
    name="Held-Out: API Gateway CPU Throttling Inducing Request Queue Stalls",
    description="High CPU burn on API Gateway proxy layer creates downstream socket connection backpressure",
    service="api-gateway",
    severity=IncidentSeverity.HIGH,
    symptom_description="API Gateway proxy latency spiked to 110ms with 100% CPU core utilization",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=85.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="CPU saturation on api_gateway proxy layer causing downstream socket stalls",
        injected_fault_config={"cpu_burn_ms": 85.0},
        expected_remediation="scale_workers",
        verification_criteria={"max_cpu_burn_ms": 0.0}
    )
)

# 6. Compositional: Memory Leak + DB Row Lock Wait
SCENARIO_HELDOUT_MEMORY_PLUS_LOCK = ScenarioDefinition(
    scenario_id="scenario_heldout_memory_plus_lock",
    name="Held-Out: Heap Memory Pressure with Concurrent Order Row Locks",
    description="Order Service memory consumption slows query execution, compounding table lock wait durations",
    service="order-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Order Service latency elevated to 75ms with memory growth and query lock waits",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        db_query_delay_ms=75.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="database_regression",
        description="Database query lock delays on order-service under memory pressure",
        injected_fault_config={"db_query_delay_ms": 75.0},
        expected_remediation="optimize_db_index",
        verification_criteria={"max_p95_latency_ms": 30.0}
    )
)

# 7. Compositional: Schema Migration Drop + Worker Crash Loop
SCENARIO_HELDOUT_SCHEMA_PLUS_WORKER = ScenarioDefinition(
    scenario_id="scenario_heldout_schema_plus_worker",
    name="Held-Out: Schema Migration Column Drop Causing Worker Crash Loop",
    description="Payment release v3.2.0 dropped column causing async worker consumers to crash repeatedly",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Payment Service 500 errors: missing column merchant_payout_id in release v3.2.0",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.85
    ),
    deployment_event={
        "deployment_id": "dep_pay_320",
        "service": "payment-service",
        "version": "3.2.0",
        "previous_version": "3.1.0",
        "change_description": "Release v3.2.0: schema refactoring"
    },
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Buggy deployment v3.2.0 schema drop on payment-service",
        injected_fault_config={"version": "3.2.0", "error_rate": 0.85},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

# 8. Compositional: Flapping 503 Route + Client Retry Storm
SCENARIO_HELDOUT_FLAP_PLUS_RETRY = ScenarioDefinition(
    scenario_id="scenario_heldout_flap_plus_retry",
    name="Held-Out: Intermittent 503 Flapping Driving Downstream Retry Overload",
    description="Flapping 503 bank gateway triggers uncoordinated client retries, saturating dependency connection pool",
    service="dependency-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Bank dependency latency 190ms with 50% intermittent HTTP 503 failures",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=190.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Intermittent 503 dependency degradation on dependency-service",
        injected_fault_config={"latency_ms": 190.0},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

# 9. Compositional: File Descriptor Leak + Slow DB Queries
SCENARIO_HELDOUT_FD_PLUS_DB = ScenarioDefinition(
    scenario_id="scenario_heldout_fd_plus_db",
    name="Held-Out: Gateway Socket FD Leak Compounded by DB Latency",
    description="Socket file descriptor leakage on API Gateway throttles incoming connections",
    service="api-gateway",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="API Gateway rejecting connections with EMFILE socket exhaustion",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=80.0
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="Socket file descriptor exhaustion on api_gateway",
        injected_fault_config={"cpu_burn_ms": 80.0},
        expected_remediation="scale_workers",
        verification_criteria={"max_cpu_burn_ms": 0.0}
    )
)

# 10. Compositional: Poison Pill Payload + 10x Webhook Surge
SCENARIO_HELDOUT_POISON_PLUS_BURST = ScenarioDefinition(
    scenario_id="scenario_heldout_poison_plus_burst",
    name="Held-Out: Poison-Pill Payload During 10x Webhook Producer Burst",
    description="Malformed event payload stalls partition consumer right as producer traffic surges 10x",
    service="worker-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Worker Service queue backlog surging with repeated dead-letter partition stalls",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.75
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Poison pill payload during producer surge on worker_service",
        injected_fault_config={"error_rate": 0.75},
        expected_remediation="restart_workers",
        verification_criteria={"max_error_rate": 0.05}
    )
)

HELDOUT_SCENARIOS: List[ScenarioDefinition] = [
    SCENARIO_HELDOUT_DEPLOY_PLUS_DB,
    SCENARIO_HELDOUT_DEP_TIMEOUT_PLUS_QUEUE,
    SCENARIO_HELDOUT_CANARY_PLUS_ROUTE,
    SCENARIO_HELDOUT_WEBHOOK_DELAY_PLUS_QUEUE,
    SCENARIO_HELDOUT_CPU_PLUS_DB_PRESSURE,
    SCENARIO_HELDOUT_MEMORY_PLUS_LOCK,
    SCENARIO_HELDOUT_SCHEMA_PLUS_WORKER,
    SCENARIO_HELDOUT_FLAP_PLUS_RETRY,
    SCENARIO_HELDOUT_FD_PLUS_DB,
    SCENARIO_HELDOUT_POISON_PLUS_BURST
]

# Register all 10 Held-Out Scenarios into Global Taxonomy with HELD_OUT_TEST split
for sc in HELDOUT_SCENARIOS:
    fam = ScenarioFamily.DATABASE
    if "deploy" in sc.ground_truth.root_cause_type:
        fam = ScenarioFamily.DEPLOYMENT
    elif "dependency" in sc.ground_truth.root_cause_type:
        fam = ScenarioFamily.DEPENDENCY
    elif "resource" in sc.ground_truth.root_cause_type:
        fam = ScenarioFamily.RESOURCE
    elif "queue" in sc.ground_truth.root_cause_type:
        fam = ScenarioFamily.QUEUE

    global_taxonomy.register(TaxonomyEntry(
        scenario_id=sc.scenario_id,
        family=fam,
        variant=sc.ground_truth.root_cause_type,
        difficulty=ScenarioDifficulty.HARD,
        split=DatasetSplit.HELD_OUT_TEST,
        ground_truth_root_cause=sc.ground_truth.description,
        root_cause_service=sc.ground_truth.root_cause_service,
        root_cause_category=fam.value,
        required_evidence=[],
        allowed_actions=[sc.ground_truth.expected_remediation],
        expected_outcome="RESOLVED",
        payment_domain=("payment" in sc.service),
        adversarial=False
    ))
