# Evaluator Integrity & Anti-Tampering Security Audit Suite
import pytest
from backend.incidents.models import Incident, GroundTruth, IncidentSeverity
from benchmark.scenarios.registry import ALL_SCENARIOS
from benchmark.evaluators.evaluator import matches_ground_truth
from agent.verification.models import RootCauseDecision
from agent.hypothesis.models import HypothesisCategory

def test_agent_view_strictly_strips_ground_truth():
    gt = GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Secret ground truth description that must never leak",
        injected_fault_config={"secret_key": "confidential"},
        expected_remediation="rollback_version"
    )
    inc = Incident(
        scenario_id="sec_test_01",
        service="payment-service",
        symptom="High error rate",
        severity=IncidentSeverity.CRITICAL,
        ground_truth=gt
    )

    agent_view = inc.to_agent_view()
    assert not hasattr(agent_view, "ground_truth")
    assert not hasattr(agent_view, "expected_remediation")
    assert "secret_key" not in agent_view.model_dump_json()

def test_evaluator_scores_independently():
    sc = ALL_SCENARIOS[0]
    
    # Correct decision
    dec_correct = RootCauseDecision(
        decision_id="dec_eval_1",
        incident_id="inc_1",
        root_cause_service=sc.ground_truth.root_cause_service,
        root_cause_category=HypothesisCategory.DATABASE,
        confidence=0.95,
        description="Database regression",
        supporting_evidence_ids=["ev_1"]
    )
    
    # Tampered / incorrect decision
    dec_incorrect = RootCauseDecision(
        decision_id="dec_eval_2",
        incident_id="inc_2",
        root_cause_service="wrong-service",
        root_cause_category=HypothesisCategory.UNKNOWN,
        confidence=0.99,
        description="Fabricated claim without evidence",
        supporting_evidence_ids=[]
    )
    
    match_correct = matches_ground_truth(
        dec_correct.root_cause_service,
        dec_correct.root_cause_category,
        sc.ground_truth.root_cause_service,
        sc.ground_truth.root_cause_type
    )
    match_incorrect = matches_ground_truth(
        dec_incorrect.root_cause_service,
        dec_incorrect.root_cause_category,
        sc.ground_truth.root_cause_service,
        sc.ground_truth.root_cause_type
    )
    
    assert match_correct is True
    assert match_incorrect is False
