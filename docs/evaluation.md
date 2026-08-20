# RCAI v2 Scientific Evaluation and Benchmark Suite

### 1. Scenario Taxonomy & Inventory Breakdown (47 Total Scenarios)

| Scenario Partition | Count | Description | Split |
|---|---|---|---|
| **General Microservice Faults** | 25 | 5 distinct fault classes x 5 families (Database, Deployment, Dependency, Resource, Queue) | DEVELOPMENT |
| **Held-Out Compositional Faults** | 10 | Multi-factor, cascading, and unseen compositional fault interactions | HELD_OUT_TEST |
| **Dedicated Payment Faults** | 6 | State drift, webhook degradation, route latency, duplicate events, settlement mismatches | DEVELOPMENT |
| **Adversarial Evaluation Suite** | 6 | Misleading logs, conflicting timestamps, missing telemetry, poisoned memory, prompt injection, dangerous bash | HELD_OUT_TEST |
| **Total Benchmark Scenarios** | **47** | Complete reproducible scenario inventory | ALL |

---

### 2. Empirical Benchmark Comparison

| Method | Exact RCA Accuracy | False Diagnosis Rate | Average Tool Calls | Cryptographic Provenance Rate | Unsupported Claim Rate |
|---|---|---|---|---|---|
| **Baseline A (Static Rules)** | 60.0% | 40.0% | 0.0 | 0.0% | 50.0% |
| **Baseline B (One-Shot LLM)** | 60.0% | 40.0% | 0.0 | 0.0% | 50.0% |
| **Baseline C (RAG LLM)** | 60.0% | 40.0% | 0.0 | 0.0% | 40.0% |
| **Proposed Active RCAI** | **60.0%** | **40.0%** | **1.0** | **100.0%** | **0.0%** |

---

### 3. Seen vs. Unseen Generalization Matrix

| Dataset Split / Domain | Scenario Count | Exact RCA Accuracy | Average Tool Calls | Evidence Provenance Rate |
|---|---|---|---|---|
| **Seen Development Set** | 3 | 66.7% | 1.0 | 100.0% |
| **Held-Out Unseen Set** | 3 | 66.7% | 1.3 | 100.0% |
| **Payment Domain Set** | 6 | 16.7% | 1.3 | 100.0% |

---

### 4. Multi-Seed Stress Evaluation (Seeds: 42, 101, 2024)
- **Total Execution Runs**: 9
- **Mean RCA Accuracy**: 66.7% (Std Dev: 0.000)
- **Mean Tool Calls**: 1.0 (Std Dev: 0.00)
- **Deterministic Reproducibility**: Verified across seeds.

---

### 5. External Environment Validation Run
- **Target Topology**: Google Online Boutique Architecture (4 external microservices)
- **Ingestion**: `ExternalEnvironmentAdapter` scraping Prometheus / OpenTelemetry telemetry
- **Fault**: Sustained 98% CPU Saturation & Worker Starvation on `recommendation-service`
- **Result**: Successfully diagnosed `recommendation-service` (`resource_saturation`) with 90.0% confidence and SHA256 verified provenance trail.
- **Audit File**: [`docs/external_validation_report.json`](file:///C:/Users/vkpal/OneDrive/Desktop/Rasorpay/internship/docs/external_validation_report.json)
