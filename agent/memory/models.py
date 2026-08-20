# Historical Incident Memory Models
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class HistoricalIncidentExperience(BaseModel):
    experience_id: str
    incident_id: str
    scenario_id: str
    service: str
    symptom: str
    root_cause_service: str
    root_cause_category: str
    successful_tool_sequence: List[str] = Field(default_factory=list)
    failed_tool_sequence: List[str] = Field(default_factory=list)
    successful_remediation_action: str
    time_to_diagnosis_ms: float
    tool_calls_count: int
    resolution_status: str = "RESOLVED"
    recorded_at: float = Field(default_factory=time.time)
