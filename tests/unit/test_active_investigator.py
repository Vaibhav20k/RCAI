# Unit Tests for Active Investigation Loop
import pytest
from simulator.services.runner import InProcessCluster
from simulator.faults.models import FaultConfig, FaultType
from observability.metrics.collector import MetricsCollector
from observability.deployments.store import global_deployment_store, DeploymentRecord
from tools.registry import create_default_investigation_tools
from backend.incidents.models import AgentIncidentView, IncidentSeverity, IncidentStatus
from agent.investigator.loop import ActiveInvestigator
from agent.hypothesis.models import HypothesisCategory, HypothesisStatus

@pytest.fixture
def cluster_env():
    c = InProcessCluster()
    metrics = MetricsCollector(c)
    tools = create_default_investigation_tools(c, metrics)
    yield c, tools
    c.clear_all_faults()

def test_active_investigation_loop_payment_bad_deployment(cluster_env):
    cluster, tools = cluster_env
    
    # Setup bad deployment scenario on payment-service
    fault = FaultConfig(
        service_name="payment-service",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0
    )
    cluster.payment_service.fault_injector.set_fault(fault)
    
    global_deployment_store.record_deployment(
        DeploymentRecord(
            deployment_id="dep_bad_v241",
            service="payment-service",
            version="2.4.1",
            previous_version="2.4.0",
            change_description="Buggy deployment release v2.4.1"
        )
    )

    incident = AgentIncidentView(
        incident_id="inc_active_test_01",
        scenario_id="scenario_bad_deploy_payment",
        started_at=1000.0,
        detected_at=1060.0,
        severity=IncidentSeverity.CRITICAL,
        service="payment-service",
        symptom="Payment service error rate 100%",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": 800.0, "end_ts": 1060.0}
    )

    investigator = ActiveInvestigator(tool_registry=tools, max_tool_calls=10, confidence_threshold=0.70)
    final_state = investigator.run_investigation(incident)

    assert final_state.is_completed is True
    assert final_state.current_step > 0
    assert len(final_state.action_history) > 0
    assert final_state.final_root_cause_hypothesis is not None
    assert final_state.final_root_cause_hypothesis.category == HypothesisCategory.DEPLOYMENT
    assert final_state.final_root_cause_hypothesis.confidence >= 0.70

def test_active_investigation_loop_halts_on_budget_limit(cluster_env):
    cluster, tools = cluster_env
    incident = AgentIncidentView(
        incident_id="inc_active_test_02",
        scenario_id="scenario_generic",
        started_at=1000.0,
        detected_at=1060.0,
        severity=IncidentSeverity.MEDIUM,
        service="dependency-service",
        symptom="Slight latency bump",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": 800.0, "end_ts": 1060.0}
    )
    
    # Strict budget of 2 tool calls
    investigator = ActiveInvestigator(tool_registry=tools, max_tool_calls=2, confidence_threshold=0.99)
    final_state = investigator.run_investigation(incident)

    assert final_state.is_completed is True
    assert final_state.current_step <= 2
    assert final_state.stop_reason in ["BUDGET_EXHAUSTED", "NO_FURTHER_ACTIONS", "CONFIDENCE_THRESHOLD_REACHED"]
