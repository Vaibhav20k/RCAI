# RCAI — Local Startup & Setup Guide

Welcome to **RCAI** (Root Cause AI) — Autonomous AI Investigator & Microservice Incident Diagnosis System!

This guide provides simple, step-by-step instructions to start the **FastAPI Backend Server** and the **Interactive Frontend Console** on your local machine.

---

## System Requirements
- **Python**: 3.10+ (Python 3.11, 3.12, 3.13, or 3.14)
- **Virtual Environment**: Pre-configured in `.venv`

---

## Quick Start (2-Step Launch)

### Step 1: Start the Backend API (Port 8000)

Open a terminal and run:

```bash
# 1. Navigate to the project directory
cd /home/vaibhav/Desktop/Projects/RCAI

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Start the FastAPI Uvicorn server
uvicorn backend.api.app:app --host 127.0.0.1 --port 8000 --reload
```

> **Backend is now live at:**
> - **API Base URL**: `http://localhost:8000`
> - **Interactive Swagger Docs**: `http://localhost:8000/docs`
> - **Health Check**: `http://localhost:8000/health`

---

### Step 2: Start the Frontend Console (Port 3000)

Open a **second terminal** window and run:

```bash
# 1. Navigate to the project directory
cd /home/vaibhav/Desktop/Projects/RCAI

# 2. Serve the static frontend on port 3000
python3 -m http.server 3000 --directory frontend
```

> **Frontend Console is now live at:**
> - **Web Console**: `http://localhost:3000`

---

## How to Use the Console

1. **Select a Fault Scenario**:
   - Choose any scenario from the top dropdown (e.g. *Database Query Latency Regression*, *Bad Software Deployment*, etc.).
   - Click **`INJECT SCENARIO`** to simulate the fault on the microservice cluster.
2. **Run Autonomous Investigation**:
   - Click **`RUN AUTONOMOUS INVESTIGATION`**.
   - The multi-step Bayesian agent will execute read-only diagnostic tools, collect cryptographic evidence hashes, and converge on the verified root cause.
3. **Review & Execute Remediation**:
   - Review the policy-gated bounded remediation action.
   - Click **`REVIEW & EXECUTE REMEDIATION`** to apply the fix and verify post-action traffic normalization.
4. **Reset / Refresh Investigation**:
   - Click the **`[Refresh Investigation]`** button in the header or **`[RESET]`** in the action bar to reset transient UI results and test another scenario cleanly.

---

## Running Automated Tests

RCAI includes a comprehensive 97-test validation suite:

```bash
cd /home/vaibhav/Desktop/Projects/RCAI
source .venv/bin/activate
pytest tests/
```
*(Expected: 97 passed)*

---

## Troubleshooting

* **Port 8000 or 3000 already in use**:
  - You can run backend on a different port: `uvicorn backend.api.app:app --port 8005`
  - Run frontend on a different port: `python3 -m http.server 3005 --directory frontend`
  - In `frontend/app.js`, update `DEFAULT_REMOTE_API` or pass `window.RCAI_API_URL` if needed.
* **Offline Guarantee**: RCAI does NOT require any external OpenAI/Groq API keys — all fault simulation and Bayesian causal analysis run 100% locally.
