# Scenario Specification Models
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from simulator.faults.models import FaultConfig, FaultType
from backend.incidents.models import GroundTruth, IncidentSeverity

class ScenarioDefinition(BaseModel):
    scenario_id: str
    name: str
    description: str
    service: str
    severity: IncidentSeverity
    symptom_description: str
    fault_config: FaultConfig
    deployment_event: Optional[Dict[str, Any]] = None
    ground_truth: GroundTruth
    baseline_traffic_count: int = 10
    incident_traffic_count: int = 20
