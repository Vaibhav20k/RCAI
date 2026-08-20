# Unit Tests for Remediation Outcome Verification
import pytest
from simulator.services.runner import InProcessCluster
from simulator.faults.models import FaultConfig, FaultType
from backend.incidents.models import Incident, IncidentStatus, IncidentSeverity
from agent.policies.models import RemediationProposal, RemediationActionType
from tools.remediation.executor import BoundedRemediationExecutor
from agent.verification.outcome import RemediationOutcomeVerifier

@pytest.fixture
def test_env():
    c = InProcessCluster()
    executor = BoundedRemediationExecutor(c)
    verifier = RemediationOutcomeVerifier(c)
    yield c, executor, verifier
    c.clear_all_faults()

def test_successful_remediation_outcome_verification(test_env):
    cluster, executor, verifier = test_env
    
    # 1. Inject bad deployment
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0
    )
    cluster.payment_service.fault_injector.set_fault(fault)

    incident = Incident(
        scenario_id="scenario_test",
        service="payment-service",
        symptom="Payment service 100% errors",
        status=IncidentStatus.REMEDIATION_PENDING
    )

    # 2. Capture pre-metrics
    pre_metrics = verifier.capture_metrics_snapshot("payment-service")
    assert pre_metrics["active_faults"] == 1.0

    # 3. Execute rollback
    proposal = RemediationProposal(
        incident_id=incident.incident_id,
        action_type=RemediationActionType.ROLLBACK_VERSION,
        target_service="payment-service",
        parameters={"target_version": "1.0.0"},
        rationale="Rollback buggy version"
    )
    exec_res = executor.execute_remediation(proposal)
    assert exec_res.status.value == "SUCCESS"

    # 4. Verify outcome
    outcome = verifier.verify_remediation_outcome(
        proposal=proposal,
        pre_metrics=pre_metrics,
        incident=incident,
        test_traffic_count=10
    )
    assert outcome.is_recovered is True
    assert outcome.status == "RESOLVED"
    assert incident.status == IncidentStatus.RESOLVED

def test_failed_remediation_outcome_verification(test_env):
    cluster, executor, verifier = test_env
    
    # 1. Inject bad deployment on payment-service
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0
    )
    cluster.payment_service.fault_injector.set_fault(fault)

    incident = Incident(
        scenario_id="scenario_test",
        service="payment-service",
        symptom="Payment service 100% errors",
        status=IncidentStatus.REMEDIATION_PENDING
    )
    pre_metrics = verifier.capture_metrics_snapshot("payment-service")

    # 2. Execute wrong action: DB index optimization instead of rollback
    proposal = RemediationProposal(
        incident_id=incident.incident_id,
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="order-service",
        rationale="Incorrect action on wrong service"
    )
    executor.execute_remediation(proposal)

    # 3. Verify outcome on payment-service
    outcome = verifier.verify_remediation_outcome(
        proposal=RemediationProposal(
            incident_id=incident.incident_id,
            action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
            target_service="payment-service",
            rationale="Check payment status"
        ),
        pre_metrics=pre_metrics,
        incident=incident,
        test_traffic_count=10
    )
    assert outcome.is_recovered is False
    assert outcome.status == "REMEDIATION_FAILED"
    assert incident.status == IncidentStatus.UNRESOLVED
