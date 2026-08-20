# Autonomous AI System Investigator (RCAI)
# Architecture Decision Records (ADRs)

## ADR-001: Explicit Hypothesis State Machine vs. Autonomous LLM Prompt Loop
- **Context:** Incident investigation can be implemented either as an autonomous free-form LLM conversation loop or as a structured state machine with explicit hypothesis objects.
- **Decision:** Implement an explicit state machine (inspired by ROSER and gitrade) maintaining typed hypothesis records, confidence values, and supporting/contradicting evidence lists.
- **Rationale:** Free-form LLM loops suffer from confirmation bias, hidden reasoning, and unmeasurable state transitions. Explicit state allows auditing, deterministic stopping criteria, and rigorous ablation.

## ADR-002: Constrained Predefined Tools vs. Unrestricted Code Execution
- **Context:** Some AI agents use dynamic Python or Bash code generation to explore environments.
- **Decision:** Restrict the agent to strongly-typed, validated Pydantic tool interfaces (`query_logs`, `query_metrics`, etc.).
- **Rationale:** Security and repeatability. Unrestricted code execution creates severe operational risk, prompt injection vulnerabilities, and non-reproducible benchmark runs.

## ADR-003: External Authoritative Evaluator vs. Agent Self-Scoring
- **Context:** Measuring RCA accuracy requires ground truth evaluation.
- **Decision:** The evaluation harness and ground truth remain strictly external to the agent context. Agent confidence is treated as an internal diagnostic signal, not evaluation truth.
- **Rationale:** Prevents circular self-approval and reward gaming.

## ADR-004: Independent Outcome Verification for Remediation
- **Context:** Automated or recommended remediation can either be assumed successful upon execution or verified through telemetry.
- **Decision:** Require mandatory pre- and post-remediation telemetry comparison before an incident state can transition to `RESOLVED`.
- **Rationale:** Fixes may fail, be incomplete, or cause side effects. Independent measurement is necessary for engineering trust.
