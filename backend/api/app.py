# Frontend Investigation Console REST API Server
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from simulator.services.runner import InProcessCluster
from simulator.scenarios.runner import ScenarioRunner
from benchmark.scenarios.registry import ALL_SCENARIOS
from backend.incidents.models import Incident, IncidentSeverity, IncidentStatus, AgentIncidentView
from backend.incidents.detector import IncidentDetector
from tools.registry import create_default_investigation_tools
from agent.investigator.loop import ActiveInvestigator
from agent.investigator.state import InvestigationState
from agent.verification.engine import RootCauseVerifier
from agent.verification.models import RootCauseDecision, IncidentReport
from agent.policies.models import RemediationProposal, RemediationActionType
from agent.policies.engine import PolicyEngine
from tools.remediation.executor import BoundedRemediationExecutor
from agent.verification.outcome import RemediationOutcomeVerifier
from benchmark.evaluators.evaluator import BenchmarkRunner
from benchmark.evaluators.ablation import AblationExperimentRunner

app = FastAPI(title="RCAI Investigation Console API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared In-Memory Runtime State
cluster = InProcessCluster()
scenario_runner = ScenarioRunner(cluster)
incident_detector = IncidentDetector(cluster)
tools_reg = create_default_investigation_tools(cluster)
investigator = ActiveInvestigator(tool_registry=tools_reg)
verifier = RootCauseVerifier()
policy_engine = PolicyEngine()
remediation_executor = BoundedRemediationExecutor(cluster, policy_engine)
outcome_verifier = RemediationOutcomeVerifier(cluster)

incidents_db: Dict[str, Incident] = {}
investigations_db: Dict[str, InvestigationState] = {}
reports_db: Dict[str, IncidentReport] = {}

# Seed initial incident from Scenario 1
sc1 = ALL_SCENARIOS[0]
scenario_runner.execute_scenario(sc1)
seed_inc = Incident(
    scenario_id=sc1.scenario_id,
    service=sc1.service,
    symptom=sc1.symptom_description,
    severity=sc1.severity,
    ground_truth=sc1.ground_truth
)
incidents_db[seed_inc.incident_id] = seed_inc

@app.get("/health")
def health():
    return {"status": "UP", "timestamp": time.time()}

@app.get("/api/incidents")
def list_incidents():
    return [inc.model_dump() for inc in incidents_db.values()]

@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    inc = incidents_db.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc.model_dump()

@app.post("/api/investigate/{incident_id}")
def trigger_investigation(incident_id: str):
    inc = incidents_db.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    inc.status = IncidentStatus.INVESTIGATING
    agent_view = inc.to_agent_view()
    
    state = investigator.run_investigation(agent_view)
    investigations_db[state.investigation_id] = state
    
    report = verifier.generate_incident_report(state)
    reports_db[inc.incident_id] = report
    
    inc.status = IncidentStatus.ROOT_CAUSE_PROPOSED
    
    return {
        "investigation_id": state.investigation_id,
        "incident_id": inc.incident_id,
        "is_completed": state.is_completed,
        "stop_reason": state.stop_reason,
        "steps_taken": state.current_step,
        "action_history": [a.model_dump() for a in state.action_history],
        "top_hypothesis": state.final_root_cause_hypothesis.model_dump() if state.final_root_cause_hypothesis else None,
        "report": report.model_dump()
    }

class RemediationRequest(BaseModel):
    incident_id: str
    action_type: str
    target_service: str
    parameters: Dict[str, Any] = {}
    rationale: str = ""

@app.post("/api/remediate")
def execute_remediation(req: RemediationRequest):
    inc = incidents_db.get(req.incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    proposal = RemediationProposal(
        incident_id=req.incident_id,
        action_type=RemediationActionType(req.action_type),
        target_service=req.target_service,
        parameters=req.parameters,
        rationale=req.rationale
    )

    pre_metrics = outcome_verifier.capture_metrics_snapshot(req.target_service)
    exec_res = remediation_executor.execute_remediation(proposal)
    
    if exec_res.status.value != "SUCCESS":
        return {
            "status": "FAILED",
            "error": exec_res.error_message,
            "is_recovered": False
        }

    outcome = outcome_verifier.verify_remediation_outcome(
        proposal=proposal,
        pre_metrics=pre_metrics,
        incident=inc,
        test_traffic_count=10
    )

    return {
        "status": "SUCCESS",
        "outcome": outcome.model_dump()
    }

@app.get("/api/benchmark/summary")
def get_benchmark_summary():
    runner = BenchmarkRunner(cluster)
    bench_results = runner.evaluate_all_systems(ALL_SCENARIOS[:2])
    ablation_runner = AblationExperimentRunner(cluster)
    ablation_results = ablation_runner.run_all_ablations(ALL_SCENARIOS[:2], budget_tool_calls=6)
    
    return {
        "benchmarks": {k: v.model_dump() for k, v in bench_results.items()},
        "ablations": {k: v.model_dump() for k, v in ablation_results.ablation_scores.items()}
    }
