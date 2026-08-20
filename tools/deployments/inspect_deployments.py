# Tool: inspect_deployment_history
import time
from typing import Optional, List, Dict, Any
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.deployments.store import global_deployment_store
from observability.normalizer import TelemetryNormalizer

class InspectDeploymentHistoryTool(BaseTool):
    name: str = "inspect_deployment_history"
    description: str = "Inspect recent software version deployments and configuration releases"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 0.5

    def execute(
        self,
        service: Optional[str] = None,
        window_seconds: float = 3600.0
    ) -> ToolResult:
        t0 = time.perf_counter()
        try:
            if service:
                records = global_deployment_store.get_service_history(service)
            else:
                records = global_deployment_store.query_recent_deployments(window_seconds)

            duration_ms = (time.perf_counter() - t0) * 1000.0
            if not records:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolExecutionStatus.NO_EVIDENCE_FOUND,
                    error_message="No deployments recorded in the requested window",
                    duration_ms=duration_ms
                )

            evidence_items = [
                TelemetryNormalizer.normalize_deployment_record(r, query=f"inspect_deployment_history(service={service})")
                for r in records
            ]
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=evidence_items,
                raw_output={"count": len(records), "deployments": [r.model_dump() for r in records]},
                duration_ms=duration_ms
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Deployment store unavailable: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )
