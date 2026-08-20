# Unit Tests for Incident Models and Agent-Facing Views
import time
import pytest
from backend.incidents.models import (
    Incident,
    IncidentStatus,
    IncidentSeverity,
    GroundTruth,
    AgentIncidentView
)

def test_incident_creation_and_agent_view_isolation():
    gt = GroundTruth(
        root_cause_service="payment-service",
        root_cause_type="bad_deployment",
        description="Hidden ground truth description",
        expected_remediation="rollback_payment_service_v2.4.0",
        verification_criteria={"max_error_rate": 0.05}
    )
    inc = Incident(
        scenario_id="scenario_test_01",
        service="payment-service",
        symptom="Payment API error rate spiked to 80%",
        severity=IncidentSeverity.CRITICAL,
        ground_truth=gt
    )
    assert inc.ground_truth is not None
    assert inc.ground_truth.root_cause_type == "bad_deployment"

    # Agent view extraction
    agent_view = inc.to_agent_view()
    assert isinstance(agent_view, AgentIncidentView)
    assert agent_view.incident_id == inc.incident_id
    assert agent_view.service == "payment-service"
    assert not hasattr(agent_view, "ground_truth")
    assert "ground_truth" not in agent_view.model_dump()

def test_incident_state_transitions():
    inc = Incident(
        scenario_id="scenario_test_02",
        service="order-service",
        symptom="Database query slowdown"
    )
    assert inc.status == IncidentStatus.DETECTED
    
    inc.status = IncidentStatus.INVESTIGATING
    assert inc.status == IncidentStatus.INVESTIGATING
    
    inc.status = IncidentStatus.HYPOTHESES_GENERATED
    assert inc.status == IncidentStatus.HYPOTHESES_GENERATED
