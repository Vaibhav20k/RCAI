# Integration Tests for Seen vs Unseen Generalization Evaluator
import pytest
from simulator.services.runner import InProcessCluster
from benchmark.scenarios.registry import ALL_SCENARIOS
from benchmark.scenarios.held_out import HELDOUT_SCENARIOS
from benchmark.evaluators.generalization import GeneralizationEvaluator

def test_generalization_evaluator_runs_matrix():
    cluster = InProcessCluster()
    evaluator = GeneralizationEvaluator(cluster)
    
    matrix = evaluator.evaluate_generalization(
        seen_scenarios=ALL_SCENARIOS[:3],
        held_out_scenarios=HELDOUT_SCENARIOS[:3]
    )
    
    assert matrix.seen_development_performance.scenario_count == 3
    assert matrix.held_out_unseen_performance.scenario_count == 3
    assert matrix.seen_development_performance.provenance_rate == 1.0
    assert matrix.held_out_unseen_performance.provenance_rate == 1.0
    assert matrix.held_out_unseen_performance.unsupported_claim_rate == 0.0
    assert "DATABASE" in matrix.family_breakdown
