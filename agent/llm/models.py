# Structured Schemas for Constrained LLM Inference
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from agent.hypothesis.models import HypothesisCategory

class HypothesisItemSchema(BaseModel):
    target_service: str = Field(description="Target microservice name associated with this hypothesis")
    category: HypothesisCategory = Field(description="Category of the incident root cause hypothesis")
    description: str = Field(description="Detailed diagnostic hypothesis explanation")
    confidence: float = Field(default=0.25, ge=0.0, le=1.0, description="Initial Bayesian confidence prior [0.0, 1.0]")
    next_action: Optional[str] = Field(default=None, description="Recommended initial diagnostic tool name")

class HypothesisGenerationResponseSchema(BaseModel):
    reasoning: str = Field(description="Chain-of-thought diagnostic reasoning synthesizing observed symptoms and telemetry")
    hypotheses: List[HypothesisItemSchema] = Field(description="Structured list of candidate root cause hypotheses")

class PlaybookSelectionSchema(BaseModel):
    action: str = Field(description="Name of the selected remediation playbook from the approved catalogue")
    target: str = Field(description="Target microservice name to execute the remediation against")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters required by the selected playbook function")
    rationale: str = Field(description="Human-readable justification for selecting this playbook based on evidence")
    risk_level: str = Field(default="LOW", description="Risk classification: LOW, MEDIUM, HIGH, or CRITICAL")

class RootCauseDiagnosisSchema(BaseModel):
    root_cause_service: str = Field(description="Verified faulty microservice or UNKNOWN")
    root_cause_category: HypothesisCategory = Field(description="Root cause category classification")
    description: str = Field(description="Root cause explanation grounded in collected evidence")
    confidence: float = Field(default=0.75, ge=0.0, le=1.0, description="Final posterior confidence score")
    reasoning: str = Field(description="Detailed diagnostic synthesis of supporting and contradicting evidence")

class LLMInferenceResult(BaseModel):
    raw_text: str = ""
    parsed_data: Optional[Any] = None
    is_valid: bool = True
    attempts: int = 1
    backend_name: str = "rule_based"
    model_name: str = "default"
    duration_ms: float = 0.0
    error_message: Optional[str] = None
