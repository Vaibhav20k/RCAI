# Integration Tests for Benchmark Harness and Baselines
import pytest
from simulator.services.runner import InProcessCluster
from benchmark.evaluators.evaluator import BenchmarkRunner, SystemEvaluationScore
from benchmark.scenarios.registry import SCENARIO_BAD_DEPLOY_PAYMENT, SCENARIO_DB_REGRESSION_ORDER

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_benchmark_runner_evaluates_all_baselines(cluster):
    runner = BenchmarkRunner(cluster)
    scenarios = [SCENARIO_BAD_DEPLOY_PAYMENT, SCENARIO_DB_REGRESSION_ORDER]
    
    results = runner.evaluate_all_systems(scenarios=scenarios)
    
    assert "Baseline_A_Rules" in results
    assert "Baseline_B_OneShot" in results
    assert "Baseline_C_RAG" in results
    assert "Proposed_Active_RCAI" in results

    rcai_score = results["Proposed_Active_RCAI"]
    assert isinstance(rcai_score, SystemEvaluationScore)
    assert rcai_score.exact_rca_accuracy >= 0.50
    assert rcai_score.evidence_provenance_rate == 1.0
    assert rcai_score.unsupported_claim_rate == 0.0
