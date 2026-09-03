# Incident Hypothesis Generator with Pluggable LLM Inference Support
from typing import List, Optional
from backend.incidents.models import AgentIncidentView
from agent.hypothesis.models import Hypothesis, HypothesisCategory, HypothesisSet
from observability.models import NormalizedEvidence
from agent.llm.models import HypothesisGenerationResponseSchema
from agent.llm.interface import BaseLLMBackend, llm_infer
from backend.config import get_settings
from discovery.registry import get_current_topology, is_service_db_related, is_service_queue_related

class HypothesisGenerator:
    @staticmethod
    def generate_candidate_hypotheses(
        incident: AgentIncidentView,
        evidence: Optional[List[NormalizedEvidence]] = None,
        llm_backend: Optional[BaseLLMBackend] = None
    ) -> HypothesisSet:
        settings = get_settings()
        use_llm = llm_backend is not None or settings.LLM_BACKEND in ["ollama", "hosted"] or settings.is_live_mode()

        topo = get_current_topology()
        target_node = topo.get_node(incident.service)

        # Inspect evidence for domain signals
        has_db_evidence = False
        has_queue_evidence = False
        if evidence:
            for e in evidence:
                text = f"{e.summary} {str(e.data)}".lower()
                if any(kw in text for kw in ["db", "database", "sql", "query", "pool", "lock", "postgres", "mysql"]):
                    has_db_evidence = True
                if any(kw in text for kw in ["queue", "backlog", "consumer", "worker", "stream", "lag", "celery"]):
                    has_queue_evidence = True

        target_is_db = is_service_db_related(incident.service) or has_db_evidence
        target_is_queue = is_service_queue_related(incident.service) or has_queue_evidence

        if use_llm:
            evidence_summary = ""
            if evidence:
                evidence_summary = "\nObserved Live Telemetry Evidence:\n" + "\n".join([f"- {e.summary}" for e in evidence[:5]])

            capabilities = ["resource saturation", "software version release regression", "downstream dependency failure"]
            if target_is_db:
                capabilities.append("database query latency or connection exhaustion")
            if target_is_queue:
                capabilities.append("asynchronous queue backlog or worker starvation")

            node_info = f" (Role: {target_node.service_type})" if target_node else ""
            prompt = (
                f"Incident Investigation Context:\n"
                f"- Incident ID: {incident.incident_id}\n"
                f"- Affected Service: {incident.service}{node_info}\n"
                f"- Reported Symptom: {incident.symptom}\n"
                f"- Severity: {incident.severity.value}\n"
                f"- Applicable Failure Profile: {', '.join(capabilities)}\n"
                f"{evidence_summary}\n\n"
                f"Generate a set of competing, distinct root cause hypotheses with initial confidence scores and recommended next diagnostic actions."
            )

            result = llm_infer(
                prompt=prompt,
                schema=HypothesisGenerationResponseSchema,
                system_prompt="You are an autonomous SRE root-cause investigator. Generate plausible, competing microservice failure hypotheses conforming strictly to the service's discovered capabilities.",
                backend=llm_backend
            )

            if result.is_valid and result.parsed_data and isinstance(result.parsed_data, HypothesisGenerationResponseSchema):
                hypo_set = HypothesisSet(incident_id=incident.incident_id)
                for item in result.parsed_data.hypotheses:
                    # Filter out DB hypotheses for non-DB services unless evidence explicitly indicated DB
                    if item.category == HypothesisCategory.DATABASE and not target_is_db:
                        continue
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

        # Fallback / Deterministic Default Candidate Hypotheses
        hypo_set = HypothesisSet(incident_id=incident.incident_id)
        target_service = incident.service

        candidates = []

        # 1. Database Regression (Only if service has DB component, dependencies, or evidence)
        if target_is_db:
            candidates.append(
                Hypothesis(
                    incident_id=incident.incident_id,
                    target_service=target_service,
                    category=HypothesisCategory.DATABASE,
                    description=f"Database query latency regression or connection exhaustion on {target_service}",
                    confidence=0.25,
                    next_action="query_db_metrics"
                )
            )

        # 2. Bad Deployment Hypothesis (Generic - applicable to any service)
        candidates.append(
            Hypothesis(
                incident_id=incident.incident_id,
                target_service=target_service,
                category=HypothesisCategory.DEPLOYMENT,
                description=f"Recent software version deployment or config release introduced bugs in {target_service}",
                confidence=0.25,
                next_action="inspect_deployment_history"
            )
        )

        # 3. Downstream Dependency Failure (Generic - applicable to any service)
        candidates.append(
            Hypothesis(
                incident_id=incident.incident_id,
                target_service=target_service,
                category=HypothesisCategory.DEPENDENCY,
                description=f"Downstream dependency service or third-party bank API latency/outage affecting {target_service}",
                confidence=0.20,
                next_action="inspect_dependency_health"
            )
        )

        # 4. Resource Saturation Hypothesis (Generic - applicable to any service)
        candidates.append(
            Hypothesis(
                incident_id=incident.incident_id,
                target_service=target_service,
                category=HypothesisCategory.RESOURCE,
                description=f"CPU, memory pressure, or thread starvation on {target_service}",
                confidence=0.15,
                next_action="query_metrics"
            )
        )

        # 5. Queue Backlog Hypothesis (Only if worker/queue related or evidence indicated)
        if target_is_queue:
            candidates.append(
                Hypothesis(
                    incident_id=incident.incident_id,
                    target_service=target_service,
                    category=HypothesisCategory.QUEUE,
                    description=f"Asynchronous queue backlog or stuck message consumer impacting {target_service}",
                    confidence=0.15,
                    next_action="inspect_service_health"
                )
            )

        # Normalize confidences if any conditional category was excluded
        total_conf = sum(c.confidence for c in candidates)
        if total_conf > 0:
            for c in candidates:
                c.confidence = round(c.confidence / total_conf, 2)

        for c in candidates:
            hypo_set.add_hypothesis(c)

        return hypo_set

