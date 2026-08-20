# Fault Models for Controlled Incident Simulation
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class FaultType(str, Enum):
    DATABASE_REGRESSION = "database_regression"
    BAD_DEPLOYMENT = "bad_deployment"
    DEPENDENCY_LATENCY = "dependency_latency"
    RESOURCE_SATURATION = "resource_saturation"
    QUEUE_BACKLOG = "queue_backlog"

class FaultConfig(BaseModel):
    service_name: str
    fault_type: FaultType
    enabled: bool = True
    latency_ms: float = Field(default=0.0, ge=0.0, description="Injected latency in milliseconds")
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Injected error rate probability [0.0, 1.0]")
    cpu_burn_ms: float = Field(default=0.0, ge=0.0, description="CPU burn duration per request in ms")
    db_query_delay_ms: float = Field(default=0.0, ge=0.0, description="Injected database query latency in ms")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom fault parameters")
