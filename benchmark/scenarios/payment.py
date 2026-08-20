# Dedicated Payment-Domain Benchmark Scenarios for RCAI v2
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

# 1. Payment State Inconsistency
SCENARIO_PAYMENT_STATE_INCONSISTENCY = ScenarioDefinition(
    scenario_id="scenario_payment_state_inconsistency",
    name="Payment Gateway State Inconsistency on Authorization Capture",
    description="Asynchronous authorization capture failure leads to state mismatch between gateway and database",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="State inconsistency: Gateway reports CAPTURED while internal record is stuck in AUTHORIZED",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        error_rate=0.40,
        parameters={"state_inconsistency": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="payment_state_inconsistency",
        description="Async capture state synchronization failure on payment-service",
        injected_fault_config={"state_inconsistency": True},
        expected_remediation="reconcile_payment_state",
        verification_criteria={"state_drift_count": 0}
    )
)

# 2. Webhook Delivery Degradation
SCENARIO_PAYMENT_WEBHOOK_DEGRADATION = ScenarioDefinition(
    scenario_id="scenario_payment_webhook_degradation",
    name="Merchant Webhook Dispatch Pipeline Degradation",
    description="Webhook dispatcher queue blockage prevents merchant notification delivery",
    service="worker-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Merchant webhook delivery latency exceeding 5000ms with 45% retry exhaustion",
    fault_config=FaultConfig(
        service_name="worker-service",
        fault_type=FaultType.QUEUE_BACKLOG,
        error_rate=0.45,
        parameters={"webhook_dispatch_drop": True, "queue_depth_increment": 75}
    ),
    ground_truth=GroundTruth(
        root_cause_service="worker-service",
        root_cause_type="webhook_degradation",
        description="Merchant webhook dispatcher queue blockage on worker-service",
        injected_fault_config={"webhook_dispatch_drop": True},
        expected_remediation="scale_workers",
        verification_criteria={"webhook_failure_rate": 0.02}
    )
)

# 3. Gateway / Bank Partner Latency
SCENARIO_PAYMENT_GATEWAY_LATENCY = ScenarioDefinition(
    scenario_id="scenario_payment_gateway_latency",
    name="Payment Gateway Partner PSP Route Latency Spike",
    description="Upstream partner PSP bank route experiences severe network socket delays",
    service="dependency-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="UPI payment authorization p95 latency spiked to 220ms on partner route",
    fault_config=FaultConfig(
        service_name="dependency-service",
        fault_type=FaultType.DEPENDENCY_LATENCY,
        latency_ms=200.0,
        parameters={"route": "hdfc_upi_primary"}
    ),
    ground_truth=GroundTruth(
        root_cause_service="dependency-service",
        root_cause_type="dependency_latency",
        description="Partner PSP bank route latency degradation",
        injected_fault_config={"latency_ms": 200.0},
        expected_remediation="circuit_breaker",
        verification_criteria={"max_dependency_latency_ms": 40.0}
    )
)

# 4. Duplicate Event Processing
SCENARIO_PAYMENT_DUPLICATE_EVENT = ScenarioDefinition(
    scenario_id="scenario_payment_duplicate_event",
    name="Payment Webhook Duplicate Event Ingestion Race Condition",
    description="Idempotency lock release race condition causes double capture processing",
    service="payment-service",
    severity=IncidentSeverity.CRITICAL,
    symptom_description="Duplicate payment capture event logged for transaction idemp_race_90",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        parameters={"idempotency_race": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="duplicate_event_processing",
        description="Idempotency key lock race condition on payment capture",
        injected_fault_config={"idempotency_race": True},
        expected_remediation="optimize_db_index",
        verification_criteria={"duplicate_count": 0}
    )
)

# 5. Settlement / Ledger Mismatch
SCENARIO_PAYMENT_SETTLEMENT_MISMATCH = ScenarioDefinition(
    scenario_id="scenario_payment_settlement_mismatch",
    name="Settlement Ledger Net Payout Reconciliation Mismatch",
    description="Rounding error in merchant fee deduction creates ledger payout mismatch",
    service="order-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Daily settlement batch reconciliation balance discrepancy detected",
    fault_config=FaultConfig(
        service_name="order-service",
        fault_type=FaultType.DATABASE_REGRESSION,
        parameters={"fee_rounding_drift": True}
    ),
    ground_truth=GroundTruth(
        root_cause_service="order-service",
        root_cause_type="settlement_mismatch",
        description="Settlement batch fee deduction ledger mismatch",
        injected_fault_config={"fee_rounding_drift": True},
        expected_remediation="optimize_db_index",
        verification_criteria={"discrepancy_amount": 0.0}
    )
)

# 6. Payment-Route Partial Degradation
SCENARIO_PAYMENT_ROUTE_DEGRADATION = ScenarioDefinition(
    scenario_id="scenario_payment_route_degradation",
    name="Partial Route Degradation on Axis Bank UPI Channel",
    description="Specific bank route fails while other payment methods remain healthy",
    service="payment-service",
    severity=IncidentSeverity.HIGH,
    symptom_description="Targeted 80% error rate on axis_upi_route while card routes healthy",
    fault_config=FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=0.80,
        parameters={"route": "axis_upi_route", "http_status": 502}
    ),
    ground_truth=GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Bank channel routing configuration regression on payment-service",
        injected_fault_config={"route": "axis_upi_route", "error_rate": 0.80},
        expected_remediation="rollback_version",
        verification_criteria={"max_error_rate": 0.05}
    )
)

PAYMENT_SCENARIOS: List[ScenarioDefinition] = [
    SCENARIO_PAYMENT_STATE_INCONSISTENCY,
    SCENARIO_PAYMENT_WEBHOOK_DEGRADATION,
    SCENARIO_PAYMENT_GATEWAY_LATENCY,
    SCENARIO_PAYMENT_DUPLICATE_EVENT,
    SCENARIO_PAYMENT_SETTLEMENT_MISMATCH,
    SCENARIO_PAYMENT_ROUTE_DEGRADATION
]

# Register all Payment Scenarios into Global Taxonomy
for sc in PAYMENT_SCENARIOS:
    global_taxonomy.register(TaxonomyEntry(
        scenario_id=sc.scenario_id,
        family=ScenarioFamily.PAYMENT,
        variant=sc.ground_truth.root_cause_type,
        difficulty=ScenarioDifficulty.HARD,
        split=DatasetSplit.DEVELOPMENT,
        ground_truth_root_cause=sc.ground_truth.description,
        root_cause_service=sc.ground_truth.root_cause_service,
        root_cause_category="payment",
        required_evidence=[],
        allowed_actions=[sc.ground_truth.expected_remediation],
        expected_outcome="RESOLVED",
        payment_domain=True,
        adversarial=False
    ))
