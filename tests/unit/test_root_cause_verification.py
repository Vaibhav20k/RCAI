# Unit Tests for Root-Cause Verification and Evidence Provenance
import pytest
from backend.incidents.models import AgentIncidentView, IncidentSeverity, IncidentStatus
from agent.hypothesis.models import Hypothesis, HypothesisCategory, HypothesisSet, HypothesisStatus
from agent.investigator.state import InvestigationState
from agent.verification.engine import RootCauseVerifier
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType

@pytest.fixture
def sample_state():
    incident = AgentIncidentView(
        incident_id="inc_verif_01",
        scenario_id="scenario_test",
        started_at=100.0,
        detected_at=160.0,
        severity=IncidentSeverity.HIGH,
        service="order-service",
        symptom="DB latency regression",
        status=IncidentStatus.INVESTIGATING,
        incident_window={"start_ts": 50.0, "end_ts": 160.0}
    )
    h_set = HypothesisSet(incident_id="inc_verif_01")
    h = Hypothesis(
        incident_id="inc_verif_01",
        target_service="order-service",
        category=HypothesisCategory.DATABASE,
        description="Database query latency regression in order_service",
        confidence=0.85,
        status=HypothesisStatus.CONFIRMED,
        supporting_evidence=["ev_test_1", "ev_test_2"]
    )
    h_set.add_hypothesis(h)

    ev1 = NormalizedEvidence.create(
        source=EvidenceSource.DATABASE,
        evidence_type=EvidenceType.DATABASE_METRIC,
        summary="DB query delay 90ms",
        data={"query_time_ms": 90},
        query="query_db_metrics",
        collector="MetricsCollector"
    )
    ev1.evidence_id = "ev_test_1"

    ev2 = NormalizedEvidence.create(
        source=EvidenceSource.METRICS,
        evidence_type=EvidenceType.METRIC_SERIES,
        summary="Latency histogram elevated",
        data={"p95": 92.0},
        query="query_metrics",
        collector="MetricsCollector"
    )
    ev2.evidence_id = "ev_test_2"

    state = InvestigationState(
        investigation_id="inv_test",
        incident=incident,
        hypothesis_set=h_set,
        evidence_store={"ev_test_1": ev1, "ev_test_2": ev2},
        final_root_cause_hypothesis=h
    )
    return state

def test_root_cause_verifier_validates_evidence_and_provenance(sample_state):
    verifier = RootCauseVerifier(min_confidence_for_certainty=0.65)
    decision = verifier.verify_and_generate_decision(sample_state)

    assert decision.is_unknown is False
    assert decision.root_cause_service == "order-service"
    assert decision.root_cause_category == HypothesisCategory.DATABASE
    assert len(decision.supporting_evidence_ids) == 2
    assert len(decision.provenance_audit) == 2
    assert decision.provenance_audit[0]["hash_signature"] is not None

def test_root_cause_verifier_returns_unknown_when_confidence_insufficient(sample_state):
    sample_state.final_root_cause_hypothesis.confidence = 0.30
    verifier = RootCauseVerifier(min_confidence_for_certainty=0.65)
    decision = verifier.verify_and_generate_decision(sample_state)

    assert decision.is_unknown is True
    assert decision.root_cause_category == HypothesisCategory.UNKNOWN
    assert "ROOT_CAUSE_UNKNOWN" in decision.description

def test_root_cause_verifier_returns_insufficient_when_evidence_unbacked(sample_state):
    # Empty out evidence store
    sample_state.evidence_store.clear()
    verifier = RootCauseVerifier(min_confidence_for_certainty=0.65)
    decision = verifier.verify_and_generate_decision(sample_state)

    assert decision.is_unknown is True
    assert "INSUFFICIENT_EVIDENCE" in decision.description

def test_generate_incident_report(sample_state):
    verifier = RootCauseVerifier()
    report = verifier.generate_incident_report(sample_state)

    assert report.report_id.startswith("rep_")
    assert report.incident.service == "order-service"
    assert report.root_cause_decision.root_cause_service == "order-service"
    assert "order-service" in report.executive_summary
    assert report.recommended_action is not None
