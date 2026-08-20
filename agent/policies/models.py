# Policy Engine Models
import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from tools.base import ToolPermission

class RemediationActionType(str, Enum):
    ROLLBACK_VERSION = "rollback_version"
    RESTART_WORKERS = "restart_workers"
    OPTIMIZE_DB_INDEX = "optimize_db_index"
    CIRCUIT_BREAKER = "circuit_breaker"
    SCALE_WORKERS = "scale_workers"
    FORBIDDEN_COMMAND = "forbidden_command"

class RemediationRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RemediationProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:8]}")
    incident_id: str
    action_type: RemediationActionType
    target_service: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RemediationRiskLevel = RemediationRiskLevel.LOW
    rationale: str
    proposed_at: float = Field(default_factory=time.time)

class PolicyCheckResult(BaseModel):
    is_allowed: bool
    requires_human_approval: bool = False
    policy_code: str # ALLOWED, DENIED_UNKNOWN_SERVICE, DENIED_INACTIVE_INCIDENT, DENIED_DUPLICATE_ACTION, DENIED_FORBIDDEN_ACTION
    rejection_reason: Optional[str] = None
    approval_token: Optional[str] = None
