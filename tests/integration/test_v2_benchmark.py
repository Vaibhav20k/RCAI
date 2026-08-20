# Integration Tests for RCAI v2 Unified Benchmark Suite
import pytest
from simulator.services.runner import InProcessCluster
from benchmark.scenarios.registry import ALL_SCENARIOS
from benchmark.evaluators.evaluator import BenchmarkRunner

def test_unified_benchmark_evaluates_all_systems():
    cluster = InProcessCluster()
    runner = BenchmarkRunner(cluster)
    
    # Evaluate a 3-scenario subset across all baselines
    results = runner.evaluate_all_systems(scenarios=ALL_SCENARIOS[:3])
    
    assert "Baseline_A_Rules" in results
    assert "Baseline_B_OneShot" in results
    assert "Baseline_C_RAG" in results
    assert "Proposed_Active_RCAI" in results
    
    rcai = results["Proposed_Active_RCAI"]
    assert rcai.exact_rca_accuracy >= 0.60
    assert rcai.evidence_provenance_rate == 1.0
    assert rcai.unsupported_claim_rate == 0.0
