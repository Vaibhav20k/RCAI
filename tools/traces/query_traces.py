# Tool: query_traces
import time
from typing import Optional, List, Dict, Any
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.tracing.collector import global_trace_collector
from observability.normalizer import TelemetryNormalizer

class QueryTracesTool(BaseTool):
    name: str = "query_traces"
    description: str = "Query distributed traces and spans filtered by service, duration, or errors"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.5

    def execute(
        self,
        service: Optional[str] = None,
        min_duration_ms: Optional[float] = None,
        only_errors: bool = False,
        limit: int = 20
    ) -> ToolResult:
        t0 = time.perf_counter()
        try:
            spans = global_trace_collector.query_spans(
                service=service,
                min_duration_ms=min_duration_ms,
                only_errors=only_errors,
                limit=limit
            )
            duration_ms = (time.perf_counter() - t0) * 1000.0
            if not spans:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolExecutionStatus.NO_EVIDENCE_FOUND,
                    error_message="No trace spans matched the filter criteria",
                    duration_ms=duration_ms
                )

            evidence_items = [
                TelemetryNormalizer.normalize_trace_span(s, query=f"query_traces(service={service})")
                for s in spans
            ]
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=evidence_items,
                raw_output={"count": len(spans), "spans": [s.model_dump() for s in spans]},
                duration_ms=duration_ms
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Tracing backend unavailable: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )
