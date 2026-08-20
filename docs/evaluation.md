# Autonomous AI System Investigator (RCAI)
# Evaluation Discipline and Metric Definitions

## 1. Evaluation Philosophy

1. **Immutable Ground Truth:** Injected incident causes are stored in an external test manifest invisible to the agent during evaluation.
2. **External Evaluator Authority:** The agent self-confidence score is purely advisory. The external test harness makes the authoritative decision.
3. **Strict Equal Budgets:** All systems in competitive evaluations are evaluated under identical budget constraints:
   - Maximum investigation wall-clock time: 90 seconds
   - Maximum tool calls: 20 calls
   - Token budget: Fixed maximum tokens
   - Maximum active hypotheses: 5 hypotheses
   - Maximum remediation attempts: 2 attempts
4. **No Fabricated Data:** Experimental tables must contain measured data or explicit placeholders (X / TBD) until experiments are executed.

## 2. Benchmark Metrics

### 2.1 Root Cause Accuracy Metrics
- **Exact RCA Accuracy (%):** Proportion of incidents where the agent identified the exact ground-truth root cause component and fault mechanism.
- **Top-K RCA Accuracy (%):** Proportion of incidents where the ground-truth root cause appears in the agent top-K ranked hypotheses.
- **False Diagnosis Rate (%):** Proportion of completed investigations where an incorrect root cause was confirmed with high confidence (>0.7).
- **Hypothesis Rejection Quality (%):** Precision and recall of rejecting demonstrably false competing hypotheses.

### 2.2 Investigation Efficiency Metrics
- **Time to Diagnosis (TTD):** Median wall-clock seconds from incident detection to root-cause proposal.
- **Tool Call Count:** Total diagnostic tool executions per incident.
- **Diagnostic Efficiency Ratio:** Ratio of evidence items contributing directly to the final decision versus total evidence queried.

### 2.3 Evidence Integrity Metrics
- **Evidence Provenance Rate (%):** Percentage of claims in the final incident report mapped directly to verified evidence IDs.
- **Unsupported Claim Rate (%):** Frequency of assertions made without backing evidence records.
- **Contradiction Handling Score:** Ability of the agent to demote or reject hypotheses when faced with negative telemetry signals.

### 2.4 Remediation & Safety Metrics
- **Remediation Success Rate (%):** Percentage of executed remediations that resulted in measured system recovery.
- **Recovery Time (TTR):** Elapsed seconds from remediation execution to confirmed metric normalization.
- **Unsafe Action Rate (%):** Proportion of attempted actions that violated policy bounds or executed without required approval.

## 3. Benchmark Dataset Classes

1. **Database Regressions:** Query slowdown, connection pool exhaustion, missing index degradation.
2. **Bad Deployments:** Inefficient code version, configuration parameter corruption, broken dependency update.
3. **Downstream Dependency Failures:** High latency downstream, HTTP 503 error storms, network timeouts.
4. **Resource Saturation:** CPU throttling, memory leaks leading to OOM, worker thread starvation.
5. **Queue & Async Backlog:** Producer burst overload, consumer worker stalls.
