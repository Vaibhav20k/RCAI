# Run Scientific Benchmark, Ablations, and Generalization CLI Tool - RCAI v2 Frozen
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from simulator.services.runner import InProcessCluster
from benchmark.evaluators.evaluator import BenchmarkRunner
from benchmark.evaluators.generalization import GeneralizationEvaluator
from benchmark.evaluators.multi_seed import MultiSeedStressEvaluator
from benchmark.scenarios.registry import ALL_SCENARIOS
from benchmark.scenarios.held_out import HELDOUT_SCENARIOS
from benchmark.scenarios.payment import PAYMENT_SCENARIOS
from benchmark.scenarios.adversarial import ADVERSARIAL_SCENARIOS

def main():
    total_count = len(ALL_SCENARIOS) + len(HELDOUT_SCENARIOS) + len(PAYMENT_SCENARIOS) + len(ADVERSARIAL_SCENARIOS)
    print("=" * 80)
    print("RCAI v2 Comprehensive Scientific Evaluation Suite (FROZEN MANIFEST)")
    print(f"Total Scenarios: {len(ALL_SCENARIOS)} General + {len(HELDOUT_SCENARIOS)} Held-Out + {len(PAYMENT_SCENARIOS)} Payment + {len(ADVERSARIAL_SCENARIOS)} Adversarial = {total_count} Total")
    print("=" * 80)

    cluster = InProcessCluster()

    # 1. Main System Benchmark Matrix (General Microservice Scenarios)
    bench = BenchmarkRunner(cluster)
    results = bench.evaluate_all_systems(ALL_SCENARIOS)

    print("\n" + "=" * 80)
    print("1. BENCHMARK COMPARISON MATRIX (25 General Microservice Scenarios)")
    print("=" * 80)
    print("{:<25} | {:<14} | {:<10} | {:<10} | {:<10}".format("Method", "Exact RCA Acc", "False Diag", "Avg Tools", "Prov Rate"))
    print("-" * 80)
    for name, s in results.items():
        print("{:<25} | {:>12.1f}% | {:>8.1f}% | {:>9.1f} | {:>8.1f}%".format(s.system_name, s.exact_rca_accuracy*100, s.false_diagnosis_rate*100, s.avg_tool_calls_count, s.evidence_provenance_rate*100))
    print("=" * 80)

    # 2. Seen vs Unseen Generalization Matrix
    gen_eval = GeneralizationEvaluator(cluster)
    gen_matrix = gen_eval.evaluate_generalization(
        seen_scenarios=ALL_SCENARIOS,
        held_out_scenarios=HELDOUT_SCENARIOS,
        payment_scenarios=PAYMENT_SCENARIOS
    )
    print("\n" + "=" * 80)
    print("2. SEEN VS UNSEEN GENERALIZATION MATRIX")
    print("=" * 80)
    print("{:<25} | {:<6} | {:<10} | {:<10} | {:<10}".format("Split / Domain", "Count", "Exact Acc", "Avg Tools", "Provenance"))
    print("-" * 80)
    for perf in [gen_matrix.seen_development_performance, gen_matrix.held_out_unseen_performance, gen_matrix.payment_domain_performance]:
        print("{:<25} | {:>5}  | {:>8.1f}% | {:>9.1f} | {:>8.1f}%".format(perf.split_name, perf.scenario_count, perf.exact_rca_accuracy*100, perf.avg_tool_calls, perf.provenance_rate*100))
    print("=" * 80)

    # 3. Multi-Seed Stress Stability
    multi_seed_eval = MultiSeedStressEvaluator(cluster)
    seed_summary = multi_seed_eval.run_multi_seed_evaluation(
        scenarios=ALL_SCENARIOS[:5],
        seeds=[42, 101, 2024],
        budget_tool_calls=8
    )
    print("\n" + "=" * 80)
    print("3. MULTI-SEED STATISTICAL STRESS EVALUATION (Seeds 42, 101, 2024)")
    print("=" * 80)
    print(f"Total Runs: {seed_summary.total_runs}")
    print(f"Mean RCA Accuracy: {seed_summary.mean_accuracy*100:.1f}% (Std Dev: {seed_summary.std_dev_accuracy:.3f})")
    print(f"Mean Tool Calls: {seed_summary.mean_tool_calls:.1f} (Std Dev: {seed_summary.std_dev_tool_calls:.2f})")
    print("=" * 80)

if __name__ == "__main__":
    main()
