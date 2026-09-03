# Live Alert Normalizer: Maps Alertmanager & Cloud Alerts to Incident Models
import time
import datetime
from typing import Dict, Any, Optional
from backend.ingestion.models import AlertmanagerAlert
from backend.incidents.models import Incident, IncidentSeverity, IncidentStatus
from discovery.registry import get_current_topology_services

class AlertNormalizer:
    @staticmethod
    def parse_iso_timestamp(ts_str: Optional[str]) -> float:
        if not ts_str:
            return time.time()
        try:
            clean_ts = ts_str.replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(clean_ts)
            return dt.timestamp()
        except Exception:
            return time.time()

    @classmethod
    def resolve_target_service(cls, alert: AlertmanagerAlert) -> str:
        labels = alert.labels
        valid_services = get_current_topology_services()

        # 1. Direct label checks
        for key in ["service", "app", "job", "component", "microservice", "target_service"]:
            val = labels.get(key, "").strip().lower()
            if val in valid_services:
                return val

        # 2. Check alertname or annotations for topology keywords (exact and unhyphenated)
        search_blob = f"{labels.get('alertname', '')} {alert.annotations.get('summary', '')} {alert.annotations.get('description', '')}".lower()
        search_blob_clean = search_blob.replace("-", "").replace("_", "")

        for svc in valid_services:
            svc_clean = svc.replace("-", "")
            if svc in search_blob or svc_clean in search_blob_clean:
                return svc

        # Check domain service roots
        if "order" in search_blob_clean and "order-service" in valid_services:
            return "order-service"
        elif ("payment" in search_blob_clean or "settlement" in search_blob_clean) and "payment-service" in valid_services:
            return "payment-service"
        elif ("worker" in search_blob_clean or "queue" in search_blob_clean) and "worker-service" in valid_services:
            return "worker-service"
        elif ("dependency" in search_blob_clean or "bank" in search_blob_clean) and "dependency-service" in valid_services:
            return "dependency-service"
        elif ("gateway" in search_blob_clean or "ingress" in search_blob_clean) and "api-gateway" in valid_services:
            return "api-gateway"

        # Fallback to api-gateway or first recognized service
        if "api-gateway" in valid_services:
            return "api-gateway"
        elif valid_services:
            return sorted(list(valid_services))[0]
        return "unknown"


    @classmethod
    def resolve_severity(cls, alert: AlertmanagerAlert) -> IncidentSeverity:
        raw_sev = alert.labels.get("severity", "high").strip().lower()
        if raw_sev in ["critical", "fatal", "p1", "page", "disaster"]:
            return IncidentSeverity.CRITICAL
        elif raw_sev in ["high", "error", "p2"]:
            return IncidentSeverity.HIGH
        elif raw_sev in ["medium", "warning", "warn", "p3"]:
            return IncidentSeverity.MEDIUM
        elif raw_sev in ["low", "info", "p4"]:
            return IncidentSeverity.LOW
        return IncidentSeverity.HIGH

    @classmethod
    def normalize_alertmanager_alert(
        cls,
        alert: AlertmanagerAlert,
        scenario_id: Optional[str] = None
    ) -> Incident:
        service = cls.resolve_target_service(alert)
        severity = cls.resolve_severity(alert)
        starts_at = cls.parse_iso_timestamp(alert.startsAt)
        detected_at = time.time()
        end_ts = max(detected_at, starts_at + 60.0)
        start_ts = starts_at - 300.0

        # Extract symptom summary from annotations or alertname
        alertname = alert.labels.get("alertname", "ProductionAnomalyDetected")
        desc = alert.annotations.get("description") or alert.annotations.get("summary") or alert.annotations.get("message")
        if desc:
            symptom = f"[{alertname}] {desc}"
        else:
            symptom = f"[{alertname}] Anomaly detected on {service} (severity: {severity.value})"

        fp = alert.fingerprint or f"{service}_{int(starts_at)}"
        inc_id = f"inc_alert_{fp[:8]}"
        sc_id = scenario_id or f"live_alert_{service}_{int(starts_at)}"

        return Incident(
            incident_id=inc_id,
            scenario_id=sc_id,
            started_at=starts_at,
            detected_at=detected_at,
            severity=severity,
            service=service,
            symptom=symptom,
            status=IncidentStatus.DETECTED,
            incident_window={"start_ts": start_ts, "end_ts": end_ts}
        )
