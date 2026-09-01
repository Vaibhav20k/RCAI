# Integration Tests for Stage 4: Real Executor & Live Verification with Auto-Rollback
import time
import json
import pytest
from unittest.mock import patch, MagicMock
from backend.config import Settings, get_settings, reset_settings
from agent.policies.models import (
    RemediationProposal,
    RemediationActionType,
    RemediationRiskLevel,
    PolicyCheckResult
)
from agent.policies.engine import PolicyEngine
from tools.remediation.live_executor import (
    LiveInfrastructureExecutor,
    KubernetesExecutorClient,
    DockerExecutorClient,
    WebhookExecutorClient
)
from tools.remediation.factory import get_remediation_executor
from agent.verification.live_outcome import LiveRemediationOutcomeVerifier
from agent.verification.outcome import get_outcome_verifier, OutcomeVerificationResult
from backend.incidents.models import Incident, IncidentStatus, IncidentSeverity
from tools.base import ToolExecutionStatus

@pytest.fixture(autouse=True)
def reset_cfg():
    reset_settings()
    yield
    reset_settings()

def test_kubernetes_executor_command_invocation():
    k8s = KubernetesExecutorClient(kubectl_path="/usr/local/bin/kubectl", namespace="production")

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "deployment.apps/order-service rolled back"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        # 1. Rollback deployment
        p_roll = RemediationProposal(
            incident_id="inc_k8s_01",
            action_type=RemediationActionType.ROLLBACK_DEPLOY,
            target_service="order-service",
            rationale="Rollback faulty release"
        )
        res1 = k8s.execute_playbook(p_roll)
        assert "kubectl rollout undo deployment/order-service" in res1["command"]
        assert mock_run.call_args[0][0] == [
            "/usr/local/bin/kubectl", "rollout", "undo", "deployment/order-service", "-n", "production"
        ]

        # 2. Scale replicas
        p_scale = RemediationProposal(
            incident_id="inc_k8s_02",
            action_type=RemediationActionType.SCALE_REPLICAS,
            target_service="worker-service",
            parameters={"replicas": 5},
            rationale="Scale queue workers"
        )
        res2 = k8s.execute_playbook(p_scale)
        assert "--replicas=5" in res2["command"]

        # 3. Restart service
        p_restart = RemediationProposal(
            incident_id="inc_k8s_03",
            action_type=RemediationActionType.RESTART_SERVICE,
            target_service="payment-service",
            rationale="Restart hung pods"
        )
        res3 = k8s.execute_playbook(p_restart)
        assert "kubectl rollout restart deployment/payment-service" in res3["command"]

        # 4. Reversal procedure
        rev_res = k8s.trigger_reversal(p_scale)
        assert rev_res["reversal"] == "scale_down"

def test_docker_executor_command_invocation():
    docker = DockerExecutorClient(docker_path="/usr/bin/docker")

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "api-gateway restarted"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        p_restart = RemediationProposal(
            incident_id="inc_doc_01",
            action_type=RemediationActionType.RESTART_SERVICE,
            target_service="api-gateway",
            rationale="Restart gateway container"
        )
        res = docker.execute_playbook(p_restart)
        assert res["command"] == "docker restart api-gateway"
        assert mock_run.call_args[0][0] == ["/usr/bin/docker", "restart", "api-gateway"]

def test_webhook_executor_with_hmac_signature():
    webhook = WebhookExecutorClient(
        webhook_url="http://sre-automation.internal/remediation",
        webhook_secret="super-secret-key-123"
    )

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"status": "SUCCESS", "job_id": "job_99"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        p = RemediationProposal(
            incident_id="inc_web_01",
            action_type=RemediationActionType.CIRCUIT_BREAKER,
            target_service="dependency-service",
            parameters={"trip_threshold": 3},
            rationale="Trip circuit on partner outage"
        )
        res = webhook.execute_playbook(p)
        assert res["status"] == "SUCCESS"
        assert res["job_id"] == "job_99"

        # Verify HMAC signature header was sent
        call_headers = mock_post.call_args[1]["headers"]
        assert "X-Remediation-Signature" in call_headers
        assert len(call_headers["X-Remediation-Signature"]) == 64 # SHA256 hex string

def test_live_infrastructure_executor_enforces_policy_gate():
    policy_engine = PolicyEngine()
    executor = LiveInfrastructureExecutor(policy_engine=policy_engine, target_mode="kubernetes")

    # 1. Unknown service target rejected by policy before K8s execution
    p_bad_svc = RemediationProposal(
        incident_id="inc_test_01",
        action_type=RemediationActionType.RESTART_SERVICE,
        target_service="rogue-service",
        rationale="Restart unknown service"
    )
    res1 = executor.execute_remediation(p_bad_svc)
    assert res1.status == ToolExecutionStatus.PERMISSION_DENIED
    assert "not recognized in microservice topology" in res1.error_message

    # 2. Forbidden command action rejected
    p_forbidden = RemediationProposal(
        incident_id="inc_test_02",
        action_type=RemediationActionType.FORBIDDEN_COMMAND,
        target_service="order-service",
        rationale="Run bash script"
    )
    res2 = executor.execute_remediation(p_forbidden)
    assert res2.status == ToolExecutionStatus.PERMISSION_DENIED
    assert "strictly forbidden" in res2.error_message

    # 3. Valid execution generates provenanced evidence
    with patch.object(executor.k8s_client, "execute_playbook", return_value={"status": "OK"}):
        p_valid = RemediationProposal(
            incident_id="inc_test_03",
            action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
            target_service="order-service",
            rationale="Optimize order index"
        )
        res3 = executor.execute_remediation(p_valid)
        assert res3.status == ToolExecutionStatus.SUCCESS
        assert len(res3.evidence) == 1
        assert res3.evidence[0].provenance.hash_signature is not None

def test_live_outcome_verifier_successful_recovery():
    verifier = LiveRemediationOutcomeVerifier(
        max_error_rate=0.05,
        max_p99_ms=100.0
    )

    # Mock Prometheus queries returning clean healthy metrics
    mock_prom = MagicMock()
    mock_prom.query_instant.side_effect = [
        {"data": {"result": [{"value": [time.time(), "0.002"]}]}}, # error rate 0.2%
        {"data": {"result": [{"value": [time.time(), "28.5"]}]}}   # p99 28.5ms
    ]
    verifier.prom_client = mock_prom

    # Mock HTTP health probe returning 200 OK
    with patch.object(verifier, "check_service_http_health", return_value=True):
        inc = Incident(
            scenario_id="sc_01",
            service="order-service",
            symptom="DB latency regression",
            status=IncidentStatus.REMEDIATION_EXECUTED
        )
        proposal = RemediationProposal(
            incident_id=inc.incident_id,
            action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
            target_service="order-service",
            rationale="Fix index"
        )

        outcome = verifier.verify_live_remediation_outcome(
            proposal=proposal,
            pre_metrics={"error_rate": 0.40, "p99_latency_ms": 250.0},
            incident=inc
        )

        assert outcome.is_recovered is True
        assert outcome.status == "RESOLVED"
        assert inc.status == IncidentStatus.RESOLVED
        assert "Live Verification SUCCESS" in outcome.verification_summary

def test_live_outcome_verifier_failure_triggers_automatic_reversal_and_escalation():
    verifier = LiveRemediationOutcomeVerifier(
        max_error_rate=0.05,
        max_p99_ms=100.0
    )

    # Mock Prometheus queries returning failing metrics
    mock_prom = MagicMock()
    mock_prom.query_instant.side_effect = [
        {"data": {"result": [{"value": [time.time(), "0.35"]}]}}, # error rate 35% (> 5%)
        {"data": {"result": [{"value": [time.time(), "320.0"]}]}} # p99 320ms (> 100ms)
    ]
    verifier.prom_client = mock_prom

    reversal_mock = MagicMock(return_value={"reversal": "rollout_reverted_to_base", "status": "COMPLETED"})

    with patch.object(verifier, "check_service_http_health", return_value=False):
        inc = Incident(
            scenario_id="sc_02",
            service="payment-service",
            symptom="Payment outage",
            status=IncidentStatus.REMEDIATION_EXECUTED
        )
        proposal = RemediationProposal(
            incident_id=inc.incident_id,
            action_type=RemediationActionType.ROLLBACK_DEPLOY,
            target_service="payment-service",
            rationale="Rollback deploy"
        )

        outcome = verifier.verify_live_remediation_outcome(
            proposal=proposal,
            pre_metrics={"error_rate": 0.80, "p99_latency_ms": 500.0},
            incident=inc,
            executor_reversal_fn=reversal_mock
        )

        # Automatic rollback was triggered and incident escalated
        assert outcome.is_recovered is False
        assert outcome.status == "ROLLED_BACK_AND_ESCALATED"
        assert inc.status == IncidentStatus.ESCALATED
        assert reversal_mock.called
        assert "Live Verification FAILED" in outcome.verification_summary
        assert "Automated reversal executed" in outcome.verification_summary

def test_underlying_executor_subprocess_failure_returns_error_and_blocks():
    k8s = KubernetesExecutorClient(kubectl_path="/usr/local/bin/kubectl", namespace="production")

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "error: timed out waiting for the condition on deployments/order-service"
        mock_run.return_value = mock_proc

        executor = LiveInfrastructureExecutor(k8s_client=k8s, target_mode="kubernetes")
        proposal = RemediationProposal(
            incident_id="inc_k8s_fail",
            action_type=RemediationActionType.RESTART_SERVICE,
            target_service="order-service",
            rationale="Restart hung service"
        )

        res = executor.execute_remediation(proposal)
        assert res.status == ToolExecutionStatus.ERROR
        assert "Infrastructure remediation failed" in res.error_message
        assert "timed out waiting for the condition" in res.error_message

def test_reversal_failure_lands_in_terminal_escalated_state_without_looping():
    verifier = LiveRemediationOutcomeVerifier(
        max_error_rate=0.05,
        max_p99_ms=100.0
    )

    # Mock Prometheus returning failing metrics (post-remediation error rate 40%)
    mock_prom = MagicMock()
    mock_prom.query_instant.side_effect = [
        {"data": {"result": [{"value": [time.time(), "0.40"]}]}},
        {"data": {"result": [{"value": [time.time(), "350.0"]}]}}
    ]
    verifier.prom_client = mock_prom

    # Mock reversal execution throwing a cluster connection error
    def failing_reversal(p):
        raise RuntimeError("kubectl: connection refused / cluster unreachable")

    with patch.object(verifier, "check_service_http_health", return_value=False):
        inc = Incident(
            scenario_id="sc_03",
            service="order-service",
            symptom="Order service database deadlock",
            status=IncidentStatus.REMEDIATION_EXECUTED
        )
        proposal = RemediationProposal(
            incident_id=inc.incident_id,
            action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
            target_service="order-service",
            rationale="Fix index"
        )

        outcome = verifier.verify_live_remediation_outcome(
            proposal=proposal,
            pre_metrics={"error_rate": 0.50, "p99_latency_ms": 400.0},
            incident=inc,
            executor_reversal_fn=failing_reversal
        )

        # Verification must handle reversal exception gracefully without looping or crashing
        assert outcome.is_recovered is False
        assert outcome.status == "ROLLED_BACK_AND_ESCALATED"
        assert inc.status == IncidentStatus.ESCALATED
        assert "reversal_error" in outcome.verification_summary or "Live Verification FAILED" in outcome.verification_summary

def test_reversal_policy_gating_blocks_unknown_service():
    policy_engine = PolicyEngine()
    executor = LiveInfrastructureExecutor(policy_engine=policy_engine, target_mode="kubernetes")

    p_unknown = RemediationProposal(
        incident_id="inc_rev_unknown",
        action_type=RemediationActionType.ROLLBACK_DEPLOY,
        target_service="unknown-third-party-service",
        rationale="Rollback unknown target"
    )

    rev_res = executor.trigger_reversal(p_unknown)
    assert rev_res["status"] == "BLOCKED"
    assert rev_res["policy_code"] == "DENIED_UNKNOWN_SERVICE"
    assert "not recognized in microservice topology" in rev_res["rejection_reason"]

def test_reversal_policy_gating_prevents_duplicate_reversal_execution():
    policy_engine = PolicyEngine()
    executor = LiveInfrastructureExecutor(policy_engine=policy_engine, target_mode="kubernetes")

    with patch.object(executor.k8s_client, "trigger_reversal", return_value={"reversal": "rollout_undo", "status": "OK"}):
        p = RemediationProposal(
            incident_id="inc_rev_dup",
            action_type=RemediationActionType.SCALE_REPLICAS,
            target_service="worker-service",
            parameters={"replicas": 3},
            rationale="Scale workers"
        )

        # 1. First reversal allowed and recorded
        res1 = executor.trigger_reversal(p)
        assert res1["status"] == "SUCCESS"
        assert res1["reversal"] == "rollout_undo"

        # 2. Second duplicate reversal blocked by policy gate
        res2 = executor.trigger_reversal(p)
        assert res2["status"] == "BLOCKED"
        assert res2["policy_code"] == "DENIED_DUPLICATE_REVERSAL"
        assert "has already been executed" in res2["rejection_reason"]

def test_reversal_emits_provenanced_evidence_and_records_deployment_audit():
    policy_engine = PolicyEngine()
    executor = LiveInfrastructureExecutor(policy_engine=policy_engine, target_mode="docker")

    with patch.object(executor.docker_client, "trigger_reversal", return_value={"reversal": "docker_noop", "status": "COMPLETED"}):
        p = RemediationProposal(
            incident_id="inc_rev_audit",
            action_type=RemediationActionType.RESTART_SERVICE,
            target_service="order-service",
            rationale="Restart order service"
        )

        res = executor.trigger_reversal(p)
        assert res["status"] == "SUCCESS"
        assert "evidence_id" in res

        # Verify deployment record was persisted
        from observability.deployments.store import global_deployment_store
        records = global_deployment_store.get_service_history("order-service")
        assert any(r.status == "REVERSAL_ROLLED_BACK" for r in records)

def test_remediation_factory_switching():
    import os
    with patch.dict(os.environ, {"DATA_SOURCE": "simulator", "REMEDIATION_EXECUTION_TARGET": "simulated"}):
        reset_settings()
        ex1 = get_remediation_executor()
        assert ex1.__class__.__name__ == "BoundedRemediationExecutor"
        ov1 = get_outcome_verifier()
        assert ov1.__class__.__name__ == "RemediationOutcomeVerifier"

    with patch.dict(os.environ, {"DATA_SOURCE": "live", "REMEDIATION_EXECUTION_TARGET": "kubernetes"}):
        reset_settings()
        ex2 = get_remediation_executor()
        assert ex2.__class__.__name__ == "LiveInfrastructureExecutor"
        ov2 = get_outcome_verifier()
        assert ov2.__class__.__name__ == "LiveRemediationOutcomeVerifier"


