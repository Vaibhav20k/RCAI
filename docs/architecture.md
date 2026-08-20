# Autonomous AI System Investigator (RCAI)
# Architecture Specification

## 1. System Overview

The Autonomous AI System Investigator (RCAI) is an evidence-driven, agentic system designed to diagnose, verify, and remediate software microservice incidents under strict safety and resource bounds.

Unlike traditional monitoring tools that merely detect threshold violations, or one-shot LLM assistants that generate unverified summaries, RCAI implements an active hypothesis-testing loop with explicit evidence provenance and post-remediation verification.

## 2. Core Architecture Pipeline

```text
+--------------------------------------------------------------------------+
|                       Controlled Service Environment                     |
|  [API Gateway] <---> [Order Service] <---> [Payment Service] <-> [DB]   |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                     Observability & Normalization                        |
|  - Metrics (Prometheus)   - Logs (Structured JSON)   - Traces (OTel)     |
|  - Deployment Registry    - Dependency Topology                          |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                     Incident Detection & Scenarios                       |
|  - Deterministic Anomaly Triggers                                        |
|  - Incident Context & Time Window Bounding                              |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                        Active Investigation Loop                         |
|                                                                          |
|   [Incident Ingestion]                                                   |
|           |                                                              |
|           v                                                              |
|   [Hypothesis Engine] <------------------------------------+             |
|     - Generate competing hypotheses                       |             |
|     - Explicit confidence scoring                          |             |
|           |                                                |             |
|           v                                                |             |
|   [Evidence Selector / Router]                             |             |
|     - Maximize utility: (Info Gain / Action Cost)          |             |
|           |                                                |             |
|           v                                                |             |
|   [Constrained Tool Execution]                             |             |
|     - Read-only queries (logs, metrics, traces, deploys)   |             |
|     - Guaranteed no evidence fabrication                  |             |
|           |                                                |             |
|           v                                                |             |
|   [Evidence Updater & Rejector] ---------------------------+             |
|     - Update support/contradiction sets                                  |
|     - Reject invalid hypotheses                                          |
|           |                                                              |
|           v                                                              |
|   [Stopping Policy] (Confidence threshold / budget exhausted)            |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                      Root Cause & Provenance                             |
|  - Grounded Root Cause Decision                                          |
|  - Complete Evidence Provenance Audit Trail                              |
|  - Explicit "ROOT_CAUSE_UNKNOWN" / "INSUFFICIENT_EVIDENCE" support       |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                    Bounded Remediation & Policy Engine                   |
|  - Permission Check (READ_ONLY -> APPROVAL -> AUTO_LOW_RISK)             |
|  - Idempotency & Target Validation                                       |
|  - Human Approval Gating for High-Impact Actions                         |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                     Independent Outcome Verification                     |
|  - Pre vs. Post Telemetry Measurement                                    |
|  - Deterministic Recovery Threshold Check                                |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|               Historical Incident Memory & Strategy Routing              |
|  - Structured Experience Storage                                         |
|  - Prior Path Weighting for Future Investigations                        |
+--------------------------------------------------------------------------+
```

## 3. Component Decomposition

### 3.1 Agent Subsystem (`agent/`)
- `agent/investigator/`: Orchestrates the active investigation lifecycle using an explicit state machine.
- `agent/hypothesis/`: Maintains the set of active, supported, and rejected hypotheses.
- `agent/evidence/`: Ingests, normalizes, and links evidence records to hypotheses.
- `agent/routing/`: Implements the dynamic investigation action selection heuristic.
- `agent/verification/`: Verifies root-cause claims against evidence provenance and measures post-remediation metrics.
- `agent/policies/`: Enforces authorization, risk limits, idempotency, and human approval constraints.
- `agent/memory/`: Stores structured post-incident execution trajectories for future strategy routing.

### 3.2 Tools Subsystem (`tools/`)
- Predefined tools with explicit input and output Pydantic schemas.
- Strict isolation: Read-only query tools cannot execute side-effecting operations.
- Explicit error handling for timeouts, empty datasets (`NO_EVIDENCE_FOUND`), and unreachable backends (`EVIDENCE_SOURCE_UNAVAILABLE`).

### 3.3 Simulator & Fault Engine (`simulator/`)
- Provides a reproducible microservice topology (Gateway, Order, Payment, Dependency, Postgres, Redis).
- Deterministic fault injection for database regressions, deployment bugs, downstream dependency latency, and resource saturation.

### 3.4 Benchmark & Evaluator (`benchmark/`)
- Authoritative evaluation harness that compares the proposed investigator against baseline architectures.
- External to the agent: Ground truth is hidden from the agent during evaluation and cannot be modified by the agent.

### 3.5 Backend API & Audit (`backend/`)
- FastAPI endpoints for incident lifecycle management, real-time investigation streaming, and human approval gates.
- Immutable append-only audit log capturing every state transition and tool execution.

## 4. State Machine Model

Every incident progresses through explicit states:
```text
NEW -> DETECTED -> INVESTIGATING -> HYPOTHESES_GENERATED -> EVIDENCE_COLLECTING 
    -> ROOT_CAUSE_PROPOSED -> REMEDIATION_PENDING -> REMEDIATION_EXECUTED 
    -> VERIFYING -> RESOLVED / UNRESOLVED / ESCALATED
```
