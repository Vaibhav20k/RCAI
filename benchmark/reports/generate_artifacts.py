# Research Artifacts and LaTeX Table Generator
import json
import pathlib
from typing import Dict, Any
from simulator.services.runner import InProcessCluster
from benchmark.evaluators.evaluator import BenchmarkRunner
from benchmark.evaluators.ablation import AblationExperimentRunner
from benchmark.scenarios.registry import ALL_SCENARIOS

def generate_all_research_artifacts(output_dir: str = "docs/results") -> Dict[str, str]:
    out_path = pathlib.Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    cluster = InProcessCluster()
    bench_runner = BenchmarkRunner(cluster)
    ablation_runner = AblationExperimentRunner(cluster)
    bench_results = bench_runner.evaluate_all_systems(ALL_SCENARIOS)
    ablation_results = ablation_runner.run_all_ablations(ALL_SCENARIOS, budget_tool_calls=8)
    bench_data = {k: v.model_dump() for k, v in bench_results.items()}
    bench_json_path = out_path / "benchmark_comparison.json"
    bench_json_path.write_text(json.dumps(bench_data, indent=2), encoding="utf-8")
    ablation_data = {k: v.model_dump() for k, v in ablation_results.ablation_scores.items()}
    ablation_json_path = out_path / "ablation_table.json"
    ablation_json_path.write_text(json.dumps(ablation_data, indent=2), encoding="utf-8")

    table1_lines = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\small",
        "\\caption{Root-Cause Localization and Evidence Grounding across Microservice Incident Scenarios.}",
        "\\label{tab:benchmark_comparison}",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
        "\\textbf{Method} & \\textbf{Exact RCA Acc. (\\%)} & \\textbf{False Diagnosis (\\%)} & \\textbf{Avg. Tools} & \\textbf{Time (ms)} & \\textbf{Prov. Rate (\\%)} & \\textbf{Unsup. Claims (\\%)} \\\\",
        "\\midrule"
    ]
    for name, s in bench_results.items():
        clean_name = s.system_name.replace("_", " ")
        table1_lines.append(f"{clean_name} & {s.exact_rca_accuracy*100:.1f} & {s.false_diagnosis_rate*100:.1f} & {s.avg_tool_calls_count:.1f} & {s.avg_diagnosis_time_ms:.1f} & {s.evidence_provenance_rate*100:.1f} & {s.unsupported_claim_rate*100:.1f} \\\\")
    table1_lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}"])
    table1_path = out_path / "table1_latex.tex"
    table1_path.write_text("\n".join(table1_lines) + "\n", encoding="utf-8")

    table2_lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{Ablation Study of Autonomous Investigator Components under Equal Budget (8 Tool Calls).}",
        "\\label{tab:ablation_results}",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        "\\textbf{Ablation Variant} & \\textbf{Exact Acc. (\\%)} & \\textbf{False Diag. (\\%)} & \\textbf{Prov. (\\%)} & \\textbf{Unsup. (\\%)} \\\\",
        "\\midrule"
    ]
    for name, s in ablation_results.ablation_scores.items():
        clean_name = s.system_name.replace("_", " ")
        table2_lines.append(f"{clean_name} & {s.exact_rca_accuracy*100:.1f} & {s.false_diagnosis_rate*100:.1f} & {s.evidence_provenance_rate*100:.1f} & {s.unsupported_claim_rate*100:.1f} \\\\")
    table2_lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    table2_path = out_path / "table2_latex.tex"
    table2_path.write_text("\n".join(table2_lines) + "\n", encoding="utf-8")

    return {
        "benchmark_json": str(bench_json_path),
        "ablation_json": str(ablation_json_path),
        "table1_tex": str(table1_path),
        "table2_tex": str(table2_path)
    }

if __name__ == "__main__":
    generate_all_research_artifacts()
