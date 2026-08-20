# Unit Tests for Hypothesis Engine
import pytest
from backend.incidents.models import AgentIncidentView, IncidentSeverity, IncidentStatus
from agent.hypothesis.models import Hypothesis, HypothesisCategory, HypothesisStatus, HypothesisSet
from agent.hypothesis.generator import HypothesisGenerator

@pytest.fixture
def sample_incident():
    return AgentIncidentView(
        incident_id="inc_unit_hypo_01",
        scenario_id="scenario_test",
        started_at=1000.0,
        detected_at=1060.0,
        severity=IncidentSeverity.HIGH,
        service="order-service",
        symptom="Order endpoint latency spike",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": 800.0, "end_ts": 1060.0}
    )

def test_hypothesis_generator_creates_competing_hypotheses(sample_incident):
    hypo_set = HypothesisGenerator.generate_candidate_hypotheses(sample_incident)
    assert len(hypo_set.hypotheses) == 5
    
    categories = [h.category for h in hypo_set.hypotheses]
    assert HypothesisCategory.DATABASE in categories
    assert HypothesisCategory.DEPLOYMENT in categories
    assert HypothesisCategory.DEPENDENCY in categories
    assert HypothesisCategory.RESOURCE in categories
    assert HypothesisCategory.QUEUE in categories

def test_supporting_evidence_updates_confidence_and_status():
    h = Hypothesis(
        incident_id="inc_01",
        target_service="order-service",
        category=HypothesisCategory.DATABASE,
        description="DB regression",
        confidence=0.3
    )
    assert h.status == HypothesisStatus.OPEN
    
    h.add_supporting_evidence("ev_db_slow_1", weight=0.3)
    assert h.confidence == 0.6
    assert "ev_db_slow_1" in h.supporting_evidence
    assert h.status == HypothesisStatus.SUPPORTED

    h.add_supporting_evidence("ev_db_slow_2", weight=0.25)
    assert h.confidence == 0.85
    assert h.status == HypothesisStatus.SUPPORTED

def test_contradicting_evidence_and_rejection():
    h = Hypothesis(
        incident_id="inc_01",
        target_service="order-service",
        category=HypothesisCategory.DEPENDENCY,
        description="Downstream dependency failure",
        confidence=0.4
    )
    h.add_contradicting_evidence("ev_dep_healthy", weight=0.3)
    assert h.confidence == 0.1
    assert h.status == HypothesisStatus.WEAKENED

    h.reject("ev_dep_explicit_ok")
    assert h.status == HypothesisStatus.REJECTED
    assert h.confidence == 0.0
    assert "ev_dep_explicit_ok" in h.contradicting_evidence

def test_hypothesis_set_ranking():
    hypo_set = HypothesisSet(incident_id="inc_01")
    
    h1 = Hypothesis(incident_id="inc_01", target_service="s1", category=HypothesisCategory.DATABASE, description="DB", confidence=0.4)
    h2 = Hypothesis(incident_id="inc_01", target_service="s1", category=HypothesisCategory.DEPLOYMENT, description="Deploy", confidence=0.8)
    h3 = Hypothesis(incident_id="inc_01", target_service="s1", category=HypothesisCategory.DEPENDENCY, description="Dep", confidence=0.1)
    h3.reject()

    hypo_set.add_hypothesis(h1)
    hypo_set.add_hypothesis(h2)
    hypo_set.add_hypothesis(h3)

    top = hypo_set.get_top_hypothesis()
    assert top is not None
    assert top.category == HypothesisCategory.DEPLOYMENT
    assert top.confidence == 0.8

    ranked = hypo_set.get_ranked_hypotheses()
    assert ranked[0].category == HypothesisCategory.DEPLOYMENT
    assert ranked[1].category == HypothesisCategory.DATABASE
    assert ranked[2].status == HypothesisStatus.REJECTED
