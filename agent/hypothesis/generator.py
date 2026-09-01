# Incident Hypothesis Generator with Pluggable LLM Inference Support
from typing import List, Optional
from backend.incidents.models import AgentIncidentView
from agent.hypothesis.models import Hypothesis, HypothesisCategory, HypothesisSet
from observability.models import NormalizedEvidence
from agent.llm.models import HypothesisGenerationResponseSchema
from agent.llm.interface import BaseLLMBackend, llm_infer
from backend.config import get_settings

class HypothesisGenerator:
    @staticmethod
    def generate_candidate_hypotheses(
        incident: AgentIncidentView,
        evidence: Optional[List[NormalizedEvidence]] = None,
        llm_backend: Optional[BaseLLMBackend] = None
    ) -> HypothesisSet:
        settings = get_settings()
        use_llm = llm_backend is not None or settings.LLM_BACKEND in ["ollama", "hosted"] or settings.is_live_mode()

        if use_llm:
            evidence_summary = ""
            if evidence:
                evidence_summary = "\nObserved Live Telemetry Evidence:\n" + "\n".join([f"- {e.summary}" for e in evidence[:5]])

            prompt = (
                f"Incident Investigation Context:\n"
                f"- Incident ID: {incident.incident_id}\n"
                f"- Affected Service: {incident.service}\n"
                f"- Reported Symptom: {incident.symptom}\n"
                f"- Severity: {incident.severity.value}\n"
                f"{evidence_summary}\n\n"
                f"Generate a set of competing, distinct root cause hypotheses with initial confidence scores and recommended next diagnostic actions."
            )

            result = llm_infer(
                prompt=prompt,
                schema=HypothesisGenerationResponseSchema,
                system_prompt="You are an autonomous SRE root-cause investigator. Generate plausible, competing microservice failure hypotheses.",
                backend=llm_backend
            )

            if result.is_valid and result.parsed_data and isinstance(result.parsed_data, HypothesisGenerationResponseSchema):
                hypo_set = HypothesisSet(incident_id=incident.incident_id)
                for item in result.parsed_data.hypotheses:
                    h = Hypothesis(
                        incident_id=incident.incident_id,
                        target_service=item.target_service or incident.service,
                        category=item.category,
                        description=item.description,
                        confidence=item.confidence,
                        next_action=item.next_action
                    )
                    hypo_set.add_hypothesis(h)

                if len(hypo_set.hypotheses) > 0:
                    return hypo_set

        # Fallback / Deterministic Default Candidate Hypotheses (Regression Harness Scaffolding)
        hypo_set = HypothesisSet(incident_id=incident.incident_id)
        target_service = incident.service
        
        # 1. Database Regression Hypothesis
        h_db = Hypothesis(
            incident_id=incident.incident_id,
            target_service=target_service,
            category=HypothesisCategory.DATABASE,
            description=f"Database query latency regression or connection exhaustion on {target_service}",
            confidence=0.25,
            next_action="query_db_metrics"
        )
        hypo_set.add_hypothesis(h_db)

        # 2. Bad Deployment Hypothesis
        h_deploy = Hypothesis(
            incident_id=incident.incident_id,
            target_service=target_service,
            category=HypothesisCategory.DEPLOYMENT,
            description=f"Recent software version deployment or config release introduced bugs in {target_service}",
            confidence=0.25,
            next_action="inspect_deployment_history"
        )
        hypo_set.add_hypothesis(h_deploy)

        # 3. Downstream Dependency Failure
        h_dep = Hypothesis(
            incident_id=incident.incident_id,
            target_service=target_service,
            category=HypothesisCategory.DEPENDENCY,
            description=f"Downstream dependency service or third-party bank API latency/outage affecting {target_service}",
            confidence=0.20,
            next_action="inspect_dependency_health"
        )
        hypo_set.add_hypothesis(h_dep)

        # 4. Resource Saturation Hypothesis
        h_res = Hypothesis(
            incident_id=incident.incident_id,
            target_service=target_service,
            category=HypothesisCategory.RESOURCE,
            description=f"CPU, memory pressure, or thread starvation on {target_service}",
            confidence=0.15,
            next_action="query_metrics"
        )
        hypo_set.add_hypothesis(h_res)

        # 5. Queue Backlog Hypothesis
        h_queue = Hypothesis(
            incident_id=incident.incident_id,
            target_service=target_service,
            category=HypothesisCategory.QUEUE,
            description=f"Asynchronous queue backlog or stuck message consumer impacting {target_service}",
            confidence=0.15,
            next_action="inspect_service_health"
        )
        hypo_set.add_hypothesis(h_queue)

        return hypo_set
