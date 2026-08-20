# RCAI v2 — Root Cause Analysis Intelligence
## Stress-Tested, Payment-Domain-Aware, Evidence-Driven Autonomous Investigation System

> **Version:** RCAI v2  
> **Purpose:** Strengthen the completed RCAI system from a controlled proof-of-concept into a substantially more defensible research and engineering submission.
>
> **Primary goal:** Preserve the existing RCAI investigation engine while expanding benchmark coverage, introducing genuine payment-domain incident families, making the console unquestionably live and API-driven, adding external-environment validation where feasible, and performing adversarial evaluation of the investigator and evaluator.
>
> **Core principle:**  
> **The v2 effort is not a feature-accumulation exercise. It is a validation and generalization effort.**

---

# 1. Why RCAI v2 Exists

RCAI v1 already contains:

- a controlled microservice environment,
- structured telemetry,
- active hypothesis management,
- dynamic evidence selection,
- root-cause verification,
- bounded remediation,
- independent outcome verification,
- historical memory,
- benchmark baselines,
- ablation experiments,
- safety policies,
- cryptographic evidence provenance,
- an operator console.

The remaining weaknesses are not primarily missing AI features.

The important unanswered questions are:

1. Does RCAI still work beyond five handcrafted scenarios?
2. Can it handle unseen fault variants rather than recognizing known templates?
3. Is the payment-domain framing substantive rather than cosmetic?
4. Is the polished console genuinely connected to the live system?
5. Can RCAI be broken by misleading, conflicting, incomplete, or poisoned evidence?
6. Can an evaluator independently verify RCAI without circular assumptions?
7. Can the architecture be demonstrated on a recognizable external microservice environment in addition to the controlled simulator?

RCAI v2 answers these questions.

---

# 2. v2 Product Positioning

RCAI should not be presented as:

> "An AI that predicts root cause."

It should be presented as:

> **An evidence-driven investigation system that actively selects diagnostic evidence, maintains competing hypotheses, verifies conclusions, executes bounded actions, and independently validates recovery.**

For v2, this is demonstrated across:

```text
General Microservice Incidents
+
Payment Infrastructure Incidents
+
Unseen Fault Variants
+
Adversarial Incidents
+
External Environment Validation
```

The system remains general-purpose, but the payment-domain track becomes a **real demonstration vertical**, not a renamed generic SRE environment.

---

# 3. What v2 Must Preserve

Do not regress or weaken existing v1 capabilities.

The following remain authoritative:

```text
Active hypothesis engine
Active evidence selection
Evidence provenance
Root-cause verification
Bounded remediation
Policy engine
Idempotency
Outcome verification
Historical memory
Benchmark baselines
Ablation framework
Operator console
Fault injection
Audit trail
No arbitrary shell execution
```

The v2 work must be additive or corrective.

Do not rewrite working architecture unnecessarily.

---

# 4. v2 Design Principles

## 4.1 Validation over feature count

A new feature is justified only if it:

- improves generalization,
- improves domain realism,
- improves evaluation quality,
- improves safety,
- or makes the existing capabilities demonstrable.

Do not add speculative AI features merely to make the project sound more advanced.

## 4.2 Honest benchmarking

Never hide the denominator.

Always report:

```text
scenarios evaluated
scenario families
held-out scenarios
exact RCA accuracy
false diagnosis
unsupported claims
provenance rate
average tool calls
```

## 4.3 Unseen faults matter more than repeated faults

The benchmark must include variations not seen during development.

A benchmark of 30 near-identical copies is not meaningfully stronger than a benchmark of 5.

## 4.4 Controlled + external validation

The controlled simulator remains essential because it gives:

- ground truth,
- deterministic fault injection,
- reproducibility,
- safe remediation testing.

An external environment adds realism and reduces the risk of entirely self-authored validation.

These two evaluation environments serve different purposes.

## 4.5 Payment-domain realism without losing generality

The system should remain a general investigator.

Payment incidents are one vertical in which RCAI is demonstrated with domain-specific failure semantics.

Do not turn RCAI into the separate Track 03 revenue-recovery project.

---

# 5. v2 Benchmark Strategy

The benchmark should move from:

```text
5 scenarios
```

to:

```text
25–30+ controlled scenarios
+
unseen held-out variants
+
adversarial cases
```

The exact final number must be reported from the actual benchmark.

## Recommended target

At minimum:

```text
20 development/validation scenarios
10 held-out test scenarios
```

A stronger target:

```text
30+ total scenarios
10+ held-out scenarios
```

Use scenario families rather than simple duplication.

---

# 6. Scenario Family Design

## 6.1 Database Family

Potential variants:

1. Slow query.
2. Query-plan regression.
3. Missing/ineffective index.
4. Connection-pool exhaustion.
5. Lock contention.
6. DB connection timeout.
7. Partial DB degradation.
8. DB latency + deployment interaction.

## 6.2 Deployment Family

Potential variants:

1. 100% failure after deployment.
2. Partial failure.
3. Latency regression.
4. Configuration regression.
5. Dependency-version regression.
6. Feature-flag regression.
7. Deployment + DB interaction.
8. Canary-specific failure.

## 6.3 Dependency Family

Potential variants:

1. Latency spike.
2. Timeout.
3. Intermittent error.
4. Partial degradation.
5. Retry storm.
6. Downstream saturation.
7. Dependency recovery after cooldown.

## 6.4 Resource Family

Potential variants:

1. CPU saturation.
2. Memory pressure.
3. Worker exhaustion.
4. Thread starvation.
5. File/resource exhaustion.
6. CPU + latency interaction.

## 6.5 Queue Family

Potential variants:

1. Consumer slowdown.
2. Producer burst.
3. Stuck consumer.
4. Poison message.
5. Delayed processing.
6. Worker failure.
7. Queue + dependency interaction.

---

# 7. Unseen / Compositional Faults

The held-out set should include combinations and variants that are not directly represented in development.

Example:

Development may contain:

```text
DB latency
Deployment regression
```

Held-out case:

```text
Deployment regression
+
DB latency
+
partial traffic degradation
```

Another:

```text
Dependency timeout
+
queue backlog
```

The purpose is to test:

> Does RCAI investigate evidence and reason causally, or does it memorize fault templates?

---

# 8. Payment-Domain Incident Vertical

RCAI v2 should include a genuine payment-infrastructure environment.

This is not a revenue-recovery system.

The objective is:

> **Root-cause analysis of realistic payment-system incidents.**

Suggested topology:

```text
                    Payment API
                         |
                         v
                 Gateway / Router
                    /         \
                   v           v
             Payment State   Bank / PSP
                 Store       Dependency
                   |
                   v
               Webhook
               Service
                   |
                   v
             Event Queue
                   |
                   v
                Ledger
                   |
                   v
             Settlement
```

The final topology should remain manageable.

---

# 9. Payment Incident Family

Implement real payment-system failure modes.

## 9.1 Payment State Inconsistency

Example:

```text
Gateway:
SUCCESS

Internal payment state:
PENDING
```

RCAI should investigate:

```text
gateway response
→ webhook delivery
→ event queue
→ payment state store
→ event ordering
→ reconciliation
```

Possible root causes:

- webhook delay,
- dropped event,
- consumer backlog,
- state-write failure,
- event-ordering issue.

---

## 9.2 Webhook Delivery Degradation

Example:

```text
Payment succeeds
↓
Webhook queue grows
↓
Merchant confirmation delayed
```

Investigation evidence:

- queue depth,
- worker health,
- webhook latency,
- downstream errors,
- delivery attempts.

---

## 9.3 Gateway / Bank Dependency Latency

Example:

```text
Payment API p95 latency ↑
Bank dependency latency ↑
```

RCAI must distinguish:

```text
application regression
vs
bank dependency degradation
```

This is a natural test of competing hypotheses.

---

## 9.4 Duplicate Callback / Event Processing

Example:

```text
same payment event
received twice
```

Investigate:

- event IDs,
- idempotency state,
- consumer retry behaviour,
- duplicate delivery.

---

## 9.5 Settlement / Ledger Mismatch

Example:

```text
Gateway settlement total
≠
Internal ledger expectation
```

Investigate:

```text
payment events
→ ledger entries
→ settlement batch
→ reconciliation state
```

This is a particularly valuable fintech-domain scenario because the investigator must reason across multiple system states.

---

## 9.6 Payment Route Partial Degradation

Example:

```text
UPI route healthy
card route degraded
```

RCAI should use route-specific evidence rather than treating the entire payment system as unhealthy.

---

# 10. Payment-Domain Ground Truth

Each payment incident must have hidden ground truth defining:

```text
root_cause
fault_type
expected evidence
valid remediation
invalid remediation
expected recovery
state transitions
```

The ground truth must be held outside the agent-accessible environment.

---

# 11. External Environment Validation

The controlled simulator remains the primary benchmark environment.

In addition, evaluate RCAI against at least one recognizable open-source microservice environment where practical.

Potential process:

```text
External Application
        ↓
Observe existing telemetry
        ↓
Inject or reproduce a documented fault
        ↓
RCAI investigation
        ↓
Compare diagnosis against known fault
```

The external environment does not need to support every RCAI remediation.

The first objective is:

> **Generalize investigation and diagnosis beyond the project's own simulator.**

If a safe, reliable external environment cannot be integrated without creating more complexity than value, document the limitation rather than forcing a fragile integration.

---

# 12. Live Console Requirement

The final console must be genuinely connected to the live system.

Required flow:

```text
Frontend
   ↓
Real API
   ↓
Real investigator state
   ↓
Real telemetry
   ↓
Real scenario
```

The console must not depend on:

- hardcoded JSON,
- fake timers,
- random confidence changes,
- fake tool calls,
- fake timestamps,
- decorative investigation playback.

If real-time transport is already available:

- use SSE/WebSocket.

Otherwise:

- use polling against actual state.

---

# 13. Console Interaction Requirements

Every visible control must be functional.

Required functional actions include:

- scenario injection,
- investigation start,
- incident selection,
- hypothesis inspection,
- evidence inspection,
- evidence filtering,
- remediation approval,
- remediation execution,
- benchmark inspection,
- retry on failure,
- navigation,
- state refresh.

No dead buttons.

No fake buttons.

No control should appear interactive unless it has a real action.

---

# 14. Adversarial Evaluation

RCAI v2 must attempt to break itself.

Create a dedicated adversarial evaluation suite.

## 14.1 Misleading Evidence

Example:

```text
DB latency increases
but actual root cause = deployment
```

Expected:

- agent does not anchor on DB,
- further evidence is gathered.

## 14.2 Conflicting Evidence

Example:

```text
Metrics → DB problem
Logs → dependency problem
Traces → deployment regression
```

Expected:

- competing hypotheses remain active,
- additional evidence is selected,
- arbitrary early commitment is avoided.

## 14.3 Missing Evidence

Remove traces or another key source.

Expected:

```text
ROOT_CAUSE_UNKNOWN
```

or safe escalation when confidence cannot be established.

No hallucinated evidence.

## 14.4 Poisoned Historical Memory

Provide historical cases supporting an incorrect diagnosis.

Expected:

- current evidence dominates stale memory,
- memory is guidance, not truth.

## 14.5 Evaluator Manipulation

Attempt to modify or influence:

```text
ground truth
scoring
benchmark scripts
audit records
```

Expected:

- access denied,
- evaluator remains authoritative.

## 14.6 Ambiguous Remediation

Two candidate remediations have similar expected value.

Expected:

```text
ESCALATE
```

or another safe non-automatic resolution.

---

# 15. Evaluator Integrity

The evaluator must be reviewed for circularity.

Check:

```text
ground truth
agent output
scoring
audit
```

are independent.

The evaluator must not:

- read agent-written ground truth,
- accept agent-generated labels as truth,
- use the agent's own confidence as correctness,
- allow the agent to alter scoring.

The evaluator should determine correctness from hidden scenario truth and observable outcome.

---

# 16. Benchmark Report v2

The final report should include:

```text
Total scenarios
Development scenarios
Validation scenarios
Held-out scenarios
Payment-domain scenarios
Adversarial scenarios
External-environment scenarios
```

Then:

```text
Exact RCA accuracy
Top-k RCA accuracy
False diagnosis
Unknown / insufficient evidence rate
Unsupported claim rate
Evidence provenance rate
Average tool calls
Median diagnosis time
Remediation verification rate
Unsafe-action rate
```

Always report denominators.

---

# 17. Required Benchmark Views

## Overall

```text
RCAI v2
N scenarios
X% exact RCA
X% false diagnosis
X% unsupported claims
X% provenance
```

## By Scenario Family

```text
DATABASE
DEPLOYMENT
DEPENDENCY
RESOURCE
QUEUE
PAYMENT
ADVERSARIAL
```

## Seen vs Unseen

```text
Seen variants
Held-out unseen variants
```

This is one of the most important v2 comparisons.

---

# 18. Generalization Experiment

Compare:

```text
Known fault variants
vs
Unseen fault variants
```

The goal is not necessarily to achieve identical performance.

The useful question is:

> **How much does performance degrade when the fault is novel?**

A credible paper/result can say:

```text
Known:
X%

Unseen:
Y%

Relative degradation:
Z%
```

rather than pretending the system is perfect.

---

# 19. Stress Testing

Run multiple repetitions with:

- different random seeds,
- different traffic patterns,
- different fault timing,
- different evidence availability,
- varying tool budgets.

Measure:

```text
mean
standard deviation
worst case
best case
```

Do not rely on one lucky run.

---

# 20. Investigation Budget Evaluation

Continue evaluating under fixed budgets.

For example:

```text
4 tool calls
8 tool calls
12 tool calls
16 tool calls
```

Measure:

- exact RCA
- unsupported claims
- time
- tool calls
- unresolved incidents.

This provides a curve showing how investigation quality scales with available evidence budget.

---

# 21. Safety Evaluation

Measure:

```text
policy violation rate
duplicate-action rate
unauthorized-action rate
unsafe-remediation rate
```

Target:

```text
0 policy violations
0 arbitrary shell execution
0 duplicate financial/system actions in tested scenarios
```

If a failure is observed, document it instead of hiding it.

---

# 22. External Environment Reporting

Separate these results:

```text
Controlled Benchmark
```

from:

```text
External Environment Demonstration
```

Do not combine them into one inflated accuracy metric.

The external environment may not have complete ground truth, so report what can actually be verified.

---

# 23. Updated Frontend Visual Direction

RCAI v2 must use the finalized instrument-style design.

## Color

```text
--bg           #000000
--panel        #0C0C0B
--panel-raised #151412
--line         #232019
--text         #EDEAE2
--text-dim     #9C978A
--text-faint   #5C584E
--accent       #D9A55A
--accent-dim   #8A6B3B
--critical     #E5484D
--verified     #6FA88A
```

Semantic rules:

```text
GRAY  = structural
AMBER = live/active/current
SAGE  = verified/resolved/passed
RED   = severity/fault
```

No blue, violet, cyan, saturated green, or additional semantic colors.

---

# 24. Typography

Use:

### Space Grotesk

For:

- headers
- labels
- body
- buttons

### IBM Plex Mono

For:

- timestamps
- IDs
- confidence
- tool names
- latency
- budgets
- metrics
- hashes
- technical state

Measured values should visually read as telemetry.

---

# 25. Final Dashboard Information Hierarchy

The dashboard should prioritize:

```text
1. Current incident
2. Current investigation stage
3. Current hypothesis
4. What RCAI is doing next
5. Evidence collected
6. Root cause verification
7. Remediation policy
8. Outcome verification
```

Supporting pages:

```text
Evidence
Benchmarks
Incidents
Scenarios
Audit
```

Do not turn the dashboard into a collection of unrelated widgets.

---

# 26. Failure Handling UX

When something fails:

```text
WHAT FAILED
WHY
WHAT STATE ARE WE IN
WHAT CAN THE USER DO NEXT
```

Example:

```text
Remediation execution failed

Reason:
Upstream timeout

Current state:
RECONCILIATION_REQUIRED

RCAI did not retry automatically because the
payment/system state is uncertain.

[Reconcile State]
[Escalate]
```

No fake success.

---

# 27. Documentation Requirements

Update:

```text
README.md
docs/architecture.md
docs/evaluation.md
docs/safety.md
docs/decisions.md
```

Create/update:

```text
docs/adversarial-evaluation.md
docs/payment-domain.md
docs/external-validation.md
docs/benchmark-v2.md
```

Document:

- what changed,
- why,
- metrics,
- limitations,
- known failures,
- benchmark methodology.

---

# 28. Research Reporting Rules

The final v2 report must distinguish:

### Source-derived facts

What was actually measured in the implementation.

### Controlled benchmark results

Results from the simulator.

### External validation

Results from outside environments.

### Engineering inference

Claims about why a component likely helped.

### Limitations

What the evaluation does not establish.

Do not collapse these categories.

---

# 29. What v2 Is Not

Do not turn v2 into:

- a new product,
- a second revenue recovery agent,
- a generic chatbot,
- a larger observability platform,
- an autonomous unrestricted SRE,
- a fake production deployment,
- a benchmark with duplicated scenarios,
- an exercise in cosmetic UI improvement.

The v2 objective is:

> **Make existing RCAI claims harder to dismiss.**

---

# 30. Final v2 Success Criteria

RCAI v2 is complete only when:

- [ ] Benchmark has at least 20 total meaningful scenarios.
- [ ] Preferably 25–30+ scenarios exist.
- [ ] At least 10 held-out scenarios exist for a strong target.
- [ ] Scenario families contain genuine variants.
- [ ] Unseen/compositional faults exist.
- [ ] Payment-domain incident family exists.
- [ ] Payment incidents represent real system failure modes.
- [ ] Controlled benchmark remains reproducible.
- [ ] Adversarial suite exists.
- [ ] Evaluator integrity has been tested.
- [ ] External environment validation exists if feasible and safe.
- [ ] Console is genuinely API-driven.
- [ ] No fake investigation playback.
- [ ] All visible controls are functional.
- [ ] UI follows the instrument-style design specification.
- [ ] Known vs unseen performance is reported.
- [ ] Stress tests across multiple seeds/patterns are reported.
- [ ] Fixed-budget investigation results are reported.
- [ ] Safety metrics are reported.
- [ ] Limitations are documented honestly.
- [ ] Final benchmark is reproducible from the final commit.
- [ ] No benchmark numbers are fabricated.

---

# 31. Final v2 Product Statement

> **RCAI v2 is an evidence-driven autonomous investigation system that actively selects diagnostic evidence, maintains and tests competing hypotheses, verifies root causes, performs bounded remediation, and independently validates recovery across diverse microservice and payment-system failure scenarios, including unseen and adversarial cases.**

The central claim is no longer:

> "We built an AI that gets 100%."

It is:

> **"We built an investigator whose reasoning is measurable, whose evidence is auditable, whose actions are bounded, and whose performance is tested beyond the fault templates it was designed around."**
