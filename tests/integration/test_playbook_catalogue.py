# Integration Tests for Remediation Playbook Catalogue and LLM Selection (Stage 3)
import time
import pytest
from unittest.mock import patch, MagicMock
from agent.playbooks.models import PlaybookDefinition
from agent.playbooks.catalogue import PlaybookCatalogue, global_playbook_catalogue
from agent.playbooks.selector import PlaybookSelector, global_playbook_selector
from agent.policies.models import (
    RemediationProposal,
    RemediationActionType,
    RemediationRiskLevel,
    PolicyCheckResult
)
from agent.policies.engine import PolicyEngine
from tools.remediation.executor import BoundedRemediationExecutor
from simulator.services.runner import InProcessCluster
from agent.verification.models import RootCauseDecision, IncidentReport
from agent.hypothesis.models import HypothesisCategory, Hypothesis, HypothesisSet
from backend.incidents.models import AgentIncidentView, IncidentSeverity, IncidentStatus, Incident
from agent.investigator.state import InvestigationState
from agent.verification.engine import RootCauseVerifier
from agent.llm.interface import BaseLLMBackend
from agent.llm.backends.rule_based import RuleBasedLLMBackend
from tools.base import ToolExecutionStatus

def test_playbook_catalogue_initialization_and_metadata():
    catalogue = PlaybookCatalogue()
    playbooks = catalogue.list_playbooks()
    assert len(playbooks) >= 7

    required_playbook_names = [
        "optimize_db_index",
        "rollback_deploy",
        "rollback_version",
        "restart_service",
        "restart_workers",
        "scale_replicas",
        "scale_workers",
        "circuit_breaker",
        "flush_cache",
        "toggle_feature_flag"
    ]
    for name in required_playbook_names:
        p = catalogue.get_playbook(name)
        assert p is not None, f"Missing playbook: {name}"
        assert p.version == "1.0.0"
        assert len(p.description) > 10
        assert len(p.reversal_procedure) > 5
        assert isinstance(p.risk_level, RemediationRiskLevel)

def test_playbook_catalogue_validation_rules():
    catalogue = PlaybookCatalogue()

    # 1. Valid selection
    valid, err = catalogue.validate_playbook_selection(
        action="optimize_db_index",
        target="order-service",
        params={}
    )
    assert valid is True
    assert err is None

    # 2. Uncatalogued / dangerous action
    invalid_act, err_act = catalogue.validate_playbook_selection(
        action="drop_database",
        target="order-service",
        params={}
    )
    assert invalid_act is False
    assert "not in the approved remediation playbook catalogue" in err_act

    # 3. Missing required parameter (flag_name for toggle_feature_flag)
    invalid_param, err_param = catalogue.validate_playbook_selection(
        action="toggle_feature_flag",
        target="order-service",
        params={"state": False} # missing flag_name
    )
    assert invalid_param is False
    assert "missing required parameter: 'flag_name'" in err_param

    # 4. Empty target service
    invalid_target, err_target = catalogue.validate_playbook_selection(
        action="restart_service",
        target="",
        params={}
    )
    assert invalid_target is False
    assert "Target service must be specified" in err_target

def test_playbook_selector_with_rule_based_inference():
    selector = PlaybookSelector()
    now = time.time()
    incident = AgentIncidentView(
        incident_id="inc_play_01",
        scenario_id="scenario_bad_deploy_payment",
        started_at=now - 60,
        detected_at=now,
        severity=IncidentSeverity.CRITICAL,
        service="payment-service",
        symptom="Payment service 100% error rate after deploy v2.4.1",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": now - 300, "end_ts": now}
    )

    decision = RootCauseDecision(
        decision_id="dec_01",
        incident_id="inc_play_01",
        root_cause_service="payment-service",
        root_cause_category=HypothesisCategory.DEPLOYMENT,
        description="Bad software deployment v2.4.1 introduced unhandled exception",
        confidence=0.88,
        supporting_evidence_ids=["ev_1"]
    )

    proposal, err = selector.select_playbook(
        decision=decision,
        incident=incident,
        llm_backend=RuleBasedLLMBackend()
    )

    assert err is None
    assert proposal is not None
    assert proposal.action_type in [RemediationActionType.ROLLBACK_VERSION, RemediationActionType.ROLLBACK_DEPLOY]
    assert proposal.target_service == "payment-service"
    assert proposal.risk_level in [RemediationRiskLevel.LOW, RemediationRiskLevel.MEDIUM]
    assert "Rollback" in proposal.rationale

def test_playbook_selector_uncatalogued_action_routes_to_escalation():
    class UncataloguedLLMBackend(BaseLLMBackend):
        name = "mock_rogue_llm"
        model_name = "rogue-v1"

        def _call_model_raw(self, prompt, system_prompt=None, json_schema=None):
            import json
            return json.dumps({
                "action": "delete_all_pods_and_tables",
                "target": "order-service",
                "params": {"force": True},
                "rationale": "Arbitrary unapproved command generated by hallucinating model",
                "risk_level": "CRITICAL"
            })

    selector = PlaybookSelector()
    now = time.time()
    incident = AgentIncidentView(
        incident_id="inc_play_02",
        scenario_id="scenario_test",
        started_at=now - 60,
        detected_at=now,
        severity=IncidentSeverity.HIGH,
        service="order-service",
        symptom="Latency spike",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": now - 300, "end_ts": now}
    )

    decision = RootCauseDecision(
        decision_id="dec_02",
        incident_id="inc_play_02",
        root_cause_service="order-service",
        root_cause_category=HypothesisCategory.DATABASE,
        description="Database query latency regression",
        confidence=0.85
    )

    proposal, err = selector.select_playbook(
        decision=decision,
        incident=incident,
        llm_backend=UncataloguedLLMBackend()
    )

    # Hard safety rule: must reject uncatalogued action and route to human escalation
    assert proposal is None
    assert err is not None
    assert "Playbook catalogue rejection" in err
    assert "not in the approved remediation playbook catalogue" in err

def test_playbook_selector_missing_required_parameter_routes_to_escalation():
    class MissingParamLLMBackend(BaseLLMBackend):
        name = "mock_missing_param_llm"
        model_name = "missing-param-v1"

        def _call_model_raw(self, prompt, system_prompt=None, json_schema=None):
            import json
            # Proposes valid action 'toggle_feature_flag' but omits required 'flag_name'
            return json.dumps({
                "action": "toggle_feature_flag",
                "target": "order-service",
                "params": {"state": False},
                "rationale": "Disable experimental feature without specifying flag name",
                "risk_level": "MEDIUM"
            })

    selector = PlaybookSelector()
    now = time.time()
    incident = AgentIncidentView(
        incident_id="inc_play_missing_param",
        scenario_id="scenario_test",
        started_at=now - 60,
        detected_at=now,
        severity=IncidentSeverity.HIGH,
        service="order-service",
        symptom="Latency spike",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": now - 300, "end_ts": now}
    )

    decision = RootCauseDecision(
        decision_id="dec_missing_param",
        incident_id="inc_play_missing_param",
        root_cause_service="order-service",
        root_cause_category=HypothesisCategory.DEPLOYMENT,
        description="Feature flag rollout regression",
        confidence=0.85
    )

    proposal, err = selector.select_playbook(
        decision=decision,
        incident=incident,
        llm_backend=MissingParamLLMBackend()
    )

    # Must reject incomplete parameter selection and escalate, never default or guess
    assert proposal is None
    assert err is not None
    assert "Playbook catalogue rejection" in err
    assert "missing required parameter: 'flag_name'" in err

def test_playbook_selector_malformed_json_exhausts_retries_and_routes_to_escalation():
    class MalformedLLMBackend(BaseLLMBackend):
        name = "mock_malformed_llm"
        model_name = "malformed-v1"
        attempts = 0

        def _call_model_raw(self, prompt, system_prompt=None, json_schema=None):
            self.attempts += 1
            return "This response is not valid JSON and contains no JSON blocks."

    selector = PlaybookSelector()
    now = time.time()
    incident = AgentIncidentView(
        incident_id="inc_play_malformed",
        scenario_id="scenario_test",
        started_at=now - 60,
        detected_at=now,
        severity=IncidentSeverity.HIGH,
        service="order-service",
        symptom="500 errors",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": now - 300, "end_ts": now}
    )

    decision = RootCauseDecision(
        decision_id="dec_malformed",
        incident_id="inc_play_malformed",
        root_cause_service="order-service",
        root_cause_category=HypothesisCategory.DATABASE,
        description="Database regression",
        confidence=0.80
    )

    mock_backend = MalformedLLMBackend()
    proposal, err = selector.select_playbook(
        decision=decision,
        incident=incident,
        llm_backend=mock_backend
    )

    # Exhausts max_retries (1 retry = 2 attempts) and routes strictly to human escalation
    assert proposal is None
    assert mock_backend.attempts == 2
    assert err is not None
    assert "Playbook selection schema validation failed" in err
    assert "Routing to human escalation" in err

def test_policy_engine_strictly_gates_llm_selected_proposals():
    policy_engine = PolicyEngine()
    
    # 1. Unknown service target rejected
    p_unknown = RemediationProposal(
        incident_id="inc_01",
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="unknown-external-svc",
        rationale="Fix index"
    )
    res1 = policy_engine.evaluate_proposal(p_unknown)
    assert res1.is_allowed is False
    assert res1.policy_code == "DENIED_UNKNOWN_SERVICE"

    # 2. Forbidden command action rejected
    p_forbidden = RemediationProposal(
        incident_id="inc_01",
        action_type=RemediationActionType.FORBIDDEN_COMMAND,
        target_service="order-service",
        rationale="Run shell command"
    )
    res2 = policy_engine.evaluate_proposal(p_forbidden)
    assert res2.is_allowed is False
    assert res2.policy_code == "DENIED_FORBIDDEN_ACTION"

    # 3. Inactive incident rejected
    inc_resolved = Incident(
        scenario_id="sc_01",
        service="order-service",
        symptom="resolved",
        status=IncidentStatus.RESOLVED
    )
    p_resolved = RemediationProposal(
        incident_id=inc_resolved.incident_id,
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="order-service",
        rationale="Fix index"
    )
    res3 = policy_engine.evaluate_proposal(p_resolved, incident=inc_resolved)
    assert res3.is_allowed is False
    assert res3.policy_code == "DENIED_INACTIVE_INCIDENT"

    # 4. Valid proposal allowed
    p_valid = RemediationProposal(
        incident_id="inc_02",
        action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
        target_service="order-service",
        rationale="Valid index optimization"
    )
    res4 = policy_engine.evaluate_proposal(p_valid)
    assert res4.is_allowed is True
    assert res4.policy_code == "ALLOWED"

    # 5. Idempotency prevents duplicate action
    policy_engine.record_execution(p_valid)
    res5 = policy_engine.evaluate_proposal(p_valid)
    assert res5.is_allowed is False
    assert res5.policy_code == "DENIED_DUPLICATE_ACTION"

def test_executor_runs_all_catalogue_playbook_types():
    cluster = InProcessCluster()
    policy_engine = PolicyEngine()
    executor = BoundedRemediationExecutor(cluster, policy_engine)

    playbooks_to_test = [
        (RemediationActionType.ROLLBACK_DEPLOY, "payment-service", {"target_version": "1.0.0"}),
        (RemediationActionType.OPTIMIZE_DB_INDEX, "order-service", {}),
        (RemediationActionType.RESTART_SERVICE, "api-gateway", {}),
        (RemediationActionType.SCALE_REPLICAS, "worker-service", {"replicas": 3}),
        (RemediationActionType.CIRCUIT_BREAKER, "dependency-service", {"trip_threshold": 5}),
        (RemediationActionType.FLUSH_CACHE, "payment-service", {}),
        (RemediationActionType.TOGGLE_FEATURE_FLAG, "order-service", {"flag_name": "new_checkout", "state": False})
    ]

    for action_type, service, params in playbooks_to_test:
        proposal = RemediationProposal(
            incident_id=f"inc_{action_type.value}",
            action_type=action_type,
            target_service=service,
            parameters=params,
            rationale=f"Testing execution of {action_type.value}"
        )
        res = executor.execute_remediation(proposal)
        assert res.status == ToolExecutionStatus.SUCCESS
        assert len(res.evidence) == 1
        assert res.raw_output["status"] == "EXECUTED"

def test_incident_report_generates_catalogued_proposal():
    cluster = InProcessCluster()
    verifier = RootCauseVerifier()
    
    now = time.time()
    incident = AgentIncidentView(
        incident_id="inc_report_test",
        scenario_id="scenario_db_regression_order",
        started_at=now - 60,
        detected_at=now,
        severity=IncidentSeverity.HIGH,
        service="order-service",
        symptom="Order service database latency regression",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": now - 300, "end_ts": now}
    )

    hypo_set = HypothesisSet(incident_id=incident.incident_id)
    h_db = Hypothesis(
        incident_id=incident.incident_id,
        target_service="order-service",
        category=HypothesisCategory.DATABASE,
        description="Database query latency regression on order-service",
        confidence=0.88,
        supporting_evidence=["ev_test_1"]
    )
    hypo_set.add_hypothesis(h_db)

    state = InvestigationState(
        investigation_id="inv_report_01",
        incident=incident,
        hypothesis_set=hypo_set
    )
    # Add verified evidence
    from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType
    state.evidence_store["ev_test_1"] = NormalizedEvidence.create(
        source=EvidenceSource.DATABASE,
        evidence_type=EvidenceType.DATABASE_METRIC,
        summary="DB latency spike > 90ms on order-service",
        data={"service": "order-service"},
        query="query_db_metrics(order-service)",
        collector="MetricsCollector"
    )

    report = verifier.generate_incident_report(state)
    assert report.recommended_proposal is not None
    assert report.recommended_proposal.action_type == RemediationActionType.OPTIMIZE_DB_INDEX
    assert report.recommended_proposal.target_service == "order-service"
    assert "optimize_db_index" in report.recommended_action
