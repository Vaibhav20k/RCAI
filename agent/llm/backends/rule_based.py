# Rule-Based Baseline LLM Backend
import json
from typing import Dict, Any, Optional
from agent.llm.interface import BaseLLMBackend
from agent.hypothesis.models import HypothesisCategory

class RuleBasedLLMBackend(BaseLLMBackend):
    name: str = "rule_based"
    model_name: str = "deterministic-rules-baseline"

    def _call_model_raw(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None
    ) -> str:
        prompt_lower = prompt.lower()
        schema_title = str(json_schema.get("title", "") if json_schema else "").lower()
        schema_props = set(json_schema.get("properties", {}).keys() if json_schema else [])

        # Extract target service dynamically from active topology or prompt
        import re
        from discovery.registry import get_current_topology_services
        active_services = list(get_current_topology_services())

        target_service = None
        match = re.search(r"(?:affected target service|affected service|target service|service):\s*([a-zA-Z0-9_\-]+)", prompt, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if extracted in active_services or not active_services:
                target_service = extracted

        if not target_service:
            for svc in active_services:
                if svc.lower() in prompt_lower:
                    target_service = svc
                    break

        if not target_service:
            target_service = active_services[0] if active_services else "order-service"


        # 1. Root Cause Diagnosis Schema matching
        if "rootcause" in schema_title or "root_cause_category" in schema_props or "root_cause_service" in schema_props:
            cat = HypothesisCategory.DEPLOYMENT
            if "database" in prompt_lower or "latency" in prompt_lower or "unindexed" in prompt_lower or "lock" in prompt_lower:
                cat = HypothesisCategory.DATABASE
            elif "bank" in prompt_lower or "dependency" in prompt_lower or "503" in prompt_lower:
                cat = HypothesisCategory.DEPENDENCY
            elif "cpu" in prompt_lower or "resource" in prompt_lower or "burn" in prompt_lower or "saturation" in prompt_lower:
                cat = HypothesisCategory.RESOURCE
            elif "queue" in prompt_lower or "backlog" in prompt_lower:
                cat = HypothesisCategory.QUEUE

            return json.dumps({
                "root_cause_service": target_service,
                "root_cause_category": cat.value,
                "description": f"Heuristic root cause identification: {cat.value} on {target_service}",
                "confidence": 0.75,
                "reasoning": f"Derived from symptom keywords in prompt: {prompt[:80]}"
            })

        # 2. Playbook Selection Schema matching
        elif "playbook" in schema_title or "action" in schema_props:
            # First check explicit diagnosed category if available
            if "diagnosed category: database" in prompt_lower or "category: database" in prompt_lower or ("database" in prompt_lower and "diagnosed category:" not in prompt_lower):
                action = "optimize_db_index"
                params = {}
                rationale = f"Optimize table index and query execution on {target_service}"
            elif "diagnosed category: dependency" in prompt_lower or "category: dependency" in prompt_lower or ("dependency" in prompt_lower and "diagnosed category:" not in prompt_lower):
                action = "circuit_breaker"
                params = {"trip_threshold": 5}
                rationale = f"Engage fast-fail circuit breaker for degraded downstream partner dependency"
            elif "diagnosed category: resource" in prompt_lower or "category: resource" in prompt_lower or ("resource" in prompt_lower and "diagnosed category:" not in prompt_lower):
                action = "restart_service"
                params = {}
                rationale = f"Restart service worker processes to clear CPU/memory saturation on {target_service}"
            elif "diagnosed category: queue" in prompt_lower or "category: queue" in prompt_lower or ("queue" in prompt_lower and "diagnosed category:" not in prompt_lower):
                action = "scale_replicas"
                params = {"replicas": 3}
                rationale = f"Scale worker queue consumer pool to drain message backlog on {target_service}"
            elif "diagnosed category: deployment" in prompt_lower or "category: deployment" in prompt_lower or "deploy" in prompt_lower:
                action = "rollback_version"
                params = {"target_version": "1.0.0"}
                rationale = f"Rollback faulty release on {target_service} to known baseline version"
            else:
                action = "restart_service"
                params = {}
                rationale = f"Heuristic restart for {target_service}"

            return json.dumps({
                "action": action,
                "target": target_service,
                "params": params,
                "rationale": rationale,
                "risk_level": "LOW"
            })

        # 3. Hypothesis Generation Schema matching
        elif "hypothesisgeneration" in schema_title or "hypotheses" in schema_props:
            hypotheses = [
                {
                    "target_service": target_service,
                    "category": HypothesisCategory.DATABASE.value,
                    "description": f"Database query latency regression or lock contention on {target_service}",
                    "confidence": 0.35 if ("db" in prompt_lower or "latency" in prompt_lower or "unindexed" in prompt_lower) else 0.20,
                    "next_action": "query_db_metrics"
                },
                {
                    "target_service": target_service,
                    "category": HypothesisCategory.DEPLOYMENT.value,
                    "description": f"Recent software deployment or configuration release introduced bugs in {target_service}",
                    "confidence": 0.35 if ("deploy" in prompt_lower or "release" in prompt_lower or "version" in prompt_lower or "error rate" in prompt_lower) else 0.20,
                    "next_action": "inspect_deployment_history"
                },
                {
                    "target_service": target_service,
                    "category": HypothesisCategory.DEPENDENCY.value,
                    "description": f"Downstream dependency service or partner API latency/outage affecting {target_service}",
                    "confidence": 0.35 if ("bank" in prompt_lower or "dependency" in prompt_lower or "timeout" in prompt_lower or "503" in prompt_lower) else 0.20,
                    "next_action": "inspect_dependency_health"
                },
                {
                    "target_service": target_service,
                    "category": HypothesisCategory.RESOURCE.value,
                    "description": f"CPU, memory pressure, or thread starvation on {target_service}",
                    "confidence": 0.35 if ("cpu" in prompt_lower or "memory" in prompt_lower or "burn" in prompt_lower or "saturation" in prompt_lower) else 0.20,
                    "next_action": "query_metrics"
                },
                {
                    "target_service": target_service,
                    "category": HypothesisCategory.QUEUE.value,
                    "description": f"Asynchronous queue backlog or stuck message consumer impacting {target_service}",
                    "confidence": 0.35 if ("queue" in prompt_lower or "worker" in prompt_lower or "backlog" in prompt_lower or "lag" in prompt_lower) else 0.20,
                    "next_action": "inspect_service_health"
                }
            ]
            return json.dumps({
                "reasoning": f"Rule-based diagnostic heuristic analysis of symptom: {prompt[:100]}",
                "hypotheses": hypotheses
            })

        return json.dumps({"status": "OK", "reasoning": "Rule-based fallback response"})
