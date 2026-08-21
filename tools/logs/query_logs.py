# Tool: query_logs
import time
from typing import Optional, List, Dict, Any
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.logs.collector import global_log_collector
from observability.normalizer import TelemetryNormalizer

class QueryLogsTool(BaseTool):
    name: str = "query_logs"
    description: str = "Query centralized structured logs by service, level, keyword, or time window"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def execute(
        self,
        service: Optional[str] = None,
        level: Optional[str] = None,
        keyword: Optional[str] = None,
        window_seconds: float = 300.0,
        limit: int = 50
    ) -> ToolResult:
        t0 = time.perf_counter()
        try:
            start_ts = time.time() - window_seconds
            logs = global_log_collector.query_logs(
                service=service,
                level=level,
                keyword=keyword,
                start_ts=start_ts,
                limit=limit
            )
            duration_ms = (time.perf_counter() - t0) * 1000.0
            
            if not logs:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolExecutionStatus.NO_EVIDENCE_FOUND,
                    duration_ms=duration_ms,
                    error_message="No log entries matched the filter criteria"
                )

            evidence_items = [
                TelemetryNormalizer.normalize_log_entry(l, query=f"query_logs(service={service},level={level})")
                for l in logs
            ]
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=evidence_items,
                raw_output={"count": len(logs), "logs": [l.model_dump() for l in logs]},
                duration_ms=duration_ms
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Log storage query error: {str(exc)}",
                duration_ms=duration_ms
            )
