# Root-Cause Verification and Evidence Provenance Engine
import uuid
import time
from typing import Dict, Any, List, Optional
from agent.investigator.state import InvestigationState
from agent.verification.models import RootCauseDecision, IncidentReport
from agent.hypothesis.models import HypothesisCategory, HypothesisStatus
from agent.policies.models import RemediationProposal
from agent.playbooks.selector import PlaybookSelector, global_playbook_selector
from agent.llm.interface import BaseLLMBackend
from observability.models import NormalizedEvidence

class RootCauseVerifier:
    def __init__(
        self,
        min_confidence_for_certainty: float = 0.65,
        playbook_selector: Optional[PlaybookSelector] = None,
        llm_backend: Optional[BaseLLMBackend] = None
    ):
        self.min_confidence_for_certainty = min_confidence_for_certainty
        self.playbook_selector = playbook_selector or global_playbook_selector
        self.llm_backend = llm_backend

    def verify_and_generate_decision(self, state: InvestigationState) -> RootCauseDecision:
        decision_id = f"dec_{uuid.uuid4().hex[:8]}"
        top_h = state.final_root_cause_hypothesis or state.hypothesis_set.get_top_hypothesis()

        # 1. Unknown / Insufficient evidence case
        if not top_h or top_h.confidence < self.min_confidence_for_certainty or top_h.status == HypothesisStatus.REJECTED:
            return RootCauseDecision(
                decision_id=decision_id,
                incident_id=state.incident.incident_id,
                root_cause_service="UNKNOWN",
                root_cause_category=HypothesisCategory.UNKNOWN,
                description="ROOT_CAUSE_UNKNOWN: Telemetry evidence is insufficient or ambiguous to establish root cause with required certainty",
                confidence=round(top_h.confidence, 3) if top_h else 0.0,
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
                unresolved_questions=["Insufficient distinctive telemetry signals collected within budget"],
                is_unknown=True
            )

        # 2. Verify evidence provenance integrity
        audit_trail: List[Dict[str, Any]] = []
        valid_supporting: List[str] = []
        
        for ev_id in top_h.supporting_evidence:
            ev = state.evidence_store.get(ev_id)
            if ev and ev.provenance and ev.provenance.hash_signature:
                valid_supporting.append(ev_id)
                audit_trail.append({
                    "evidence_id": ev_id,
                    "source": ev.source.value,
                    "collector": ev.provenance.collector,
                    "query": ev.provenance.query,
                    "hash_signature": ev.provenance.hash_signature,
                    "summary": ev.summary,
                    "reliability": ev.reliability
                })

        valid_contradicting = [
            ev_id for ev_id in top_h.contradicting_evidence
            if ev_id in state.evidence_store
        ]

        # 3. If no valid provenanced evidence exists, demote to unknown
        if not valid_supporting:
            return RootCauseDecision(
                decision_id=decision_id,
                incident_id=state.incident.incident_id,
                root_cause_service="UNKNOWN",
                root_cause_category=HypothesisCategory.UNKNOWN,
                description="INSUFFICIENT_EVIDENCE: No valid verified evidence records ground the proposed hypothesis",
                confidence=0.0,
                unresolved_questions=["Evidence provenance verification failed"],
                is_unknown=True
            )

        return RootCauseDecision(
            decision_id=decision_id,
            incident_id=state.incident.incident_id,
            root_cause_service=top_h.target_service,
            root_cause_category=top_h.category,
            description=top_h.description,
            confidence=round(top_h.confidence, 3),
            supporting_evidence_ids=valid_supporting,
            contradicting_evidence_ids=valid_contradicting,
            provenance_audit=audit_trail,
            unresolved_questions=[],
            is_unknown=False
        )

    def generate_incident_report(self, state: InvestigationState) -> IncidentReport:
        decision = self.verify_and_generate_decision(state)
        report_id = f"rep_{uuid.uuid4().hex[:8]}"
        duration_ms = (time.time() - state.start_time) * 1000.0
        
        # Select playbook from catalogue via PlaybookSelector
        proposal, error_msg = self.playbook_selector.select_playbook(
            decision=decision,
            incident=state.incident,
            evidence_trail=decision.provenance_audit,
            llm_backend=self.llm_backend
        )

        recs = {
            HypothesisCategory.DEPLOYMENT: f"Rollback {decision.root_cause_service} to previous known good release",
            HypothesisCategory.DATABASE: f"Apply database query optimization / index rebuild on {decision.root_cause_service}",
            HypothesisCategory.DEPENDENCY: "Engage partner dependency gateway circuit breaker",
            HypothesisCategory.RESOURCE: f"Scale replicas / restart workers for {decision.root_cause_service}",
            HypothesisCategory.QUEUE: f"Scale queue consumer workers for {decision.root_cause_service}",
            HypothesisCategory.UNKNOWN: "Escalate to on-call engineer with collected audit telemetry"
        }

        if proposal:
            rec_action_str = f"Execute catalogue playbook '{proposal.action_type.value}' on {proposal.target_service}: {proposal.rationale}"
        else:
            rec_action_str = recs.get(decision.root_cause_category, "Manual SRE inspection required")

        exec_summary = (
            f"Incident on {state.incident.service}: {state.incident.symptom}. "
            f"Diagnosis: {decision.description} (Confidence: {decision.confidence*100:.1f}%). "
            f"Grounded by {len(decision.supporting_evidence_ids)} provenanced evidence items."
        )

        return IncidentReport(
            report_id=report_id,
            incident=state.incident,
            root_cause_decision=decision,
            hypotheses_evaluated_count=len(state.hypothesis_set.hypotheses),
            tool_calls_executed_count=len(state.action_history),
            investigation_duration_ms=duration_ms,
            executive_summary=exec_summary,
            evidence_trail=decision.provenance_audit,
            recommended_action=rec_action_str,
            recommended_proposal=proposal
        )
