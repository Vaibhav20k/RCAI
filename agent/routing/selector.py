# Dynamic Evidence Action Selector / Utility Router
from typing import Dict, Any, List, Optional, Tuple
from agent.hypothesis.models import HypothesisSet, HypothesisStatus, HypothesisCategory
from tools.registry import ToolRegistry

class EvidenceSelector:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    def select_next_action(
        self,
        hypothesis_set: HypothesisSet,
        executed_actions: List[Tuple[str, str]], # (tool_name, service)
        target_service: str
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        # Compute diagnostic utility = Expected hypothesis distinction / action cost
        active_hypotheses = hypothesis_set.get_active_hypotheses()
        if not active_hypotheses:
            return None

        # Prioritize actions linked to the highest uncertainty active hypotheses
        sorted_hypo = sorted(active_hypotheses, key=lambda h: abs(h.confidence - 0.5), reverse=False)

        action_map = {
            HypothesisCategory.DATABASE: ("query_db_metrics", {"service": target_service}),
            HypothesisCategory.DEPLOYMENT: ("inspect_deployment_history", {"service": target_service}),
            HypothesisCategory.DEPENDENCY: ("inspect_dependency_health", {}),
            HypothesisCategory.RESOURCE: ("query_metrics", {"service": target_service}),
            HypothesisCategory.QUEUE: ("inspect_service_health", {"service": target_service}),
        }

        # First pass: try next action for the most uncertain hypothesis
        for h in sorted_hypo:
            candidate = action_map.get(h.category)
            if candidate:
                tool_name, args = candidate
                action_key = (tool_name, str(args.get("service", "")))
                if action_key not in executed_actions:
                    return (tool_name, args)

        # Fallback diagnostics: query_logs, query_traces, compare_versions
        fallbacks = [
            ("compare_versions", {"service": target_service}),
            ("query_logs", {"service": target_service, "level": "ERROR"}),
            ("query_traces", {"service": target_service, "only_errors": True}),
            ("query_metrics", {"service": target_service}),
        ]
        for tool_name, args in fallbacks:
            action_key = (tool_name, str(args.get("service", "")))
            if action_key not in executed_actions:
                return (tool_name, args)

        return None
