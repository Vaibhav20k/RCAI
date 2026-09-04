# Remediation Outcome Verification Engine
import time
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from backend.incidents.models import Incident, IncidentStatus
from agent.policies.models import RemediationProposal
from simulator.services.runner import InProcessCluster
from simulator.traffic.generator import TrafficGenerator
from observability.metrics.collector import MetricsCollector
from backend.config import get_settings

class OutcomeVerificationResult(BaseModel):
    incident_id: str
    proposal_id: str
    target_service: str
    is_recovered: bool
    status: str # RESOLVED, REMEDIATION_FAILED, ROLLED_BACK_AND_ESCALATED
    pre_metrics: Dict[str, Any]
    post_metrics: Dict[str, Any]
    verification_summary: str
    data_source: str = Field(default="simulated", description="'simulated' or 'live'")
    target_mode: str = Field(default="SIMULATED", description="'LIVE', 'SIMULATED', or 'UNREACHABLE'")
    verified_at: float = Field(default_factory=time.time)

class RemediationOutcomeVerifier:
    def __init__(self, cluster: InProcessCluster, metrics_collector: Optional[MetricsCollector] = None):
        self.cluster = cluster
        self.metrics_collector = metrics_collector or MetricsCollector(cluster)

    def capture_metrics_snapshot(self, service: str) -> Dict[str, Any]:
        from discovery.registry import get_current_topology
        from observability.live_http.collector import global_live_http_collector
        topo = get_current_topology()
        node = topo.nodes.get(service)

        if node and node.mode == "LIVE" and node.ports:
            # Query real live HTTP endpoint
            active_port = node.metrics_port or node.ports[0]
            live_health = global_live_http_collector.query_service_health("127.0.0.1", active_port)
            live_metrics = global_live_http_collector.scrape_service_metrics("127.0.0.1", active_port)
            return {
                "error_rate": live_metrics.get("error_rate", 0.0),
                "active_faults": 0.0 if live_health.get("is_healthy") else 1.0,
                "is_healthy": live_health.get("is_healthy", False),
                "total_requests": live_metrics.get("total_requests", 0.0),
                "is_live": True
            }

        stats = self.metrics_collector.calculate_service_health_stats(service)
        client_map = {
            "api-gateway": self.cluster.gateway_client,
            "order-service": self.cluster.order_client,
            "payment-service": self.cluster.payment_client,
            "dependency-service": self.cluster.dep_client,
            "worker-service": self.cluster.worker_client,
        }
        client = client_map.get(service)
        if not client and hasattr(self.cluster, "get_service_map"):
            svc = self.cluster.get_service_map().get(service)
            if svc and hasattr(svc, "app"):
                from starlette.testclient import TestClient
                client = TestClient(svc.app)

        is_healthy = False
        if client:
            try:
                resp = client.get("/health")
                is_healthy = (resp.status_code == 200)
            except Exception:
                is_healthy = False

        return {
            "error_rate": stats.get("error_rate", 0.0),
            "active_faults": stats.get("active_faults", 0.0),
            "is_healthy": is_healthy,
            "total_requests": stats.get("total_requests", 0.0),
            "is_live": False
        }

    def verify_remediation_outcome(
        self,
        proposal: RemediationProposal,
        pre_metrics: Dict[str, Any],
        incident: Optional[Incident] = None,
        test_traffic_count: int = 15
    ) -> OutcomeVerificationResult:
        from discovery.registry import get_current_topology
        service = proposal.target_service
        topo = get_current_topology()
        node = topo.nodes.get(service)
        target_mode = node.mode if node else "SIMULATED"
        data_source = "live" if target_mode == "LIVE" else "simulated"

        if target_mode == "LIVE":
            post_metrics = self.capture_metrics_snapshot(service)
            is_recovered = (post_metrics.get("is_healthy", False) is True and post_metrics.get("error_rate", 0.0) <= 0.05)
            if is_recovered:
                status_label = "RESOLVED"
                summary = f"Live Remediation SUCCESS: {service} verified healthy over HTTP socket. Error rate {post_metrics.get('error_rate', 0.0):.3f}."
                if incident:
                    incident.status = IncidentStatus.RESOLVED
            else:
                status_label = "REMEDIATION_FAILED"
                summary = f"Live Remediation FAILED: {service} remains degraded or unreachable over HTTP socket."
                if incident:
                    incident.status = IncidentStatus.UNRESOLVED

            return OutcomeVerificationResult(
                incident_id=proposal.incident_id,
                proposal_id=proposal.proposal_id,
                target_service=service,
                is_recovered=is_recovered,
                status=status_label,
                pre_metrics=pre_metrics,
                post_metrics=post_metrics,
                verification_summary=summary,
                data_source=data_source,
                target_mode=target_mode
            )

        gen = TrafficGenerator(client=self.cluster.gateway_client, seed=101)
        traffic_stats = gen.generate_batch(count=test_traffic_count)
        post_metrics = self.capture_metrics_snapshot(service)
        post_metrics["post_traffic_error_rate"] = traffic_stats.error_rate
        post_metrics["post_traffic_p95_ms"] = traffic_stats.p95_latency_ms

        is_recovered = (
            post_metrics.get("is_healthy", False) is True
            and post_metrics.get("active_faults", 0.0) == 0.0
            and traffic_stats.error_rate <= 0.05
        )

        if is_recovered:
            status_label = "RESOLVED"
            summary = f"Remediation SUCCESS: {service} verified healthy (SIMULATED). Error rate {traffic_stats.error_rate:.3f}, p95 {traffic_stats.p95_latency_ms}ms."
            if incident:
                incident.status = IncidentStatus.RESOLVED
        else:
            status_label = "REMEDIATION_FAILED"
            summary = f"Remediation FAILED: {service} remains degraded after intervention."
            if incident:
                incident.status = IncidentStatus.UNRESOLVED

        return OutcomeVerificationResult(
            incident_id=proposal.incident_id,
            proposal_id=proposal.proposal_id,
            target_service=service,
            is_recovered=is_recovered,
            status=status_label,
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            verification_summary=summary,
            data_source=data_source,
            target_mode=target_mode
        )

def get_outcome_verifier(
    cluster: Optional[InProcessCluster] = None,
    metrics_collector: Optional[MetricsCollector] = None
) -> Union[RemediationOutcomeVerifier, Any]:
    settings = get_settings()
    if settings.DATA_SOURCE == "live":
        from agent.verification.live_outcome import LiveRemediationOutcomeVerifier
        return LiveRemediationOutcomeVerifier()
    return RemediationOutcomeVerifier(cluster or InProcessCluster(), metrics_collector)
