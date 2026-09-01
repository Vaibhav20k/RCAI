# Remediation Playbook Definitions & Data Models
import time
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field
from agent.policies.models import RemediationActionType, RemediationRiskLevel
from agent.hypothesis.models import HypothesisCategory

class PlaybookDefinition(BaseModel):
    name: str = Field(description="Unique canonical identifier for the playbook")
    version: str = Field(default="1.0.0", description="Semantic version of this playbook specification")
    description: str = Field(description="Clear explanation of the action, applicability, and operational effects")
    action_type: RemediationActionType = Field(description="Associated remediation action type enum")
    required_parameters: List[str] = Field(default_factory=list, description="List of required parameter keys")
    optional_parameters: Dict[str, Any] = Field(default_factory=dict, description="Optional parameter keys with default values")
    risk_level: RemediationRiskLevel = Field(default=RemediationRiskLevel.LOW, description="Safety risk classification")
    applicable_categories: List[HypothesisCategory] = Field(default_factory=list, description="Failure categories this playbook resolves")
    reversal_procedure: str = Field(description="Documented procedure to revert or rollback the remediation if unsuccessful")
    idempotency_key_format: str = Field(default="{action}:{target}", description="Template string for duplicate detection key")
