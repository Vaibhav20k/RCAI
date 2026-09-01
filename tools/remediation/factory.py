# Remediation Executor Factory
from typing import Optional, Union
from simulator.services.runner import InProcessCluster
from agent.policies.engine import PolicyEngine
from tools.remediation.executor import BoundedRemediationExecutor
from tools.remediation.live_executor import LiveInfrastructureExecutor
from backend.config import get_settings

def get_remediation_executor(
    cluster: Optional[InProcessCluster] = None,
    policy_engine: Optional[PolicyEngine] = None
) -> Union[BoundedRemediationExecutor, LiveInfrastructureExecutor]:
    settings = get_settings()
    if settings.DATA_SOURCE == "live" or settings.REMEDIATION_EXECUTION_TARGET != "simulated":
        return LiveInfrastructureExecutor(policy_engine=policy_engine)
    return BoundedRemediationExecutor(cluster=cluster or InProcessCluster(), policy_engine=policy_engine)
