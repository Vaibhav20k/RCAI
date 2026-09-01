# Bounded Remediation Tools and Executor
import time
from typing import Dict, Any, Optional
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from agent.policies.models import RemediationProposal, RemediationActionType
from agent.policies.engine import PolicyEngine
from simulator.services.runner import InProcessCluster
from observability.deployments.store import global_deployment_store, DeploymentRecord
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType

class BoundedRemediationExecutor:
    def __init__(self, cluster: InProcessCluster, policy_engine: Optional[PolicyEngine] = None):
        self.cluster = cluster
        self.policy_engine = policy_engine or PolicyEngine()

    def execute_remediation(self, proposal: RemediationProposal) -> ToolResult:
        t0 = time.perf_counter()
        
        # 1. Enforce Policy check (deterministic safety boundary)
        policy_res = self.policy_engine.evaluate_proposal(proposal)
        if not policy_res.is_allowed:
            return ToolResult(
                tool_name=proposal.action_type.value,
                status=ToolExecutionStatus.PERMISSION_DENIED,
                error_message=policy_res.rejection_reason,
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

        if policy_res.requires_human_approval:
            return ToolResult(
                tool_name=proposal.action_type.value,
                status=ToolExecutionStatus.PERMISSION_DENIED,
                error_message=f"Action requires human approval token: {policy_res.approval_token}",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

        # 2. Execute bounded remediation against cluster services
        service_obj = self.cluster.get_service_map().get(proposal.target_service)
        if not service_obj:
            return ToolResult(
                tool_name=proposal.action_type.value,
                status=ToolExecutionStatus.ERROR,
                error_message=f"Service {proposal.target_service} not found in cluster",
                duration_ms=(time.perf_counter() - t0) * 1000.0
            )

        action = proposal.action_type
        if action in [RemediationActionType.ROLLBACK_VERSION, RemediationActionType.ROLLBACK_DEPLOY]:
            # Revert deployment to previous version and clear fault
            target_version = proposal.parameters.get("target_version", "1.0.0")
            service_obj.version = target_version
            service_obj.fault_injector.clear_faults()
            
            # Record rollback deployment in store
            global_deployment_store.record_deployment(
                DeploymentRecord(
                    deployment_id=f"rollback_{proposal.target_service}_{int(time.time())}",
                    service=proposal.target_service,
                    version=target_version,
                    status="ROLLED_BACK",
                    change_description=f"Automated rollback for incident {proposal.incident_id}"
                )
            )

        elif action == RemediationActionType.OPTIMIZE_DB_INDEX:
            # Clear database regression fault
            service_obj.fault_injector.clear_faults()

        elif action in [RemediationActionType.RESTART_WORKERS, RemediationActionType.RESTART_SERVICE]:
            # Clear CPU spinlock/resource saturation fault
            service_obj.fault_injector.clear_faults()

        elif action == RemediationActionType.CIRCUIT_BREAKER:
            # Clear downstream dependency latency fault
            dep_service = self.cluster.get_service_map().get("dependency-service")
            if dep_service:
                dep_service.fault_injector.clear_faults()

        elif action in [RemediationActionType.SCALE_WORKERS, RemediationActionType.SCALE_REPLICAS]:
            # Clear queue worker backlog
            worker_service = self.cluster.get_service_map().get("worker-service")
            if worker_service:
                worker_service.fault_injector.clear_faults()

        elif action == RemediationActionType.FLUSH_CACHE:
            # Clear cache corruption or memory contention
            service_obj.fault_injector.clear_faults()

        elif action == RemediationActionType.TOGGLE_FEATURE_FLAG:
            # Toggle feature flag and clear fault
            service_obj.fault_injector.clear_faults()

        self.policy_engine.record_execution(proposal)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        auth_mode_str = proposal.authorization_mode.value
        
        ev = NormalizedEvidence.create(
            source=EvidenceSource.DEPLOYMENTS,
            evidence_type=EvidenceType.DEPLOYMENT_EVENT,
            summary=f"[{auth_mode_str}] Executed bounded remediation {proposal.action_type.value} on {proposal.target_service}",
            data={
                "proposal_id": proposal.proposal_id,
                "action": proposal.action_type.value,
                "target": proposal.target_service,
                "authorization_mode": auth_mode_str
            },
            query=f"remediation.execute({proposal.action_type.value})",
            collector="BoundedRemediationExecutor",
            reliability=1.0
        )
        return ToolResult(
            tool_name=proposal.action_type.value,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output={"status": "EXECUTED", "proposal_id": proposal.proposal_id, "authorization_mode": auth_mode_str},
            duration_ms=duration_ms
        )
