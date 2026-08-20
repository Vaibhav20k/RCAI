# Inspectable Investigation State Model
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.incidents.models import AgentIncidentView
from agent.hypothesis.models import HypothesisSet, Hypothesis, HypothesisStatus
from observability.models import NormalizedEvidence
from tools.base import ToolResult

class InvestigationActionRecord(BaseModel):
    step_index: int
    tool_name: str
    arguments: Dict[str, Any]
    result_status: str
    evidence_ids: List[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    selection_reason: str = ""
    estimated_cost: float = 1.0
    hypothesis_impact: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)

class InvestigationState(BaseModel):
    investigation_id: str
    incident: AgentIncidentView
    hypothesis_set: HypothesisSet
    evidence_store: Dict[str, NormalizedEvidence] = Field(default_factory=dict)
    action_history: List[InvestigationActionRecord] = Field(default_factory=list)
    budget_max_tool_calls: int = 15
    budget_max_seconds: float = 60.0
    start_time: float = Field(default_factory=time.time)
    current_step: int = 0
    is_completed: bool = False
    stop_reason: Optional[str] = None
    final_root_cause_hypothesis: Optional[Hypothesis] = None
