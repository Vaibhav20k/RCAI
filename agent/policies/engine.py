# Safety and Authorization Policy Engine
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from agent.policies.models import (
    RemediationProposal,
    PolicyCheckResult,
    RemediationActionType,
    RemediationRiskLevel,
    ExecutionAuthorizationMode
)
from backend.incidents.models import Incident, IncidentStatus
from backend.config import get_settings
from discovery.registry import get_current_topology_services, DEFAULT_SIMULATOR_NODES

# Fallback reference set for backwards-compatibility
VALID_TOPOLOGY_SERVICES = set(DEFAULT_SIMULATOR_NODES.keys())

class PolicyEngine:
    def __init__(
        self,
        auto_approve_low_risk: bool = True,
        allowed_services: Optional[Set[str]] = None
    ):
        self.auto_approve_low_risk = auto_approve_low_risk
        self.allowed_services = allowed_services
        self._executed_remediations: Dict[str, Set[str]] = {} # incident_id -> set of action_keys
        self._approval_tokens: Dict[str, RemediationProposal] = {}

    def get_valid_services(self) -> Set[str]:
        if self.allowed_services is not None:
            return self.allowed_services
        return get_current_topology_services()

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

        # 2. Validate target service against dynamic topology
        valid_services = self.get_valid_services()
        if proposal.target_service not in valid_services:
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

        # 5. Pre-authorized execution mode bypasses manual approval modal
        if proposal.authorization_mode == ExecutionAuthorizationMode.PRE_AUTHORIZED_AUTO:
            return PolicyCheckResult(
                is_allowed=True,
                requires_human_approval=False,
                is_pre_authorized=True,
                authorization_mode=ExecutionAuthorizationMode.PRE_AUTHORIZED_AUTO,
                policy_code="ALLOWED_PRE_AUTHORIZED"
            )

        # 6. Risk level and human approval check
        if proposal.risk_level in [RemediationRiskLevel.HIGH, RemediationRiskLevel.CRITICAL]:
            token = f"appr_tok_{uuid.uuid4().hex[:8]}"
            self._approval_tokens[token] = proposal
            return PolicyCheckResult(
                is_allowed=True,
                requires_human_approval=True,
                is_pre_authorized=False,
                authorization_mode=ExecutionAuthorizationMode.HUMAN_APPROVED,
                policy_code="REQUIRES_HUMAN_APPROVAL",
                approval_token=token
            )

        # Approved for standard human-approved execution
        return PolicyCheckResult(
            is_allowed=True,
            requires_human_approval=False,
            is_pre_authorized=False,
            authorization_mode=ExecutionAuthorizationMode.HUMAN_APPROVED,
            policy_code="ALLOWED"
        )

    def evaluate_auto_execution_eligibility(
        self,
        proposal: RemediationProposal,
        decision: Any, # RootCauseDecision
        incident: Optional[Incident] = None
    ) -> Tuple[bool, Optional[str]]:
        settings = get_settings()

        # 1. Check if auto-execution is globally enabled
        if not settings.AUTO_EXECUTE_ENABLED:
            return False, "Autonomous execution disabled (AUTO_EXECUTE_ENABLED=false)"

        # 2. Check if playbook is on the approved pre-authorized list
        if proposal.action_type.value not in settings.AUTO_EXECUTE_PLAYBOOKS:
            return False, f"Playbook '{proposal.action_type.value}' is not on the pre-authorized auto-execution whitelist"

        # 3. Check high confidence threshold (e.g. >= 0.90)
        if decision.confidence < settings.AUTO_EXECUTE_CONFIDENCE_THRESHOLD:
            return False, f"Diagnostic confidence ({decision.confidence*100:.1f}%) is below auto-execution threshold ({settings.AUTO_EXECUTE_CONFIDENCE_THRESHOLD*100:.1f}%)"

        # 4. Check cryptographic evidence provenance requirement
        if settings.AUTO_EXECUTE_REQUIRE_PROVENANCE:
            if not decision.supporting_evidence_ids or len(decision.supporting_evidence_ids) == 0:
                return False, "Auto-execution blocked: Supporting evidence missing"
            if decision.provenance_audit:
                for audit_item in decision.provenance_audit:
                    if not audit_item.get("hash_signature") or audit_item.get("reliability", 0.0) < 0.8:
                        return False, "Auto-execution blocked: Supporting evidence lacks verified cryptographic hash provenance"

        # 5. Check core safety policy gate
        temp_prop = proposal.model_copy()
        temp_prop.authorization_mode = ExecutionAuthorizationMode.PRE_AUTHORIZED_AUTO
        policy_res = self.evaluate_proposal(temp_prop, incident=incident)
        if not policy_res.is_allowed:
            return False, f"Policy gate rejection: {policy_res.rejection_reason}"

        return True, "Eligible for pre-authorized autonomous execution"

    def evaluate_reversal_proposal(
        self,
        proposal: RemediationProposal
    ) -> PolicyCheckResult:
        # 1. Validate target service topology against dynamic topology
        valid_services = self.get_valid_services()
        if proposal.target_service not in valid_services:
            return PolicyCheckResult(
                is_allowed=False,
                policy_code="DENIED_UNKNOWN_SERVICE",
                rejection_reason=f"Reversal target service '{proposal.target_service}' not recognized in microservice topology"
            )


        # 2. Idempotency / duplicate reversal protection
        reversal_key = f"reversal:{proposal.action_type}:{proposal.target_service}"
        attempted = self._executed_remediations.get(proposal.incident_id, set())
        if reversal_key in attempted:
            return PolicyCheckResult(
                is_allowed=False,
                policy_code="DENIED_DUPLICATE_REVERSAL",
                rejection_reason=f"Reversal '{reversal_key}' has already been executed for incident {proposal.incident_id}"
            )

        # Allowed for immediate compensating reversal (skips human approval re-elevation)
        return PolicyCheckResult(
            is_allowed=True,
            requires_human_approval=False,
            policy_code="ALLOWED_REVERSAL"
        )

    def record_execution(self, proposal: RemediationProposal) -> None:
        action_key = f"{proposal.action_type}:{proposal.target_service}"
        if proposal.incident_id not in self._executed_remediations:
            self._executed_remediations[proposal.incident_id] = set()
        self._executed_remediations[proposal.incident_id].add(action_key)

    def record_reversal(self, proposal: RemediationProposal) -> None:
        reversal_key = f"reversal:{proposal.action_type}:{proposal.target_service}"
        if proposal.incident_id not in self._executed_remediations:
            self._executed_remediations[proposal.incident_id] = set()
        self._executed_remediations[proposal.incident_id].add(reversal_key)
