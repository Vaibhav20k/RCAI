# Tool: query_metrics
import time
from typing import Optional, Dict, Any, Union
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.metrics.collector import MetricsCollector
from observability.live.adapter import LivePrometheusAdapter, LiveTelemetryNormalizer
from observability.normalizer import TelemetryNormalizer
from backend.config import get_settings

class QueryMetricsTool(BaseTool):
    name: str = "query_metrics"
    description: str = "Query Prometheus telemetry metrics for a service (error rates, requests, latency, CPU)"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, metrics_collector: Optional[Union[MetricsCollector, LivePrometheusAdapter]] = None):
        super().__init__(
            name="query_metrics",
            description="Query Prometheus telemetry metrics for a service (error rates, requests, latency, CPU)"
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

        from discovery.registry import get_current_topology
        from observability.live_http.collector import global_live_http_collector
        topo = get_current_topology()
        node = topo.nodes.get(service)

        if node and node.mode == "LIVE" and node.ports:
            active_port = node.metrics_port or node.ports[0]
            metrics_data = global_live_http_collector.scrape_service_metrics("127.0.0.1", active_port)
            duration_ms = (time.perf_counter() - t0) * 1000.0

            if metrics_data.get("status") == "UP":
                evidence_items = []
                err_ev = global_live_http_collector.normalize_live_metric(
                    service=service,
                    metric_name="error_rate",
                    metric_value=metrics_data.get("error_rate", 0.0),
                    unit="ratio"
                )
                evidence_items.append(err_ev)

                req_ev = global_live_http_collector.normalize_live_metric(
                    service=service,
                    metric_name="total_requests",
                    metric_value=metrics_data.get("total_requests", 0.0),
                    unit="count"
                )
                evidence_items.append(req_ev)

                for g_name, g_val in metrics_data.get("gauges", {}).items():
                    g_ev = global_live_http_collector.normalize_live_metric(
                        service=service,
                        metric_name=g_name,
                        metric_value=g_val
                    )
                    evidence_items.append(g_ev)

                return ToolResult(
                    tool_name=self.name,
                    status=ToolExecutionStatus.SUCCESS,
                    evidence=evidence_items,
                    duration_ms=duration_ms
                )
            else:
                # Scrape failed on live socket
                return ToolResult(
                    tool_name=self.name,
                    status=ToolExecutionStatus.ERROR,
                    error_message=f"Failed to scrape metrics from live port {active_port}: {metrics_data.get('error')}",
                    duration_ms=duration_ms
                )

        if not self._collector:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message="MetricsCollector not connected to active cluster or live Prometheus endpoint",
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

            # Check for resource saturation anomalies
            has_res_fault = False
            is_live = getattr(self._collector, "is_live_telemetry", False) or isinstance(self._collector, LivePrometheusAdapter)
            
            if not is_live and hasattr(self._collector, "cluster") and self._collector.cluster:
                svc_map = self._collector.cluster.get_service_map()
                svc = svc_map.get(service)
                if svc:
                    faults = svc.fault_injector.get_active_faults()
                    has_res_fault = any(f.fault_type.value == "resource_saturation" for f in faults)
            elif is_live:
                has_res_fault = stats.get("cpu_burn_ms", 0.0) > 0.0 or stats.get("active_faults", 0.0) > 0.0

            if is_live:
                ev1 = LiveTelemetryNormalizer.normalize_prometheus_metric(
                    service=service,
                    metric_name="error_rate",
                    metric_value=stats.get("error_rate", 0.0),
                    unit="ratio",
                    query=f"query_metrics(service={service})"
                )
                ev2 = LiveTelemetryNormalizer.normalize_prometheus_metric(
                    service=service,
                    metric_name="total_requests",
                    metric_value=stats.get("total_requests", 0.0),
                    unit="count",
                    query=f"query_metrics(service={service})"
                )
                ev3 = LiveTelemetryNormalizer.normalize_prometheus_metric(
                    service=service,
                    metric_name="cpu_burn_ms",
                    metric_value=stats.get("cpu_burn_ms", 80.0 if has_res_fault else 0.0),
                    unit="ms",
                    query=f"query_metrics(service={service})"
                )
            else:
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
                ev3 = TelemetryNormalizer.normalize_metric_summary(
                    service_name=service,
                    metric_name="cpu_burn_ms",
                    metric_value=80.0 if has_res_fault else 0.0,
                    unit="ms",
                    query=f"query_metrics(service={service})"
                )

            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=[ev1, ev2, ev3],
                raw_output={**stats, "has_resource_anomaly": has_res_fault},
                duration_ms=duration_ms
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Metrics source unavailable: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )
