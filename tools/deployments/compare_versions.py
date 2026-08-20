# Tool: compare_versions
import time
from typing import Optional, Dict, Any
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.deployments.store import global_deployment_store
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType

class CompareVersionsTool(BaseTool):
    name: str = "compare_versions"
    description: str = "Compare current active version against previous version for a microservice"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 0.5

    def execute(self, service: str, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        try:
            history = global_deployment_store.get_service_history(service)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            if not history:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolExecutionStatus.NO_EVIDENCE_FOUND,
                    error_message=f"No version history for service {service}",
                    duration_ms=duration_ms
                )

            latest = history[-1]
            prev = history[-2] if len(history) >= 2 else None
            prev_ver = prev.version if prev else "none"
            prev_cfg = prev.config_version if prev else "none"
            
            diff_summary = {
                "service": service,
                "current_version": latest.version,
                "current_config": latest.config_version,
                "previous_version": prev_ver,
                "previous_config": prev_cfg,
                "last_change_description": latest.change_description,
                "deployed_at": latest.deployed_at
            }
            
            ev = NormalizedEvidence.create(
                source=EvidenceSource.DEPLOYMENTS,
                evidence_type=EvidenceType.DEPLOYMENT_EVENT,
                summary=f"Version diff on {service}: current={latest.version}, previous={prev_ver}, change={latest.change_description}",
                data=diff_summary,
                query=f"compare_versions(service={service})",
                collector="DeploymentStore",
                reliability=1.0
            )
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=[ev],
                raw_output=diff_summary,
                duration_ms=duration_ms
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Version comparison failed: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )
