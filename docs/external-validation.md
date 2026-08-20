# External Microservice Environment Validation Report
## RCAI v2 OpenTelemetry / Prometheus Ingestion & Verification

### 1. Objective and Setup
This validation demonstrates RCAI diagnosing an incident on an external microservice architecture (Google Online Boutique topology) without using internal simulator hooks or private engine state.

### 2. External Topology
- **frontend-proxy**: Edge reverse proxy router (`http://external-boutique:8080`)
- **recommendation-service**: Python/gRPC service computing personalized recommendations (`http://external-boutique:8081`)
- **cart-service**: In-memory Redis cart storage service (`http://external-boutique:8082`)
- **payment-service**: External processor integration (`http://external-boutique:8083`)

### 3. Injected Fault & Telemetry Scrape
- **Fault Injected**: Resource saturation (CPU utilization sustained at 98%, p95 latency spiked to 220ms)
- **Collector**: `ExternalPrometheusScraper` via `ExternalEnvironmentAdapter`
- **Normalized Telemetry Signatures**:
  - Metric `cpu_utilization=0.98` on `recommendation-service` (SHA256 Provenance Signature)
  - Metric `memory_usage_mb=480.0` on `recommendation-service`
  - Metric `p95_latency_ms=220.0` on `recommendation-service`

### 4. Investigation Trajectory & Diagnosis
- **Candidate Hypotheses Evaluated**: 5 (`DATABASE`, `DEPLOYMENT`, `DEPENDENCY`, `RESOURCE`, `QUEUE`)
- **Diagnostic Tool Executed**: `query_external_telemetry(service="recommendation-service")`
- **Verified Root Cause**: `recommendation-service` (`resource_saturation`)
- **Diagnosis Confidence**: 90.0%
- **Cryptographic Provenance Verified**: 100% (SHA256 verified)
- **Recommended Bounded Remediation**: `scale_workers` on `recommendation-service`

### 5. Reproducibility
To reproduce the external validation run independently:
```bash
python scripts/run_external_validation.py
```
Audit output is persisted in `docs/external_validation_report.json`.
