# Multi-Seed Benchmark Evaluation & Statistical Stress Harness
import time
import statistics
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from benchmark.scenarios.registry import ALL_SCENARIOS, ScenarioDefinition
from simulator.services.runner import InProcessCluster
from simulator.scenarios.runner import ScenarioRunner
from simulator.traffic.generator import TrafficGenerator
from tools.registry import create_default_investigation_tools
from backend.incidents.models import Incident
from agent.investigator.loop import ActiveInvestigator
from agent.verification.engine import RootCauseVerifier
from benchmark.evaluators.evaluator import matches_ground_truth

class SeedEvaluationMetric(BaseModel):
    seed: int
    scenarios_evaluated: int
    exact_rca_accuracy: float
    avg_tool_calls: float
    avg_duration_ms: float

class MultiSeedStatisticalSummary(BaseModel):
    seeds_evaluated: List[int]
    total_runs: int
    mean_accuracy: float
    median_accuracy: float
    std_dev_accuracy: float
    min_accuracy: float
    max_accuracy: float
    mean_tool_calls: float
    std_dev_tool_calls: float

class MultiSeedStressEvaluator:
    def __init__(self, cluster: Optional[InProcessCluster] = None):
        self.cluster = cluster or InProcessCluster()

    def run_multi_seed_evaluation(
        self,
        scenarios: List[ScenarioDefinition],
        seeds: List[int] = [42, 101, 2024, 777],
        budget_tool_calls: int = 10
    ) -> MultiSeedStatisticalSummary:
        seed_results: List[SeedEvaluationMetric] = []
        tools = create_default_investigation_tools(self.cluster)
        verifier = RootCauseVerifier()

        accuracies: List[float] = []
        tool_counts: List[float] = []

        for seed in seeds:
            correct_count = 0
            total_tools = 0
            durations: List[float] = []

            for sc in scenarios:
                self.cluster.clear_all_faults()
                gen = TrafficGenerator(client=self.cluster.gateway_client, seed=seed)
                # Apply fault
                target = self.cluster.get_service_map().get(sc.fault_config.service_name)
                if target:
                    target.fault_injector.set_fault(sc.fault_config)

                gen.generate_batch(count=sc.incident_traffic_count)

                inc = Incident(
                    scenario_id=sc.scenario_id,
                    service=sc.service,
                    symptom=sc.symptom_description,
                    severity=sc.severity,
                    ground_truth=sc.ground_truth
                )
                investigator = ActiveInvestigator(tool_registry=tools, max_tool_calls=budget_tool_calls)
                state = investigator.run_investigation(inc.to_agent_view())
                report = verifier.generate_incident_report(state)

                dec = report.root_cause_decision
                is_match = matches_ground_truth(
                    dec.root_cause_service,
                    dec.root_cause_category,
                    sc.ground_truth.root_cause_service,
                    sc.ground_truth.root_cause_type
                )
                if is_match and not dec.is_unknown:
                    correct_count += 1
                total_tools += state.current_step

            acc = correct_count / len(scenarios) if scenarios else 0.0
            avg_tools = total_tools / len(scenarios) if scenarios else 0.0
            accuracies.append(acc)
            tool_counts.append(avg_tools)

        mean_acc = statistics.mean(accuracies) if accuracies else 0.0
        med_acc = statistics.median(accuracies) if accuracies else 0.0
        std_acc = statistics.stdev(accuracies) if len(accuracies) > 1 else 0.0
        min_acc = min(accuracies) if accuracies else 0.0
        max_acc = max(accuracies) if accuracies else 0.0

        mean_tc = statistics.mean(tool_counts) if tool_counts else 0.0
        std_tc = statistics.stdev(tool_counts) if len(tool_counts) > 1 else 0.0

        return MultiSeedStatisticalSummary(
            seeds_evaluated=seeds,
            total_runs=len(seeds) * len(scenarios),
            mean_accuracy=round(mean_acc, 4),
            median_accuracy=round(med_acc, 4),
            std_dev_accuracy=round(std_acc, 4),
            min_accuracy=round(min_acc, 4),
            max_accuracy=round(max_acc, 4),
            mean_tool_calls=round(mean_tc, 2),
            std_dev_tool_calls=round(std_tc, 2)
        )
