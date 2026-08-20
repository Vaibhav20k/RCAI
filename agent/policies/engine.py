# Safety and Authorization Policy Engine
import uuid
from typing import Dict, Any, List, Optional, Set
from agent.policies.models import RemediationProposal, PolicyCheckResult, RemediationActionType, RemediationRiskLevel
from backend.incidents.models import Incident, IncidentStatus

VALID_TOPOLOGY_SERVICES = {
    "api-gateway",
    "order-service",
    "payment-service",
    "dependency-service",
    "worker-service"
}

class PolicyEngine:
    def __init__(self, auto_approve_low_risk: bool = True):
        self.auto_approve_low_risk = auto_approve_low_risk
        self._executed_remediations: Dict[str, Set[str]] = {} # incident_id -> set of action_keys
        self._approval_tokens: Dict[str, RemediationProposal] = {}

    def evaluate_proposal(
        self,
        proposal: RemediationProposal,
        incident: Optional[Incident] = None
    ) -> PolicyCheckResult:
        # 1. Check forbidden actions
        if proposal.action_type == RemediationActionType.FORBIDDEN_COMMAND:
            return PolicyCheckResult(
                is_allowed=False,
                policy_code="DENIED_FORBIDDEN_ACTION",
                rejection_reason="Direct shell execution and arbitrary commands are strictly forbidden"
            )

        # 2. Validate target service
        if proposal.target_service not in VALID_TOPOLOGY_SERVICES:
            return PolicyCheckResult(
                is_allowed=False,
                policy_code="DENIED_UNKNOWN_SERVICE",
                rejection_reason=f"Target service {proposal.target_service} not recognized in microservice topology"
            )

        # 3. Check incident active status if incident object is provided
        if incident and incident.status in [IncidentStatus.RESOLVED, IncidentStatus.ESCALATED]:
            return PolicyCheckResult(
                is_allowed=False,
                policy_code="DENIED_INACTIVE_INCIDENT",
                rejection_reason=f"Incident {incident.incident_id} is already in {incident.status} state"
            )

        # 4. Idempotency protection
        action_key = f"{proposal.action_type}:{proposal.target_service}"
        attempted = self._executed_remediations.get(proposal.incident_id, set())
        if action_key in attempted:
            return PolicyCheckResult(
                is_allowed=False,
                policy_code="DENIED_DUPLICATE_ACTION",
                rejection_reason=f"Action {action_key} has already been executed for incident {proposal.incident_id}"
            )

        # 5. Risk level and approval check
        if proposal.risk_level in [RemediationRiskLevel.HIGH, RemediationRiskLevel.CRITICAL]:
            token = f"appr_tok_{uuid.uuid4().hex[:8]}"
            self._approval_tokens[token] = proposal
            return PolicyCheckResult(
                is_allowed=True,
                requires_human_approval=True,
                policy_code="REQUIRES_HUMAN_APPROVAL",
                approval_token=token
            )

        # Approved for controlled low-risk execution
        return PolicyCheckResult(
            is_allowed=True,
            requires_human_approval=False,
            policy_code="ALLOWED"
        )

    def record_execution(self, proposal: RemediationProposal) -> None:
        action_key = f"{proposal.action_type}:{proposal.target_service}"
        if proposal.incident_id not in self._executed_remediations:
            self._executed_remediations[proposal.incident_id] = set()
        self._executed_remediations[proposal.incident_id].add(action_key)
