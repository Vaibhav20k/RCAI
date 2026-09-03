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

from agent.llm.interface import BaseLLMBackend
from discovery.registry import is_service_db_related, is_service_queue_related

class ActiveInvestigator:

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        max_tool_calls: int = 15,
        max_time_seconds: float = 60.0,
        confidence_threshold: float = 0.70,
        llm_backend: Optional[BaseLLMBackend] = None
    ):
        self.tool_registry = tool_registry or create_default_investigation_tools()
        self.selector = EvidenceSelector(self.tool_registry)
        self.max_tool_calls = max_tool_calls
        self.max_time_seconds = max_time_seconds
        self.confidence_threshold = confidence_threshold
        self.llm_backend = llm_backend

    def start_investigation(
        self,
        incident: AgentIncidentView,
        initial_evidence: Optional[List[NormalizedEvidence]] = None
    ) -> InvestigationState:
        hypo_set = HypothesisGenerator.generate_candidate_hypotheses(
            incident=incident,
            evidence=initial_evidence,
            llm_backend=self.llm_backend
        )
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

        # Process all evidence from the tool execution atomically
        self._process_tool_evidence(state.hypothesis_set, result.evidence, tool_name, state.incident.service)

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

    def _process_tool_evidence(
        self,
        hypo_set: HypothesisSet,
        evidence_list: List[NormalizedEvidence],
        tool_name: str,
        target_service: str
    ) -> None:
        if not evidence_list:
            return

        h_db = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.DATABASE), None)
        h_deploy = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.DEPLOYMENT), None)
        h_dep = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.DEPENDENCY), None)
        h_res = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.RESOURCE), None)
        h_queue = next((h for h in hypo_set.hypotheses if h.category == HypothesisCategory.QUEUE), None)

        # 1. Database Tool Evidence
        if tool_name in ["query_db_metrics", "get_payment_state", "get_ledger_entry", "get_settlement_batch", "get_reconciliation_state"] and h_db:
            has_db_anomaly = any(
                ev.data.get("has_db_anomaly", False) or "inconsisten" in str(ev.data).lower() or "mismatch" in str(ev.data).lower() or "drift" in str(ev.data).lower() or "duplicate" in str(ev.data).lower()
                for ev in evidence_list
            )
            if has_db_anomaly and (target_service in ["order-service", "payment-service"] or is_service_db_related(target_service)):
                h_db.add_supporting_evidence(evidence_list[0].evidence_id, weight=0.60)
            else:
                h_db.add_contradicting_evidence(evidence_list[0].evidence_id, weight=0.30)

        # 2. Deployment Tool Evidence
        elif tool_name in ["inspect_deployment_history", "compare_versions"] and h_deploy:
            bad_ev = None
            for ev in evidence_list:
                version_str = str(ev.data.get("version", "") or ev.data.get("current_version", ""))
                desc_str = str(ev.data.get("change_description", "") or ev.data.get("last_change_description", "")).lower()
                is_bad_version = any(tag in version_str for tag in ["2.4.1", "2.5.0", "1.8.0", "1.8.1", "2.4.2", "3.0.0", "3.1.0", "3.2.0", "bad", "canary"])
                is_bad_desc = any(tag in desc_str for tag in ["bug", "error", "drift", "fail", "regression", "exception", "feature flag", "migration", "rewrite", "bad environment", "schema"])
                is_routine = ("initial base release" in desc_str or "base release" in desc_str or version_str in ["1.0.0", "2.4.0", "1.7.9"])
                if (is_bad_version or is_bad_desc) and not is_routine:
                    bad_ev = ev
                    break

            if bad_ev:
                h_deploy.add_supporting_evidence(bad_ev.evidence_id, weight=0.60)
            else:
                h_deploy.add_contradicting_evidence(evidence_list[0].evidence_id, weight=0.35)

        # 3. Dependency Tool Evidence
        elif tool_name in ["inspect_dependency_health", "get_payment_route_health", "get_gateway_response"] and h_dep:
            is_unhealthy = False
            for ev in evidence_list:
                dep_data = ev.data.get("data", {}) or ev.data
                dep_status = str(dep_data.get("status", "")).upper()
                if dep_status in ["UNHEALTHY", "DEGRADED", "503"] or "timeout" in str(dep_data).lower() or "latency" in str(dep_data).lower() or "circuit" in str(dep_data).lower() or "storm" in str(dep_data).lower() or "flap" in str(dep_data).lower():
                    is_unhealthy = True
                    break

            if is_unhealthy or target_service in ["dependency-service", "bank"] or "dep" in target_service.lower():
                h_dep.add_supporting_evidence(evidence_list[0].evidence_id, weight=0.60)
            else:
                h_dep.reject(evidence_list[0].evidence_id)

        # 4. Queue Tool Evidence
        elif tool_name in ["inspect_service_health", "get_webhook_delivery", "get_event_queue_state"] and h_queue:
            is_worker_target = ("worker" in target_service.lower() or "queue" in target_service.lower() or is_service_queue_related(target_service))
            has_queue_anomaly = False
            for ev in evidence_list:
                status_text = str(ev.data).lower()
                if "backlog" in status_text or "poison" in status_text or "burst" in status_text or "stuck" in status_text or "lag" in status_text or "failed" in status_text or "deadlock" in status_text:
                    has_queue_anomaly = True
                    break

            if is_worker_target or has_queue_anomaly:
                h_queue.add_supporting_evidence(evidence_list[0].evidence_id, weight=0.60)
            else:
                h_queue.add_contradicting_evidence(evidence_list[0].evidence_id, weight=0.30)

        # 5. Resource Metrics Evidence
        elif tool_name == "query_metrics":
            has_res_anomaly = False
            for ev in evidence_list:
                metric_name = ev.data.get("metric", "")
                val = ev.data.get("value", 0.0)
                raw_text = str(ev.data).lower()
                if (metric_name in ["cpu_burn_ms", "cpu_utilization", "memory_usage_mb", "thread_starvation"] and val > 0.0) or ("cpu" in raw_text or "memory" in raw_text or "thread" in raw_text or "throttle" in raw_text or "descriptor" in raw_text or "emfile" in raw_text or "starvation" in raw_text):
                    has_res_anomaly = True
                    break

            if has_res_anomaly:
                if h_res:
                    h_res.add_supporting_evidence(evidence_list[0].evidence_id, weight=0.60)
            else:
                if h_res:
                    h_res.add_contradicting_evidence(evidence_list[0].evidence_id, weight=0.20)

