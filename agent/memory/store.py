# Historical Incident Experience Store and Strategy Router
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from agent.memory.models import HistoricalIncidentExperience

class HistoricalMemoryStore:
    def __init__(self):
        self._experiences: List[HistoricalIncidentExperience] = []
        self._seed_initial_experience()

    def _seed_initial_experience(self) -> None:
        # Seed realistic prior investigation trajectories
        self._experiences.append(
            HistoricalIncidentExperience(
                experience_id="exp_seed_01",
                incident_id="inc_prior_01",
                scenario_id="scenario_bad_deploy_payment",
                service="payment-service",
                symptom="Payment service 100% error rate",
                root_cause_service="payment-service",
                root_cause_category="deployment",
                successful_tool_sequence=["inspect_deployment_history", "compare_versions", "inspect_service_health"],
                failed_tool_sequence=["query_db_metrics"],
                successful_remediation_action="rollback_version",
                time_to_diagnosis_ms=180.0,
                tool_calls_count=3,
                resolution_status="RESOLVED"
            )
        )
        self._experiences.append(
            HistoricalIncidentExperience(
                experience_id="exp_seed_02",
                incident_id="inc_prior_02",
                scenario_id="scenario_db_regression_order",
                service="order-service",
                symptom="Order service latency regression",
                root_cause_service="order-service",
                root_cause_category="database",
                successful_tool_sequence=["query_db_metrics", "query_metrics"],
                failed_tool_sequence=["inspect_dependency_health"],
                successful_remediation_action="optimize_db_index",
                time_to_diagnosis_ms=120.0,
                tool_calls_count=2,
                resolution_status="RESOLVED"
            )
        )

    def record_experience(self, exp: HistoricalIncidentExperience) -> None:
        self._experiences.append(exp)

    def query_similar_experiences(self, service: str, symptom: str, limit: int = 3) -> List[HistoricalIncidentExperience]:
        matches: List[Tuple[float, HistoricalIncidentExperience]] = []
        symptom_words = set(symptom.lower().split())

        for exp in self._experiences:
            score = 0.0
            if exp.service == service:
                score += 0.6
            exp_words = set(exp.symptom.lower().split())
            overlap = len(symptom_words.intersection(exp_words))
            score += min(0.4, overlap * 0.1)
            
            if score > 0.3:
                matches.append((score, exp))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:limit]]

    def get_recommended_actions(self, service: str, symptom: str) -> List[str]:
        similar = self.query_similar_experiences(service, symptom)
        if not similar:
            return []
        
        recommended: List[str] = []
        for exp in similar:
            for tool in exp.successful_tool_sequence:
                if tool not in recommended:
                    recommended.append(tool)
        return recommended

global_memory_store = HistoricalMemoryStore()
