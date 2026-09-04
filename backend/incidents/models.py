# Incident Models with Strict Ground-Truth Isolation
import time
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class IncidentStatus(str, Enum):
    NEW = "NEW"
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    HYPOTHESES_GENERATED = "HYPOTHESES_GENERATED"
    EVIDENCE_COLLECTING = "EVIDENCE_COLLECTING"
    ROOT_CAUSE_PROPOSED = "ROOT_CAUSE_PROPOSED"
    REMEDIATION_PENDING = "REMEDIATION_PENDING"
    REMEDIATION_EXECUTED = "REMEDIATION_EXECUTED"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    ESCALATED = "ESCALATED"

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class GroundTruth(BaseModel):
    root_cause_service: str
    root_cause_type: str
    description: str
    injected_fault_config: Dict[str, Any] = Field(default_factory=dict)
    expected_remediation: str
    verification_criteria: Dict[str, Any] = Field(default_factory=dict)

class AgentIncidentView(BaseModel):
    incident_id: str
    scenario_id: str
    started_at: float
    detected_at: float
    severity: IncidentSeverity
    service: str
    symptom: str
    status: IncidentStatus
    incident_window: Dict[str, float]
    data_source: str = "simulated"
    target_mode: str = "SIMULATED"

class Incident(BaseModel):
    incident_id: str = Field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:8]}")
    scenario_id: str
    started_at: float = Field(default_factory=time.time)
    detected_at: float = Field(default_factory=time.time)
    severity: IncidentSeverity = IncidentSeverity.HIGH
    service: str
    symptom: str
    status: IncidentStatus = IncidentStatus.DETECTED
    incident_window: Dict[str, float] = Field(default_factory=dict)
    data_source: str = Field(default="simulated", description="'simulator' or 'live'")
    target_mode: str = Field(default="SIMULATED", description="'LIVE', 'SIMULATED', or 'UNREACHABLE'")
    ground_truth: Optional[GroundTruth] = Field(
        default=None,
        description="External ground truth hidden from the AI agent"
    )

    def to_agent_view(self) -> AgentIncidentView:
        return AgentIncidentView(
            incident_id=self.incident_id,
            scenario_id=self.scenario_id,
            started_at=self.started_at,
            detected_at=self.detected_at,
            severity=self.severity,
            service=self.service,
            symptom=self.symptom,
            status=self.status,
            incident_window=self.incident_window,
            data_source=self.data_source,
            target_mode=self.target_mode
        )
