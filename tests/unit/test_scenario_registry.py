# Unit Tests for Scenario Definitions and Registry
import pytest
from benchmark.scenarios.registry import ALL_SCENARIOS, get_scenario

def test_all_five_scenarios_registered():
    assert len(ALL_SCENARIOS) >= 5
    scenario_ids = [s.scenario_id for s in ALL_SCENARIOS]
    
    expected = [
        "scenario_db_regression_order",
        "scenario_bad_deploy_payment",
        "scenario_dependency_latency_bank",
        "scenario_resource_saturation_gateway",
        "scenario_queue_backlog_worker",
    ]
    for exp_id in expected:
        assert exp_id in scenario_ids
        scen = get_scenario(exp_id)
        assert scen is not None
        assert scen.ground_truth.root_cause_service is not None
        assert scen.ground_truth.expected_remediation is not None
