# Tool: query_db_metrics
import time
from typing import Optional, Dict, Any
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.metrics.collector import MetricsCollector
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType

class QueryDatabaseMetricsTool(BaseTool):
    name: str = "query_db_metrics"
    description: str = "Query database latency metrics and query execution histograms"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        super().__init__(
            name="query_db_metrics",
            description="Query database latency metrics and query execution histograms"
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
                error_message="MetricsCollector not connected",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

        try:
            raw = self._collector.query_service_metrics(service)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            if "error" in raw:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolExecutionStatus.NO_EVIDENCE_FOUND,
                    error_message=raw["error"],
                    duration_ms=duration_ms
                )

            histograms = raw.get("histograms", {})
            db_samples = histograms.get("db_query_duration_seconds_bucket", [])
            
            db_data = {
                "service": service,
                "db_query_samples_count": len(db_samples),
                "active_faults": raw.get("gauges", {}).get("active_faults_count", {}).get("value", 0.0)
            }
            ev = NormalizedEvidence.create(
                source=EvidenceSource.DATABASE,
                evidence_type=EvidenceType.DATABASE_METRIC,
                summary=f"Database query histogram metrics on {service}: {len(db_samples)} bucket samples",
                data=db_data,
                query=f"query_db_metrics(service={service})",
                collector="MetricsCollector",
                reliability=0.99
            )
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=[ev],
                raw_output=db_data,
                duration_ms=duration_ms
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Database metric query error: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )
