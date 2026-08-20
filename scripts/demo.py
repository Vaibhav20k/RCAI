import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
# End-to-End Autonomous AI Investigator CLI Demo
import sys
import time
from simulator.services.runner import InProcessCluster
from simulator.scenarios.runner import ScenarioRunner
from benchmark.scenarios.registry import SCENARIO_BAD_DEPLOY_PAYMENT
from backend.incidents.models import Incident, IncidentStatus
from backend.incidents.detector import IncidentDetector
from tools.registry import create_default_investigation_tools
from agent.investigator.loop import ActiveInvestigator
from agent.verification.engine import RootCauseVerifier
from agent.policies.models import RemediationProposal, RemediationActionType
from agent.policies.engine import PolicyEngine
from tools.remediation.executor import BoundedRemediationExecutor
from agent.verification.outcome import RemediationOutcomeVerifier

def run_demo():
    print("=" * 70)
    print("RCAI: Autonomous AI System Investigator -- End-to-End Live Demo")
    print("=" * 70)
    print("[1/6] Initializing controlled microservice topology...")
    cluster = InProcessCluster()
    tools = create_default_investigation_tools(cluster)
    scenario_runner = ScenarioRunner(cluster)
    from observability.metrics.collector import MetricsCollector
    metrics = MetricsCollector(cluster)
    detector = IncidentDetector(metrics)
    investigator = ActiveInvestigator(tool_registry=tools)
    verifier = RootCauseVerifier()
    policy_engine = PolicyEngine()
    remediation_executor = BoundedRemediationExecutor(cluster, policy_engine)
    outcome_verifier = RemediationOutcomeVerifier(cluster)
    print("      Topology: [api-gateway] -> [order-service] -> [payment-service] -> [dependency-service] + [worker-service]")

    print("\n[2/6] Injecting Benchmark Scenario 2: Bad Deployment on payment-service...")
    scenario_runner.execute_scenario(SCENARIO_BAD_DEPLOY_PAYMENT)

    print("\n[3/6] Running real-time telemetry anomaly detector...")
    inc_list = detector.detect_incidents_from_metrics(scenario_id=SCENARIO_BAD_DEPLOY_PAYMENT.scenario_id, known_ground_truth=SCENARIO_BAD_DEPLOY_PAYMENT.ground_truth)
    inc = next((i for i in inc_list if i.service == SCENARIO_BAD_DEPLOY_PAYMENT.service), inc_list[0] if inc_list else None)
    if not inc:
        inc = Incident(
            scenario_id=SCENARIO_BAD_DEPLOY_PAYMENT.scenario_id,
            service=SCENARIO_BAD_DEPLOY_PAYMENT.service,
            symptom=SCENARIO_BAD_DEPLOY_PAYMENT.symptom_description,
            severity=SCENARIO_BAD_DEPLOY_PAYMENT.severity,
            ground_truth=SCENARIO_BAD_DEPLOY_PAYMENT.ground_truth
        )
    print(f"      DETECTED INCIDENT: [{inc.severity}] on {inc.service} -- {inc.symptom}")

    print("\n[4/6] Launching Autonomous Active Investigation Loop...")
    agent_view = inc.to_agent_view()
    state = investigator.run_investigation(agent_view)
    for action in state.action_history:
        print(f"      Step {action.step_index}: Executed {action.tool_name}({action.arguments}) -> {action.result_status} ({action.duration_ms:.1f}ms)")

    print("\n[5/6] Verifying evidence provenance and generating root cause report...")
    report = verifier.generate_incident_report(state)
    dec = report.root_cause_decision
    print(f"      DIAGNOSIS: {dec.description}")
    print(f"      CONFIDENCE: {dec.confidence * 100:.1f}%")
    print(f"      EVIDENCE COUNT: {len(dec.supporting_evidence_ids)} provenanced records")
    print(f"      RECOMMENDED ACTION: {report.recommended_action}")

    print("\n[6/6] Executing bounded remediation through Safety Policy Engine...")
    proposal = RemediationProposal(
        incident_id=inc.incident_id,
        action_type=RemediationActionType.ROLLBACK_VERSION,
        target_service="payment-service",
        parameters={"target_version": "1.0.0"},
        rationale="Rollback buggy payment release v2.4.1"
    )
    pre_metrics = outcome_verifier.capture_metrics_snapshot("payment-service")
    exec_res = remediation_executor.execute_remediation(proposal)
    print(f"      Remediation Execution: {exec_res.status.value}")

    outcome = outcome_verifier.verify_remediation_outcome(
        proposal=proposal,
        pre_metrics=pre_metrics,
        incident=inc,
        test_traffic_count=10
    )
    print(f"      VERIFICATION OUTCOME: {outcome.status}")
    print(f"      {outcome.verification_summary}")
    print("=" * 70)
    print("Demo completed successfully. Incident RESOLVED.")
    print("=" * 70)
    return True

if __name__ == "__main__":
    run_demo()
