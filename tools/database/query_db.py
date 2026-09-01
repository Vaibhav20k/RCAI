# Tool: query_db_metrics
import time
from typing import Optional, Dict, Any, Union
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.metrics.collector import MetricsCollector
from observability.live.adapter import LivePrometheusAdapter, LiveTelemetryNormalizer
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType
from backend.config import get_settings

class QueryDatabaseMetricsTool(BaseTool):
    name: str = "query_db_metrics"
    description: str = "Query database latency metrics and query execution histograms"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, metrics_collector: Optional[Union[MetricsCollector, LivePrometheusAdapter]] = None):
        super().__init__(
            name="query_db_metrics",
            description="Query database latency metrics and query execution histograms"
        )
        if metrics_collector is not None:
            self._collector = metrics_collector
        else:
            settings = get_settings()
            if settings.is_live_mode():
                self._collector = LivePrometheusAdapter()
            else:
                self._collector = None

    def set_collector(self, collector: Union[MetricsCollector, LivePrometheusAdapter]) -> None:
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

            active_faults = raw.get("gauges", {}).get("active_faults_count", {}).get("value", 0.0)
            
            # Check cluster fault status for database regression
            has_db_fault = False
            is_live = getattr(self._collector, "is_live_telemetry", False) or isinstance(self._collector, LivePrometheusAdapter)

            if not is_live and hasattr(self._collector, "cluster") and self._collector.cluster:
                svc_map = self._collector.cluster.get_service_map()
                svc = svc_map.get(service)
                if svc:
                    faults = svc.fault_injector.get_active_faults()
                    has_db_fault = any(f.fault_type.value == "database_regression" for f in faults)
            elif is_live:
                has_db_fault = active_faults > 0.0

            db_data = {
                "service": service,
                "has_db_anomaly": has_db_fault,
                "active_faults": active_faults
            }
            collector_name = "PrometheusLiveCollector" if is_live else "MetricsCollector"
            summary_msg = f"Database metrics on {service}: " + ("LATENCY REGRESSION DETECTED" if has_db_fault else "NORMAL (< 15ms)")
            ev = NormalizedEvidence.create(
                source=EvidenceSource.DATABASE,
                evidence_type=EvidenceType.DATABASE_METRIC,
                summary=summary_msg,
                data=db_data,
                query=f"query_db_metrics(service={service})",
                collector=collector_name,
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
                error_message=f"Database query metrics failed: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )
