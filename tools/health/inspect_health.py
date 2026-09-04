# Tools: inspect_service_health and inspect_dependency_health
import time
from typing import Optional, Dict, Any
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from simulator.services.runner import InProcessCluster
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType

class InspectServiceHealthTool(BaseTool):
    name: str = "inspect_service_health"
    description: str = "Query live HTTP health check and uptime status for a service"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 0.5

    def __init__(self, cluster: Optional[InProcessCluster] = None):
        super().__init__(
            name="inspect_service_health",
            description="Query live HTTP health check and uptime status for a service"
        )
        self._cluster = cluster

    def set_cluster(self, cluster: InProcessCluster) -> None:
        self._cluster = cluster

    def execute(self, service: str, **kwargs) -> ToolResult:
        t0 = time.perf_counter()

        from discovery.registry import get_current_topology
        from observability.live_http.collector import global_live_http_collector
        topo = get_current_topology()
        node = topo.nodes.get(service)

        if node and node.mode == "LIVE" and node.ports:
            active_port = node.metrics_port or node.ports[0]
            res = global_live_http_collector.query_service_health("127.0.0.1", active_port)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            is_up = res.get("is_healthy", False)
            status_text = "UP" if is_up else "DOWN"
            status_code = res.get("status_code", 0)

            ev = NormalizedEvidence.create(
                source=EvidenceSource.METRICS,
                evidence_type=EvidenceType.METRIC_SERIES,
                summary=f"Live HTTP socket probe on {service} (port {active_port}): status={status_code} ({status_text})",
                data={
                    "service": service,
                    "status_code": status_code,
                    "is_up": is_up,
                    "body": res.get("body", {}),
                    "error": res.get("error"),
                    "is_live": True,
                    "probe_target": f"http://127.0.0.1:{active_port}/health"
                },
                query=f"live_http.get(url=http://127.0.0.1:{active_port}/health)",
                collector="LiveHttpCollector",
                reliability=0.99
            )

            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=[ev],
                duration_ms=duration_ms
            )

        if not self._cluster:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message="Cluster not connected",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

        clients = {
            "api-gateway": self._cluster.gateway_client,
            "order-service": self._cluster.order_client,
            "payment-service": self._cluster.payment_client,
            "dependency-service": self._cluster.dep_client,
            "worker-service": self._cluster.worker_client,
        }
        client = clients.get(service)
        if not client:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.NO_EVIDENCE_FOUND,
                error_message=f"Service not found in topology: {service}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

        try:
            resp = client.get("/health")
            duration_ms = (time.perf_counter() - t0) * 1000.0
            data = resp.json()
            is_up = (resp.status_code == 200 and data.get("status") == "UP")
            status_text = "UP" if is_up else "DEGRADED"
            
            ev = NormalizedEvidence.create(
                source=EvidenceSource.METRICS,
                evidence_type=EvidenceType.METRIC_SERIES,
                summary=f"Service health on {service}: status={resp.status_code} ({status_text})",
                data={"status_code": resp.status_code, "health_payload": data, "is_up": is_up},
                query=f"inspect_service_health(service={service})",
                collector="ServiceHealthClient",
                reliability=1.0
            )
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=[ev],
                raw_output={"status_code": resp.status_code, "data": data},
                duration_ms=duration_ms
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Failed to query health: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

class InspectDependencyHealthTool(BaseTool):
    name: str = "inspect_dependency_health"
    description: str = "Query health status of third-party external dependencies"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, cluster: Optional[InProcessCluster] = None):
        super().__init__(
            name="inspect_dependency_health",
            description="Query health status of third-party external dependencies"
        )
        self._cluster = cluster

    def set_cluster(self, cluster: InProcessCluster) -> None:
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        t0 = time.perf_counter()
        if not self._cluster:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message="Cluster not connected",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

        try:
            resp = self._cluster.dep_client.get("/api/v1/bank/status")
            duration_ms = (time.perf_counter() - t0) * 1000.0
            data = resp.json() if resp.status_code == 200 else {"status": "UNHEALTHY"}
            status_text = data.get("status", "UNKNOWN")
            
            ev = NormalizedEvidence.create(
                source=EvidenceSource.METRICS,
                evidence_type=EvidenceType.METRIC_SERIES,
                summary=f"Dependency status for Bank Gateway: {status_text}",
                data={"status_code": resp.status_code, "data": data},
                query="inspect_dependency_health()",
                collector="DependencyClient",
                reliability=0.95
            )
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.SUCCESS,
                evidence=[ev],
                raw_output={"status_code": resp.status_code, "data": data},
                duration_ms=duration_ms
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status=ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE,
                error_message=f"Dependency check failed: {str(exc)}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )
