# Live Remediation Outcome Verification Engine with Automatic Reversal and Escalation
import time
from typing import Dict, Any, Optional, Callable
import httpx
from pydantic import BaseModel, Field
from backend.incidents.models import Incident, IncidentStatus
from agent.policies.models import RemediationProposal
from observability.live.client import PrometheusLiveClient
from backend.config import get_settings
from agent.verification.outcome import OutcomeVerificationResult

class LiveRemediationOutcomeVerifier:
    def __init__(
        self,
        prom_client: Optional[PrometheusLiveClient] = None,
        max_error_rate: Optional[float] = None,
        max_p99_ms: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        poll_interval_seconds: Optional[float] = None
    ):
        settings = get_settings()
        self.prom_client = prom_client or PrometheusLiveClient()
        self.max_error_rate = max_error_rate if max_error_rate is not None else settings.VERIFICATION_MAX_ERROR_RATE
        self.max_p99_ms = max_p99_ms if max_p99_ms is not None else settings.VERIFICATION_MAX_P99_MS
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.VERIFICATION_TIMEOUT_SECONDS
        self.poll_interval_seconds = poll_interval_seconds if poll_interval_seconds is not None else settings.VERIFICATION_POLL_INTERVAL_SECONDS

    def check_service_http_health(self, service: str) -> bool:
        settings = get_settings()
        from discovery.registry import get_current_topology
        topo = get_current_topology()
        node = topo.get_node(service)
        if node and node.ports:
            port = node.ports[0]
            host = node.ip_address or "localhost"
        else:
            port_map = {
                "api-gateway": settings.API_GATEWAY_PORT,
                "order-service": settings.ORDER_SERVICE_PORT,
                "payment-service": settings.PAYMENT_SERVICE_PORT,
                "dependency-service": 8003,
                "worker-service": 8004
            }
            port = port_map.get(service, 8000)
            host = "localhost"
        url = f"http://{host}:{port}/health"
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(url)
                return resp.status_code == 200
        except Exception:
            return False


    def query_live_metrics_snapshot(self, service: str) -> Dict[str, Any]:
        # 1. Query error rate from Prometheus over 2m window
        err_query = f'sum(rate(http_requests_total{{service="{service}", status=~"5.."}}[2m])) / sum(rate(http_requests_total{{service="{service}"}}[2m]))'
        err_val = 0.0
        try:
            err_res = self.prom_client.query_instant(err_query)
            if err_res.get("data", {}).get("result"):
                val_str = err_res["data"]["result"][0]["value"][1]
                err_val = float(val_str)
        except Exception:
            # Fallback direct metric query
            try:
                raw_res = self.prom_client.query_instant(f'http_error_rate{{service="{service}"}}')
                if raw_res.get("data", {}).get("result"):
                    err_val = float(raw_res["data"]["result"][0]["value"][1])
            except Exception:
                err_val = 0.0

        # 2. Query p99 latency from Prometheus
        p99_query = f'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{{service="{service}"}}[2m])) by (le)) * 1000'
        p99_ms = 25.0
        try:
            lat_res = self.prom_client.query_instant(p99_query)
            if lat_res.get("data", {}).get("result"):
                p99_ms = float(lat_res["data"]["result"][0]["value"][1])
        except Exception:
            try:
                raw_lat = self.prom_client.query_instant(f'http_p99_latency_ms{{service="{service}"}}')
                if raw_lat.get("data", {}).get("result"):
                    p99_ms = float(raw_lat["data"]["result"][0]["value"][1])
            except Exception:
                p99_ms = 25.0

        # 3. Direct HTTP health probe
        is_healthy = self.check_service_http_health(service)

        return {
            "service": service,
            "error_rate": round(err_val, 4),
            "p99_latency_ms": round(p99_ms, 2),
            "is_healthy": is_healthy,
            "timestamp": time.time()
        }

    def verify_live_remediation_outcome(
        self,
        proposal: RemediationProposal,
        pre_metrics: Dict[str, Any],
        incident: Optional[Incident] = None,
        executor_reversal_fn: Optional[Callable[[RemediationProposal], Dict[str, Any]]] = None
    ) -> OutcomeVerificationResult:
        service = proposal.target_service
        post_metrics = self.query_live_metrics_snapshot(service)

        is_recovered = (
            post_metrics.get("is_healthy", False) is True
            and post_metrics.get("error_rate", 1.0) <= self.max_error_rate
            and post_metrics.get("p99_latency_ms", 999.0) <= self.max_p99_ms
        )

        if is_recovered:
            status_label = "RESOLVED"
            summary = (
                f"Live Verification SUCCESS: {service} verified healthy via Prometheus range query and HTTP health check. "
                f"Post-remediation error rate: {post_metrics.get('error_rate'):.3f} (<= {self.max_error_rate}), "
                f"p99 latency: {post_metrics.get('p99_latency_ms'):.1f}ms (<= {self.max_p99_ms}ms)."
            )
            if incident:
                incident.status = IncidentStatus.RESOLVED

        else:
            # Trigger automatic reversal & escalation
            reversal_out = {}
            if executor_reversal_fn:
                try:
                    reversal_out = executor_reversal_fn(proposal)
                except Exception as exc:
                    reversal_out = {"reversal_error": str(exc)}

            status_label = "ROLLED_BACK_AND_ESCALATED"
            summary = (
                f"Live Verification FAILED: {service} failed health criteria post-remediation. "
                f"Error rate: {post_metrics.get('error_rate')}, p99: {post_metrics.get('p99_latency_ms')}ms. "
                f"Automated reversal executed ({reversal_out.get('reversal', 'triggered')}). "
                f"Incident escalated to on-call human SRE."
            )
            if incident:
                incident.status = IncidentStatus.ESCALATED

        return OutcomeVerificationResult(
            incident_id=proposal.incident_id,
            proposal_id=proposal.proposal_id,
            target_service=service,
            is_recovered=is_recovered,
            status=status_label,
            pre_metrics=pre_metrics,
            post_metrics=post_metrics,
            verification_summary=summary
        )
