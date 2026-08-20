# Stress Tests for Multi-Seed Statistical Stability
import pytest
from simulator.services.runner import InProcessCluster
from benchmark.scenarios.registry import ALL_SCENARIOS
from benchmark.evaluators.multi_seed import MultiSeedStressEvaluator

def test_multi_seed_evaluation_stability():
    cluster = InProcessCluster()
    evaluator = MultiSeedStressEvaluator(cluster)
    
    # Test across multiple random seeds on benchmark subset
    test_scenarios = ALL_SCENARIOS[:3]
    summary = evaluator.run_multi_seed_evaluation(
        scenarios=test_scenarios,
        seeds=[42, 101, 2024],
        budget_tool_calls=8
    )
    
    assert summary.total_runs == 9
    assert summary.mean_accuracy >= 0.90
    assert summary.std_dev_accuracy <= 0.15
    assert summary.mean_tool_calls > 0.0
