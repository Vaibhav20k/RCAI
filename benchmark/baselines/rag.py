# Baseline C: RAG / Retrieved Context LLM Diagnoser
import time
from typing import Dict, Any, Optional
from backend.incidents.models import AgentIncidentView
from agent.verification.models import RootCauseDecision
from agent.hypothesis.models import HypothesisCategory
from agent.memory.store import HistoricalMemoryStore, global_memory_store

class RAGLLMBaseline:
    name: str = "Baseline_C_RAG"

    def __init__(self, memory_store: Optional[HistoricalMemoryStore] = None):
        self.memory_store = memory_store or global_memory_store

    def diagnose(self, incident: AgentIncidentView) -> RootCauseDecision:
        similar = self.memory_store.query_similar_experiences(incident.service, incident.symptom, limit=2)
        if similar:
            best_match = similar[0]
            cat_map = {
                "deployment": HypothesisCategory.DEPLOYMENT,
                "database": HypothesisCategory.DATABASE,
                "dependency": HypothesisCategory.DEPENDENCY,
                "resource": HypothesisCategory.RESOURCE,
                "queue": HypothesisCategory.QUEUE,
            }
            cat = cat_map.get(best_match.root_cause_category.lower(), HypothesisCategory.UNKNOWN)
            return RootCauseDecision(
                decision_id=f"dec_rag_{int(time.time()*1000)}",
                incident_id=incident.incident_id,
                root_cause_service=best_match.root_cause_service,
                root_cause_category=cat,
                description=f"RAG retrieved prior incident {best_match.incident_id}: {best_match.symptom}",
                confidence=0.72,
                supporting_evidence_ids=[],
                is_unknown=False
            )

        return RootCauseDecision(
            decision_id=f"dec_rag_fallback_{int(time.time()*1000)}",
            incident_id=incident.incident_id,
            root_cause_service=incident.service,
            root_cause_category=HypothesisCategory.UNKNOWN,
            description="RAG: No relevant historical incidents found in index",
            confidence=0.20,
            is_unknown=True
        )
