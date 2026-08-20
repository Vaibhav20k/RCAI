# Deterministic Incident Detector
import time
from typing import List, Optional, Dict, Any
from backend.incidents.models import Incident, IncidentStatus, IncidentSeverity
from observability.metrics.collector import MetricsCollector

class IncidentDetector:
    def __init__(
        self,
        metrics_collector: MetricsCollector,
        error_rate_threshold: float = 0.05,
        latency_p95_threshold_ms: float = 60.0
    ):
        self.metrics_collector = metrics_collector
        self.error_rate_threshold = error_rate_threshold
        self.latency_p95_threshold_ms = latency_p95_threshold_ms

    def detect_incidents_from_metrics(
        self,
        scenario_id: str = "detected_runtime",
        known_ground_truth: Optional[Any] = None
    ) -> List[Incident]:
        incidents: List[Incident] = []
        if not self.metrics_collector.cluster:
            return incidents

        service_map = self.metrics_collector.cluster.get_service_map()
        
        for service_name in service_map.keys():
            stats = self.metrics_collector.calculate_service_health_stats(service_name)
            if "error" in stats:
                continue

            error_rate = stats.get("error_rate", 0.0)
            active_faults = stats.get("active_faults", 0.0)
            
            # Anomaly condition: Error rate violation or explicit active fault presence
            if error_rate > self.error_rate_threshold or active_faults > 0:
                severity = IncidentSeverity.CRITICAL if error_rate > 0.5 else IncidentSeverity.HIGH
                symptom = (
                    f"Elevated error rate {error_rate*100:.1f}% on {service_name}"
                    if error_rate > 0
                    else f"Active telemetry anomaly detected on {service_name}"
                )
                
                now = time.time()
                inc = Incident(
                    scenario_id=scenario_id,
                    started_at=now - 60,
                    detected_at=now,
                    severity=severity,
                    service=service_name,
                    symptom=symptom,
                    status=IncidentStatus.DETECTED,
                    incident_window={"start_ts": now - 300, "end_ts": now},
                    ground_truth=known_ground_truth
                )
                incidents.append(inc)

        return incidents
