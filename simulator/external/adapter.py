# External Microservice Environment Adapter & Telemetry Ingestion Bridge
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType
from backend.incidents.models import AgentIncidentView, IncidentSeverity

class ExternalServiceTelemetrySnapshot(BaseModel):
    service_name: str
    endpoint_url: str
    prometheus_metrics: Dict[str, float] = Field(default_factory=dict)
    recent_error_logs: List[str] = Field(default_factory=list)
    span_durations_ms: Dict[str, float] = Field(default_factory=dict)
    active_version: str = "1.0.0"

class ExternalEnvironmentAdapter:
    def __init__(self, external_services: Optional[Dict[str, ExternalServiceTelemetrySnapshot]] = None):
        self.services = external_services or {
            "frontend-proxy": ExternalServiceTelemetrySnapshot(
                service_name="frontend-proxy",
                endpoint_url="http://external-boutique:8080",
                prometheus_metrics={"http_requests_total": 1200.0, "http_errors_total": 0.0, "p95_latency_ms": 18.0}
            ),
            "recommendation-service": ExternalServiceTelemetrySnapshot(
                service_name="recommendation-service",
                endpoint_url="http://external-boutique:8081",
                prometheus_metrics={"cpu_utilization": 0.25, "memory_usage_mb": 210.0}
            ),
            "cart-service": ExternalServiceTelemetrySnapshot(
                service_name="cart-service",
                endpoint_url="http://external-boutique:8082",
                prometheus_metrics={"redis_connection_errors": 0.0, "p95_latency_ms": 12.0}
            )
        }

    def inject_external_anomaly(self, service_name: str, metric_name: str, value: float) -> None:
        if service_name in self.services:
            self.services[service_name].prometheus_metrics[metric_name] = value

    def scrape_external_evidence(self, service_name: str) -> List[NormalizedEvidence]:
        svc = self.services.get(service_name)
        if not svc:
            return []

        ev_list = []
        for metric, val in svc.prometheus_metrics.items():
            ev = NormalizedEvidence.create(
                source=EvidenceSource.METRICS,
                evidence_type=EvidenceType.METRIC_SERIES,
                collector="ExternalPrometheusScraper",
                summary=f"External metric {metric}={val} on {service_name}",
                data={"service": service_name, "metric": metric, "value": val},
                query=f"scrape(service={service_name}, metric={metric})",
                reliability=0.99
            )
            ev_list.append(ev)
        return ev_list
