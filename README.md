# RCAI: Autonomous AI System Investigator

An autonomous, multimodal, evidence-grounded AI investigator for complex microservice environments.

RCAI investigates production incidents through iterative hypothesis generation, dynamic utility-based tool calling, cryptographic telemetry provenance verification (SHA256), safety-gated bounded remediation, and empirical outcome verification.

---

## System Architecture

```text
               +-------------------------------------------+
               |         Real-Time Incident Detector       |
               +---------------------+---------------------+
                                     |
                                     v
                       [Agent Incident View]
                                     |
                                     v
               +-------------------------------------------+
               |     Structured Hypothesis Generator       |
               +---------------------+---------------------+
                                     |
                                     v
           +---------------------------------------------------+
           |           Active Investigation Loop               |
           |  (Expected Information Gain / Cost Action Router) |
           +-------------------------+-------------------------+
                                     |
                                     v
                     +-------------------------------+
                     |   Read-Only Diagnostic Tools  |
                     |  - query_logs                 |
                     |  - query_metrics              |
                     |  - query_traces               |
                     |  - inspect_deployments        |
                     |  - compare_versions           |
                     |  - query_db_metrics           |
                     |  - inspect_service_health     |
                     |  - inspect_dependency_health  |
                     +---------------+---------------+
                                     |
                                     v
               +-------------------------------------------+
               |   Evidence Provenance Verification Engine |
               |     (SHA256 Cryptographic Signatures)     |
               +---------------------+---------------------+
                                     |
                                     v
               +-------------------------------------------+
               |     Safety Policy & Bounded Remediation   |
               |     (Permissions, Idempotency, Tokens)    |
               +---------------------+---------------------+
                                     |
                                     v
               +-------------------------------------------+
               |    Remediation Outcome Verifier (Post-Tx) |
               +-------------------------------------------+
```

---

## Benchmark Results across 5 Scenarios

| Method | Exact RCA Accuracy (%) | False Diagnosis (%) | Avg. Tool Calls | Provenance Rate (%) | Unsupported Claims (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline A (Static Rules)** | 100.0% | 0.0% | 0.0 | 0.0% | 100.0% |
| **Baseline B (One-Shot LLM)** | 60.0% | 40.0% | 0.0 | 0.0% | 100.0% |
| **Baseline C (RAG LLM)** | 40.0% | 60.0% | 0.0 | 0.0% | 50.0% |
| **Proposed Active RCAI** | **100.0%** | **0.0%** | **2.8** | **100.0%** | **0.0%** |

---

## Quickstart Guide

### 1. Run the Full Test Suite
```bash
python -m pytest
```

### 2. Run the Interactive End-to-End CLI Demo
```bash
python scripts/demo.py
```

### 3. Run Scientific Benchmark and Ablation Experiments
```bash
python scripts/run_benchmarks.py
```

### 4. Launch the Operator Investigation Console API & UI
```bash
uvicorn backend.api.app:app --host 0.0.0.0 --port 8000
```
Open `frontend/index.html` in your browser.

---

## Repository Structure

```text
.
├── agent/                  # Autonomous Investigator core
│   ├── hypothesis/         # Hypothesis state models & candidate generator
│   ├── investigator/       # Active investigation loop & concurrency
│   ├── memory/             # Historical incident experience store
│   ├── policies/           # Safety policy & authorization engine
│   ├── routing/            # Dynamic utility evidence selector
│   └── verification/       # Evidence provenance & outcome verifier
├── backend/                # Incidents and Console REST API
│   ├── api/                # FastAPI console backend
│   └── incidents/          # Anomaly detector & incident models
├── benchmark/              # Benchmark harness & baselines
│   ├── baselines/          # Rules, One-Shot, RAG baselines
│   ├── evaluators/         # Benchmark & ablation evaluation engines
│   ├── reports/            # LaTeX artifact & report generator
│   └── scenarios/          # 5 reproducible microservice fault scenarios
├── docs/                   # Authoritative specifications & research artifacts
│   ├── results/            # Benchmark JSON, LaTeX tables, ablation reports
│   ├── architecture.md     # Architecture documentation
│   ├── evaluation.md       # Benchmark evaluation methodology
│   ├── research.md         # Formal research thesis
│   └── safety.md           # Safety invariants and policy rules
├── frontend/               # Operator Investigation Web Dashboard
├── observability/          # Telemetry collectors, normalizer, and cache
├── scripts/                # CLI demo and benchmark runners
├── simulator/              # Controlled microservice environment & fault injector
├── tests/                  # Unit, contract, integration, and stress test suites
└── tools/                  # Read-only diagnostic tools and remediation executor
```
