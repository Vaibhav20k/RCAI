# Baseline A: Static Rule-Based Incident Classifier
import time
from typing import Dict, Any, Optional
from backend.incidents.models import AgentIncidentView
from agent.verification.models import RootCauseDecision
from agent.hypothesis.models import HypothesisCategory

class StaticRulesBaseline:
    name: str = "Baseline_A_StaticRules"

    def diagnose(self, incident: AgentIncidentView, telemetry_summary: Optional[Dict[str, Any]] = None) -> RootCauseDecision:
        t0 = time.perf_counter()
        symptom = incident.symptom.lower()
        service = incident.service
        
        # Hard-coded rule heuristics
        if "error rate" in symptom or "500" in symptom:
            cat = HypothesisCategory.DEPLOYMENT
            desc = f"Static rule triggered: high error rate on {service} mapped to bad deployment"
            conf = 0.60
        elif "latency" in symptom and service == "order-service":
            cat = HypothesisCategory.DATABASE
            desc = f"Static rule triggered: latency on order-service mapped to DB slow queries"
            conf = 0.55
        elif "bank" in symptom or service == "dependency-service":
            cat = HypothesisCategory.DEPENDENCY
            desc = "Static rule triggered: partner bank dependency degradation"
            conf = 0.50
        elif "cpu" in symptom or service == "api-gateway":
            cat = HypothesisCategory.RESOURCE
            desc = "Static rule triggered: API gateway resource saturation"
            conf = 0.50
        elif "queue" in symptom or service == "worker-service":
            cat = HypothesisCategory.QUEUE
            desc = "Static rule triggered: worker queue backlog"
            conf = 0.50
        else:
            cat = HypothesisCategory.UNKNOWN
            desc = "Static rule: No rule match"
            conf = 0.10

        return RootCauseDecision(
            decision_id=f"dec_rule_{int(time.time()*1000)}",
            incident_id=incident.incident_id,
            root_cause_service=service,
            root_cause_category=cat,
            description=desc,
            confidence=conf,
            supporting_evidence_ids=[],
            is_unknown=(cat == HypothesisCategory.UNKNOWN)
        )
