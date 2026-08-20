# Unit Tests for Bounded Remediation and Safety Policy Engine
import pytest
from simulator.services.runner import InProcessCluster
from simulator.faults.models import FaultConfig, FaultType
from agent.policies.models import RemediationProposal, RemediationActionType, RemediationRiskLevel
from agent.policies.engine import PolicyEngine
from tools.remediation.executor import BoundedRemediationExecutor
from tools.base import ToolExecutionStatus

@pytest.fixture
def cluster_and_executor():
    c = InProcessCluster()
    pol = PolicyEngine()
    executor = BoundedRemediationExecutor(c, pol)
    yield c, pol, executor
    c.clear_all_faults()

def test_rollback_remediation_clears_fault(cluster_and_executor):
    cluster, policy_engine, executor = cluster_and_executor
    
    # Inject bad deployment on payment-service
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0
    )
    cluster.payment_service.fault_injector.set_fault(fault)
    assert cluster.payment_client.get("/health").status_code == 500

    proposal = RemediationProposal(
        incident_id="inc_rem_01",
        action_type=RemediationActionType.ROLLBACK_VERSION,
        target_service="payment-service",
        parameters={"target_version": "1.0.0"},
        risk_level=RemediationRiskLevel.LOW,
        rationale="Rollback buggy deployment v2.4.1"
    )
    res = executor.execute_remediation(proposal)
    assert res.status == ToolExecutionStatus.SUCCESS
    
    # Verify payment health restored
    assert cluster.payment_client.get("/health").status_code == 200

def test_forbidden_command_denied_by_policy(cluster_and_executor):
    cluster, policy_engine, executor = cluster_and_executor
    proposal = RemediationProposal(
        incident_id="inc_rem_02",
        action_type=RemediationActionType.FORBIDDEN_COMMAND,
        target_service="payment-service",
        rationale="Attempt direct bash command"
    )
    res = executor.execute_remediation(proposal)
    assert res.status == ToolExecutionStatus.PERMISSION_DENIED
    assert "strictly forbidden" in res.error_message.lower()

def test_unknown_target_service_denied(cluster_and_executor):
    cluster, policy_engine, executor = cluster_and_executor
    proposal = RemediationProposal(
        incident_id="inc_rem_03",
        action_type=RemediationActionType.RESTART_WORKERS,
        target_service="non_existent_microservice",
        rationale="Restart unknown service"
    )
    res = executor.execute_remediation(proposal)
    assert res.status == ToolExecutionStatus.PERMISSION_DENIED
    assert "not recognized" in res.error_message.lower()

def test_idempotency_prevents_duplicate_remediation(cluster_and_executor):
    cluster, policy_engine, executor = cluster_and_executor
    proposal = RemediationProposal(
        incident_id="inc_rem_04",
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="order-service",
        rationale="Optimize order index"
    )
    res1 = executor.execute_remediation(proposal)
    assert res1.status == ToolExecutionStatus.SUCCESS

    # Attempt duplicate execution
    res2 = executor.execute_remediation(proposal)
    assert res2.status == ToolExecutionStatus.PERMISSION_DENIED
    assert "already been executed" in res2.error_message.lower()

def test_high_risk_action_requires_human_approval(cluster_and_executor):
    cluster, policy_engine, executor = cluster_and_executor
    proposal = RemediationProposal(
        incident_id="inc_rem_05",
        action_type=RemediationActionType.RESTART_WORKERS,
        target_service="api-gateway",
        risk_level=RemediationRiskLevel.CRITICAL,
        rationale="Critical infrastructure worker restart"
    )
    res = executor.execute_remediation(proposal)
    assert res.status == ToolExecutionStatus.PERMISSION_DENIED
    assert "approval token" in res.error_message.lower()
