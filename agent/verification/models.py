# Root-Cause Decision and Incident Report Models
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.incidents.models import AgentIncidentView
from agent.hypothesis.models import HypothesisCategory
from agent.policies.models import RemediationProposal

class RootCauseDecision(BaseModel):
    decision_id: str
    incident_id: str
    root_cause_service: str
    root_cause_category: HypothesisCategory
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    provenance_audit: List[Dict[str, Any]] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    is_unknown: bool = False
    decision_timestamp: float = Field(default_factory=time.time)

class IncidentReport(BaseModel):
    report_id: str
    incident: AgentIncidentView
    root_cause_decision: RootCauseDecision
    hypotheses_evaluated_count: int
    tool_calls_executed_count: int
    investigation_duration_ms: float
    executive_summary: str
    evidence_trail: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    recommended_proposal: Optional[RemediationProposal] = None
    created_at: float = Field(default_factory=time.time)
