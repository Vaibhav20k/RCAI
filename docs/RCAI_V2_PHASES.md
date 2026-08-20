# RCAI v2 — Update Implementation Plan
## Stress Testing, Payment-Domain Validation, Live Console Integration, and Submission Hardening

> **Purpose:** Extend the completed RCAI v1 system without rebuilding it.
>
> **Core rule:** RCAI v1 remains the baseline. v2 changes must be additive, measured, documented, and reversible.
>
> **Git rule:** Every phase below ends with tests, verification, documentation, and one focused Git commit. Never use `git add .` or `git add -A`.

---

# 0. v2 Execution Principles

Before coding:

1. Read `docs/README.md`.
2. Read `docs/PHASES.md`.
3. Read the RCAI v2 specification.
4. Inspect current repository state.
5. Check Git branch and working tree.
6. Determine exactly what v1 already implements.
7. Do not rewrite working components unless a measured v2 requirement demands it.

Run:

```bash
git status
git branch --show-current
git log --oneline --decorate -n 20
```

The v2 implementation must preserve:

- evidence grounding
- hypothesis state
- policy enforcement
- bounded actions
- outcome verification
- evaluator isolation
- existing benchmark reproducibility
- prior phase commit history

---

# Phase 1 — Benchmark Inventory and Scenario Taxonomy

## Objective

Replace the five-scenario benchmark assumption with a formal scenario taxonomy before generating new scenarios.

## Tasks

Create a machine-readable registry of:

```text
scenario_id
family
variant
difficulty
ground_truth_root_cause
required_evidence
allowed_actions
expected_outcome
seen_or_held_out
adversarial
payment_domain
```

Define families:

- DATABASE
- DEPLOYMENT
- DEPENDENCY
- RESOURCE
- QUEUE
- PAYMENT
- ADVERSARIAL

## Tests

- unique scenario IDs
- no duplicate ground truth
- schema validation
- valid family classification

## Exit Criteria

Every current scenario is registered and classified.

## Git Commit

```bash
git status
git diff
git diff --check
git add benchmark/ docs/ tests/
git commit -m "feat: formalize RCAI v2 scenario taxonomy"
```

---

# Phase 2 — Expand General Microservice Scenarios

## Objective

Increase the controlled benchmark to at least 20 meaningful scenarios, preferably 25–30+.

## Implement variants across:

### Database
- slow query
- query-plan regression
- index regression
- connection exhaustion
- lock contention
- timeout

### Deployment
- total failure
- partial failure
- latency regression
- configuration regression
- dependency-version regression

### Dependency
- latency
- timeout
- intermittent error
- partial degradation
- retry storm

### Resource
- CPU saturation
- memory pressure
- worker exhaustion
- thread starvation

### Queue
- backlog
- producer burst
- stuck consumer
- poison message
- delayed processing

Use genuine differences in evidence patterns.

Do not copy the same fault with altered labels.

## Tests

For every scenario:

```text
inject
→ detect
→ collect telemetry
→ ground truth hidden
→ verify expected symptom
```

## Exit Criteria

At least 20 meaningful scenarios are reproducible.

## Git Commit

```bash
git status
git diff
git diff --check
git add simulator/ benchmark/scenarios/ tests/ docs/
git commit -m "feat: expand RCAI fault scenario coverage"
```

---

# Phase 3 — Unseen and Compositional Faults

## Objective

Create a held-out set that tests generalization rather than memorization.

## Design

Development/validation scenarios:

```text
known families and variants
```

Held-out:

```text
new variants
+
multi-factor combinations
+
different timing
+
different affected services
```

Examples:

```text
deployment + DB regression
dependency timeout + queue backlog
partial payment degradation + webhook delay
```

## Rule

The agent must not receive hidden ground truth.

## Tests

Verify:

- held-out files are inaccessible to agent
- benchmark evaluator has independent access
- no scenario leakage

## Exit Criteria

At least 10 strong held-out scenarios exist for a preferred target.

## Git Commit

```bash
git status
git diff
git diff --check
git add datasets/ benchmark/ evaluator/ tests/ docs/
git commit -m "test: add held-out unseen RCA scenarios"
```

---

# Phase 4 — Payment-Domain Environment

## Objective

Introduce a genuinely payment-oriented incident environment.

## Topology

Implement a manageable topology such as:

```text
Payment API
   ↓
Gateway Router
   ├── Payment State Store
   ├── Bank / PSP Dependency
   └── Webhook Service
          ↓
       Event Queue
          ↓
        Ledger
          ↓
      Settlement
```

## Requirements

Every service needs:

- health endpoint
- structured logs
- request IDs
- trace context
- metrics
- version metadata where relevant

## Exit Criteria

The payment topology runs deterministically and produces realistic telemetry.

## Git Commit

```bash
git status
git diff
git diff --check
git add simulator/services/ observability/ docker-compose.yml docs/
git commit -m "feat: add payment incident investigation environment"
```

---

# Phase 5 — Payment Incident Families

## Objective

Create real payment-system failure scenarios.

Implement at minimum:

### 1. Payment State Inconsistency

```text
gateway success
internal state pending
```

### 2. Webhook Degradation

```text
payment success
webhook queue backlog
merchant confirmation delayed
```

### 3. Gateway / Bank Latency

```text
payment latency
→ downstream dependency degradation
```

### 4. Duplicate Event Processing

```text
same payment event delivered twice
```

### 5. Settlement / Ledger Mismatch

```text
settlement total ≠ expected ledger total
```

### 6. Route-Specific Degradation

```text
one payment method/route degraded
others healthy
```

## Ground Truth

Each case must define:

- root cause
- supporting evidence
- expected state transitions
- valid remediation
- expected resolution

## Exit Criteria

At least six meaningful payment incident scenarios exist.

## Git Commit

```bash
git status
git diff
git diff --check
git add simulator/ benchmark/scenarios/ tests/ docs/
git commit -m "feat: add payment-domain incident scenarios"
```

---

# Phase 6 — Payment Investigation Tools

## Objective

Expose domain-specific read-only evidence tools.

Implement as needed:

```text
get_payment_state()
get_gateway_response()
get_webhook_delivery()
get_event_queue_state()
get_ledger_entry()
get_settlement_batch()
get_payment_route_health()
get_reconciliation_state()
```

Every tool must define:

```text
input
output
permission
timeout
failure modes
provenance
```

Do not give unrestricted database or shell access.

## Tests

- valid queries
- missing state
- stale state
- tool failure
- malformed inputs

## Exit Criteria

RCAI can investigate payment incidents through structured evidence tools.

## Git Commit

```bash
git status
git diff
git diff --check
git add agent/ tools/ simulator/ tests/ docs/
git commit -m "feat: add payment investigation evidence tools"
```

---

# Phase 7 — Live Console Integration Audit

## Objective

Verify that the RCAI console is genuinely connected to the engine.

## Trace Every UI Action

For every button/control:

```text
UI
→ API
→ service
→ state change
→ response/event
→ UI update
```

Identify any:

- hardcoded state
- fake timers
- random confidence changes
- hardcoded tool trajectory
- mock evidence
- dead actions

## Fix

Replace with:

- real API
- SSE/WebSocket
- polling
- real database/state

as appropriate.

## Required actions

Verify:

- Run Investigation
- Inject Scenario
- Select Incident
- Inspect Hypothesis
- Inspect Evidence
- Apply Remediation
- Verify Outcome

## Exit Criteria

Every displayed interactive action is backed by real system functionality.

## Git Commit

```bash
git status
git diff
git diff --check
git add frontend/ backend/api/ tests/ docs/
git commit -m "feat: wire RCAI console to live investigation state"
```

---

# Phase 8 — UI/UX Instrument Redesign

## Objective

Implement the finalized black + amber instrument-console design.

## Tokens

```text
background      #000000
panel           #0C0C0B
panel-raised    #151412
line            #232019
text            #EDEAE2
text-dim        #9C978A
text-faint      #5C584E
accent          #D9A55A
accent-dim      #8A6B3B
critical        #E5484D
verified        #6FA88A
```

## Rules

```text
gray     = structure
amber    = active/current
sage     = verified
red      = severity/fault
```

No additional semantic colors.

Typography:

- Space Grotesk
- IBM Plex Mono

## Components

Implement/refine:

- KPI strip
- topology
- stepper
- hypothesis board
- trajectory
- budget monitor
- evidence explorer
- provenance
- root-cause verification
- policy/remediation
- outcome verification
- audit trail
- scenario injector
- benchmarks

## Exit Criteria

Design spec is implemented without breaking functionality.

## Git Commit

```bash
git status
git diff
git diff --check
git add frontend/ docs/ tests/
git commit -m "feat: redesign RCAI console as instrument dashboard"
```

---

# Phase 9 — Functional Interaction Pass

## Objective

Make every visible interaction easy and reliable.

## Requirements

Every button has:

```text
default
hover
focus
disabled
loading
success
error
```

Every asynchronous operation has:

- loading
- success
- failure
- retry where appropriate

Implement clear labels:

```text
Run Investigation
Inject Scenario
Inspect Evidence
Approve Remediation
Execute Rollback
```

Avoid vague labels such as `Run`, `Go`, `Apply`.

## Accessibility

Ensure:

- keyboard focus
- readable contrast
- color-independent state indication
- accessible button labels
- sensible click targets

## Exit Criteria

A first-time user can operate the console without guessing.

## Git Commit

```bash
git status
git diff
git diff --check
git add frontend/ tests/ docs/
git commit -m "feat: complete RCAI console interaction states"
```

---

# Phase 10 — Adversarial Evaluation Suite

## Objective

Attempt to break the investigator and prove failure handling.

## Cases

### A. Misleading evidence

DB signal looks bad, deployment is actual cause.

### B. Conflicting evidence

Metrics, logs, and traces disagree.

### C. Missing evidence

Remove a key telemetry source.

Expected:

```text
ROOT_CAUSE_UNKNOWN
```

when evidence is insufficient.

### D. Poisoned historical memory

Memory suggests an incorrect diagnosis.

Expected:

Current evidence dominates memory.

### E. Evaluator manipulation

Try to alter:

- ground truth
- score
- audit
- scenario files

Expected:

Access denied / impossible.

### F. Ambiguous remediation

Two actions have similar expected outcomes.

Expected:

Escalation or safe non-automatic resolution.

## Exit Criteria

All adversarial cases produce safe, explicit outcomes.

## Git Commit

```bash
git status
git diff
git diff --check
git add benchmark/adversarial/ tests/ agent/ evaluator/ docs/
git commit -m "test: add adversarial RCA evaluation suite"
```

---

# Phase 11 — Evaluator Integrity Audit

## Objective

Audit the benchmark for circularity and leakage.

## Verify

The evaluator must independently know:

```text
ground truth
expected outcome
scenario identity
```

The agent must not be able to influence:

```text
ground truth
scoring
test files
audit
```

## Add Tests

Create tests that attempt to:

- modify ground truth
- modify evaluator
- inject fake success
- write fake evidence
- alter scoring

## Exit Criteria

Evaluator remains independent under adversarial tests.

## Git Commit

```bash
git status
git diff
git diff --check
git add evaluator/ benchmark/ tests/ docs/
git commit -m "test: harden evaluator isolation and integrity"
```

---

# Phase 12 — Stress and Multi-Seed Evaluation

## Objective

Measure performance stability.

Run multiple seeds and traffic patterns.

Vary:

- fault timing
- traffic volume
- evidence availability
- tool budget
- initial conditions

Record:

```text
mean
std dev
best
worst
median
```

## Exit Criteria

Results are reproducible and variance is reported.

## Git Commit

```bash
git status
git diff
git diff --check
git add evaluation/ benchmark/ reports/ tests/ docs/
git commit -m "test: add multi-seed RCA stress evaluation"
```

---

# Phase 13 — Seen vs Unseen Generalization Study

## Objective

Quantify how RCAI behaves on unseen faults.

Produce:

```text
Known Variant Accuracy
Held-Out Variant Accuracy
Relative Performance Change
```

Break down by family:

```text
DATABASE
DEPLOYMENT
DEPENDENCY
RESOURCE
QUEUE
PAYMENT
```

## Important

Do not optimize the model against the held-out set after viewing results.

## Exit Criteria

A reproducible generalization report exists.

## Git Commit

```bash
git status
git diff
git diff --check
git add evaluation/reports/ benchmark/ docs/
git commit -m "test: measure RCAI seen versus unseen generalization"
```

---

# Phase 14 — External Environment Validation

## Objective

Demonstrate RCAI beyond the self-authored simulator if technically feasible.

## Requirements

Select one recognizable open-source microservice environment.

Possible workflow:

```text
External application
→ telemetry integration
→ documented fault / safe fault injection
→ RCAI investigation
→ diagnosis comparison
```

Do not force unsafe or ungrounded remediation.

## Reporting

Keep external results separate from controlled benchmark results.

If exact ground truth is unavailable:

report:

- diagnosis evidence
- investigation trajectory
- operator confirmation
- limitations

Do not manufacture accuracy numbers.

## Exit Criteria

At least one meaningful external-environment investigation is demonstrated, or the limitation is documented with a clear reason.

## Git Commit

```bash
git status
git diff
git diff --check
git add integrations/ external_validation/ evaluation/ docs/
git commit -m "feat: add external environment RCA validation"
```

---

# Phase 15 — Final v2 Benchmark

## Objective

Freeze and run the complete evaluation.

Freeze:

```text
development data
validation data
held-out test set
ground truth
evaluator
scoring
budgets
scenario registry
```

Run:

```text
Static Rules
One-Shot LLM
RAG LLM
RCAI
```

Then:

- ablations
- adversarial tests
- payment-domain tests
- seen/unseen tests
- multi-seed tests

## Required Metrics

```text
scenario count
exact RCA accuracy
top-k accuracy
false diagnosis
unknown rate
unsupported claim rate
provenance rate
average tool calls
diagnosis latency
remediation verification
policy violations
duplicate actions
unsafe action rate
```

## Exit Criteria

Final report is reproducible from the final commit.

## Git Commit

```bash
git status
git diff
git diff --check
git add evaluation/ reports/ benchmark/ docs/
git commit -m "test: finalize RCAI v2 benchmark"
```

---

# Phase 16 — Final Submission Hardening

## Objective

Prepare the final project as a defensible research/engineering submission.

## Documentation

Update:

```text
README.md
docs/architecture.md
docs/evaluation.md
docs/safety.md
docs/decisions.md
docs/adversarial-evaluation.md
docs/payment-domain.md
docs/external-validation.md
docs/benchmark-v2.md
```

Include:

- benchmark denominators
- known vs unseen performance
- adversarial failures
- external validation
- limitations
- exact environment
- reproducibility instructions

## Demo

Demonstrate:

1. payment incident
2. competing hypotheses
3. active evidence selection
4. root-cause verification
5. bounded remediation
6. independent recovery verification
7. adversarial failure path
8. benchmark comparison

## Exit Criteria

A reviewer can understand both:

```text
what RCAI does
```

and:

```text
how seriously it was evaluated
```

## Git Commit

```bash
git status
git diff
git diff --check
git add README.md docs/ frontend/ evaluation/reports/ .github/
git commit -m "docs: finalize RCAI v2 submission hardening"
```

---

# 4. v2 Expected Commit Trajectory

```text
feat: formalize RCAI v2 scenario taxonomy
feat: expand RCAI fault scenario coverage
test: add held-out unseen RCA scenarios
feat: add payment-domain investigation environment
feat: add payment-domain incident scenarios
feat: add payment investigation evidence tools
feat: wire RCAI console to live investigation state
feat: redesign RCAI console as instrument dashboard
feat: complete RCAI console interaction states
test: add adversarial RCA evaluation suite
test: harden evaluator isolation and integrity
test: add multi-seed RCA stress evaluation
test: measure RCAI seen versus unseen generalization
feat: add external environment RCA validation
test: finalize RCAI v2 benchmark
docs: finalize RCAI v2 submission hardening
```

Do not squash these commits.

Do not rewrite the v1 phase history.

---

# 5. Final v2 Definition of Done

RCAI v2 is complete only when:

- [ ] 20+ meaningful scenarios exist.
- [ ] 25–30+ is the preferred target.
- [ ] At least 10 held-out scenarios exist for a strong final evaluation.
- [ ] Scenario families contain genuinely different variants.
- [ ] Compositional unseen faults exist.
- [ ] Payment-domain incident family exists.
- [ ] Payment incidents are substantively modeled.
- [ ] Live console is API-driven.
- [ ] No fake investigation playback exists.
- [ ] Every interactive button works.
- [ ] The UI is easy to operate.
- [ ] Instrument-style design is implemented.
- [ ] Adversarial suite exists.
- [ ] Evaluator integrity tests pass.
- [ ] Multi-seed stress testing is complete.
- [ ] Seen vs unseen results are reported.
- [ ] External validation is completed if feasible.
- [ ] Safety metrics are reported.
- [ ] Final held-out evaluation is frozen and reproducible.
- [ ] All benchmark numbers are measured, not fabricated.
- [ ] Known limitations are explicitly documented.
- [ ] Every v2 phase has a focused Git commit.
- [ ] No v2 phase uses `git add .` or `git add -A`.

---

# 6. Final v2 Objective

> **Make RCAI difficult to dismiss not by adding more features, but by demonstrating that its investigation process remains evidence-grounded, safe, auditable, and useful when the faults become more numerous, more realistic, more novel, more adversarial, and more domain-specific.**
