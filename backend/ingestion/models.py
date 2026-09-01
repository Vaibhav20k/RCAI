# Live Alert Ingestion Data Models (Prometheus Alertmanager, Sentry, Datadog)
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AlertmanagerAlert(BaseModel):
    status: str = Field(default="firing", description="'firing' or 'resolved'")
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None

class AlertmanagerPayload(BaseModel):
    version: str = "4"
    groupKey: Optional[str] = None
    status: str = "firing"
    receiver: Optional[str] = None
    groupLabels: Dict[str, str] = Field(default_factory=dict)
    commonLabels: Dict[str, str] = Field(default_factory=dict)
    commonAnnotations: Dict[str, str] = Field(default_factory=dict)
    externalURL: Optional[str] = None
    alerts: List[AlertmanagerAlert] = Field(default_factory=list)

class AlertIngestionResult(BaseModel):
    status: str = "PROCESSED"
    total_alerts_received: int
    incidents_created: List[str] = Field(default_factory=list)
    investigations_started: List[str] = Field(default_factory=list)
    duplicates_skipped: int = 0
    errors: List[str] = Field(default_factory=list)
    processed_at: float = Field(default_factory=time.time)
