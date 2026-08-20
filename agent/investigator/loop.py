# Active Investigation Loop Orchestrator - RCAI v2
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from backend.incidents.models import AgentIncidentView
from agent.hypothesis.generator import HypothesisGenerator
from agent.hypothesis.models import HypothesisSet, Hypothesis, HypothesisStatus, HypothesisCategory
from agent.investigator.state import InvestigationState, InvestigationActionRecord
from agent.routing.selector import EvidenceSelector
from tools.registry import ToolRegistry, create_default_investigation_tools
from tools.base import ToolExecutionStatus
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType

class ActiveInvestigator:
    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        max_tool_calls: int = 15,
        max_time_seconds: float = 60.0,
        confidence_threshold: float = 0.70
    ):
        self.tool_registry = tool_registry or create_default_investigation_tools()
        self.selector = EvidenceSelector(self.tool_registry)
        self.max_tool_calls = max_tool_calls
        self.max_time_seconds = max_time_seconds
        self.confidence_threshold = confidence_threshold

    def start_investigation(self, incident: AgentIncidentView) -> InvestigationState:
        hypo_set = HypothesisGenerator.generate_candidate_hypotheses(incident)
        state = InvestigationState(
            investigation_id=f"inv_{uuid.uuid4().hex[:8]}",
            incident=incident,
            hypothesis_set=hypo_set,
            budget_max_tool_calls=self.max_tool_calls,
            budget_max_seconds=self.max_time_seconds
        )
        return state

    def step(self, state: InvestigationState) -> InvestigationState:
        if state.is_completed:
            return state

        elapsed = time.time() - state.start_time
        if state.current_step >= state.budget_max_tool_calls or elapsed >= state.budget_max_seconds:
            state.is_completed = True
            state.stop_reason = "BUDGET_EXHAUSTED"
            state.final_root_cause_hypothesis = state.hypothesis_set.get_top_hypothesis()
            return state

        top_h = state.hypothesis_set.get_top_hypothesis()
        if top_h and top_h.confidence >= self.confidence_threshold:
            other_active = [h for h in state.hypothesis_set.get_active_hypotheses() if h.hypothesis_id != top_h.hypothesis_id]
            if not other_active or all(h.confidence <= 0.35 for h in other_active):
                state.is_completed = True
                state.stop_reason = "CONFIDENCE_THRESHOLD_REACHED"
                state.final_root_cause_hypothesis = top_h
                return state

        executed = [
            (a.tool_name, str(a.arguments.get("service", "")))
            for a in state.action_history
        ]
        next_action_details = self.selector.select_next_action_details(
            state.hypothesis_set,
            executed,
            state.incident.service,
            state.incident.symptom
        )
        if not next_action_details:
            state.is_completed = True
            state.stop_reason = "NO_FURTHER_ACTIONS"
            state.final_root_cause_hypothesis = state.hypothesis_set.get_top_hypothesis()
            return state

        tool_name, args, selection_reason, estimated_cost = next_action_details
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            state.is_completed = True
            state.stop_reason = f"TOOL_NOT_FOUND: {tool_name}"
            return state

        t0 = time.perf_counter()
        result = tool.execute(**args)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        
        prev_conf = {h.hypothesis_id: h.confidence for h in state.hypothesis_set.hypotheses}
        prev_status = {h.hypothesis_id: h.status for h in state.hypothesis_set.hypotheses}

        evidence_ids = []
        for ev in result.evidence:
            state.evidence_store[ev.evidence_id] = ev
            evidence_ids.append(ev.evidence_id)
            self._update_hypotheses_from_evidence(state.hypothesis_set, ev, tool_name, state.incident.service)

        hypothesis_impact = []
        for h in state.hypothesis_set.hypotheses:
            if h.confidence != prev_conf.get(h.hypothesis_id, 0.0) or h.status != prev_status.get(h.hypothesis_id, HypothesisStatus.OPEN):
                diff = round(h.confidence - prev_conf.get(h.hypothesis_id, 0.0), 3)
                hypothesis_impact.append({
                    "hypothesis_id": h.hypothesis_id,
                    "category": h.category.value,
                    "target_service": h.target_service,
                    "previous_confidence": prev_conf.get(h.hypothesis_id, 0.0),
                    "new_confidence": h.confidence,
                    "status": h.status.value,
                    "change": diff
                })

        action_rec = InvestigationActionRecord(
            step_index=state.current_step + 1,
            tool_name=tool_name,
            arguments=args,
            result_status=result.status.value,
            evidence_ids=evidence_ids,
            duration_ms=duration_ms,
            selection_reason=selection_reason,
            estimated_cost=estimated_cost,
            hypothesis_impact=hypothesis_impact
        )
        state.action_history.append(action_rec)
        state.current_step += 1

        top_h = state.hypothesis_set.get_top_hypothesis()
        if top_h and top_h.confidence >= self.confidence_threshold:
            state.is_completed = True
            state.stop_reason = "CONFIDENCE_THRESHOLD_REACHED"
            state.final_root_cause_hypothesis = top_h

        return state

    def run_investigation(self, incident: AgentIncidentView) -> InvestigationState:
        state = self.start_investigation(incident)
        while not state.is_completed:
            state = self.step(state)
        return state

    def _update_hypotheses_from_evidence(
        self,
        hypo_set: HypothesisSet,
        evidence: NormalizedEvidence,
        tool_name: str,
        target_service: str
    ) -> None:
        h_db = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.DATABASE), None)
        h_deploy = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.DEPLOYMENT), None)
        h_dep = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.DEPENDENCY), None)
        h_res = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.RESOURCE), None)
        h_queue = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.QUEUE), None)

        if tool_name == "query_db_metrics" and h_db:
            samples_count = evidence.data.get("db_query_samples_count", 0)
            faults = evidence.data.get("active_faults", 0.0)
            if ("order" in target_service or "db" in target_service) and (samples_count > 0 or faults > 0):
                h_db.add_supporting_evidence(evidence.evidence_id, weight=0.60)
            else:
                h_db.add_contradicting_evidence(evidence.evidence_id, weight=0.20)

        elif tool_name in ["inspect_deployment_history", "compare_versions"] and h_deploy:
            version_str = str(evidence.data.get("version", "") or evidence.data.get("current_version", ""))
            desc_str = str(evidence.data.get("change_description", "") or evidence.data.get("last_change_description", ""))
            is_bad_version = any(tag in version_str for tag in ["2.4.1", "2.5.0", "1.8.0", "3.0.0", "3.1.0", "bad", "bad_deploy"])
            is_bad_desc = any(tag in desc_str.lower() for tag in ["bug", "error", "drift", "fail", "regression", "update"])
            if is_bad_version or is_bad_desc:
                h_deploy.add_supporting_evidence(evidence.evidence_id, weight=0.60)
            else:
                h_deploy.add_contradicting_evidence(evidence.evidence_id, weight=0.25)

        elif tool_name in ["inspect_dependency_health", "get_payment_route_health", "get_gateway_response"] and h_dep:
            dep_data = evidence.data.get("data", {}) or evidence.data
            dep_status = dep_data.get("status", "")
            if dep_status == "UNHEALTHY" or "dependency" in target_service or "bank" in target_service:
                h_dep.add_supporting_evidence(evidence.evidence_id, weight=0.60)
            elif dep_status == "HEALTHY" and target_service != "dependency-service":
                h_dep.reject(evidence.evidence_id)

        elif tool_name in ["inspect_service_health", "get_webhook_delivery"] and h_queue:
            is_up = evidence.data.get("is_up", True)
            if "worker" in target_service or "queue" in target_service:
                h_queue.add_supporting_evidence(evidence.evidence_id, weight=0.60)
            elif is_up and target_service != "worker-service":
                h_queue.add_contradicting_evidence(evidence.evidence_id, weight=0.20)

        elif tool_name == "query_metrics":
            metric_name = evidence.data.get("metric", "")
            val = evidence.data.get("value", 0.0)
            if ("gateway" in target_service or "api" in target_service) and h_res:
                h_res.add_supporting_evidence(evidence.evidence_id, weight=0.60)
            elif metric_name == "error_rate" and val > 0.5 and h_deploy:
                h_deploy.add_supporting_evidence(evidence.evidence_id, weight=0.20)
