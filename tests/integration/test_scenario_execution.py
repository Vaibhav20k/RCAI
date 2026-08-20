# Integration Tests for Scenario Execution and Isolation
import pytest
from simulator.services.runner import InProcessCluster
from simulator.scenarios.runner import ScenarioRunner
from benchmark.scenarios.registry import ALL_SCENARIOS
from backend.incidents.detector import IncidentDetector
from observability.metrics.collector import MetricsCollector

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_all_scenarios_execute_reproducibly(cluster):
    runner = ScenarioRunner(cluster)
    metrics_collector = MetricsCollector(cluster)
    detector = IncidentDetector(metrics_collector)

    for scenario in ALL_SCENARIOS:
        res = runner.execute_scenario(scenario)
        assert res["scenario_id"] == scenario.scenario_id
        assert res["ground_truth"]["root_cause_service"] == scenario.service
        
        # Detector identifies incident
        incidents = detector.detect_incidents_from_metrics(
            scenario_id=scenario.scenario_id,
            known_ground_truth=scenario.ground_truth
        )
        assert len(incidents) > 0
        
        # Verify Agent view contains zero ground truth
        agent_view = incidents[0].to_agent_view()
        assert not hasattr(agent_view, "ground_truth")
        assert "ground_truth" not in agent_view.model_dump()
        assert agent_view.scenario_id == scenario.scenario_id
