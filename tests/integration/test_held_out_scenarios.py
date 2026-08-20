# Integration Tests for Held-Out / Compositional Generalization Scenarios
import pytest
from simulator.services.runner import InProcessCluster
from simulator.scenarios.runner import ScenarioRunner
from benchmark.scenarios.held_out import HELDOUT_SCENARIOS
from backend.incidents.models import Incident
from tools.registry import create_default_investigation_tools
from agent.investigator.loop import ActiveInvestigator
from agent.verification.engine import RootCauseVerifier

@pytest.fixture
def cluster():
    return InProcessCluster()

def test_held_out_scenarios_execute_reproducibly(cluster):
    runner = ScenarioRunner(cluster)
    for sc in HELDOUT_SCENARIOS:
        cluster.clear_all_faults()
        res = runner.execute_scenario(sc)
        assert "incident_stats" in res
        assert res["incident_stats"]["total_requests"] > 0

def test_rcai_investigates_held_out_scenarios(cluster):
    runner = ScenarioRunner(cluster)
    tools = create_default_investigation_tools(cluster)
    investigator = ActiveInvestigator(tool_registry=tools, max_tool_calls=10)
    verifier = RootCauseVerifier()

    for sc in HELDOUT_SCENARIOS:
        cluster.clear_all_faults()
        runner.execute_scenario(sc)

        inc = Incident(
            scenario_id=sc.scenario_id,
            service=sc.service,
            symptom=sc.symptom_description,
            severity=sc.severity,
            ground_truth=sc.ground_truth
        )
        agent_view = inc.to_agent_view()
        state = investigator.run_investigation(agent_view)
        assert state.is_completed
        assert state.current_step > 0

        report = verifier.generate_incident_report(state)
        assert report is not None
        assert report.root_cause_decision is not None
