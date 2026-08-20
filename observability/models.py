# Normalized Evidence and Telemetry Data Models
import hashlib
import time
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class EvidenceSource(str, Enum):
    METRICS = "metrics"
    LOGS = "logs"
    TRACES = "traces"
    DEPLOYMENTS = "deployments"
    CONFIGS = "configs"
    DATABASE = "database"

class EvidenceType(str, Enum):
    METRIC_SERIES = "metric_series"
    LOG_RECORD = "log_record"
    TRACE_SPAN = "trace_span"
    DEPLOYMENT_EVENT = "deployment_event"
    CONFIG_SNAPSHOT = "config_snapshot"
    DATABASE_METRIC = "database_metric"

class EvidenceProvenance(BaseModel):
    collector: str
    query: str
    raw_source_id: Optional[str] = None
    hash_signature: str
    recorded_at: float = Field(default_factory=time.time)

class NormalizedEvidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:8]}")
    source: EvidenceSource
    evidence_type: EvidenceType
    timestamp: float = Field(default_factory=time.time)
    incident_window: Dict[str, float] = Field(default_factory=dict, description="Window with start_ts and end_ts")
    data: Dict[str, Any] = Field(default_factory=dict)
    summary: str = Field(description="Human/AI-readable summary of the observed telemetry signal")
    provenance: EvidenceProvenance
    derived: bool = False
    reliability: float = Field(default=1.0, ge=0.0, le=1.0, description="Data source reliability score [0.0, 1.0]")

    @classmethod
    def create(
        cls,
        source: EvidenceSource,
        evidence_type: EvidenceType,
        summary: str,
        data: Dict[str, Any],
        query: str,
        collector: str,
        incident_window: Optional[Dict[str, float]] = None,
        derived: bool = False,
        reliability: float = 1.0,
        timestamp: Optional[float] = None
    ) -> "NormalizedEvidence":
        ts = timestamp or time.time()
        raw_signature = f"{source}:{evidence_type}:{query}:{ts}:{str(data)}"
        hash_sig = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()[:16]
        
        prov = EvidenceProvenance(
            collector=collector,
            query=query,
            hash_signature=hash_sig,
            recorded_at=time.time()
        )
        return cls(
            source=source,
            evidence_type=evidence_type,
            timestamp=ts,
            incident_window=incident_window or {"start_ts": ts - 300, "end_ts": ts},
            data=data,
            summary=summary,
            provenance=prov,
            derived=derived,
            reliability=reliability
        )
