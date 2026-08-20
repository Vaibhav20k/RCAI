# Held-Out Unseen & Compositional Benchmark Scenarios for RCAI v2 Generalization Testing
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

# 1. Compositional: Deploy + DB Query Plan Regression
SCENARIO_HELDOUT_DEPLOY_PLUS_DB = ScenarioDefinition(
    scenario_id="scenario_heldout_deploy_plus_db",
    name="Held-Out: Version 2.5.0 Deployment Introducing Unindexed DB Full-Table Scan",
    description="Canary release v2.5.0 introduces an unindexed table scan query regression in order-service",
    service="order-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Order placement endpoint p95 latency spiked to 140ms following release v2.5.0",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        db_query_delay_ms=130.0,
        error_rate=0.20,
        parameters={"version": "2.5.0", "unindexed_scan": True}
    ),
    deployment_event={
        "deployment_id": "dep_order_v250",
        "service": "order-service",
        "version": "2.5.0",
        "previous_version": "2.4.9",
        "change_description": "Order querying pipeline refactor v2.5.0"
    },
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="bad_deployment",
        description="Version 2.5.0 deployment regression with unindexed database query scan",
        injected_fault_config={"version": "2.5.0", "db_query_delay_ms": 130.0},
        expected_remediation="rollback_version",
        verification_criteria={"max_p95_latency_ms": 30.0}
    )
)

# 2. Compositional: Downstream Timeout + Worker Queue Cascading Backlog
SCENARIO_HELDOUT_DEP_TIMEOUT_QUEUE_BURST = ScenarioDefinition(
    scenario_id="scenario_heldout_dep_timeout_queue_burst",
    name="Held-Out: Partner Bank Gateway Outage Triggering Worker Queue Accumulation",
    description="Downstream partner bank outage stalls worker tasks and creates cascading queue backlog",
    service="dependency-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Downstream partner bank connection timeout with 85+ async task backlog",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=280.0,
        error_rate=0.70,
        parameters={"queue_cascade": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Downstream partner bank gateway timeout causing queue backlog cascade",
        injected_fault_config={"latency_ms": 280.0, "error_rate": 0.70},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

# 3. Compositional: CPU Contention + DB Row Lock Wait
SCENARIO_HELDOUT_CPU_LOCK_CONTENTION = ScenarioDefinition(
    scenario_id="scenario_heldout_cpu_lock_contention",
    name="Held-Out: CPU Saturation Inducing DB Row Lock Timeout Cascade",
    description="API Gateway CPU exhaustion causes slow socket handling and prolonged DB lock acquisition",
    service="api-gateway",
    severity=IncidentSeverity.HIGH,
    symptom_description="API Gateway 100% CPU thread burn with cascading transaction lock contention",
    fault_config=FaultConfig(
        service_name="api-gateway",
        fault_type=FaultType.RESOURCE_SATURATION,
        cpu_burn_ms=110.0,
        parameters={"lock_cascade": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="api-gateway",
        root_cause_type="resource_saturation",
        description="API Gateway CPU thread burn spinlock",
        injected_fault_config={"cpu_burn_ms": 110.0},
        expected_remediation="restart_workers",
        verification_criteria={"max_p95_latency_ms": 25.0}
    )
)

# 4. Compositional: Microservice Rolling Upgrade Protocol Incompatibility
SCENARIO_HELDOUT_ROLLING_UPGRADE_MISMATCH = ScenarioDefinition(
    scenario_id="scenario_heldout_rolling_upgrade_mismatch",
    name="Held-Out: Payment Service Protocol Mismatch on Rolling Update v3.0.0",
    description="Payment service rolling upgrade to v3.0.0 uses deprecated serialization headers",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Payment processing 502 Bad Gateway due to serialization protocol mismatch",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.90,
        parameters={"http_status": 502, "protocol_version": "v3.0.0"}
    ),
    deployment_event={
        "deployment_id": "dep_pay_v300_mismatch",
        "service": "payment-service",
        "version": "3.0.0",
        "previous_version": "2.4.0",
        "change_description": "Protobuf transport layer upgrade v3.0.0"
    },
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Protocol serialization mismatch on payment-service v3.0.0",
        injected_fault_config={"version": "3.0.0", "error_rate": 0.90},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

# 5. Compositional: Slow Consumer Thread Starvation with Intermittent Flapping
SCENARIO_HELDOUT_SLOW_DRAIN_THREAD_STARVATION = ScenarioDefinition(
    scenario_id="scenario_heldout_slow_drain_thread_starvation",
    name="Held-Out: Worker Consumer Starvation with Upstream Flapping Latency",
    description="Worker service background thread exhaustion under intermittent latency",
    service="worker-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Worker execution threads stalled with async queue lag above 100",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        parameters={"thread_starvation": True, "queue_depth_increment": 110}
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="queue_backlog",
        description="Worker thread pool exhaustion causing queue drain stalls",
        injected_fault_config={"queue_depth_increment": 110},
        expected_remediation="scale_workers",
        verification_criteria={"max_queue_depth": 5}
    )
)

HELDOUT_SCENARIOS: List[ScenarioDefinition] = [
    SCENARIO_HELDOUT_DEPLOY_PLUS_DB,
    SCENARIO_HELDOUT_DEP_TIMEOUT_QUEUE_BURST,
    SCENARIO_HELDOUT_CPU_LOCK_CONTENTION,
    SCENARIO_HELDOUT_ROLLING_UPGRADE_MISMATCH,
    SCENARIO_HELDOUT_SLOW_DRAIN_THREAD_STARVATION
]

# Register Held-Out Scenarios into Global Taxonomy
for sc in HELDOUT_SCENARIOS:
    fam = ScenarioFamily.DEPLOYMENT
    if sc.fault_config.fault_type == FaultType.DATABASE_REGRESSION:
        fam = ScenarioFamily.DATABASE
    elif sc.fault_config.fault_type == FaultType.DEPENDENCY_LATENCY:
        fam = ScenarioFamily.DEPENDENCY
    elif sc.fault_config.fault_type == FaultType.RESOURCE_SATURATION:
        fam = ScenarioFamily.RESOURCE
    elif sc.fault_config.fault_type == FaultType.QUEUE_BACKLOG:
        fam = ScenarioFamily.QUEUE

    global_taxonomy.register(TaxonomyEntry(
        scenario_id=sc.scenario_id,
        family=fam,
        variant=sc.ground_truth.root_cause_type,
        difficulty=ScenarioDifficulty.COMPOSITIONAL,
        split=DatasetSplit.HELD_OUT_TEST,
        ground_truth_root_cause=sc.ground_truth.description,
        root_cause_service=sc.ground_truth.root_cause_service,
        root_cause_category=fam.value.lower(),
        required_evidence=[],
        allowed_actions=[sc.ground_truth.expected_remediation],
        expected_outcome="RESOLVED",
        payment_domain=("payment" in sc.service or "bank" in sc.service),
        adversarial=False
    ))
