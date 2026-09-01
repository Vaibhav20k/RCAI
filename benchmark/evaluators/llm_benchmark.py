# Multi-Backend LLM Benchmark Evaluator (Local Ollama vs Hosted vs Rule-Based)
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from benchmark.scenarios.registry import ALL_SCENARIOS, ScenarioDefinition
from benchmark.evaluators.evaluator import matches_ground_truth, SystemEvaluationScore
from backend.incidents.models import Incident, IncidentSeverity, IncidentStatus, AgentIncidentView
from benchmark.baselines.rules import StaticRulesBaseline
from benchmark.baselines.one_shot import OneShotLLMBaseline
from agent.llm.interface import BaseLLMBackend
from agent.llm.backends.rule_based import RuleBasedLLMBackend
from agent.llm.backends.ollama import OllamaBackend
from agent.llm.backends.hosted import HostedLLMBackend
from simulator.services.runner import InProcessCluster
from tools.registry import create_default_investigation_tools
from agent.investigator.loop import ActiveInvestigator
from agent.verification.engine import RootCauseVerifier

class PartitionBenchmarkScore(BaseModel):
    partition_name: str
    scenario_count: int
    accuracy: float
    avg_latency_ms: float

class ModelBenchmarkReport(BaseModel):
    backend_type: str
    model_name: str
    overall_accuracy: float
    total_scenarios: int
    false_diagnosis_rate: float
    avg_latency_ms: float
    partition_scores: Dict[str, PartitionBenchmarkScore]

class LLMBenchmarkRunner:
    def __init__(self, cluster: Optional[InProcessCluster] = None):
        self.cluster = cluster or InProcessCluster()

    def _create_incident_for_scenario(self, scenario: ScenarioDefinition) -> Incident:
        now = time.time()
        return Incident(
            incident_id=f"inc_eval_{scenario.scenario_id}",
            scenario_id=scenario.scenario_id,
            started_at=now - 60,
            detected_at=now,
            severity=scenario.severity,
            service=scenario.service,
            symptom=scenario.symptom_description,
            status=IncidentStatus.DETECTED,
            incident_window={"start_ts": now - 300, "end_ts": now},
            ground_truth=scenario.ground_truth
        )

    def evaluate_model_backend(
        self,
        backend: BaseLLMBackend,
        scenarios: Optional[List[ScenarioDefinition]] = None
    ) -> ModelBenchmarkReport:
        eval_scenarios = scenarios or ALL_SCENARIOS
        baseline = OneShotLLMBaseline(llm_backend=backend)
        
        correct_by_partition: Dict[str, int] = {}
        total_by_partition: Dict[str, int] = {}
        latency_by_partition: Dict[str, float] = {}

        total_time = 0.0
        total_correct = 0

        for sc in eval_scenarios:
            # Determine partition from scenario_id
            partition = "general"
            if "comp" in sc.scenario_id or "compositional" in sc.scenario_id:
                partition = "compositional"
            elif "payment" in sc.scenario_id or "settlement" in sc.scenario_id or "ledger" in sc.scenario_id:
                partition = "payment"
            elif "adv" in sc.scenario_id or "adversarial" in sc.scenario_id or "misleading" in sc.scenario_id:
                partition = "adversarial"

            total_by_partition[partition] = total_by_partition.get(partition, 0) + 1

            inc = self._create_incident_for_scenario(sc)
            t0 = time.perf_counter()
            dec = baseline.diagnose(inc.to_agent_view())
            elapsed = (time.perf_counter() - t0) * 1000.0

            total_time += elapsed
            latency_by_partition[partition] = latency_by_partition.get(partition, 0.0) + elapsed

            is_correct = matches_ground_truth(
                dec.root_cause_service,
                dec.root_cause_category,
                sc.ground_truth.root_cause_service,
                sc.ground_truth.root_cause_type
            )
            if is_correct:
                total_correct += 1
                correct_by_partition[partition] = correct_by_partition.get(partition, 0) + 1

        overall_acc = round(total_correct / len(eval_scenarios), 3) if eval_scenarios else 0.0
        partition_reports: Dict[str, PartitionBenchmarkScore] = {}

        for p_name, count in total_by_partition.items():
            c_correct = correct_by_partition.get(p_name, 0)
            p_lat = latency_by_partition.get(p_name, 0.0)
            partition_reports[p_name] = PartitionBenchmarkScore(
                partition_name=p_name,
                scenario_count=count,
                accuracy=round(c_correct / count, 3) if count > 0 else 0.0,
                avg_latency_ms=round(p_lat / count, 2) if count > 0 else 0.0
            )

        return ModelBenchmarkReport(
            backend_type=backend.name,
            model_name=backend.model_name,
            overall_accuracy=overall_acc,
            total_scenarios=len(eval_scenarios),
            false_diagnosis_rate=round(1.0 - overall_acc, 3),
            avg_latency_ms=round(total_time / len(eval_scenarios), 2) if eval_scenarios else 0.0,
            partition_scores=partition_reports
        )

    def run_multi_backend_comparison(
        self,
        scenarios: Optional[List[ScenarioDefinition]] = None
    ) -> Dict[str, ModelBenchmarkReport]:
        eval_scenarios = scenarios or ALL_SCENARIOS
        reports: Dict[str, ModelBenchmarkReport] = {}

        # 1. Rule-Based Baseline
        reports["rule_based"] = self.evaluate_model_backend(
            RuleBasedLLMBackend(),
            eval_scenarios
        )

        # 2. Local Ollama - Small Model (~7B-8B class)
        ollama_small = OllamaBackend(model_name="llama3:8b")
        reports["ollama_small_8b"] = self.evaluate_model_backend(
            ollama_small,
            eval_scenarios
        )

        # 3. Local Ollama - Large / MoE Model (~30B-70B class)
        ollama_large = OllamaBackend(model_name="mixtral:8x7b")
        reports["ollama_large_moe"] = self.evaluate_model_backend(
            ollama_large,
            eval_scenarios
        )

        # 4. Hosted LLM Backend
        hosted_backend = HostedLLMBackend(model_name="gpt-4o")
        reports["hosted_gpt4o"] = self.evaluate_model_backend(
            hosted_backend,
            eval_scenarios
        )

        return reports
