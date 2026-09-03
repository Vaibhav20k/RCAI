# LLM-Driven Playbook Selector with Strict Catalogue and Safety Validation
from typing import Dict, Any, List, Optional, Tuple
from agent.verification.models import RootCauseDecision
from backend.incidents.models import AgentIncidentView
from agent.policies.models import RemediationProposal, RemediationActionType, RemediationRiskLevel
from agent.playbooks.catalogue import PlaybookCatalogue, global_playbook_catalogue
from agent.llm.models import PlaybookSelectionSchema
from agent.llm.interface import BaseLLMBackend, llm_infer
from backend.config import get_settings
from discovery.registry import get_current_topology_services

class PlaybookSelector:
    def __init__(self, catalogue: Optional[PlaybookCatalogue] = None):
        self.catalogue = catalogue or global_playbook_catalogue

    def select_playbook(
        self,
        decision: RootCauseDecision,
        incident: AgentIncidentView,
        evidence_trail: Optional[List[Dict[str, Any]]] = None,
        llm_backend: Optional[BaseLLMBackend] = None
    ) -> Tuple[Optional[RemediationProposal], Optional[str]]:
        # If root cause is unknown, cannot recommend automated playbook -> escalate to human
        if decision.is_unknown or decision.root_cause_service == "UNKNOWN":
            return None, "Root cause is UNKNOWN or unproven. Automated remediation blocked; escalated to human SRE."

        # Validate target service against active topology
        valid_services = get_current_topology_services()
        if decision.root_cause_service not in valid_services:
            return None, f"Target service '{decision.root_cause_service}' is not recognized in active microservice topology. Automated remediation blocked; escalated to human SRE."

        catalogue_prompt = self.catalogue.get_catalogue_prompt_description(target_service=decision.root_cause_service)
        evidence_str = ""

        if evidence_trail:
            evidence_str = "\nEvidence Audit Trail:\n" + "\n".join([f"- [{e.get('source')}] {e.get('summary')}" for e in evidence_trail[:5]])

        prompt = (
            f"Incident Root Cause Diagnosis Context:\n"
            f"- Incident ID: {incident.incident_id}\n"
            f"- Affected Target Service: {decision.root_cause_service}\n"
            f"- Diagnosed Category: {decision.root_cause_category.value}\n"
            f"- Diagnosis Details: {decision.description}\n"
            f"- Diagnostic Confidence: {decision.confidence * 100:.1f}%\n"
            f"{evidence_str}\n\n"
            f"{catalogue_prompt}\n\n"
            f"Select the exact single matching playbook action from the catalogue above and provide parameter values and justification rationale."
        )

        system_prompt = (
            "You are an SRE remediation expert AI. "
            "You MUST select an action ONLY from the approved playbook catalogue. "
            "Never generate shell commands, raw code, or arbitrary API calls. "
            "Output valid JSON conforming strictly to the requested PlaybookSelectionSchema."
        )

        result = llm_infer(
            prompt=prompt,
            schema=PlaybookSelectionSchema,
            system_prompt=system_prompt,
            backend=llm_backend,
            max_retries=1
        )

        if not result.is_valid or not result.parsed_data or not isinstance(result.parsed_data, PlaybookSelectionSchema):
            return None, f"Playbook selection schema validation failed: {result.error_message}. Routing to human escalation."

        selection = result.parsed_data
        action_name = selection.action.strip()
        target_service = selection.target.strip() or decision.root_cause_service
        params = selection.params or {}

        # Validate strictly against deterministic catalogue
        is_valid, validation_err = self.catalogue.validate_playbook_selection(action_name, target_service, params)
        if not is_valid:
            return None, f"Playbook catalogue rejection: {validation_err}. Routing to human escalation."

        playbook_def = self.catalogue.get_playbook(action_name)
        proposal = RemediationProposal(
            incident_id=incident.incident_id,
            action_type=playbook_def.action_type,
            target_service=target_service,
            parameters=params,
            risk_level=playbook_def.risk_level,
            rationale=selection.rationale or f"Automated catalogue remediation for {decision.description}"
        )

        return proposal, None

global_playbook_selector = PlaybookSelector()
