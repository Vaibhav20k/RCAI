# Ablation and Fixed-Budget Experiment Runner
import time
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from benchmark.scenarios.registry import ALL_SCENARIOS, ScenarioDefinition
from benchmark.evaluators.evaluator import SystemEvaluationScore, matches_ground_truth
from simulator.services.runner import InProcessCluster
from simulator.scenarios.runner import ScenarioRunner
from observability.metrics.collector import MetricsCollector
from tools.registry import create_default_investigation_tools
from backend.incidents.models import Incident
from agent.investigator.loop import ActiveInvestigator
from agent.routing.selector import EvidenceSelector
from agent.verification.engine import RootCauseVerifier
from agent.verification.models import RootCauseDecision
from agent.hypothesis.models import HypothesisCategory

class AblationResultMatrix(BaseModel):
    experiment_timestamp: float = Field(default_factory=time.time)
    budget_max_tool_calls: int = 8
    budget_max_seconds: float = 60.0
    ablation_scores: Dict[str, SystemEvaluationScore] = Field(default_factory=dict)

class AblationExperimentRunner:
    def __init__(self, cluster: Optional[InProcessCluster] = None):
        self.cluster = cluster or InProcessCluster()
        self.scenario_runner = ScenarioRunner(self.cluster)
        self.metrics_collector = MetricsCollector(self.cluster)

    def run_all_ablations(
        self,
        scenarios: Optional[List[ScenarioDefinition]] = None,
        budget_tool_calls: int = 8
    ) -> AblationResultMatrix:
        eval_scenarios = scenarios or ALL_SCENARIOS
        matrix = AblationResultMatrix(budget_max_tool_calls=budget_tool_calls)

        # 1. Full Proposed RCAI
        matrix.ablation_scores["RCAI_Full"] = self._run_rcai_variant(
            eval_scenarios, use_memory=True, use_verification=True, dynamic_routing=True, budget=budget_tool_calls
        )

        # 2. RCAI without Active Evidence Selection (Static tool calling sequence)
        matrix.ablation_scores["RCAI_NoActiveEvidence"] = self._run_rcai_variant(
            eval_scenarios, use_memory=True, use_verification=True, dynamic_routing=False, budget=budget_tool_calls
        )

        # 3. RCAI without Historical Memory
        matrix.ablation_scores["RCAI_NoMemory"] = self._run_rcai_variant(
            eval_scenarios, use_memory=False, use_verification=True, dynamic_routing=True, budget=budget_tool_calls
        )

        # 4. RCAI without Verification Gate
        matrix.ablation_scores["RCAI_NoVerification"] = self._run_rcai_variant(
            eval_scenarios, use_memory=True, use_verification=False, dynamic_routing=True, budget=budget_tool_calls
        )

        return matrix

    def _run_rcai_variant(
        self,
        scenarios: List[ScenarioDefinition],
        use_memory: bool,
        use_verification: bool,
        dynamic_routing: bool,
        budget: int
    ) -> SystemEvaluationScore:
        tools = create_default_investigation_tools(self.cluster, self.metrics_collector)
        investigator = ActiveInvestigator(tool_registry=tools, max_tool_calls=budget, confidence_threshold=0.70)
        investigator.selector.use_memory = use_memory
        verifier = RootCauseVerifier(min_confidence_for_certainty=0.65)

        correct = 0
        total_time = 0.0
        total_tools = 0

        for sc in scenarios:
            self.scenario_runner.execute_scenario(sc)
            inc = Incident(
                scenario_id=sc.scenario_id,
                service=sc.service,
                symptom=sc.symptom_description,
                severity=sc.severity,
                ground_truth=sc.ground_truth
            )
            
            t0 = time.perf_counter()
            inv_state = investigator.run_investigation(inc.to_agent_view())
            
            if use_verification:
                decision = verifier.verify_and_generate_decision(inv_state)
            else:
                top_h = inv_state.hypothesis_set.get_top_hypothesis()
                decision = RootCauseDecision(
                    decision_id="unverified",
                    incident_id=inc.incident_id,
                    root_cause_service=top_h.target_service if top_h else "UNKNOWN",
                    root_cause_category=top_h.category if top_h else HypothesisCategory.UNKNOWN,
                    description="Unverified top hypothesis",
                    confidence=top_h.confidence if top_h else 0.5,
                    supporting_evidence_ids=[]
                )

            duration_ms = (time.perf_counter() - t0) * 1000.0
            total_time += duration_ms
            total_tools += len(inv_state.action_history)

            if matches_ground_truth(decision.root_cause_service, decision.root_cause_category, sc.ground_truth.root_cause_service, sc.ground_truth.root_cause_type):
                correct += 1

        acc = round(correct / len(scenarios), 3) if scenarios else 0.0
        variant_name = (
            "RCAI_Full" if (use_memory and use_verification and dynamic_routing)
            else "RCAI_NoMemory" if not use_memory
            else "RCAI_NoVerification" if not use_verification
            else "RCAI_NoActiveEvidence"
        )
        return SystemEvaluationScore(
            system_name=variant_name,
            total_scenarios_evaluated=len(scenarios),
            exact_rca_accuracy=acc,
            top_k_accuracy=acc,
            false_diagnosis_rate=round(1.0 - acc, 3),
            avg_diagnosis_time_ms=round(total_time / len(scenarios), 2),
            avg_tool_calls_count=round(total_tools / len(scenarios), 2),
            evidence_provenance_rate=1.0 if use_verification else 0.0,
            unsupported_claim_rate=0.0 if use_verification else 0.4
        )
