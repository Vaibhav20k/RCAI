# Deployment & Configuration Registry
import time
import threading
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class DeploymentRecord(BaseModel):
    deployment_id: str
    service: str
    version: str
    previous_version: Optional[str] = None
    config_version: str = "v1"
    git_commit: str = "c5d1fb6"
    deployed_at: float = Field(default_factory=time.time)
    status: str = "DEPLOYED"
    change_description: str = "Standard release"
    parameters: Dict[str, Any] = Field(default_factory=dict)

class DeploymentStore:
    def __init__(self):
        self._deployments: List[DeploymentRecord] = []
        self._lock = threading.Lock()
        self._seed_initial_versions()

    def _seed_initial_versions(self) -> None:
        services = ["api-gateway", "order-service", "payment-service", "dependency-service", "worker-service"]
        base_ts = time.time() - 3600
        for s in services:
            self._deployments.append(
                DeploymentRecord(
                    deployment_id=f"dep_init_{s}",
                    service=s,
                    version="1.0.0",
                    config_version="v1",
                    deployed_at=base_ts,
                    status="HEALTHY",
                    change_description="Initial base release"
                )
            )

    def reset(self) -> None:
        with self._lock:
            self._deployments.clear()
            self._seed_initial_versions()

    def record_deployment(self, record: DeploymentRecord) -> None:
        with self._lock:
            self._deployments.append(record)

    def get_service_history(self, service: str) -> List[DeploymentRecord]:
        with self._lock:
            return sorted(
                [d for d in self._deployments if d.service == service],
                key=lambda x: x.deployed_at
            )

    def get_latest_deployment(self, service: str) -> Optional[DeploymentRecord]:
        history = self.get_service_history(service)
        return history[-1] if history else None

    def query_recent_deployments(self, window_seconds: float = 3600) -> List[DeploymentRecord]:
        cutoff = time.time() - window_seconds
        with self._lock:
            return sorted(
                [d for d in self._deployments if d.deployed_at >= cutoff],
                key=lambda x: x.deployed_at
            )

global_deployment_store = DeploymentStore()
