# Autonomous AI System Investigator
## CLI Implementation Plan — Phase-by-Phase

> **Project:** Autonomous AI System Investigator  
> **Purpose:** Build an AI agent that actively investigates software incidents by generating competing hypotheses, selecting useful evidence, testing hypotheses, identifying root cause, executing bounded remediation where allowed, and verifying whether the system actually recovered.
>
> **Core research question:**  
> Can an evidence-selecting, hypothesis-testing AI agent achieve more reliable root-cause analysis than one-shot LLM diagnosis under the same evidence/tool budget?
>
> **Critical implementation rule:**  
> **Do not move to the next phase until the current phase is implemented, tested, documented, and committed to Git.**
>
> **Git rule:**  
> **Never use `git add .`.** Every phase must stage only the intended files and must end with a clean, meaningful commit.

---

# 0. Project Scope in Short

The system is not an AI log summarizer and not primarily an observability dashboard.

It is an **AI investigation engine**.

The intended loop is:

```text
Incident
   ↓
Understand symptom
   ↓
Generate competing hypotheses
   ↓
Choose the most informative next investigation step
   ↓
Collect evidence
   ↓
Update / reject hypotheses
   ↓
Verify root cause
   ↓
Recommend / execute bounded remediation
   ↓
Verify system recovery
   ↓
Store structured investigation experience
```

The AI should answer:

> **What could be wrong? What evidence would distinguish the possibilities? What does the evidence actually show? What action is justified? Did the action work?**

---

# 1. Non-Negotiable Design Principles

## 1.1 AI is the product

Infrastructure is only the controlled environment in which the investigator operates.

Do not allow the project to become primarily:

- a Kubernetes project
- a monitoring dashboard
- a logging platform
- an observability clone
- a generic chatbot

## 1.2 Evidence before conclusion

The agent must not invent evidence.

Every important claim should trace back to:

- metrics
- logs
- traces
- deployment history
- configuration history
- service state
- structured historical incidents

## 1.3 Hypotheses are explicit

The agent should maintain:

```text
Hypothesis
Confidence
Supporting Evidence
Contradicting Evidence
Next Investigation Action
```

Do not implement the core investigation as hidden free-form reasoning only.

## 1.4 Tool use is bounded

The agent gets specific tools.

It does not get unrestricted shell access or arbitrary production-control permissions.

## 1.5 Remediation must be verified

A remediation is not considered successful because the agent says it worked.

The system must measure post-action behaviour.

## 1.6 Unknown is valid

The agent must be allowed to conclude:

```text
ROOT_CAUSE_UNKNOWN
```

and escalate when evidence is insufficient.

## 1.7 Evaluation is first-class

The benchmark and evaluator must be designed before the agent is heavily tuned.

## 1.8 Git discipline

Every completed phase must produce:

1. tested implementation,
2. updated documentation,
3. a clean working tree,
4. one focused Git commit.

Never use `git add .`.

---

# 2. Target Technology Stack

## AI / Agent

- Python
- LangGraph or equivalent explicit agent/state orchestration
- LLM via a permitted API/provider
- structured tool calling

## Backend

- FastAPI
- PostgreSQL
- Redis where genuinely useful

## Observability Environment

- Prometheus for metrics
- Loki or equivalent centralized logging
- OpenTelemetry
- Tempo or equivalent distributed tracing

## Controlled Services

Use a deliberately small set of services:

- API Gateway
- Order Service
- Payment Service
- Database-backed Service
- Dependency Service
- Queue/Worker

These exist only to create realistic incidents.

## Frontend

- Next.js
- React
- TypeScript

## Evaluation

- Pytest
- custom benchmark harness
- fixed scenarios
- baseline runners
- ablation runners

## Containers

- Docker Compose initially

Do not introduce Kubernetes in the initial implementation unless a later phase demonstrates a concrete need.

## CI

- GitHub Actions

---

# 3. High-Level Phase Map

```text
Phase 0  → Repository + research contract
Phase 1  → Controlled microservice environment
Phase 2  → Observability + telemetry normalization
Phase 3  → Incident detection + scenario engine
Phase 4  → Hypothesis engine
Phase 5  → Investigation tools
Phase 6  → Active investigation loop
Phase 7  → Root-cause verification + evidence provenance
Phase 8  → Bounded remediation + policy engine
Phase 9  → Outcome verification
Phase 10 → Investigation memory + adaptive strategy
Phase 11 → Benchmark + baselines
Phase 12 → Ablation + budget experiments
Phase 13 → Frontend investigation console
Phase 14 → Reliability, safety, failure testing
Phase 15 → Final evaluation + research report
Phase 16 → Final demo + documentation + release
```

---

# PHASE 0 — Repository, Research Contract, and Architecture

## Objective

Create a clean project foundation and make the research/evaluation contract explicit before implementation begins.

## Tasks

### Repository

Create:

```text
autonomous-ai-system-investigator/
```

Initialize:

- Git repository
- `.gitignore`
- `.env.example`
- `README.md`
- `LICENSE` if required
- base folder structure

### Documentation

Create:

```text
docs/
├── architecture.md
├── research.md
├── evaluation.md
├── safety.md
└── decisions.md
```

Document:

- project thesis
- research question
- scope
- non-goals
- architecture principles
- planned metrics
- safety model
- benchmark strategy

### Architecture

Create the initial architecture diagram:

```text
Controlled Services
        ↓
Telemetry
        ↓
Incident Layer
        ↓
Investigator
        ↓
Hypotheses
        ↓
Evidence Tools
        ↓
Root Cause
        ↓
Policy / Remediation
        ↓
Verification
```

## Testing / Verification

Confirm:

- project installs cleanly
- Python environment works
- basic test runner works
- Docker Compose skeleton validates
- documentation renders correctly

## Deliverables

- clean repository
- initial architecture
- research contract
- project README
- test skeleton

## Exit Criteria

Do not proceed until the repository is reproducible from a fresh checkout.

## Git Commit

Check first:

```bash
git status
git diff
```

Stage only intended files:

```bash
git add README.md docs/ .gitignore .env.example pyproject.toml
```

Then:

```bash
git commit -m "feat: initialize investigator architecture"
```

---

# PHASE 1 — Controlled Microservice Environment

## Objective

Create the small software system that the AI will investigate.

The environment must be realistic enough to generate meaningful incidents but small enough to remain manageable.

## Services

Implement a minimal set:

```text
API Gateway
   |
   +--> Order Service
   |
   +--> Payment Service
          |
          +--> PostgreSQL
          |
          +--> Dependency Service

Worker / Queue
```

## Requirements

Every service must expose:

- health endpoint
- structured logs
- request IDs
- basic metrics
- version metadata

Add a simple traffic generator.

## Failure Scenarios to Prepare

At minimum:

1. database query regression
2. bad application deployment
3. downstream dependency latency
4. resource saturation

Do not expose the faults yet through the agent.

## Testing

- health checks
- service-to-service requests
- database connectivity
- deterministic traffic generation
- clean startup/shutdown
- scenario reproducibility

## Exit Criteria

You can start the entire environment with one documented command and reproduce a known failure manually.

## Git Commit

```bash
git status
git diff
git add services/ simulator/ docker-compose.yml docs/
git commit -m "feat: add controlled microservice environment"
```

---

# PHASE 2 — Observability and Telemetry Normalization

## Objective

Create the evidence sources the investigator will later query.

## Metrics

Prometheus should capture:

- request count
- error count
- latency
- CPU
- memory
- queue depth
- DB query latency
- dependency latency

## Logs

Use structured JSON logs containing:

```text
timestamp
service
request_id
trace_id
level
event
message
version
```

## Traces

Add OpenTelemetry instrumentation for:

```text
Gateway
 → Order
 → Payment
 → DB / dependency
```

## Deployment History

Create a simple deployment/version store containing:

```text
service
version
deployment_time
config_version
change_id
```

## Normalized Evidence Model

Define a common evidence schema:

```text
Evidence
├── evidence_id
├── source
├── timestamp
├── incident_window
├── type
├── value
├── provenance
├── derived
└── reliability
```

## Testing

Verify that the same incident can be observed from:

- logs
- metrics
- traces
- deployment history

## Exit Criteria

A human can inspect the telemetry and identify which evidence sources are available.

## Git Commit

```bash
git status
git diff
git add observability/ services/ docs/
git commit -m "feat: add observability and telemetry layer"
```

---

# PHASE 3 — Incident Detection and Scenario Engine

## Objective

Create deterministic incident scenarios and convert observable anomalies into incident records.

## Incident Schema

Define:

```text
incident_id
scenario_id
started_at
detected_at
severity
service
symptom
status
ground_truth
```

Keep `ground_truth` outside the agent-visible evidence path.

The evaluator knows the true injected fault.

The agent does not.

## Scenario Engine

Build a controlled fault injector.

Examples:

```text
database_regression
bad_deployment
dependency_latency
resource_saturation
queue_backlog
```

Each scenario should specify:

```text
trigger
expected symptom
ground_truth root cause
expected recovery
```

## Detection

Implement a simple deterministic first-pass detector.

The goal is **incident creation**, not advanced anomaly detection yet.

## Testing

For every scenario:

- inject fault
- detect incident
- confirm incident ID
- confirm telemetry changes
- confirm ground truth remains hidden from the agent

## Exit Criteria

You have at least four reproducible incident scenarios with machine-readable ground truth.

## Git Commit

```bash
git status
git diff
git add simulator/ incidents/ benchmark/scenarios/ docs/
git commit -m "feat: add incident detection and fault scenarios"
```

---

# PHASE 4 — Hypothesis Engine

## Objective

Implement the structured state for competing root-cause hypotheses.

## Hypothesis Model

Each hypothesis should contain:

```text
hypothesis_id
description
category
confidence
supporting_evidence[]
contradicting_evidence[]
status
next_action
```

Possible statuses:

```text
OPEN
SUPPORTED
WEAKENED
REJECTED
CONFIRMED
```

## Initial Hypothesis Generation

Given an incident symptom, generate multiple plausible hypotheses.

Example:

```text
API latency spike

H1: database regression
H2: deployment regression
H3: downstream dependency
H4: CPU saturation
H5: queue backlog
```

The system should avoid generating only one answer.

## Confidence

Start with a transparent simple approach.

Do not implement complex probabilistic inference before the basic state machine works.

## Testing

- hypothesis creation
- state transition rules
- confidence updates
- evidence attachment
- duplicate hypothesis handling

## Exit Criteria

The agent can maintain multiple hypotheses throughout an investigation.

## Git Commit

```bash
git status
git diff
git add agent/hypothesis/ agent/investigator/ tests/
git commit -m "feat: add structured hypothesis engine"
```

---

# PHASE 5 — Investigation Tools

## Objective

Give the agent controlled access to the system evidence.

## Read-Only Tools

Implement:

```text
query_logs()
query_metrics()
query_traces()
inspect_deployment_history()
inspect_service_health()
inspect_dependency_health()
query_db_metrics()
compare_versions()
```

## Tool Contract

Every tool must define:

```text
name
description
inputs
outputs
permissions
timeout
error format
```

## Tool Results

Tool output should be structured.

Example:

```json
{
  "source": "prometheus",
  "query": "http_request_duration_p95",
  "window": "last_15m",
  "result": [
    {
      "timestamp": "...",
      "value": 1812
    }
  ]
}
```

## Error Handling

Every tool must explicitly handle:

- timeout
- unavailable source
- malformed query
- empty result
- stale result

The agent must be able to distinguish:

```text
"No evidence found"
```

from:

```text
"Evidence source unavailable"
```

## Testing

Unit-test every tool independently.

Also test incorrect and incomplete inputs.

## Exit Criteria

The agent can retrieve evidence without unrestricted system access.

## Git Commit

```bash
git status
git diff
git add tools/ agent/ tests/
git commit -m "feat: add evidence investigation tools"
```

---

# PHASE 6 — Active Investigation Loop

## Objective

This is the core AI phase.

The agent must choose **what to investigate next**, not simply receive all evidence.

## Loop

```text
Incident
 ↓
Generate / update hypotheses
 ↓
Select next best evidence
 ↓
Call tool
 ↓
Interpret result
 ↓
Update hypotheses
 ↓
Stop / continue
```

## Next Investigation Selection

The initial heuristic can use:

```text
expected information gain
/
investigation cost
```

Approximate the benefit of an action by:

- how many hypotheses it can distinguish,
- reliability of the evidence source,
- tool cost,
- latency.

## Investigation Memory

Store:

```text
action
result
hypothesis impact
```

## Stopping Conditions

Stop when:

- one hypothesis reaches sufficient confidence,
- all alternatives are rejected,
- investigation budget is exhausted,
- evidence sources are unavailable,
- or evidence is insufficient.

## Important

The agent must be allowed to say:

```text
INSUFFICIENT_EVIDENCE
```

## Testing

Create controlled scenarios where the best next action is different.

## Exit Criteria

The agent performs a sequence of tool calls chosen from the evolving hypothesis state.

## Git Commit

```bash
git status
git diff
git add agent/investigator/ agent/routing/ agent/evidence/ tests/
git commit -m "feat: implement active investigation loop"
```

---

# PHASE 7 — Root-Cause Verification and Evidence Provenance

## Objective

Make the final diagnosis evidence-grounded and auditable.

## Evidence Provenance

Every important claim must reference:

```text
evidence_id
source
timestamp
query/tool
incident window
```

## Supporting vs Contradicting Evidence

For each hypothesis:

```text
Supporting evidence
Contradicting evidence
```

must be explicit.

## Root-Cause Decision

Produce:

```text
root_cause
confidence
supporting_evidence
contradicting_evidence
unresolved_questions
```

## Evidence Integrity

Never let the LLM invent:

- metric values
- log lines
- deployment events
- trace spans
- timestamps

The model interprets retrieved evidence; it does not fabricate it.

## Testing

Create tests where:

- strong evidence supports H1
- contradictory evidence rejects H1
- evidence is missing
- evidence sources conflict

## Exit Criteria

The agent cannot mark an incident resolved without grounding the diagnosis in retrieved evidence.

## Git Commit

```bash
git status
git diff
git add agent/verification/ agent/evidence/ docs/ tests/
git commit -m "feat: add evidence-grounded root cause verification"
```

---

# PHASE 8 — Bounded Remediation and Policy Engine

## Objective

Add controlled remediation without giving the AI unrestricted operational access.

## Policy Layer

Every proposed action must pass:

```text
allowed action?
target valid?
incident active?
approval required?
rollback available?
risk threshold?
```

## Initial Remediation

Start with one safe, reversible action.

Example:

```text
rollback_service_version()
```

or a sandbox-only restart.

## Action Levels

```text
READ_ONLY
 ↓
RECOMMEND
 ↓
APPROVAL_REQUIRED
 ↓
AUTO_EXECUTE_LOW_RISK
```

High-impact operations require approval.

## State Machine

```text
REMEDIATION_PROPOSED
 ↓
POLICY_CHECK
 ↓
APPROVED / REJECTED
 ↓
EXECUTED
```

## Testing

- policy denial
- invalid target
- duplicate action
- unavailable remediation tool
- approval required
- successful execution

## Exit Criteria

No agent action can bypass the policy layer.

## Git Commit

```bash
git status
git diff
git add agent/policies/ tools/remediation/ tests/ docs/
git commit -m "feat: add bounded remediation and policy engine"
```

---

# PHASE 9 — Outcome Verification

## Objective

Prove whether the remediation actually solved the incident.

## Before/After Metrics

Record the relevant metrics immediately before the action.

Then measure after the action.

Examples:

```text
p95 latency
error rate
queue depth
DB latency
dependency latency
```

## Verification Logic

Example:

```text
Before:
p95 = 1.8s

Remediation:
rollback v2.4.1

After:
p95 = 620ms

Decision:
RESOLVED
```

If the system does not improve:

```text
REMEDIATION_FAILED
```

and investigation continues.

## Testing

Create:

- successful remediation
- failed remediation
- partial recovery
- delayed recovery

## Exit Criteria

The agent never marks a remediation successful purely from its own statement.

## Git Commit

```bash
git status
git diff
git add agent/verification/ benchmark/ tests/
git commit -m "feat: add remediation outcome verification"
```

---

# PHASE 10 — Historical Incident Memory and Strategy Learning

## Objective

Allow the system to learn from previous investigations without unrestricted self-modification.

## Store Structured Experience

For resolved incidents store:

```text
incident type
symptoms
successful evidence path
failed evidence paths
root cause
successful remediation
verification result
time to diagnosis
tool efficiency
```

## Historical Retrieval

Optional semantic retrieval using:

- FAISS
- PostgreSQL search
- or another controlled retrieval mechanism

Historical cases should provide **prior guidance**, not absolute truth.

## Adaptive Strategy

Example:

```text
For deployment-related latency incidents:

Useful first actions:
1. inspect deployment timeline
2. compare service versions
3. inspect DB query metrics
```

The agent can rank investigation actions using prior outcomes.

## Important Restriction

Do not allow arbitrary source-code self-modification.

The adaptation is:

```text
experience → strategy selection
```

not:

```text
experience → unrestricted code rewriting
```

## Testing

Compare:

```text
No memory
vs
Historical memory
```

Measure:

- diagnosis time
- tool calls
- RCA accuracy

## Exit Criteria

Historical experience improves at least one measured investigation metric without decreasing reliability.

## Git Commit

```bash
git status
git diff
git add agent/memory/ agent/routing/ benchmark/ tests/
git commit -m "feat: add historical investigation memory"
```

---

# PHASE 11 — Benchmark Harness and Baselines

## Objective

Build the scientific evaluation system before final optimization.

## Baselines

Implement:

### Baseline A — Static Rules

```text
symptom → fixed rule → diagnosis
```

### Baseline B — One-Shot LLM

```text
incident context → LLM → diagnosis
```

### Baseline C — LLM + Retrieval

```text
incident
→ historical evidence
→ LLM
→ diagnosis
```

### Proposed

```text
incident
→ hypotheses
→ active evidence selection
→ verification
→ root cause
```

## Metrics

### Accuracy

- exact RCA accuracy
- top-k RCA accuracy
- false-diagnosis rate

### Investigation Efficiency

- tool calls
- evidence items inspected
- diagnosis time
- budget usage

### Evidence Quality

- evidence correctness
- unsupported-claim rate
- provenance correctness
- contradiction handling

### Remediation

- recommendation correctness
- remediation success
- recovery time

## Exit Criteria

A single command can run the full benchmark.

## Git Commit

```bash
git status
git diff
git add benchmark/ evaluator/ docs/ tests/
git commit -m "test: add RCA benchmark and baselines"
```

---

# PHASE 12 — Ablation and Fixed-Budget Experiments

## Objective

Prove which parts of the architecture actually matter.

## Ablations

Compare:

```text
Full system
Full - active evidence selection
Full - historical memory
Full - hypothesis verification
Full - dynamic routing
```

## Fixed Budgets

Every system should operate under the same:

```text
time budget
tool-call budget
token budget
hypothesis budget
```

This prevents the proposed agent from winning simply by consuming more resources.

## Experiments

Test:

1. accuracy under equal tool budget
2. accuracy under equal time budget
3. diagnosis speed
4. evidence quality
5. remediation success
6. cost of investigation

## Exit Criteria

The final report can identify which modules materially improve performance.

## Git Commit

```bash
git status
git diff
git add benchmark/ evaluator/ results/ docs/
git commit -m "test: add ablation and budget experiments"
```

---

# PHASE 13 — Frontend Investigation Console

## Objective

Build a UI that makes the AI investigation process understandable.

## UI Views

### Incident Overview

Show:

- incident
- severity
- status
- affected services
- current hypothesis

### Hypothesis Board

Example:

```text
H1 Database Regression      0.74
H2 Bad Deployment           0.81
H3 Dependency Failure       0.21
H4 CPU Saturation           0.05
```

### Evidence Timeline

Show:

```text
14:21 deployment
14:27 latency starts
14:29 DB latency spikes
14:31 errors increase
```

### Investigation Actions

Show:

```text
+ queried metrics
+ checked deployment
+ inspected DB
- rejected dependency hypothesis
```

### Remediation

Show:

- proposed action
- policy status
- approval
- execution
- verification

### Audit

Provide a complete chronological event stream.

## Testing

- frontend unit tests
- API integration
- empty states
- failed tool states
- unresolved incident state

## Exit Criteria

A judge can understand the entire investigation from the UI without seeing implementation internals.

## Git Commit

```bash
git status
git diff
git add frontend/ backend/api/ docs/ tests/
git commit -m "feat: add investigator console"
```

---

# PHASE 14 — Reliability, Security, and Failure Testing

## Objective

Test the system under adversarial and operationally imperfect conditions.

## Required Failures

### Tool failure

```text
metrics backend unavailable
```

Expected:

- no hallucinated metric
- alternate evidence if available
- confidence updated
- escalation if needed

### Conflicting evidence

```text
metrics indicate DB issue
logs indicate deployment issue
```

Expected:

- both represented
- no silent overwrite
- additional investigation

### Remediation failure

Expected:

- failure recorded
- no fake success
- next step selected safely

### Duplicate action

Expected:

- idempotency protection

### LLM failure

Expected:

- controlled fallback
- deterministic state handling

### Unknown incident

Expected:

```text
INSUFFICIENT_EVIDENCE
```

## Security Tests

- tool permission enforcement
- prompt injection resistance at tool boundary
- evaluator immutability
- audit integrity
- destructive-action approval
- secret handling

## Exit Criteria

No tested failure causes the system to fabricate success or bypass policy.

## Git Commit

```bash
git status
git diff
git add tests/ agent/ tools/ docs/
git commit -m "test: harden investigator reliability and safety"
```

---

# PHASE 15 — Final Research Evaluation

## Objective

Run the final controlled evaluation without changing the benchmark after seeing the results.

## Final Protocol

Freeze:

- scenarios
- ground truth
- test set
- evaluator
- budgets
- scoring rules

Then execute:

```text
Rules
LLM
LLM + RAG
Proposed Agent
```

## Final Report

Include:

### Performance

- RCA accuracy
- diagnosis time
- tool calls
- evidence quality
- remediation success

### Ablations

Show what each component contributes.

### Failure Analysis

Document:

- wrong diagnoses
- unsupported conclusions
- failed tools
- failed remediation
- unresolved incidents

### Limitations

Be explicit about:

- synthetic environment
- limited incident classes
- model/provider dependence
- generalization limits

## Exit Criteria

All reported numbers are reproducible from committed benchmark code.

## Git Commit

```bash
git status
git diff
git add results/ reports/ docs/ benchmark/
git commit -m "test: finalize investigator evaluation"
```

---

# PHASE 16 — Final Demo, Documentation, and Release

## Objective

Prepare the project for Razorpay AI Builders submission.

## Final Demo Flow

### Demo 1 — Incident Investigation

```text
API latency increases
        ↓
Agent generates hypotheses
        ↓
Selects evidence
        ↓
Rejects weak hypotheses
        ↓
Identifies root cause
```

### Demo 2 — Bounded Remediation

```text
Rollback proposed
        ↓
Policy check
        ↓
Approved
        ↓
Execute
        ↓
Verify recovery
```

### Demo 3 — Graceful Tool Failure

```text
Trace backend unavailable
        ↓
Agent does not fabricate trace
        ↓
Uses alternate evidence
        ↓
Confidence adjusted
```

### Demo 4 — Unknown Incident

```text
Evidence insufficient
        ↓
Agent refuses unsupported root cause
        ↓
Escalates
```

## Documentation

Finalize:

```text
README.md
docs/architecture.md
docs/research.md
docs/evaluation.md
docs/safety.md
docs/limitations.md
docs/demo.md
```

README should clearly state:

- what problem is solved
- why this is different from an incident summarizer
- architecture
- setup
- benchmark
- metrics
- limitations
- inspirations
- demo instructions

## CI

Ensure:

- tests pass
- lint passes
- type checks pass
- Docker build succeeds
- benchmark smoke test passes

## Final Git Commit

```bash
git status
git diff
git add README.md docs/ .github/ Dockerfile docker-compose.yml
git commit -m "docs: finalize investigator release"
```

Only after this commit should the project be considered release-ready.

---

# 4. Suggested Final Commit History

The final history should roughly look like:

```text
feat: initialize investigator architecture
feat: add controlled microservice environment
feat: add observability and telemetry layer
feat: add incident detection and fault scenarios
feat: add structured hypothesis engine
feat: add evidence investigation tools
feat: implement active investigation loop
feat: add evidence-grounded root cause verification
feat: add bounded remediation and policy engine
feat: add remediation outcome verification
feat: add historical investigation memory
test: add RCA benchmark and baselines
test: add ablation and budget experiments
feat: add investigator console
test: harden investigator reliability and safety
test: finalize investigator evaluation
docs: finalize investigator release
```

Do not squash the history into one generic commit.

Do not use:

```bash
git add .
```

Do not commit unrelated changes from other work.

Before every commit:

```bash
git status
git diff
```

Stage exact intended paths.

---

# 5. Final Definition of Done

The project is complete only when all of the following are true:

- [ ] Controlled service environment works from a clean checkout.
- [ ] At least four reproducible fault scenarios exist.
- [ ] Telemetry is available through metrics, logs and traces.
- [ ] Incidents are created deterministically.
- [ ] Agent maintains multiple explicit hypotheses.
- [ ] Agent chooses investigation actions dynamically.
- [ ] Evidence provenance is recorded.
- [ ] Contradictory evidence is handled.
- [ ] Agent can return `INSUFFICIENT_EVIDENCE`.
- [ ] Root-cause decisions are benchmarked.
- [ ] Bounded remediation exists.
- [ ] Remediation outcome is independently verified.
- [ ] Historical investigation memory is evaluated.
- [ ] Baseline systems are implemented.
- [ ] Ablation experiments are implemented.
- [ ] Fixed-budget experiments are implemented.
- [ ] Failure scenarios are tested.
- [ ] Audit trail is complete.
- [ ] Frontend shows the investigation lifecycle.
- [ ] CI is passing.
- [ ] README and technical documentation are complete.
- [ ] All phases have focused Git commits.
- [ ] No phase relies on `git add .`.
- [ ] Final benchmark results are reproducible.

---

# 6. CLI Operating Rules

The CLI/agent implementing this plan must follow these rules:

1. **Work strictly phase-by-phase.**
2. **Read the current repository before changing anything.**
3. **Do not silently skip a phase.**
4. **Do not implement future-phase features early unless required to unblock the current phase.**
5. **After every phase, run the phase-specific tests.**
6. **After every phase, update relevant documentation.**
7. **After every phase, inspect `git status` and `git diff`.**
8. **Stage only exact intended paths.**
9. **Never use `git add .`.**
10. **Commit after every completed phase.**
11. **Do not make unrequested architecture substitutions.**
12. **Do not claim a benchmark result until the benchmark has actually been executed.**
13. **Do not fabricate incident evidence or evaluation results.**
14. **Keep the environment minimal; prioritize the AI investigation engine.**
15. **Keep all remediation bounded and policy-controlled.**
16. **Preserve an auditable state transition for every incident.**
17. **If a phase reveals that a design assumption is invalid, document the change before continuing.**

---

# 7. One-Sentence Project Goal

> **Build an AI agent that learns to investigate software incidents by actively choosing evidence, testing competing hypotheses, identifying the most supported root cause, executing bounded remediation, and verifying the outcome — with every conclusion measurable and auditable.**
