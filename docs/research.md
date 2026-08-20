# Autonomous AI System Investigator (RCAI)
# Research Foundation and Hypotheses

## 1. Core Research Question

> **Can an AI agent improve root-cause diagnosis reliability, reduce false diagnoses, and safely remediate incidents by actively selecting and testing evidence-backed hypotheses instead of performing one-shot incident summarization?**

## 2. Research Hypotheses

### Primary Hypothesis (H0)
An active evidence-selecting, hypothesis-testing AI investigator achieves statistically significant higher Root Cause Analysis (RCA) accuracy than one-shot LLM and static retrieval baselines under equal investigation budgets.

### Secondary Hypotheses
- **H1 (False Diagnosis Reduction):** Explicit tracking of contradicting evidence and hypothesis rejection reduces the rate of false diagnoses.
- **H2 (Evidence Provenance):** Requiring evidence grounding and audit IDs eliminates unsupported claims and hallucinations.
- **H3 (Investigation Efficiency):** Dynamic utility routing (information gain per unit cost) minimizes unnecessary tool calls compared to exhaustive retrieval.
- **H4 (Memory Adaptation):** Storing structured investigation paths accelerates diagnosis time for recurring incident classes.
- **H5 (Outcome Verification):** Independent post-remediation verification prevents false resolution declarations and catches incomplete fixes.

## 3. Comparison Baselines

1. **Baseline A — Static Rule Engine:**
   - Evaluates telemetry against fixed threshold rules and static runbooks.
2. **Baseline B — One-Shot LLM:**
   - Ingests raw incident alert context into a single LLM prompt to predict root cause directly.
3. **Baseline C — LLM + Retrieved Context (RAG):**
   - Retrieves historical incident logs and relevant telemetry chunks via similarity search before prompting the LLM.
4. **Proposed — Active Autonomous Investigator (RCAI):**
   - Iterative hypothesis generation, dynamic evidence tool selection, evidence-grounded verification, and verified bounded remediation.

## 4. Ablation Matrix

To isolate the causal contribution of each subsystem:
1. **Full RCAI System**
2. **RCAI without Active Evidence Selection** (Fixed exhaustive retrieval)
3. **RCAI without Historical Investigation Memory**
4. **RCAI without Hypothesis Verification Gate**
5. **RCAI without Dynamic Routing** (Fixed sequence tool calls)
