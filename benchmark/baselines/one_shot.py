# Baseline B: One-Shot LLM Diagnoser with Pluggable Backend Support
import time
from typing import Dict, Any, Optional
from backend.incidents.models import AgentIncidentView
from agent.verification.models import RootCauseDecision
from agent.hypothesis.models import HypothesisCategory
from agent.llm.models import RootCauseDiagnosisSchema
from agent.llm.interface import BaseLLMBackend, llm_infer
from backend.config import get_settings

class OneShotLLMBaseline:
    name: str = "Baseline_B_OneShotLLM"

    def __init__(self, llm_backend: Optional[BaseLLMBackend] = None):
        self.llm_backend = llm_backend

    def diagnose(self, incident: AgentIncidentView) -> RootCauseDecision:
        t0 = time.perf_counter()

        if self.llm_backend:
            prompt = (
                f"Incident Context for One-Shot Diagnosis:\n"
                f"- Service: {incident.service}\n"
                f"- Symptom: {incident.symptom}\n"
                f"- Severity: {incident.severity.value}\n\n"
                f"Identify the likely root-cause faulty service, failure category, and confidence score based on the reported symptom alone."
            )
            result = llm_infer(
                prompt=prompt,
                schema=RootCauseDiagnosisSchema,
                system_prompt="You are an SRE AI diagnosing incident root causes in a microservice architecture in one shot.",
                backend=self.llm_backend
            )

            if result.is_valid and result.parsed_data and isinstance(result.parsed_data, RootCauseDiagnosisSchema):
                parsed = result.parsed_data
                return RootCauseDecision(
                    decision_id=f"dec_oneshot_{int(time.time()*1000)}",
                    incident_id=incident.incident_id,
                    root_cause_service=parsed.root_cause_service or incident.service,
                    root_cause_category=parsed.root_cause_category,
                    description=parsed.description or f"One-shot prompt inference ({result.backend_name}/{result.model_name}) on symptom: {incident.symptom}",
                    confidence=parsed.confidence,
                    supporting_evidence_ids=[],
                    is_unknown=False
                )

        # Baseline heuristic reasoning from prompt symptom alone without active tool calls
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
