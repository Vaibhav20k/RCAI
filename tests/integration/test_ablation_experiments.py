# Integration Tests for Ablation Experiments and Fixed Budget Benchmarking
import pytest
from simulator.services.runner import InProcessCluster
from benchmark.evaluators.ablation import AblationExperimentRunner, AblationResultMatrix
from benchmark.scenarios.registry import SCENARIO_BAD_DEPLOY_PAYMENT, SCENARIO_DB_REGRESSION_ORDER

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_ablation_experiment_runner_executes_matrix(cluster):
    runner = AblationExperimentRunner(cluster)
    scenarios = [SCENARIO_BAD_DEPLOY_PAYMENT, SCENARIO_DB_REGRESSION_ORDER]
    
    matrix = runner.run_all_ablations(scenarios=scenarios, budget_tool_calls=6)
    
    assert isinstance(matrix, AblationResultMatrix)
    assert "RCAI_Full" in matrix.ablation_scores
    assert "RCAI_NoMemory" in matrix.ablation_scores
    assert "RCAI_NoVerification" in matrix.ablation_scores
    assert "RCAI_NoActiveEvidence" in matrix.ablation_scores

    full_score = matrix.ablation_scores["RCAI_Full"]
    noverif_score = matrix.ablation_scores["RCAI_NoVerification"]

    assert full_score.evidence_provenance_rate == 1.0
    assert noverif_score.evidence_provenance_rate == 0.0
    assert noverif_score.unsupported_claim_rate > 0.0
