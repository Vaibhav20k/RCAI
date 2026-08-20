# Dynamic Evidence Action Selector / Utility Router with Historical Memory Integration
from typing import Dict, Any, List, Optional, Tuple
from agent.hypothesis.models import HypothesisSet, HypothesisStatus, HypothesisCategory
from tools.registry import ToolRegistry
from agent.memory.store import HistoricalMemoryStore, global_memory_store

class EvidenceSelector:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        memory_store: Optional[HistoricalMemoryStore] = None,
        use_memory: bool = True
    ):
        self.tool_registry = tool_registry
        self.memory_store = memory_store or global_memory_store
        self.use_memory = use_memory

    def select_next_action(
        self,
        hypothesis_set: HypothesisSet,
        executed_actions: List[Tuple[str, str]], # (tool_name, service)
        target_service: str,
        symptom_text: str = ""
    ) -> Optional[Tuple[str, Dict[str, Any]]]:
        # 1. Experience-Guided Strategy Prioritization if memory is enabled
        if self.use_memory and self.memory_store and symptom_text:
            recommended_tools = self.memory_store.get_recommended_actions(target_service, symptom_text)
            for tool_name in recommended_tools:
                args = {"service": target_service} if tool_name not in ["inspect_dependency_health"] else {}
                action_key = (tool_name, str(args.get("service", "")))
                if action_key not in executed_actions and self.tool_registry.get_tool(tool_name):
                    return (tool_name, args)

        # 2. Dynamic Hypothesis Uncertainty Utility Ranking
        active_hypotheses = hypothesis_set.get_active_hypotheses()
        if not active_hypotheses:
            return None

        sorted_hypo = sorted(active_hypotheses, key=lambda h: abs(h.confidence - 0.5), reverse=False)

        action_map = {
            HypothesisCategory.DATABASE: ("query_db_metrics", {"service": target_service}),
            HypothesisCategory.DEPLOYMENT: ("inspect_deployment_history", {"service": target_service}),
            HypothesisCategory.DEPENDENCY: ("inspect_dependency_health", {}),
            HypothesisCategory.RESOURCE: ("query_metrics", {"service": target_service}),
            HypothesisCategory.QUEUE: ("inspect_service_health", {"service": target_service}),
        }

        for h in sorted_hypo:
            candidate = action_map.get(h.category)
            if candidate:
                tool_name, args = candidate
                action_key = (tool_name, str(args.get("service", "")))
                if action_key not in executed_actions and self.tool_registry.get_tool(tool_name):
                    return (tool_name, args)

        # 3. Fallback General Diagnostics
        fallbacks = [
            ("compare_versions", {"service": target_service}),
            ("query_logs", {"service": target_service, "level": "ERROR"}),
            ("query_traces", {"service": target_service, "only_errors": True}),
            ("query_metrics", {"service": target_service}),
        ]
        for tool_name, args in fallbacks:
            action_key = (tool_name, str(args.get("service", "")))
            if action_key not in executed_actions and self.tool_registry.get_tool(tool_name):
                return (tool_name, args)

        return None
