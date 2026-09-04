# Base Tool Framework with Strict Contracts and Safety Permissions
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from observability.models import NormalizedEvidence

class ToolPermission(str, Enum):
    READ_ONLY = "READ_ONLY"
    RECOMMEND = "RECOMMEND"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CONTROLLED_EXECUTION = "CONTROLLED_EXECUTION"
    FORBIDDEN = "FORBIDDEN"

class ToolExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NO_EVIDENCE_FOUND = "NO_EVIDENCE_FOUND"
    EVIDENCE_SOURCE_UNAVAILABLE = "EVIDENCE_SOURCE_UNAVAILABLE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ERROR = "ERROR"

class ToolResult(BaseModel):
    tool_name: str
    status: ToolExecutionStatus
    evidence: List[NormalizedEvidence] = Field(default_factory=list)
    raw_output: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    duration_ms: float = 0.0

    def __init__(self, **data):
        if "evidence_items" in data and "evidence" not in data:
            data["evidence"] = data.pop("evidence_items")
        super().__init__(**data)

class BaseTool(BaseModel):
    name: str
    description: str
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    timeout_seconds: float = 5.0
    cost_estimate: float = 1.0

    def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError("Subclasses must implement execute")
