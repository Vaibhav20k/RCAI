# Incident Hypothesis Generator
from typing import List
from backend.incidents.models import AgentIncidentView
from agent.hypothesis.models import Hypothesis, HypothesisCategory, HypothesisSet

class HypothesisGenerator:
    @staticmethod
    def generate_candidate_hypotheses(incident: AgentIncidentView) -> HypothesisSet:
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
