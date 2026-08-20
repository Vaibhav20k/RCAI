# Autonomous AI System Investigator (RCAI)
## Evidence-Driven Root-Cause Investigation, Verification, and Bounded Remediation

> **Project Type:** Razorpay AI Builders Internship Project  
> **Core Research Question:**  
> Can an evidence-selecting, hypothesis-testing AI agent achieve more reliable root-cause analysis than one-shot LLM diagnosis under the same evidence/tool budget?

---

### 1. Executive Thesis

Traditional observability tools alert that *something is broken*. Generic LLM incident assistants summarize alerts with single-shot explanations, frequently suffering from confirmation bias, hallucinated root causes, and lack of remediation verification.

The **Autonomous AI System Investigator** operates as an active, evidence-grounded engineer:
1. **Observe & Parse Symptom:** Ingests anomalous signals and bounds the incident window.
2. **Generate Competing Hypotheses:** Maintains multiple explicit hypotheses rather than premature single-point anchoring.
3. **Active Evidence Selection:** Dynamically selects the most informative diagnostic tools based on expected information gain and action cost.
4. **Hypothesis Updating & Rejection:** Grounded in retrieved evidence with strict provenance; rejects hypotheses contradicted by telemetry.
5. **Root-Cause Verification:** Distinguishes verified root causes from unknown or unconfirmed scenarios (`ROOT_CAUSE_UNKNOWN`).
6. **Bounded Remediation:** Executes safe, policy-checked, reversible remediations with human approval gating for high-impact actions.
7. **Outcome Verification:** Measures post-action telemetry independently to verify system recovery.

---

### 2. Architecture Overview

```text
Controlled Microservices (Gateway, Order, Payment, Dependency)
           |
           v
  Telemetry & Normalization (Prometheus, Logs, Traces, Deployments)
           |
           v
  Incident Detection & Scenario Engine
           |
           v
  Active Investigator Loop (LangGraph State Machine)
    ├── Hypothesis Engine (Confidence, Supporting/Contradicting Evidence)
    ├── Dynamic Routing & Evidence Selection (Utility / Cost Heuristic)
    ├── Constrained Tool Boundary (Read-only query tools)
    └── Stopping Policy
           |
           v
  Root Cause Decision & Evidence Provenance Audit
           |
           v
  Bounded Remediation & Policy Engine
           |
           v
  Independent Outcome Verification
           |
           v
  Historical Incident Memory & Strategy Adaptation
```

---

### 3. Repository & Documentation Structure

```text
├── agent/            # Core investigator, hypothesis engine, routing, verification, policy, memory
├── tools/            # Constrained diagnostic and remediation tools with strict schemas
├── simulator/        # Microservice environment, fault injector, traffic generator
├── observability/    # Prometheus config, logging formatters, OpenTelemetry tracing
├── benchmark/        # Reproducible evaluation harness, ground truth scenarios, baselines
├── backend/          # FastAPI incident management API and immutable audit log store
├── frontend/         # React/Next.js investigation console
├── docs/             # Authoritative technical and research documentation
│   ├── README.md     # Primary project specification
│   ├── PHASES.md     # Phase-by-phase execution plan
│   ├── architecture.md
│   ├── research.md
│   ├── evaluation.md
│   ├── safety.md
│   └── decisions.md
└── tests/            # Pytest test suite (unit, contract, integration, safety)
```

---

### 4. Running the Project

1. **Install Dependencies:**
   ```bash
   pip install -e .
   ```
2. **Environment Setup:**
   ```bash
   cp .env.example .env
   ```
3. **Execute Test Suite:**
   ```bash
   pytest
   ```
