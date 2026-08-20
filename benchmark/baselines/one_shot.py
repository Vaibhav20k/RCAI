# Baseline B: One-Shot LLM Diagnoser
import time
from typing import Dict, Any, Optional
from backend.incidents.models import AgentIncidentView
from agent.verification.models import RootCauseDecision
from agent.hypothesis.models import HypothesisCategory

class OneShotLLMBaseline:
    name: str = "Baseline_B_OneShotLLM"

    def diagnose(self, incident: AgentIncidentView) -> RootCauseDecision:
        t0 = time.perf_counter()
        # Simulated one-shot LLM reasoning from prompt symptom alone without active tool calls
        symptom = incident.symptom.lower()
        service = incident.service

        if "error rate" in symptom:
            cat = HypothesisCategory.DEPLOYMENT
            conf = 0.65
        elif "latency" in symptom:
            cat = HypothesisCategory.DATABASE if service == "order-service" else HypothesisCategory.DEPENDENCY
            conf = 0.60
        elif "queue" in symptom:
            cat = HypothesisCategory.QUEUE
            conf = 0.60
        else:
            cat = HypothesisCategory.RESOURCE
            conf = 0.50

        return RootCauseDecision(
            decision_id=f"dec_oneshot_{int(time.time()*1000)}",
            incident_id=incident.incident_id,
            root_cause_service=service,
            root_cause_category=cat,
            description=f"One-shot prompt inference on symptom: {incident.symptom}",
            confidence=conf,
            supporting_evidence_ids=[],
            is_unknown=False
        )
