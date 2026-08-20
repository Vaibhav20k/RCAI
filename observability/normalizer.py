# Unified Telemetry Normalizer
import time
from typing import Dict, Any, List, Optional
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType
from observability.logs.collector import LogEntry
from observability.tracing.collector import Span
from observability.deployments.store import DeploymentRecord

class TelemetryNormalizer:
    @staticmethod
    def normalize_log_entry(entry: LogEntry, query: str = "logs.query") -> NormalizedEvidence:
        summary = f"[{entry.service}] {entry.level} event={entry.event}: {entry.message}"
        return NormalizedEvidence.create(
            source=EvidenceSource.LOGS,
            evidence_type=EvidenceType.LOG_RECORD,
            summary=summary,
            data=entry.model_dump(),
            query=query,
            collector="LogCollector",
            timestamp=entry.timestamp,
            reliability=0.95
        )

    @staticmethod
    def normalize_trace_span(span: Span, query: str = "traces.query") -> NormalizedEvidence:
        summary = f"Span {span.service_name}:{span.operation} duration={span.duration_ms:.2f}ms status={span.status_code}"
        return NormalizedEvidence.create(
            source=EvidenceSource.TRACES,
            evidence_type=EvidenceType.TRACE_SPAN,
            summary=summary,
            data=span.model_dump(),
            query=query,
            collector="TraceCollector",
            timestamp=span.start_time,
            reliability=0.98
        )

    @staticmethod
    def normalize_deployment_record(record: DeploymentRecord, query: str = "deployments.query") -> NormalizedEvidence:
        summary = f"Deployment on {record.service}: version={record.version} status={record.status} at {record.deployed_at}"
        return NormalizedEvidence.create(
            source=EvidenceSource.DEPLOYMENTS,
            evidence_type=EvidenceType.DEPLOYMENT_EVENT,
            summary=summary,
            data=record.model_dump(),
            query=query,
            collector="DeploymentStore",
            timestamp=record.deployed_at,
            reliability=1.0
        )

    @staticmethod
    def normalize_metric_summary(
        service_name: str,
        metric_name: str,
        metric_value: float,
        unit: str,
        query: str = "metrics.query"
    ) -> NormalizedEvidence:
        summary = f"Metric {metric_name} on {service_name}: {metric_value} {unit}"
        return NormalizedEvidence.create(
            source=EvidenceSource.METRICS,
            evidence_type=EvidenceType.METRIC_SERIES,
            summary=summary,
            data={
                "service": service_name,
                "metric": metric_name,
                "value": metric_value,
                "unit": unit,
                "timestamp": time.time()
            },
            query=query,
            collector="MetricsCollector",
            reliability=0.99
        )
