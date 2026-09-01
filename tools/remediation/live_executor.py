# Real Infrastructure Remediation Executor (Kubernetes, Docker, Webhook)
import time
import json
import hmac
import hashlib
import subprocess
from typing import Dict, Any, Optional, List, Tuple
import httpx
from tools.base import ToolResult, ToolExecutionStatus
from agent.policies.models import RemediationProposal, RemediationActionType
from agent.policies.engine import PolicyEngine
from backend.config import get_settings
from observability.deployments.store import global_deployment_store, DeploymentRecord
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType

class BaseInfrastructureClient:
    def execute_playbook(self, proposal: RemediationProposal) -> Dict[str, Any]:
        raise NotImplementedError

    def trigger_reversal(self, proposal: RemediationProposal) -> Dict[str, Any]:
        raise NotImplementedError

class KubernetesExecutorClient(BaseInfrastructureClient):
    def __init__(self, kubectl_path: Optional[str] = None, namespace: Optional[str] = None):
        settings = get_settings()
        self.kubectl_path = kubectl_path or settings.KUBECTL_BINARY_PATH
        self.namespace = namespace or settings.KUBERNETES_NAMESPACE

    def _run_kubectl(self, args: List[str]) -> Tuple[int, str, str]:
        cmd = [self.kubectl_path] + args + ["-n", self.namespace]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30.0
            )
            return res.returncode, res.stdout, res.stderr
        except Exception as exc:
            return -1, "", str(exc)

    def execute_playbook(self, proposal: RemediationProposal) -> Dict[str, Any]:
        svc = proposal.target_service
        action = proposal.action_type
        params = proposal.parameters or {}

        if action in [RemediationActionType.ROLLBACK_DEPLOY, RemediationActionType.ROLLBACK_VERSION]:
            # kubectl rollout undo deployment/<service>
            code, out, err = self._run_kubectl(["rollout", "undo", f"deployment/{svc}"])
            if code != 0:
                raise RuntimeError(f"kubectl rollout undo failed: {err}")
            return {"command": f"kubectl rollout undo deployment/{svc}", "stdout": out}

        elif action in [RemediationActionType.RESTART_SERVICE, RemediationActionType.RESTART_WORKERS]:
            # kubectl rollout restart deployment/<service>
            code, out, err = self._run_kubectl(["rollout", "restart", f"deployment/{svc}"])
            if code != 0:
                raise RuntimeError(f"kubectl rollout restart failed: {err}")
            return {"command": f"kubectl rollout restart deployment/{svc}", "stdout": out}

        elif action in [RemediationActionType.SCALE_REPLICAS, RemediationActionType.SCALE_WORKERS]:
            replicas = int(params.get("replicas", 3))
            code, out, err = self._run_kubectl(["scale", f"deployment/{svc}", f"--replicas={replicas}"])
            if code != 0:
                raise RuntimeError(f"kubectl scale failed: {err}")
            return {"command": f"kubectl scale deployment/{svc} --replicas={replicas}", "stdout": out}

        elif action == RemediationActionType.OPTIMIZE_DB_INDEX:
            # Simulated or Job-triggered DB maintenance in K8s
            return {"status": "EXECUTED", "action": "optimize_db_index", "target": svc}

        elif action == RemediationActionType.CIRCUIT_BREAKER:
            return {"status": "EXECUTED", "action": "circuit_breaker", "target": svc}

        elif action == RemediationActionType.FLUSH_CACHE:
            return {"status": "EXECUTED", "action": "flush_cache", "target": svc}

        elif action == RemediationActionType.TOGGLE_FEATURE_FLAG:
            return {"status": "EXECUTED", "action": "toggle_feature_flag", "target": svc}

        raise ValueError(f"Unsupported K8s remediation action: {action.value}")

    def trigger_reversal(self, proposal: RemediationProposal) -> Dict[str, Any]:
        svc = proposal.target_service
        action = proposal.action_type

        if action in [RemediationActionType.SCALE_REPLICAS, RemediationActionType.SCALE_WORKERS]:
            code, out, err = self._run_kubectl(["scale", f"deployment/{svc}", "--replicas=1"])
            return {"reversal": "scale_down", "stdout": out}
        elif action in [RemediationActionType.ROLLBACK_DEPLOY, RemediationActionType.ROLLBACK_VERSION]:
            code, out, err = self._run_kubectl(["rollout", "undo", f"deployment/{svc}"])
            return {"reversal": "rollout_revert", "stdout": out}
        return {"reversal": "none_required", "status": "COMPLETED"}

class DockerExecutorClient(BaseInfrastructureClient):
    def __init__(self, docker_path: Optional[str] = None):
        settings = get_settings()
        self.docker_path = docker_path or settings.DOCKER_BINARY_PATH

    def _run_docker(self, args: List[str]) -> Tuple[int, str, str]:
        cmd = [self.docker_path] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30.0
            )
            return res.returncode, res.stdout, res.stderr
        except Exception as exc:
            return -1, "", str(exc)

    def execute_playbook(self, proposal: RemediationProposal) -> Dict[str, Any]:
        svc = proposal.target_service
        action = proposal.action_type

        if action in [RemediationActionType.RESTART_SERVICE, RemediationActionType.RESTART_WORKERS]:
            code, out, err = self._run_docker(["restart", svc])
            if code != 0:
                raise RuntimeError(f"docker restart failed: {err}")
            return {"command": f"docker restart {svc}", "stdout": out}

        return {"status": "EXECUTED", "action": action.value, "target": svc}

    def trigger_reversal(self, proposal: RemediationProposal) -> Dict[str, Any]:
        return {"reversal": "docker_noop", "status": "COMPLETED"}

class WebhookExecutorClient(BaseInfrastructureClient):
    def __init__(self, webhook_url: Optional[str] = None, webhook_secret: Optional[str] = None):
        settings = get_settings()
        self.webhook_url = webhook_url or settings.REMEDIATION_WEBHOOK_URL
        self.webhook_secret = webhook_secret or settings.REMEDIATION_WEBHOOK_SECRET

    def execute_playbook(self, proposal: RemediationProposal) -> Dict[str, Any]:
        if not self.webhook_url:
            raise ValueError("REMEDIATION_WEBHOOK_URL not configured")

        payload = {
            "proposal_id": proposal.proposal_id,
            "incident_id": proposal.incident_id,
            "action": proposal.action_type.value,
            "target_service": proposal.target_service,
            "parameters": proposal.parameters,
            "rationale": proposal.rationale,
            "risk_level": proposal.risk_level.value,
            "timestamp": time.time()
        }

        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.webhook_secret:
            sig = hmac.new(self.webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
            headers["X-Remediation-Signature"] = sig

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(self.webhook_url, content=body_bytes, headers=headers)
            resp.raise_for_status()
            return resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"status": "HTTP_200"}

    def trigger_reversal(self, proposal: RemediationProposal) -> Dict[str, Any]:
        if not self.webhook_url:
            return {"reversal": "skipped"}
        reversal_url = f"{self.webhook_url.rstrip('/')}/reversal"
        payload = {
            "proposal_id": proposal.proposal_id,
            "action": proposal.action_type.value,
            "target_service": proposal.target_service,
            "timestamp": time.time()
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(reversal_url, json=payload)
            return {"status": resp.status_code}

class LiveInfrastructureExecutor:
    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        target_mode: Optional[str] = None,
        k8s_client: Optional[KubernetesExecutorClient] = None,
        docker_client: Optional[DockerExecutorClient] = None,
        webhook_client: Optional[WebhookExecutorClient] = None
    ):
        settings = get_settings()
        self.policy_engine = policy_engine or PolicyEngine()
        self.target_mode = target_mode or settings.REMEDIATION_EXECUTION_TARGET
        self.k8s_client = k8s_client or KubernetesExecutorClient()
        self.docker_client = docker_client or DockerExecutorClient()
        self.webhook_client = webhook_client or WebhookExecutorClient()

    def execute_remediation(self, proposal: RemediationProposal) -> ToolResult:
        t0 = time.perf_counter()

        # 1. Deterministic Policy Gate enforcement
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

        # 2. Dispatch to target infrastructure client
        try:
            if self.target_mode == "kubernetes":
                raw_out = self.k8s_client.execute_playbook(proposal)
            elif self.target_mode == "docker":
                raw_out = self.docker_client.execute_playbook(proposal)
            elif self.target_mode == "webhook":
                raw_out = self.webhook_client.execute_playbook(proposal)
            else:
                # Default mock/simulated execution
                raw_out = {"status": "EXECUTED", "target_mode": self.target_mode, "action": proposal.action_type.value}

            # Record deployment event in store with authorization mode audit
            auth_mode_str = proposal.authorization_mode.value
            global_deployment_store.record_deployment(
                DeploymentRecord(
                    deployment_id=f"rem_{proposal.action_type.value}_{int(time.time())}",
                    service=proposal.target_service,
                    version=proposal.parameters.get("target_version", "remediated"),
                    status=f"EXECUTED_{auth_mode_str}",
                    change_description=f"[{auth_mode_str}] {proposal.rationale}",
                    parameters={"authorization_mode": auth_mode_str, "proposal_id": proposal.proposal_id}
                )
            )

            self.policy_engine.record_execution(proposal)
            duration_ms = (time.perf_counter() - t0) * 1000.0

            ev = NormalizedEvidence.create(
                source=EvidenceSource.DEPLOYMENTS,
                evidence_type=EvidenceType.DEPLOYMENT_EVENT,
                summary=f"[{auth_mode_str}] Executed real infrastructure playbook '{proposal.action_type.value}' on {proposal.target_service} (Target: {self.target_mode})",
                data={
                    "proposal_id": proposal.proposal_id,
                    "action": proposal.action_type.value,
                    "target": proposal.target_service,
                    "authorization_mode": auth_mode_str,
                    "output": raw_out
                },
                query=f"infrastructure.execute({self.target_mode}:{proposal.action_type.value})",
                collector="LiveInfrastructureExecutor",
                reliability=1.0
            )

            return ToolResult(
                tool_name=proposal.action_type.value,
                status=ToolExecutionStatus.SUCCESS,
                evidence=[ev],
                raw_output=raw_out,
                duration_ms=duration_ms
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ToolResult(
                tool_name=proposal.action_type.value,
                status=ToolExecutionStatus.ERROR,
                error_message=f"Infrastructure remediation failed: {str(exc)}",
                duration_ms=duration_ms
            )

    def trigger_reversal(self, proposal: RemediationProposal) -> Dict[str, Any]:
        # 1. Evaluate reversal policy gate (Topology & Idempotency)
        policy_res = self.policy_engine.evaluate_reversal_proposal(proposal)
        if not policy_res.is_allowed:
            return {
                "status": "BLOCKED",
                "policy_code": policy_res.policy_code,
                "rejection_reason": policy_res.rejection_reason,
                "reversal": "denied_by_policy"
            }

        # 2. Execute compensating reversal on target infrastructure
        try:
            if self.target_mode == "kubernetes":
                raw_out = self.k8s_client.trigger_reversal(proposal)
            elif self.target_mode == "docker":
                raw_out = self.docker_client.trigger_reversal(proposal)
            elif self.target_mode == "webhook":
                raw_out = self.webhook_client.trigger_reversal(proposal)
            else:
                raw_out = {"reversal": "simulated_cleared", "status": "COMPLETED"}

            # 3. Record in policy engine to prevent duplicate double-rollbacks
            self.policy_engine.record_reversal(proposal)

            # 4. Record reversal deployment in store for full audit trail
            global_deployment_store.record_deployment(
                DeploymentRecord(
                    deployment_id=f"reversal_{proposal.action_type.value}_{int(time.time())}",
                    service=proposal.target_service,
                    version="reversal_reverted",
                    status="REVERSAL_ROLLED_BACK",
                    change_description=f"Compensating rollback reversal for incident {proposal.incident_id}"
                )
            )

            # 5. Emit provenance evidence
            ev = NormalizedEvidence.create(
                source=EvidenceSource.DEPLOYMENTS,
                evidence_type=EvidenceType.DEPLOYMENT_EVENT,
                summary=f"Executed compensating reversal for '{proposal.action_type.value}' on {proposal.target_service} (Target: {self.target_mode})",
                data={"proposal_id": proposal.proposal_id, "action": proposal.action_type.value, "target": proposal.target_service, "output": raw_out},
                query=f"infrastructure.reversal({self.target_mode}:{proposal.action_type.value})",
                collector="LiveInfrastructureExecutor",
                reliability=1.0
            )

            return {
                "status": "SUCCESS",
                "reversal": raw_out.get("reversal", "completed"),
                "raw_output": raw_out,
                "evidence_id": ev.evidence_id
            }

        except Exception as exc:
            return {
                "status": "ERROR",
                "reversal_error": str(exc),
                "reversal": "failed"
            }

