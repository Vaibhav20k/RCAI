# Tool: query_metrics
import time
from typing import Optional, Dict, Any
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.metrics.collector import MetricsCollector
from observability.normalizer import TelemetryNormalizer

class QueryMetricsTool(BaseTool):
    name: str = "query_metrics"
    description: str = "Query Prometheus telemetry metrics for a service (error rates, requests, latency)"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        super().__init__(
            name="query_metrics",
            description="Query Prometheus telemetry metrics for a service (error rates, requests, latency)"
        )
        self._collector = metrics_collector

    def set_collector(self, collector: MetricsCollector) -> None:
        self._collector = collector

    def execute(self, service: str, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        if not self._collector:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message="MetricsCollector not connected to active cluster",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

        try:
            stats = self._collector.calculate_service_health_stats(service)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            if "error" in stats:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolExecutionStatus.NO_EVIDENCE_FOUND,
                    error_message=stats["error"],
                    duration_ms=duration_ms
                )

            ev1 = TelemetryNormalizer.normalize_metric_summary(
                service_name=service,
                metric_name="error_rate",
                metric_value=stats["error_rate"],
                unit="ratio",
                query=f"query_metrics(service={service})"
            )
            ev2 = TelemetryNormalizer.normalize_metric_summary(
                service_name=service,
                metric_name="total_requests",
                metric_value=stats["total_requests"],
                unit="count",
                query=f"query_metrics(service={service})"
            )
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=[ev1, ev2],
                raw_output=stats,
                duration_ms=duration_ms
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Metrics source unavailable: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )
