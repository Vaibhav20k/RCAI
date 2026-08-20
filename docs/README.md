# Autonomous AI System Investigator
## Evidence-Driven Root-Cause Investigation, Verification, and Bounded Remediation

> **Project Type:** Razorpay AI Builders Internship Project  
> **Goal:** Build an AI agent that does not merely summarize incidents, but actively investigates them by generating competing hypotheses, selecting useful evidence, testing those hypotheses, identifying the most supported root cause, recommending or executing bounded remediation, and verifying whether the system actually recovered.
>
> **Core research question:**  
> **Can an AI agent improve root-cause diagnosis by actively selecting and testing evidence-backed hypotheses instead of performing one-shot incident summarization?**

---

# 1. Executive Thesis

Modern software systems fail in ways that are difficult to diagnose because evidence is fragmented across application logs, infrastructure metrics, distributed traces, database activity, queues, deployment history, configuration changes, external dependencies, and model/version changes.

Traditional monitoring systems are good at saying:

> **"Something is wrong."**

A conventional AI incident assistant may say:

> **"This appears to be a database problem."**

This project goes further.

The Autonomous AI System Investigator behaves more like an engineer performing a real investigation:

```text
Incident
   ↓
Understand the symptom
   ↓
Generate competing hypotheses
   ↓
Choose the most informative evidence to inspect
   ↓
Collect evidence
   ↓
Update / reject hypotheses
   ↓
Test the strongest hypothesis
   ↓
Identify root cause
   ↓
Recommend or execute bounded remediation
   ↓
Verify whether the remediation worked
   ↓
Produce an evidence-backed incident report
```

The central philosophy is:

> **Do not just explain the incident. Investigate it.**

---

# 2. Why This Project Exists

There is a gap between monitoring systems and genuinely autonomous investigation.

### Monitoring systems

They expose signals:

```text
CPU = 92%
Latency = 1.8 s
Error rate = 17%
```

but leave the engineer to connect the evidence.

### LLM incident copilots

They can summarize the same information:

> "The service appears unhealthy, possibly due to database latency."

but may anchor on the first plausible explanation, hallucinate evidence, ignore contradictory signals, fail to test alternatives, or recommend actions without verification.

### Our system

The agent instead asks:

> **"What evidence would distinguish these possible causes?"**

That turns root-cause analysis into **active investigation**.

---

# 3. Project Definition

## Working Name

**Autonomous AI System Investigator**

Possible future product names:

- Aegis Investigator
- TraceMind
- RootPilot

Final naming can be decided later.

---

# 4. Core Research Question

> **Can an evidence-selecting, hypothesis-testing AI agent achieve more reliable root-cause analysis than one-shot LLM diagnosis?**

We can compare three approaches.

### Baseline A — One-shot LLM

```text
Incident
 ↓
LLM
 ↓
Root Cause
```

### Baseline B — LLM + Retrieved Context

```text
Incident
 ↓
Retrieve relevant diagnostics
 ↓
LLM
 ↓
Root Cause
```

### Proposed system — Active Investigator

```text
Incident
 ↓
Hypothesis Generation
 ↓
Active Evidence Selection
 ↓
Evidence Collection
 ↓
Hypothesis Update
 ↓
Verification
 ↓
Root Cause
```

The final evaluation should determine whether active investigation creates measurable improvement.

---

# 5. What Makes This an AI Builder Project

The interesting part is not the observability stack.

The interesting part is the **AI investigation policy**.

The agent must decide:

> **What should I inspect next?**

Suppose an API latency spike occurs.

Possible hypotheses:

```text
H1 → Database regression
H2 → Recent deployment
H3 → Downstream dependency
H4 → CPU / memory saturation
H5 → Queue backlog
```

Instead of dumping everything into an LLM, the agent selects a diagnostic action.

For example:

```text
Check deployment timeline
```

Result:

> Latency increase began six minutes after deployment.

That increases confidence in H2.

Next:

```text
Inspect database query latency
```

Result:

> One query is 4.2× slower.

Next:

```text
Compare query behaviour before/after deployment
```

Evidence may show that the deployment introduced the query regression.

The agent has **tested hypotheses**, not merely generated a plausible explanation.

---

# 6. Product Philosophy

The system should follow:

```text
OBSERVE
   ↓
HYPOTHESIZE
   ↓
INVESTIGATE
   ↓
EVIDENCE
   ↓
VERIFY
   ↓
ACT
   ↓
VERIFY AGAIN
```

The second verification step is essential.

A system should not say:

> "Rollback should fix the issue."

It should check whether the system actually improved:

```text
Before:
p95 latency = 1.8 s

After:
p95 latency = 620 ms
```

If the incident persists, the agent should continue or escalate instead of declaring success.

---

# 7. Research Foundations

## 7.1 AIOpsLab

**AIOpsLab: A Holistic Framework to Evaluate AI Agents for Enabling Autonomous Clouds** is highly relevant because it treats autonomous operations as an evaluation problem, using controlled environments, faults, telemetry and measurable incident workflows.

The useful lesson for this project is:

> **Evaluate agents in reproducible environments where failures can be injected and the complete incident lifecycle can be measured.**

Therefore we should build a small controlled benchmark environment instead of relying only on a live ad-hoc demo.

## 7.2 RCA-Copilot

Microsoft research has explored LLM-assisted root-cause analysis using diagnostic information from multiple sources.

The useful lesson is that LLMs can assist incident diagnosis, but the quality and structure of the diagnostic evidence strongly affect the result.

Our extension is to make evidence collection itself **agentic**.

## 7.3 Reliability of LLM-based RCA

Recent chaos-engineering evaluations have shown that one-shot LLM root-cause analysis can make substantial errors and that richer context and structured investigation can improve results.

This supports our research question:

> **Can active hypothesis testing and evidence selection make LLM-based RCA more reliable?**

## 7.4 AIOps Safety

Research on manipulated telemetry demonstrates that AI-operated systems can make incorrect decisions when telemetry is trusted blindly.

Therefore evidence provenance, validation, tool permissions, and external evaluation are core parts of this architecture.

---

# 8. Existing Project Foundations We Can Reuse

## 8.1 BehaviourIQ → Behavioural Context

BehaviourIQ's useful abstraction is:

```text
Entity → Event → Context → Time
```

with temporal baselines, behavioural drift, sequence signals, velocity signals, graph relationships and investigation workflows.

The transferable principle is:

> **An event has meaning only in context.**

For infrastructure investigation:

```text
Service
   ↓
Event
   ↓
Context
   ↓
Time
```

Example:

```text
Service A normally:
- p95 latency = 400 ms
- error rate = 1–2%
- DB calls = 100/s

Current:
- p95 latency = 1.8 s
- error rate = 18%
- DB calls = 900/s
```

The agent can identify a deviation from the service's own baseline rather than only comparing against a global threshold.

## 8.2 ROSER → Investigation → Response → Verification

ROSER's strongest transferable idea is its full lifecycle:

```text
Observe
 ↓
Normalize
 ↓
Detection
 ↓
Risk Fusion
 ↓
Investigation
 ↓
Response
 ↓
Verification
 ↓
Learning
```

For this project:

```text
Incident
 ↓
Evidence normalization
 ↓
Hypothesis generation
 ↓
Investigation
 ↓
Root-cause decision
 ↓
Remediation
 ↓
Verification
 ↓
Learning
```

The key principle is:

> **The agent's answer is not the end of the workflow. Outcome verification is part of the workflow.**

---

# 9. Saksham Repository-Inspired Design Principles

The goal is **not to clone Saksham's repositories**.

We are extracting reusable engineering mechanisms and adapting them to autonomous incident investigation.

---

## 9.1 Incident Engine → Investigation as a First-Class Workflow

### Source

**Incident Engine**  
https://github.com/saksham10arora-dotcom/incident-engine

### What we learned

The useful mechanism is:

```text
Observe
→ classify
→ correlate
→ investigate
→ retrieve evidence
→ validate
→ act
```

### Our adaptation

```text
Incident
 ↓
Classify symptom
 ↓
Generate hypotheses
 ↓
Select evidence
 ↓
Investigate
 ↓
Validate hypotheses
 ↓
Recommend remediation
```

The key change is:

> The agent is responsible for **deciding what to investigate next**, not merely summarizing retrieved information.

---

# 10. Latency Router → Dynamic Investigation Routing

### Source

**Latency Router**  
https://github.com/saksham10arora-dotcom/latency-router

### What we learned

The transferable principle is:

> **Choose the next path using current system state instead of relying on a static workflow.**

For example:

```text
Incident
 ↓
Complexity / ambiguity estimation
 ↓
 ┌───────────────────┬──────────────────────┐
 │ Simple            │ Complex              │
 │ known pattern     │ ambiguous incident   │
 └─────────┬─────────┴───────────┬──────────┘
           ↓                     ↓
    Fast diagnostic        Active investigation
                                    ↓
                             Multiple hypotheses
```

This prevents every incident from triggering the most expensive reasoning process.

---

# 11. AMD Hybrid Router → Escalation Architecture

### Source

**AMD Hybrid Router**  
https://github.com/saksham10arora-dotcom/amd-hybrid-router

### What we learned

The transferable principle is:

> **Use a lightweight route for routine cases and escalate only when deeper reasoning is necessary.**

For the investigator:

```text
Telemetry anomaly
      ↓
Fast diagnostic classifier
      |
      +--> obvious known failure
      |        ↓
      |   deterministic runbook
      |
      +--> ambiguous incident
               ↓
         AI investigation
```

Benefits:

- lower cost
- lower latency
- predictable behaviour
- less unnecessary LLM usage
- easier auditing

---

# 12. LMEX → Measurement-First Investigation

### Source

**LMEX**  
https://github.com/saksham10arora-dotcom/LMEX

### What we learned

The important principle is:

> **Every meaningful claim about system quality should have a measured basis.**

Therefore the investigator should track:

```text
Root-cause accuracy
Time to diagnosis
Evidence retrieval efficiency
Hypothesis elimination rate
Tool calls per investigation
Remediation success
False diagnosis rate
```

Example dashboard:

```text
Investigation Quality
──────────────────────
RCA Accuracy          84%
Median Diagnosis      52 sec
Evidence Precision    91%
Wrong Diagnosis        7%
Verified Remediation  79%
```

These values are illustrative until measured.

---

# 13. Simple-HFT-Engine → Correctness and Benchmark Discipline

### Source

**Simple-HFT-Engine**  
https://github.com/saksham10arora-dotcom/Simple-HFT-Engine

### What we learned

The transferable principle is:

> **Correctness, deterministic state transitions, benchmarking and performance discipline matter under real-time constraints.**

Our agent may be probabilistic.

The surrounding control system should not be.

The environment should guarantee:

- explicit state transitions
- idempotent actions
- bounded execution
- reproducible evaluations
- measurable latency
- consistent audit logging

---

# 14. Gitrade → Explicit Incident State Machine

### Source

**gitrade**  
https://github.com/saksham10arora-dotcom/gitrade

### What we learned

The useful abstraction is explicit, auditable state transitions.

Every incident becomes:

```text
NEW
 ↓
DETECTED
 ↓
INVESTIGATING
 ↓
HYPOTHESES_GENERATED
 ↓
EVIDENCE_COLLECTING
 ↓
ROOT_CAUSE_PROPOSED
 ↓
REMEDIATION_PENDING
 ↓
REMEDIATION_EXECUTED
 ↓
VERIFICATION
 ↓
 ┌───────────────┬───────────────┐
 ↓               ↓               ↓
RESOLVED      UNRESOLVED      ESCALATED
```

Every transition creates an audit event.

---

# 15. Active Investigation Engine

This is the proposed core innovation.

The agent maintains structured investigation state:

```text
Hypothesis
Confidence
Supporting Evidence
Contradicting Evidence
Next Best Investigation
```

Example:

```text
H1: Database regression
Confidence: 0.42

Supporting:
- DB query latency ↑ 4x

Contradicting:
- only one endpoint affected

Next action:
Compare deployment version
```

New evidence:

```text
Latency increase begins 6 minutes after deployment.
```

Updated hypothesis confidence:

```text
H1 → 0.73
```

The system stores **structured investigation state**, not private chain-of-thought.

---

# 16. Evidence Selection

The agent should not inspect everything indiscriminately.

It should choose the next evidence source using:

### Informativeness

Which diagnostic action best distinguishes competing hypotheses?

### Cost

How expensive or slow is this action?

### Reliability

How trustworthy is the evidence source?

### Recency

Does the evidence belong to the relevant incident window?

Conceptually:

```text
Investigation Utility
=
Expected hypothesis reduction
/
Investigation cost
```

This provides a principled basis for active investigation.

---

# 17. Hypothesis Management

Every incident should maintain a candidate set.

Example:

```text
Incident: payment API latency spike

H1 — Database regression
H2 — New deployment
H3 — External payment dependency
H4 — Resource saturation
H5 — Queue backlog
```

The agent should:

1. generate hypotheses,
2. collect evidence,
3. update confidence,
4. reject weak hypotheses,
5. focus resources on the strongest remaining explanation.

This is the heart of the project.

---

# 18. Evidence Provenance

Every evidence item should contain:

```text
evidence_id
source
timestamp
query/tool used
raw/derived status
incident window
reliability metadata
```

Example:

```json
{
  "evidence_id": "ev_1029",
  "source": "prometheus",
  "metric": "db_query_latency_p95",
  "timestamp": "2026-08-20T15:24:12Z",
  "value": 842,
  "unit": "ms",
  "derived": false
}
```

Final reports should link conclusions to evidence IDs.

---

# 19. Contradictory Evidence

A major design goal is to explicitly track evidence **against** a hypothesis.

Example:

```text
Hypothesis:
Database is root cause.

Supporting:
+ DB latency increased 4x

Contradicting:
- CPU remained normal
- only one endpoint degraded
- other services using the same DB were unaffected
```

The agent should not ignore contradictory evidence merely because its first hypothesis looked plausible.

This is intended to reduce confirmation bias.

---

# 20. Investigation Tools

The agent should receive constrained tools such as:

```text
query_logs()
query_metrics()
query_traces()
compare_service_versions()
inspect_deployment_history()
inspect_config_changes()
inspect_dependencies()
query_database_metrics()
run_readonly_diagnostic()
compare_before_after()
```

Potential remediation tools should be separate:

```text
create_rollback_plan()
restart_service()
rollback_deployment()
disable_feature_flag()
```

High-impact tools require a policy or human approval.

---

# 21. Tool Permission Model

The AI must not receive unrestricted system access.

### Read-only tools

Safe by default:

```text
metrics
logs
traces
deployment history
config history
dependency health
```

### Proposed-action tools

Require policy checks:

```text
rollback
restart
feature-flag change
traffic shift
```

### Destructive actions

Human approval only.

The agent must never bypass the policy layer.

---

# 22. Remediation Architecture

The first version should emphasize **recommendation and controlled execution**, not unrestricted autonomous repair.

```text
Root cause
 ↓
Candidate remediation
 ↓
Impact estimate
 ↓
Policy check
 ↓
Approval
 ↓
Execute in sandbox / controlled environment
 ↓
Verify
```

Example:

```text
Root cause:
bad deployment introduced DB regression

Candidate action:
rollback v2.4.1

Policy:
rollback approved for this service

Execute
 ↓
Verify p95 latency
 ↓
Resolved
```

---

# 23. Verification

A remediation should only be marked successful if measurable system behaviour improves.

Examples:

### Latency

```text
Before: 1.8 s p95
After: 620 ms p95
```

### Error rate

```text
Before: 18%
After: 2.3%
```

### Queue backlog

```text
Before: 24,000
After: 2,100
```

Thresholds should be predefined by the evaluation environment.

---

# 24. Learning From Investigations

The system can retain structured experience:

```text
incident type
root cause
successful evidence path
failed evidence paths
successful remediation
verification result
```

Example:

```text
Incident Type:
deployment-induced DB regression

Efficient investigation sequence:
1. deployment history
2. DB query latency
3. query diff
4. rollback simulation
```

Future incidents can use this as **experience-guided investigation knowledge**.

This is controlled strategy learning, not unrestricted recursive self-modification.

---

# 25. Optional Self-Evaluation

The self-rewarding/self-evaluation concept discussed during project selection can be used carefully.

The agent may produce:

```text
Investigation confidence
Evidence completeness
Hypothesis consistency
```

However:

> **Self-evaluation is never the ground truth.**

An external evaluator determines whether:

- the root cause was correct,
- the evidence was valid,
- the remediation was correct,
- the incident was actually resolved.

This prevents circular self-approval.

---

# 26. Controlled Benchmark Environment

Inspired by benchmark-oriented AIOps research, we should build a small controlled environment.

It does not need to be a massive production platform.

Example:

```text
                   Synthetic User Traffic
                           |
                           v
                     API Gateway
                           |
            +--------------+--------------+
            |                             |
            v                             v
       Order Service                Payment Service
            |                             |
            v                             v
       PostgreSQL                    Redis / Queue
            |
            v
      External Dependency
```

Observability:

```text
Prometheus → metrics
Centralized logs → application evidence
Distributed tracing → request flow
Deployment history → version/change evidence
```

The environment exists to create realistic evidence for the AI investigator.

---

# 27. Controlled Fault Injection

We should define repeatable incidents.

### Incident Class 1 — Database Regression

Inject:

- slow query
- connection pressure
- missing index

### Incident Class 2 — Bad Deployment

Inject:

- inefficient code version
- configuration regression
- dependency upgrade

### Incident Class 3 — Dependency Failure

Inject:

- increased downstream latency
- elevated downstream errors
- intermittent timeouts

### Incident Class 4 — Resource Saturation

Inject:

- CPU stress
- memory pressure
- worker exhaustion

### Incident Class 5 — Queue Backlog

Inject:

- producer burst
- consumer slowdown
- stuck worker

### Incident Class 6 — AI-Specific Failure

Optional:

- model service latency
- retrieval service failure
- invalid model output
- embedding service degradation

---

# 28. Evaluation Framework

The benchmark must be defined before tuning the agent.

## Root-Cause Metrics

- exact root-cause accuracy
- top-k root-cause accuracy
- false-diagnosis rate
- hypothesis rejection accuracy

## Investigation Metrics

- time to diagnosis
- number of tool calls
- evidence items inspected
- unnecessary tool calls
- useful-evidence ratio
- number of hypotheses considered

## Evidence Metrics

- evidence correctness
- evidence provenance correctness
- unsupported-claim rate
- contradictory-evidence handling

## Remediation Metrics

- recommendation correctness
- remediation success rate
- rollback success
- recovery time
- unsafe-action rate

## Reliability

- tool failure recovery
- timeout handling
- duplicate-action protection
- state-machine consistency

---

# 29. Baselines and Ablation Study

A serious project should compare multiple configurations.

### Baseline 1 — Static Rules

```text
Metric threshold
→ Fixed runbook
```

### Baseline 2 — One-Shot LLM

```text
Incident context
→ LLM
→ Root cause
```

### Baseline 3 — LLM + RAG

```text
Incident
→ retrieve historical cases
→ LLM
```

### Proposed System

```text
Incident
→ hypotheses
→ active evidence selection
→ evidence updates
→ verification
→ root cause
```

Then run ablations:

```text
Proposed
Proposed - active evidence selection
Proposed - historical memory
Proposed - hypothesis verification
Proposed - dynamic routing
```

This tells us which components actually matter.

---

# 30. Example Evaluation Table

| System | RCA Accuracy | Median Diagnosis Time | Tool Calls | Wrong Diagnosis |
|---|---:|---:|---:|---:|
| Rules | X | X sec | X | X% |
| One-shot LLM | X | X sec | X | X% |
| LLM + RAG | X | X sec | X | X% |
| Proposed Investigator | X | X sec | X | X% |

All values must come from actual experiments.

---

# 31. Research Experiments

### Primary hypothesis

> **Active evidence selection with hypothesis testing improves root-cause accuracy compared with one-shot LLM diagnosis under the same evidence/tool budget.**

### Secondary hypotheses

**H1:** Active investigation reduces false diagnoses.

**H2:** Evidence provenance reduces unsupported conclusions.

**H3:** Historical investigation memory reduces time-to-diagnosis.

**H4:** A lightweight routing layer reduces unnecessary tool calls.

**H5:** Post-remediation verification improves final incident resolution accuracy.

---

# 32. Fixed-Budget Evaluation

To prevent the agent from winning simply by consuming more resources, define fixed budgets:

```text
Maximum investigation time
Maximum tool calls
Maximum tokens
Maximum hypotheses
Maximum remediation attempts
```

Example:

```text
Budget:
20 tool calls
90 seconds
Fixed token budget
```

Compare systems under equal budgets.

This makes the benchmark substantially more scientifically defensible.

---

# 33. Cost-Aware Investigation

Not every investigation action costs the same.

Example:

```text
Read deployment metadata     → cheap
Query Prometheus             → cheap
Search historical incidents  → medium
Run benchmark                → expensive
Restart service              → high impact
```

The agent should consider cost and risk while choosing actions.

Conceptually:

```text
Investigation Utility
=
Expected diagnostic information
/
Cost + risk
```

This connects naturally to the dynamic-routing ideas extracted from Saksham's repositories.

---

# 34. Dashboard

The UI should focus on **investigation state**, not generic observability.

### Incident Overview

```text
Incident #1042
Severity: High
Status: Investigating

Symptom:
API p95 latency ↑ 4.5x
```

### Hypothesis Board

```text
H1 Database regression       0.74
H2 Deployment regression     0.81
H3 Dependency failure       0.21
H4 CPU saturation            0.05
```

### Evidence Timeline

```text
14:21 Deployment v2.4.1
14:27 Latency begins rising
14:29 DB query p95 increases
14:31 Error rate increases
```

### Investigation Actions

```text
+ Checked deployment history
+ Checked DB metrics
+ Compared query performance
- Dependency hypothesis rejected
```

### Remediation

```text
Candidate:
Rollback v2.4.1

Policy:
Approved

Result:
p95 reduced 66%

Status:
RESOLVED
```

---

# 35. Incident Report

The final report should be structured:

```text
Incident Summary

Symptom

Impact

Hypotheses Considered

Evidence Supporting Each Hypothesis

Evidence Contradicting Each Hypothesis

Root Cause

Confidence

Recommended / Executed Remediation

Verification Result

Timeline

Audit Trail
```

The report should reference structured evidence IDs.

---

# 36. Failure Handling

At least one graceful failure should be demonstrated.

## Example: Tool failure

```text
Agent requests trace data
      ↓
Trace backend unavailable
      ↓
Agent detects tool failure
      ↓
Does NOT invent trace evidence
      ↓
Uses alternative evidence source
      ↓
Confidence adjusted
      ↓
Continues or escalates
```

This is a core property of a trustworthy investigator.

A strong agent should know:

> **"I do not have enough evidence."**

instead of confidently hallucinating a diagnosis.

---

# 37. Unknown / Unresolved Incident

The system must support:

```text
ROOT CAUSE UNKNOWN
```

This is a feature, not a failure.

If:

- hypotheses remain ambiguous,
- evidence conflicts,
- tools fail,
- confidence stays below threshold,

the agent should escalate.

Example:

```text
Diagnosis confidence: 0.46

Decision:
Insufficient evidence for automatic remediation.

Action:
Escalate to human engineer.

Reason:
Two hypotheses remain statistically indistinguishable.
```

This makes the system more credible than an agent forced to produce an answer every time.

---

# 38. Security and Safety

Because the agent may receive operational tools:

### Principle 1

Read-only investigation by default.

### Principle 2

High-impact actions require policy approval.

### Principle 3

Destructive actions require human approval.

### Principle 4

Agent cannot modify its own evaluator.

### Principle 5

Agent cannot modify audit logs.

### Principle 6

Every action is logged before and after execution.

### Principle 7

Remediation should be reversible whenever possible.

---

# 39. Technology Stack

## Application Environment

- Docker Compose initially
- small microservice environment
- controlled fault injector

## AI Agent

- Python
- LangGraph or equivalent state-machine/orchestration framework
- structured tool calling

## Backend

- FastAPI
- PostgreSQL
- Redis where useful

## Observability

- Prometheus
- centralized logs
- distributed tracing

## Knowledge

- structured incident store
- optional FAISS/vector retrieval for historical incidents

## Frontend

- Next.js
- React
- TypeScript

The infrastructure should remain intentionally minimal.

> **The AI investigation engine is the product.**

---

# 40. Proposed Repository Structure

```text
autonomous-system-investigator/
│
├── agent/
│   ├── investigator/
│   ├── hypothesis/
│   ├── evidence/
│   ├── routing/
│   ├── verification/
│   ├── memory/
│   └── policies/
│
├── tools/
│   ├── logs/
│   ├── metrics/
│   ├── traces/
│   ├── deployments/
│   ├── database/
│   └── remediation/
│
├── simulator/
│   ├── services/
│   ├── faults/
│   ├── scenarios/
│   └── traffic/
│
├── benchmark/
│   ├── datasets/
│   ├── scenarios/
│   ├── evaluators/
│   ├── baselines/
│   └── reports/
│
├── backend/
│   ├── api/
│   ├── incidents/
│   ├── audit/
│   └── models/
│
├── frontend/
│   ├── dashboard/
│   ├── incidents/
│   ├── hypotheses/
│   └── evidence/
│
├── observability/
│   ├── prometheus/
│   ├── logs/
│   └── tracing/
│
├── docs/
│   ├── architecture.md
│   ├── research.md
│   ├── evaluation.md
│   └── safety.md
│
├── docker-compose.yml
├── README.md
└── .env.example
```

---

# 41. Development Phases

The implementation must follow the separate execution document:

`docs/PHASE_WISE_AUTONOMOUS_AI_SYSTEM_INVESTIGATOR.md`

The README defines **what the product is**. The phase document defines **how it is implemented**.

The authoritative phase sequence is:

```text
Phase 0  → Repository + research contract + architecture
Phase 1  → Controlled microservice environment
Phase 2  → Observability + telemetry normalization
Phase 3  → Incident detection + scenario engine
Phase 4  → Hypothesis engine
Phase 5  → Investigation tools
Phase 6  → Active investigation loop
Phase 7  → Root-cause verification + evidence provenance
Phase 8  → Bounded remediation + policy engine
Phase 9  → Outcome verification
Phase 10 → Historical incident memory + adaptive strategy
Phase 11 → Benchmark harness + baselines
Phase 12 → Ablation + fixed-budget experiments
Phase 13 → Frontend investigation console
Phase 14 → Reliability + security + failure testing
Phase 15 → Final research evaluation
Phase 16 → Final demo + documentation + release
```

### Phase synchronization rule

The phase document is the detailed execution plan for every phase.

A phase is complete only when its implementation, tests, verification, documentation, exit criteria, and Git commit requirements are satisfied.

If the implementation reveals a necessary architectural change, update both this README and the phase document before continuing.


# 42. MVP Definition

The first competitive MVP only needs:

```text
3–4 microservices
+
4 controlled incident types
+
metrics/logs/traces
+
AI investigation agent
+
hypothesis engine
+
5–8 read-only tools
+
one bounded remediation
+
verification
+
benchmark harness
```

Do not build a massive Kubernetes platform.

The goal is to make the AI investigation loop deep and measurable.

---

# 43. What We Are Explicitly NOT Building

This project is not:

- a generic AIOps dashboard
- an LLM log summarizer
- a chatbot over Prometheus
- a fully unrestricted production auto-remediation system
- a replacement for experienced SREs
- a system that claims certainty without evidence
- an agent that can modify its evaluator
- an agent that can hide failed actions
- an infrastructure project where AI is just an add-on

The infrastructure exists to create a realistic test environment.

**The AI investigator is the product.**

---

# 44. Success Criteria

The project should only be called successful if experiments show measurable improvement over useful baselines.

A strong result should demonstrate something like:

```text
One-shot LLM:
RCA accuracy = X%

LLM + RAG:
RCA accuracy = X%

Active Investigator:
RCA accuracy = X%

Active Investigator:
- fewer unsupported diagnoses
- better evidence grounding
- lower median diagnosis time
- bounded tool usage
- higher remediation verification rate
```

The values must come from actual experiments.

No benchmark result should be fabricated.

---

# 45. Final Demo Story

The best demo is a live investigation.

### Incident

> API latency has increased 4.5×.

### Agent

Generates:

```text
H1 Database regression      0.35
H2 Bad deployment           0.42
H3 Dependency failure       0.15
H4 Resource saturation      0.08
```

### Investigation

```text
Check deployment timeline
→ H2 ↑

Check DB query metrics
→ H1 ↑

Check dependency
→ H3 ↓

Compare query before/after deployment
→ H1 + H2 strongly supported
```

### Root Cause

> Deployment introduced a database query regression.

### Remediation

> Roll back to v2.4.0.

### Verification

```text
p95:
1.8 s → 620 ms

error rate:
18% → 2.3%
```

### Final status

> **Incident resolved.**

The UI displays the evidence chain and audit history behind the decision.

---

# 46. Inspiration Ledger

This section intentionally documents the sources of architectural inspiration.

| Source | Original topic | Principle borrowed | Our adaptation |
|---|---|---|---|
| Saksham — **Incident Engine** | AI incident investigation | Investigate before acting | Hypothesis → evidence → validation → root cause |
| Saksham — **Latency Router** | Dynamic routing | Select a path using current runtime state | Choose the next investigation step dynamically |
| Saksham — **AMD Hybrid Router** | Hybrid AI routing | Cheap path + escalation path | Fast diagnostics + deep investigation only when needed |
| Saksham — **LMEX** | Continuous benchmarking | Measurement-first engineering | RCA accuracy, diagnosis time, evidence quality |
| Saksham — **Simple-HFT-Engine** | Low-latency correctness | Correctness + benchmarking + deterministic control | Safe tool execution and predictable state changes |
| Saksham — **gitrade** | Event-driven state | Explicit state transitions + auditability | Incident investigation state machine |
| Our **BehaviourIQ** | Behaviour intelligence | Entity/event/context/time + temporal baselines | Service behaviour and anomaly context |
| Our **ROSER** | Security reasoning | Investigate → respond → verify → learn | Root-cause investigation and remediation verification |
| AIOps research | Autonomous cloud agents | Controlled benchmark + fault injection | Reproducible incident evaluation environment |
| Self-evaluation research | Self-rewarding / self-evaluation | Evaluate agent work explicitly | Advisory investigation confidence, never ground truth |
| Recursive self-improvement experiment | Strategy adaptation under budgets | Fixed budgets + measured improvement | Optional experience-guided investigation strategy selection |

These are **design inspirations and research references**, not copied implementations.

---

# 47. Final Product Definition

## Working Name

**Autonomous AI System Investigator**

## One-line description

> **An evidence-driven AI agent that actively investigates software incidents by generating competing hypotheses, selecting the most informative evidence, verifying root cause, executing bounded remediation, and confirming whether the system actually recovered.**

## Core differentiator

Normal AI incident assistant:

> **"Here is a summary of what might have happened."**

Our system:

> **"Here are the competing causes. I selected evidence to distinguish them, rejected unsupported hypotheses, identified the most supported root cause, executed a bounded remediation, and verified its effect."**

## Technical differentiator

```text
Active investigation
+
Hypothesis management
+
Evidence selection
+
Evidence provenance
+
Tool-based reasoning
+
Bounded remediation
+
Outcome verification
+
Benchmark-driven evaluation
```

---

# 48. Final Architecture Principle

```text
OBSERVE
   ↓
GENERATE HYPOTHESES
   ↓
CHOOSE THE MOST INFORMATIVE NEXT ACTION
   ↓
COLLECT EVIDENCE
   ↓
UPDATE / REJECT HYPOTHESES
   ↓
VERIFY ROOT CAUSE
   ↓
RECOMMEND / EXECUTE BOUNDED REMEDIATION
   ↓
VERIFY SYSTEM RECOVERY
   ↓
STORE STRUCTURED EXPERIENCE
```

The central research philosophy is:

> **An AI investigator should not be judged by how convincing its explanation sounds. It should be judged by whether it can efficiently gather the right evidence, reach the correct diagnosis, and verify that its intervention actually worked.**

---

# References / Research Starting Points

The final implementation should keep a separate research log containing exact paper versions, publication venues, benchmark definitions, and reproduction notes.

Suggested starting references:

- **AIOpsLab: A Holistic Framework to Evaluate AI Agents for Enabling Autonomous Clouds**
- **RCA-Copilot** and related LLM-assisted root-cause analysis work
- Recent empirical work evaluating LLM-based root-cause analysis under controlled chaos/fault scenarios
- Recent AIOps/Agentic NetOps work on tool boundaries, evidence traces, authorization and verification
- Research on telemetry manipulation and safety risks in AI-driven AIOps

The implementation README should be updated with exact citations and experimental results after the benchmark environment is established.


---

# 49. CLI Master Implementation Contract

This README is the **product and architecture source of truth**.

The separate file:

`docs/PHASE_WISE_AUTONOMOUS_AI_SYSTEM_INVESTIGATOR.md`

is the **execution source of truth**.

The CLI must read and obey both files **before starting work and before starting every new phase**:

```text
docs/README_AUTONOMOUS_AI_SYSTEM_INVESTIGATOR.md
docs/PHASE_WISE_AUTONOMOUS_AI_SYSTEM_INVESTIGATOR.md
```

## 49.1 Authority and precedence

Use the following precedence order:

1. Explicit user instruction in the current task.
2. This README for product intent, architecture, scope, safety, research goals, and constraints.
3. `PHASE_WISE_AUTONOMOUS_AI_SYSTEM_INVESTIGATOR.md` for phase order, deliverables, tests, exit criteria, and Git commits.
4. Existing repository code and configuration for current implementation state.

Do not silently replace the documented architecture with a different design because another framework or pattern is more convenient.

If an implementation detail is genuinely ambiguous, choose the smallest solution that preserves the documented architecture and record the decision in `docs/decisions.md`.

## 49.2 Before modifying the repository

The CLI must:

1. Inspect the repository tree.
2. Inspect existing source files, configuration, tests, and documentation.
3. Check the current Git branch and working tree.
4. Read this README.
5. Read `PHASE_WISE_AUTONOMOUS_AI_SYSTEM_INVESTIGATOR.md`.
6. Determine the current phase from repository state and existing commits.
7. Do not repeat completed work unless verification shows that it is incomplete or broken.

Required commands:

```bash
git status
git branch --show-current
git log --oneline --decorate -n 20
```

Then inspect relevant files before editing.

## 49.3 Phase execution rule

Work **strictly one phase at a time**.

For the current phase:

```text
Read phase requirements
        ↓
Inspect existing implementation
        ↓
Implement only the required scope
        ↓
Write/update tests
        ↓
Run verification
        ↓
Update documentation
        ↓
Review diff
        ↓
Commit
        ↓
Only then move to next phase
```

Do not pre-build future phases merely because they seem convenient.

Do not skip phases.

Do not mark a phase complete because the code "looks right." The phase exit criteria must be demonstrably satisfied.

## 49.4 Professional code quality requirements

Write production-quality code appropriate for a serious engineering project.

### General

- Prefer clear, small modules with single responsibilities.
- Avoid giant files and giant functions.
- Use descriptive names.
- Keep public interfaces explicit.
- Prefer composition over unnecessary inheritance.
- Avoid duplicated business logic.
- Keep configuration separate from implementation.
- Use typed models/schemas at service boundaries.
- Validate external input.
- Handle errors explicitly.
- Do not swallow exceptions silently.
- Do not rely on hidden global state.
- Make state transitions explicit.

### Python

Use:

- type hints
- dataclasses or Pydantic models where appropriate
- structured logging
- clear exception types
- async code only where it provides a concrete benefit
- pytest for tests

Avoid:

- wildcard imports
- mutable module-level state
- magic constants scattered through code
- `except Exception: pass`
- `print()` for application logging

### Backend / API

- Validate requests and responses.
- Return consistent error structures.
- Use explicit HTTP status codes.
- Keep business logic out of route handlers where practical.
- Add request IDs/correlation IDs.
- Make side-effecting operations idempotent.

### Agent code

The agent must be stateful and inspectable.

Use explicit state objects for:

```text
incident
hypotheses
evidence
investigation actions
tool results
confidence
decision
remediation
verification
```

Do not make the core investigator one giant prompt.

Prefer:

```text
state
→ planner
→ tool
→ result parser
→ hypothesis updater
→ stopping policy
```

over an opaque autonomous loop.

### Tool implementations

Every tool must define:

```text
purpose
input schema
output schema
timeout
permission level
failure modes
```

Read-only and write-capable tools must be clearly separated.

### Frontend

Keep the UI focused on the investigator's state:

- incident
- hypotheses
- evidence
- actions
- decision
- remediation
- verification
- audit trail

Do not spend implementation time on decorative UI effects before the investigation workflow works.

## 49.5 Comments and code documentation

**Do not use emojis in source-code comments, docstrings, variable names, log messages, commit messages, or identifiers.**

Comments must be professional and explain:

- why a non-obvious decision exists,
- what invariant must be preserved,
- why a workaround is required,
- what safety constraint is being enforced.

Do not write comments that merely restate the code.

Do not include decorative comments, motivational comments, emojis, or informal chat-style comments.

## 49.6 Agent reasoning and data handling

Do not persist private chain-of-thought.

Persist only structured investigation state:

```text
hypothesis
confidence
supporting_evidence
contradicting_evidence
next_action
tool_result_summary
decision
```

The system must be able to explain a conclusion through evidence IDs without storing hidden reasoning traces.

## 49.7 Evidence integrity

Never fabricate telemetry.

If a tool returns no data, record:

```text
NO_EVIDENCE_FOUND
```

If the tool fails, record:

```text
EVIDENCE_SOURCE_UNAVAILABLE
```

Do not convert a tool failure into an invented result.

Every evidence record should contain provenance.

## 49.8 External evaluator is authoritative

The agent's own confidence or self-evaluation is advisory only.

The following must remain outside the agent's control:

- benchmark ground truth
- test fixtures
- evaluation code
- scoring logic
- audit history
- immutable test harness

The agent must not modify:

```text
benchmark ground truth
evaluation scripts
test scenarios
scoring thresholds
audit records
```

## 49.9 Safety and remediation

Default permission level:

```text
READ_ONLY
```

Higher levels:

```text
RECOMMEND
APPROVAL_REQUIRED
CONTROLLED_EXECUTION
```

Destructive or high-impact actions require human approval.

Remediation must be:

- bounded
- logged
- idempotent
- reversible where possible
- independently verified

Never let an LLM directly construct unrestricted shell commands for operational execution.

Use pre-defined tools and validated parameters.

## 49.10 Evaluation discipline

Never invent benchmark results.

Use:

```text
X
```

or:

```text
TBD
```

until an experiment has actually been run.

Do not tune against the held-out test set.

Keep:

```text
development data
validation data
held-out benchmark scenarios
```

conceptually and operationally separate.

For fixed-budget experiments, keep budgets constant across compared systems.

## 49.11 Testing requirements

Every phase must add tests appropriate to what it introduces.

Minimum expectations:

- unit tests for business logic
- tool contract tests
- API integration tests
- state transition tests
- scenario tests
- failure-path tests
- benchmark/evaluator tests

A phase is not complete if tests are missing for its critical new behaviour.

## 49.12 Documentation requirements

When implementation changes architecture or contracts, update the relevant documentation in the same phase.

At minimum keep these consistent:

```text
README.md
docs/architecture.md
docs/research.md
docs/evaluation.md
docs/safety.md
docs/decisions.md
```

The phase document should remain aligned with the actual implementation.

If a phase changes, update the phase document before proceeding.

## 49.13 Git requirements

Every phase ends with one focused commit unless the user explicitly requests otherwise.

Before staging:

```bash
git status
git diff
git diff --check
```

Never:

```bash
git add .
git add -A
```

Stage only explicit files or directories that belong to the current phase.

Example:

```bash
git add agent/hypothesis/ agent/investigator/ tests/
```

Then commit with a specific message.

Preferred format:

```text
feat: ...
test: ...
docs: ...
refactor: ...
chore: ...
```

Example:

```bash
git commit -m "feat: implement active investigation loop"
```

After committing:

```bash
git status
git log --oneline -n 3
```

The working tree should be clean unless unrelated user changes were already present.

## 49.14 Protect unrelated user changes

If the repository contains uncommitted changes that were present before the current phase:

- do not overwrite them,
- do not stage them,
- do not include them in the phase commit,
- do not reset them without explicit user instruction.

Use exact path staging.

## 49.15 Dependency discipline

Do not add a dependency merely because it is popular.

Before adding a dependency:

1. Check whether the current stack can solve the problem.
2. Check whether an existing dependency already provides the functionality.
3. Prefer the smallest stable solution.
4. Update dependency lock files as required.
5. Add a short rationale to `docs/decisions.md` for significant dependencies.

## 49.16 Configuration and secrets

Never hard-code:

- API keys
- tokens
- passwords
- database credentials
- provider secrets

Use:

```text
.env.example
environment variables
secret-safe configuration
```

Do not commit `.env` files containing secrets.

## 49.17 Observability standards

Every important agent/system action should be observable through structured logs.

Include as appropriate:

```text
timestamp
request_id
incident_id
agent_run_id
tool_name
phase
state
duration_ms
status
error_type
```

Do not log secrets or sensitive payloads unnecessarily.

## 49.18 Performance discipline

Do not optimize prematurely.

First establish correctness.

Then benchmark:

- investigation latency
- tool-call count
- tokens
- service latency
- throughput
- remediation time

Use measurements before claiming improvements.

## 49.19 What the CLI must NOT do

The CLI must not:

- use `git add .`
- create fake benchmark numbers
- fabricate telemetry
- skip tests to make a phase pass
- silently mark a phase complete
- rewrite unrelated files
- expose secrets
- add decorative emojis to code/comments/logs
- let the agent modify its evaluator
- allow unrestricted operational commands
- turn the project into a generic observability dashboard
- replace evidence-based investigation with prompt-only explanations

## 49.20 Required phase completion report

After each phase, before moving on, report to the user:

```text
Phase completed: <phase number + name>

Implemented:
- ...

Tests:
- command
- result

Verification:
- ...

Files changed:
- ...

Commit:
<commit hash> <commit message>

Next phase:
<phase number + name>
```

If anything failed, state exactly what failed and do not claim completion.

## 49.21 First execution instruction

When this repository is first opened, the CLI must **not immediately start coding**.

First:

1. inspect repository state,
2. read this README,
3. read `PHASE_WISE_AUTONOMOUS_AI_SYSTEM_INVESTIGATOR.md`,
4. map repository state to the phase plan,
5. report the current phase and any pre-existing changes,
6. then begin only the current phase.

