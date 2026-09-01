# Integration Tests for Stage 6: Pre-Authorized Playbook Auto-Execution
import time
import os
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from backend.api.app import app, incidents_db, investigations_db, reports_db, outcomes_db
from backend.config import reset_settings, get_settings
from agent.policies.models import (
    RemediationProposal,
    RemediationActionType,
    RemediationRiskLevel,
    ExecutionAuthorizationMode
)
from agent.policies.engine import PolicyEngine
from agent.hypothesis.models import HypothesisCategory
from agent.verification.models import RootCauseDecision, IncidentReport
from backend.incidents.models import Incident, IncidentSeverity, IncidentStatus
from backend.escalation.dispatcher import global_escalation_dispatcher
from observability.deployments.store import global_deployment_store

@pytest.fixture(autouse=True)
def clean_runtime():
    reset_settings()
    incidents_db.clear()
    investigations_db.clear()
    reports_db.clear()
    outcomes_db.clear()
    global_escalation_dispatcher.active_escalations.clear()
    global_deployment_store.reset()
    yield
    incidents_db.clear()
    investigations_db.clear()
    reports_db.clear()
    outcomes_db.clear()
    global_escalation_dispatcher.active_escalations.clear()
    global_deployment_store.reset()
    reset_settings()

def test_auto_execution_policy_guardrails_disabled_by_default():
    policy_engine = PolicyEngine()
    proposal = RemediationProposal(
        incident_id="inc_auto_01",
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="order-service",
        rationale="Fix index contention"
    )
    decision = RootCauseDecision(
        decision_id="dec_01",
        incident_id="inc_auto_01",
        root_cause_service="order-service",
        root_cause_category=HypothesisCategory.DATABASE,
        description="Missing index on orders table",
        confidence=0.95,
        supporting_evidence_ids=["ev_1"],
        provenance_audit=[{"evidence_id": "ev_1", "hash_signature": "sha256:abc", "reliability": 1.0}]
    )

    # Disabled by default
    is_auto, reason = policy_engine.evaluate_auto_execution_eligibility(proposal, decision)
    assert is_auto is False
    assert "Autonomous execution disabled" in reason

def test_auto_execution_confidence_threshold_rejection():
    policy_engine = PolicyEngine()
    proposal = RemediationProposal(
        incident_id="inc_auto_02",
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="order-service",
        rationale="Fix index contention"
    )
    # Confidence 0.85 is below default auto threshold of 0.90
    decision = RootCauseDecision(
        decision_id="dec_02",
        incident_id="inc_auto_02",
        root_cause_service="order-service",
        root_cause_category=HypothesisCategory.DATABASE,
        description="Missing index on orders table",
        confidence=0.85,
        supporting_evidence_ids=["ev_1"],
        provenance_audit=[{"evidence_id": "ev_1", "hash_signature": "sha256:abc", "reliability": 1.0}]
    )

    with patch.dict(os.environ, {"AUTO_EXECUTE_ENABLED": "true", "AUTO_EXECUTE_CONFIDENCE_THRESHOLD": "0.90"}):
        reset_settings()
        is_auto, reason = policy_engine.evaluate_auto_execution_eligibility(proposal, decision)
        assert is_auto is False
        assert "below auto-execution threshold" in reason

def test_auto_execution_unlisted_playbook_rejection():
    policy_engine = PolicyEngine()
    # ROLLBACK_DEPLOY is not in the whitelist
    proposal = RemediationProposal(
        incident_id="inc_auto_03",
        action_type=RemediationActionType.ROLLBACK_DEPLOY,
        target_service="order-service",
        parameters={"target_version": "1.0.0"},
        rationale="Rollback risky release"
    )
    decision = RootCauseDecision(
        decision_id="dec_03",
        incident_id="inc_auto_03",
        root_cause_service="order-service",
        root_cause_category=HypothesisCategory.DEPLOYMENT,
        description="Bad release deployed",
        confidence=0.98,
        supporting_evidence_ids=["ev_1"],
        provenance_audit=[{"evidence_id": "ev_1", "hash_signature": "sha256:abc", "reliability": 1.0}]
    )

    with patch.dict(os.environ, {
        "AUTO_EXECUTE_ENABLED": "true",
        "AUTO_EXECUTE_PLAYBOOKS": "optimize_db_index,restart_service"
    }):
        reset_settings()
        is_auto, reason = policy_engine.evaluate_auto_execution_eligibility(proposal, decision)
        assert is_auto is False
        assert "is not on the pre-authorized auto-execution whitelist" in reason

def test_auto_execution_missing_provenance_rejection():
    policy_engine = PolicyEngine()
    proposal = RemediationProposal(
        incident_id="inc_auto_04",
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="order-service",
        rationale="Fix index contention"
    )
    # Missing hash_signature in provenance audit
    decision = RootCauseDecision(
        decision_id="dec_04",
        incident_id="inc_auto_04",
        root_cause_service="order-service",
        root_cause_category=HypothesisCategory.DATABASE,
        description="Missing index on orders table",
        confidence=0.95,
        supporting_evidence_ids=["ev_1"],
        provenance_audit=[{"evidence_id": "ev_1", "hash_signature": "", "reliability": 0.5}]
    )

    with patch.dict(os.environ, {
        "AUTO_EXECUTE_ENABLED": "true",
        "AUTO_EXECUTE_REQUIRE_PROVENANCE": "true"
    }):
        reset_settings()
        is_auto, reason = policy_engine.evaluate_auto_execution_eligibility(proposal, decision)
        assert is_auto is False
        assert "lacks verified cryptographic hash provenance" in reason

def test_auto_execution_policy_approval_and_audit():
    policy_engine = PolicyEngine()
    proposal = RemediationProposal(
        incident_id="inc_auto_05",
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="order-service",
        rationale="Fix index contention",
        authorization_mode=ExecutionAuthorizationMode.PRE_AUTHORIZED_AUTO
    )
    decision = RootCauseDecision(
        decision_id="dec_05",
        incident_id="inc_auto_05",
        root_cause_service="order-service",
        root_cause_category=HypothesisCategory.DATABASE,
        description="Missing index on orders table",
        confidence=0.96,
        supporting_evidence_ids=["ev_1"],
        provenance_audit=[{"evidence_id": "ev_1", "hash_signature": "sha256:valid_hash", "reliability": 1.0}]
    )

    with patch.dict(os.environ, {
        "AUTO_EXECUTE_ENABLED": "true",
        "AUTO_EXECUTE_CONFIDENCE_THRESHOLD": "0.90",
        "AUTO_EXECUTE_PLAYBOOKS": "optimize_db_index,restart_service"
    }):
        reset_settings()
        is_auto, reason = policy_engine.evaluate_auto_execution_eligibility(proposal, decision)
        assert is_auto is True
        assert "Eligible" in reason

        # Policy gate evaluation allows without human approval token
        check = policy_engine.evaluate_proposal(proposal)
        assert check.is_allowed is True
        assert check.requires_human_approval is False
        assert check.is_pre_authorized is True
        assert check.authorization_mode == ExecutionAuthorizationMode.PRE_AUTHORIZED_AUTO

def test_auto_execution_end_to_end_alert_webhook_flow():
    client = TestClient(app)
    from backend.api.app import scenario_runner, ALL_SCENARIOS
    scenario_runner.execute_scenario(ALL_SCENARIOS[2]) # Database Index Regression scenario

    env_overrides = {
        "AUTO_EXECUTE_ENABLED": "true",
        "AUTO_EXECUTE_CONFIDENCE_THRESHOLD": "0.70",
        "AUTO_EXECUTE_PLAYBOOKS": "optimize_db_index,restart_service,restart_workers",
        "DATA_SOURCE": "simulator",
        "REMEDIATION_EXECUTION_TARGET": "simulated"
    }

    with patch.dict(os.environ, env_overrides):
        reset_settings()
        payload = {
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "DatabaseDeadlock",
                        "service": "order-service",
                        "severity": "high"
                    },
                    "annotations": {
                        "description": "Order service database deadlock during heavy traffic"
                    },
                    "startsAt": "2026-09-01T22:00:00Z",
                    "fingerprint": "fp_auto_01"
                }
            ]
        }

        resp = client.post("/api/alerts/webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["incidents_created"]) == 1
        inc_id = data["incidents_created"][0]

        # Verify incident status has resolved through autonomous execution
        inc = incidents_db[inc_id]
        assert inc.status == IncidentStatus.RESOLVED

        # Verify deployment record shows PRE_AUTHORIZED_AUTO
        records = global_deployment_store.get_service_history("order-service")
        assert len(records) > 0

def test_human_approved_remediation_audit_tracking():
    client = TestClient(app)

    # Create an active incident in REMEDIATION_PENDING
    inc = Incident(
        scenario_id="sc_01",
        service="order-service",
        symptom="High 5xx error rate",
        status=IncidentStatus.ROOT_CAUSE_PROPOSED
    )
    incidents_db[inc.incident_id] = inc

    req_payload = {
        "incident_id": inc.incident_id,
        "action_type": "optimize_db_index",
        "target_service": "order-service",
        "parameters": {},
        "rationale": "Manual SRE approved index fix"
    }

    resp = client.post("/api/remediate", json=req_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["incident_status"] == "RESOLVED"
