# Structured Escalation Models for Human SRE Hand-off
import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.incidents.models import IncidentSeverity

class EscalationBrief(BaseModel):
    brief_id: str = Field(default_factory=lambda: f"esc_{uuid.uuid4().hex[:8]}")
    incident_id: str
    service: str
    severity: IncidentSeverity
    symptom: str
    escalation_reason: str
    top_hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_gathered: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_sre_actions: List[str] = Field(default_factory=list)
    escalated_at: float = Field(default_factory=time.time)
    notification_channels: List[str] = Field(default_factory=list)
    dispatch_status: str = "DISPATCHED"
