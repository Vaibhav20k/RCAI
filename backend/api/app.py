# Frontend Investigation Console REST API Server
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from simulator.services.runner import InProcessCluster
from simulator.scenarios.runner import ScenarioRunner
from benchmark.scenarios.registry import ALL_SCENARIOS, ScenarioDefinition
from backend.incidents.models import Incident, IncidentSeverity, IncidentStatus, AgentIncidentView
from backend.incidents.detector import IncidentDetector
from tools.registry import create_default_investigation_tools
from agent.investigator.loop import ActiveInvestigator
from agent.investigator.state import InvestigationState
from agent.verification.engine import RootCauseVerifier
from agent.verification.models import RootCauseDecision, IncidentReport
from agent.policies.models import RemediationProposal, RemediationActionType
from agent.policies.engine import PolicyEngine, VALID_TOPOLOGY_SERVICES
from tools.remediation.executor import BoundedRemediationExecutor
from agent.verification.outcome import RemediationOutcomeVerifier
from benchmark.evaluators.evaluator import BenchmarkRunner
from benchmark.evaluators.ablation import AblationExperimentRunner

app = FastAPI(title="RCAI Investigation Console API", version="1.0.0")

import os
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared In-Memory Runtime State
cluster = InProcessCluster()
scenario_runner = ScenarioRunner(cluster)
tools_reg = create_default_investigation_tools(cluster)
investigator = ActiveInvestigator(tool_registry=tools_reg)
verifier = RootCauseVerifier()
policy_engine = PolicyEngine()
remediation_executor = BoundedRemediationExecutor(cluster, policy_engine)
outcome_verifier = RemediationOutcomeVerifier(cluster)

incidents_db: Dict[str, Incident] = {}
investigations_db: Dict[str, InvestigationState] = {}
reports_db: Dict[str, IncidentReport] = {}
outcomes_db: Dict[str, Any] = {}

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
    return {
        "status": "UP",
        "service": "rcai-investigation-backend",
        "version": "2.0.0",
        "timestamp": time.time()
    }

@app.get("/api/scenarios")
def list_scenarios():
    return [
        {
            "scenario_id": sc.scenario_id,
            "name": sc.name,
            "service": sc.service,
            "symptom": sc.symptom_description,
            "severity": sc.severity.value,
            "category": sc.ground_truth.root_cause_type,
            "description": sc.ground_truth.description
        }
        for sc in ALL_SCENARIOS
    ]

@app.post("/api/scenarios/inject/{scenario_id}")
def inject_scenario(scenario_id: str):
    sc = next((s for s in ALL_SCENARIOS if s.scenario_id == scenario_id), None)
    if not sc:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")

    # Clear prior cluster faults and inject new scenario
    cluster.clear_all_faults()
    scenario_runner.execute_scenario(sc)

    inc = Incident(
        scenario_id=sc.scenario_id,
        service=sc.service,
        symptom=sc.symptom_description,
        severity=sc.severity,
        ground_truth=sc.ground_truth,
        status=IncidentStatus.DETECTED
    )
    incidents_db[inc.incident_id] = inc
    return {
        "status": "INJECTED",
        "scenario_id": sc.scenario_id,
        "incident": inc.model_dump()
    }

@app.get("/api/incidents")
def list_incidents():
    return [
        {
            "incident_id": inc.incident_id,
            "scenario_id": inc.scenario_id,
            "service": inc.service,
            "symptom": inc.symptom,
            "severity": inc.severity.value,
            "status": inc.status.value,
            "started_at": inc.started_at,
            "detected_at": inc.detected_at,
            "has_investigation": (inc.incident_id in [inv.incident.incident_id for inv in investigations_db.values()]),
            "has_remediation": (inc.incident_id in outcomes_db)
        }
        for inc in incidents_db.values()
    ]

@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    inc = incidents_db.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Find matching investigation state if exists
    matching_state = next((s for s in investigations_db.values() if s.incident.incident_id == incident_id), None)
    matching_report = reports_db.get(incident_id)
    matching_outcome = outcomes_db.get(incident_id)

    return {
        "incident": inc.model_dump(),
        "investigation": (
            {
                "investigation_id": matching_state.investigation_id,
                "is_completed": matching_state.is_completed,
                "stop_reason": matching_state.stop_reason,
                "current_step": matching_state.current_step,
                "hypotheses": [h.model_dump() for h in matching_state.hypothesis_set.hypotheses],
                "action_history": [a.model_dump() for a in matching_state.action_history],
                "evidence_store": {k: v.model_dump() for k, v in matching_state.evidence_store.items()},
                "budget": {
                    "tool_calls_used": matching_state.current_step,
                    "tool_calls_max": matching_state.budget_max_tool_calls,
                    "time_seconds_used": round(time.time() - matching_state.start_time, 2),
                    "time_seconds_max": matching_state.budget_max_seconds
                }
            }
            if matching_state else None
        ),
        "report": matching_report.model_dump() if matching_report else None,
        "outcome": matching_outcome
    }

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
        "hypotheses": [h.model_dump() for h in state.hypothesis_set.hypotheses],
        "action_history": [a.model_dump() for a in state.action_history],
        "evidence_store": {k: v.model_dump() for k, v in state.evidence_store.items()},
        "budget": {
            "tool_calls_used": state.current_step,
            "tool_calls_max": state.budget_max_tool_calls,
            "time_seconds_used": round(time.time() - state.start_time, 2),
            "time_seconds_max": state.budget_max_seconds
        },
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

    # Early rejection for UNKNOWN / unverified targets
    if not req.target_service or req.target_service == "UNKNOWN" or req.target_service not in VALID_TOPOLOGY_SERVICES:
        inc.status = IncidentStatus.ESCALATED
        return {
            "status": "BLOCKED",
            "policy_code": "DENIED_UNKNOWN_SERVICE",
            "rejection_reason": f"Target service '{req.target_service}' not recognized in active microservice topology",
            "error": f"Remediation blocked: Target service '{req.target_service}' is UNKNOWN or not in active topology",
            "is_recovered": False
        }

    proposal = RemediationProposal(
        incident_id=req.incident_id,
        action_type=RemediationActionType(req.action_type),
        target_service=req.target_service,
        parameters=req.parameters,
        rationale=req.rationale or f"Automated bounded remediation for {req.target_service}"
    )

    inc.status = IncidentStatus.REMEDIATION_PENDING
    pre_metrics = outcome_verifier.capture_metrics_snapshot(req.target_service)
    exec_res = remediation_executor.execute_remediation(proposal)

    if exec_res.status.value != "SUCCESS":
        inc.status = IncidentStatus.ESCALATED
        return {
            "status": "BLOCKED",
            "policy_code": "EXECUTION_REJECTED",
            "rejection_reason": exec_res.error_message,
            "error": exec_res.error_message,
            "is_recovered": False
        }

    inc.status = IncidentStatus.REMEDIATION_EXECUTED
    outcome = outcome_verifier.verify_remediation_outcome(
        proposal=proposal,
        pre_metrics=pre_metrics,
        incident=inc,
        test_traffic_count=10
    )

    outcomes_db[inc.incident_id] = outcome.model_dump()

    return {
        "status": "SUCCESS",
        "incident_status": inc.status.value,
        "outcome": outcome.model_dump()
    }

@app.get("/api/benchmark/summary")
def get_benchmark_summary():
    runner = BenchmarkRunner(cluster)
    bench_results = runner.evaluate_all_systems(ALL_SCENARIOS)
    ablation_runner = AblationExperimentRunner(cluster)
    ablation_results = ablation_runner.run_all_ablations(ALL_SCENARIOS, budget_tool_calls=8)

    return {
        "benchmarks": {k: v.model_dump() for k, v in bench_results.items()},
        "ablations": {k: v.model_dump() for k, v in ablation_results.ablation_scores.items()}
    }
@app.get("/api/topology")
def get_topology():
    services = [
        {"id": "api-gateway", "name": "API Gateway", "type": "gateway", "depends_on": ["order-service", "payment-service"]},
        {"id": "order-service", "name": "Order Service", "type": "service", "depends_on": ["payment-service", "worker-service", "database"]},
        {"id": "payment-service", "name": "Payment Service", "type": "service", "depends_on": ["dependency-service", "database"]},
        {"id": "dependency-service", "name": "Partner Bank API", "type": "dependency", "depends_on": []},
        {"id": "worker-service", "name": "Worker Queue", "type": "worker", "depends_on": ["queue"]},
        {"id": "database", "name": "Postgres DB", "type": "infrastructure", "depends_on": []},
        {"id": "queue", "name": "Redis Stream", "type": "infrastructure", "depends_on": []}
    ]
    nodes = []
    service_map = cluster.get_service_map()
    for s in services:
        sid = s["id"]
        svc_obj = service_map.get(sid)
        has_fault = False
        if svc_obj and len(svc_obj.fault_injector.get_active_faults()) > 0:
            has_fault = True
        nodes.append({
            **s,
            "has_fault": has_fault,
            "status": "FAULT" if has_fault else "HEALTHY"
        })
    return {"nodes": nodes}
import json
from fastapi.responses import StreamingResponse

@app.get("/api/investigate/stream/{incident_id}")
async def stream_investigation(incident_id: str):
    inc = incidents_db.get(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    inc.status = IncidentStatus.INVESTIGATING
    agent_view = inc.to_agent_view()
    state = investigator.start_investigation(agent_view)

    def event_generator():
        start_payload = json.dumps({"event": "START", "investigation_id": state.investigation_id, "hypotheses": [h.model_dump() for h in state.hypothesis_set.hypotheses]})
        yield f"data: {start_payload}\n\n"

        while not state.is_completed:
            investigator.step(state)
            last_action = state.action_history[-1].model_dump() if state.action_history else None
            step_payload = json.dumps({"event": "STEP", "current_step": state.current_step, "last_action": last_action, "hypotheses": [h.model_dump() for h in state.hypothesis_set.hypotheses], "budget": {"tool_calls_used": state.current_step, "tool_calls_max": state.budget_max_tool_calls}})
            yield f"data: {step_payload}\n\n"
            time.sleep(0.05)

        investigations_db[state.investigation_id] = state
        report = verifier.generate_incident_report(state)
        reports_db[inc.incident_id] = report
        inc.status = IncidentStatus.ROOT_CAUSE_PROPOSED

        complete_payload = json.dumps({"event": "COMPLETE", "stop_reason": state.stop_reason, "report": report.model_dump(), "evidence_store": {k: v.model_dump() for k, v in state.evidence_store.items()}})
        yield f"data: {complete_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
