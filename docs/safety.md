# Autonomous AI System Investigator (RCAI)
# Safety Model and Operational Policies

## 1. Tool Permission Hierarchy

To ensure the AI agent cannot perform unauthorized or destructive actions on infrastructure, tools are classified into strict permission tiers:

| Permission Level | Description | Execution Policy | Examples |
|---|---|---|---|
| `READ_ONLY` | Safe diagnostic telemetry retrieval | Automated execution permitted | `query_metrics`, `query_logs`, `query_traces`, `inspect_deployments` |
| `RECOMMEND` | Generates remediation plan for operator review | Output recommendation only | `create_rollback_plan`, `suggest_index_fix` |
| `APPROVAL_REQUIRED` | Modifies configuration or restarts services | Blocked pending human token approval | `restart_service`, `traffic_shift`, `scale_deployment` |
| `CONTROLLED_EXECUTION` | Safe, bounded, automated rollback in sandbox | Automated only if pre-approved by policy | `rollback_service_version` (low-risk services only) |
| `FORBIDDEN` | Unrestricted shell or destructive database drops | Strictly prohibited / blocked at gateway | `rm -rf`, `DROP TABLE`, arbitrary bash command execution |

## 2. Bounded Remediation Invariants

1. **Pre-Execution Policy Check:** Every proposed action must pass parameter validation, target service verification, and active incident confirmation.
2. **Idempotency Enforcement:** Repeated execution of the same remediation action within an active incident window is prevented.
3. **Reversibility Requirement:** Remediations must have a defined rollback or undo mechanism.
4. **Mandatory Post-Verification:** No incident is marked resolved until independent telemetry confirms metric recovery.

## 3. Evaluation and Audit Integrity

1. **Evaluator Isolation:** The agent execution context has no write access to evaluation harness code, benchmark ground truth, or scoring modules.
2. **Immutable Audit Trail:** Every state change, hypothesis update, tool invocation, and human approval is written to an append-only audit log.
3. **Secret Protection:** Telemetry and tool parameters are scrubbed for credentials and secrets prior to logging.
