# RCAI Live HTTP Telemetry Collector & Service Liveness Prober
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
import httpx

from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType

logger = logging.getLogger("rcai.observability.live_http")

class ServiceLivenessProbe(BaseModel):
    service_id: str
    is_live: bool = False
    port: Optional[int] = None
    health_url: Optional[str] = None
    health_status_code: Optional[int] = None
    health_data: Dict[str, Any] = Field(default_factory=dict)
    has_metrics: bool = False
    metrics_port: Optional[int] = None
    metrics_url: Optional[str] = None
    error: Optional[str] = None
    probed_at: float = Field(default_factory=time.time)

class LiveHttpCollector:
    """
    Direct HTTP socket collector and liveness prober for services running natively
    on the host OS or in unmanaged containers (e.g. without a Docker daemon socket).
    
    Provides real socket validation over GET /health and GET /metrics.
    """

    def __init__(self, timeout_seconds: float = 2.0, client: Optional[httpx.Client] = None):
        self.timeout_seconds = timeout_seconds
        self._custom_client = client

    def _get_client(self) -> httpx.Client:
        if self._custom_client is not None:
            return self._custom_client
        return httpx.Client(timeout=self.timeout_seconds)

    def probe_service_liveness(
        self,
        service_id: str,
        ports: List[int],
        target_host: str = "127.0.0.1",
        health_path: str = "/health",
        metrics_path: str = "/metrics"
    ) -> ServiceLivenessProbe:
        """
        Probes candidate ports for a discovered service over real TCP/HTTP.
        Determines whether the service is actively listening, and whether it exposes
        a valid health check or Prometheus metrics endpoint.
        """
        probe = ServiceLivenessProbe(service_id=service_id)
        if not ports:
            probe.error = f"No ports mapped for service '{service_id}'"
            return probe

        # Avoid probing standard DB raw TCP ports with HTTP GET
        excluded_raw_db_ports = {5432, 3306, 6379, 27017, 11211}
        candidate_ports = [p for p in ports if p not in excluded_raw_db_ports]
        if not candidate_ports:
            # If only DB ports exist, do a basic TCP check or mark not HTTP
            probe.error = f"Service '{service_id}' only exposes raw datastore ports ({ports})"
            return probe

        last_error = None
        for port in candidate_ports:
            # 1. Probe Health Endpoint
            h_url = f"http://{target_host}:{port}{health_path}"
            try:
                with self._get_client() as client:
                    resp = client.get(h_url)
                    if resp.status_code == 200:
                        probe.is_live = True
                        probe.port = port
                        probe.health_url = h_url
                        probe.health_status_code = 200
                        try:
                            probe.health_data = resp.json()
                        except Exception:
                            probe.health_data = {"raw": resp.text[:512]}
                        break
                    else:
                        last_error = f"HTTP {resp.status_code} at {h_url}"
            except httpx.ConnectError:
                last_error = f"Connection refused at {h_url}"
            except httpx.TimeoutException:
                last_error = f"Connection timed out at {h_url}"
            except Exception as exc:
                last_error = f"Probe failed at {h_url}: {str(exc)}"

        if not probe.is_live:
            probe.error = last_error or f"No response on ports {candidate_ports}"
            return probe

        # 2. Probe Metrics Endpoint on the active port (or other ports)
        active_port = probe.port or candidate_ports[0]
        m_url = f"http://{target_host}:{active_port}{metrics_path}"
        try:
            with self._get_client() as client:
                m_resp = client.get(m_url)
                if m_resp.status_code == 200:
                    text_sample = m_resp.text[:1024]
                    if "# HELP" in text_sample or "# TYPE" in text_sample or "promhttp" in text_sample:
                        probe.has_metrics = True
                        probe.metrics_port = active_port
                        probe.metrics_url = m_url
        except Exception:
            pass

        return probe

    def scrape_service_metrics(
        self,
        target_host: str,
        port: int,
        metrics_path: str = "/metrics"
    ) -> Dict[str, Any]:
        """Scrapes real Prometheus-format plain text metrics from http://host:port/metrics."""
        url = f"http://{target_host}:{port}{metrics_path}"
        try:
            with self._get_client() as client:
                resp = client.get(url)
                resp.raise_for_status()
                text = resp.text
        except Exception as exc:
            logger.warning(f"Failed to scrape metrics from {url}: {exc}")
            return {
                "status": "UNREACHABLE",
                "error": str(exc),
                "is_live_telemetry": False
            }

        # Parse basic Prometheus metrics lines
        counters: Dict[str, float] = {}
        gauges: Dict[str, float] = {}

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                name_and_labels = parts[0]
                val_str = parts[1]
                m_name = name_and_labels.split("{")[0]
                try:
                    val = float(val_str)
                    if "total" in m_name or "count" in m_name:
                        counters[m_name] = val
                    else:
                        gauges[m_name] = val
                except ValueError:
                    continue

        total_requests = counters.get("http_requests_total", counters.get("requests_total", 0.0))
        error_requests = counters.get("http_errors_total", counters.get("errors_total", 0.0))
        error_rate = (error_requests / total_requests) if total_requests > 0 else 0.0

        return {
            "status": "UP",
            "url": url,
            "total_requests": total_requests,
            "error_requests": error_requests,
            "error_rate": round(error_rate, 4),
            "gauges": gauges,
            "counters": counters,
            "is_live_telemetry": True
        }

    def query_service_health(
        self,
        target_host: str,
        port: int,
        health_path: str = "/health"
    ) -> Dict[str, Any]:
        """Queries the real HTTP /health endpoint of a target service."""
        url = f"http://{target_host}:{port}{health_path}"
        try:
            with self._get_client() as client:
                resp = client.get(url)
                is_healthy = resp.status_code == 200
                try:
                    body = resp.json()
                except Exception:
                    body = {"text": resp.text[:512]}
                return {
                    "status_code": resp.status_code,
                    "is_healthy": is_healthy,
                    "body": body,
                    "url": url,
                    "is_live": True
                }
        except Exception as exc:
            return {
                "status_code": 0,
                "is_healthy": False,
                "error": str(exc),
                "url": url,
                "is_live": False
            }

    def normalize_live_metric(
        self,
        service: str,
        metric_name: str,
        metric_value: float,
        unit: str = "",
        query: str = "",
        raw_data: Optional[Dict[str, Any]] = None
    ) -> NormalizedEvidence:
        ts = time.time()
        unit_str = f" {unit}".rstrip()
        summary = f"Live HTTP metric {metric_name} on {service}: {metric_value}{unit_str}"
        payload = {
            "service": service,
            "metric": metric_name,
            "value": metric_value,
            "unit": unit,
            "timestamp": ts,
            **(raw_data or {})
        }
        return NormalizedEvidence.create(
            source=EvidenceSource.METRICS,
            evidence_type=EvidenceType.METRIC_SERIES,
            summary=summary,
            data=payload,
            query=query or f"http.get(service={service},metric={metric_name})",
            collector="LiveHttpCollector",
            reliability=0.99,
            timestamp=ts
        )

# Global singleton
global_live_http_collector = LiveHttpCollector()
