import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
# Run Scientific Benchmark and Ablations CLI Tool
from simulator.services.runner import InProcessCluster
from benchmark.evaluators.evaluator import BenchmarkRunner
from benchmark.evaluators.ablation import AblationExperimentRunner
from benchmark.scenarios.registry import ALL_SCENARIOS

def main():
    print("Running RCAI Benchmark across 5 Reproducible Microservice Scenarios...")
    cluster = InProcessCluster()
    bench = BenchmarkRunner(cluster)
    results = bench.evaluate_all_systems(ALL_SCENARIOS)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPARISON MATRIX")
    print("=" * 80)
    print(f"{"Method":<25} | {"Exact RCA Acc":<14} | {"False Diag":<10} | {"Avg Tools":<10} | {"Prov Rate":<10}")
    print("-" * 80)
    for name, s in results.items():
        print(f"{s.system_name:<25} | {s.exact_rca_accuracy*100:>12.1f}% | {s.false_diagnosis_rate*100:>8.1f}% | {s.avg_tool_calls_count:>9.1f} | {s.evidence_provenance_rate*100:>8.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()
