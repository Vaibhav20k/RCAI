# Integration Tests for Reasoning Loop Generalization to Discovered Topology (Stage B)
import pytest
import time
from backend.incidents.models import AgentIncidentView, IncidentSeverity
from agent.hypothesis.generator import HypothesisGenerator
from agent.hypothesis.models import HypothesisCategory
from agent.playbooks.catalogue import PlaybookCatalogue, global_playbook_catalogue
from agent.playbooks.selector import PlaybookSelector
from agent.policies.engine import PolicyEngine
from agent.policies.models import RemediationProposal, RemediationActionType
from agent.investigator.loop import ActiveInvestigator
from agent.verification.engine import RootCauseVerifier
from discovery.models import TopologyNode, DiscoveredTopology
from discovery.registry import (
    set_active_topology,
    reset_active_topology,
    get_current_topology_services,
    is_service_db_related,
    is_service_queue_related
)
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType, EvidenceProvenance
from tools.registry import ToolRegistry
from tools.base import BaseTool, ToolResult, ToolExecutionStatus

@pytest.fixture(autouse=True)
def clean_topology():
    """Ensure topology registry is clean before and after each test."""
    reset_active_topology()
    yield
    reset_active_topology()

@pytest.fixture
def custom_discovered_topology():
    """Builds a custom 3-tier microservice topology with custom names."""
    nodes = {
        "storefront-api": TopologyNode(
            service_id="storefront-api",
            name="Storefront API Gateway",
            service_type="gateway",
            container_id="cont_storefront",
            container_name="storefront_api_prod",
            ports=[8080],
            metrics_port=8080,
            has_metrics=True,
            is_instrumented=True,
            is_db_related=False,
            depends_on=["billing-worker", "store-postgres"]
        ),
        "billing-worker": TopologyNode(
            service_id="billing-worker",
            name="Billing Async Worker",
            service_type="worker",
            container_id="cont_billing",
            container_name="billing_worker_prod",
            ports=[],
            metrics_port=9102,
            has_metrics=True,
            is_instrumented=True,
            is_db_related=False,
            depends_on=["billing-queue", "store-postgres"]
        ),
        "store-postgres": TopologyNode(
            service_id="store-postgres",
            name="Store PostgreSQL Cluster",
            service_type="database",
            container_id="cont_postgres",
            container_name="store_postgres_main",
            ports=[5432],
            metrics_port=9187,
            has_metrics=True,
            is_instrumented=True,
            is_db_related=True,
            depends_on=[]
        ),
        "external-proxy": TopologyNode(
            service_id="external-proxy",
            name="Edge Reverse Proxy",
            service_type="gateway",
            container_id="cont_proxy",
            container_name="edge_nginx_proxy",
            ports=[80, 443],
            metrics_port=None,
            has_metrics=False,
            is_instrumented=False,
            is_db_related=False,
            depends_on=["storefront-api"]
        )
    }
    topo = DiscoveredTopology(nodes=nodes, discovery_mode="docker", discovered_at=time.time())
    set_active_topology(topo)
    return topo

from backend.incidents.models import AgentIncidentView, IncidentSeverity, IncidentStatus

def make_test_incident(incident_id: str, service: str, severity: IncidentSeverity, symptom: str) -> AgentIncidentView:
    now = time.time()
    return AgentIncidentView(
        incident_id=incident_id,
        scenario_id="scenario_discovered_test",
        started_at=now - 60.0,
        detected_at=now,
        severity=severity,
        service=service,
        symptom=symptom,
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": now - 120.0, "end_ts": now}
    )

def test_hypothesis_seeding_respects_discovered_service_capabilities(custom_discovered_topology):
    """
    Verifies that hypothesis generation adapts strictly to discovered service capabilities:
    - Non-DB service (external-proxy) does NOT receive a database hypothesis
    - DB-related service (store-postgres) receives a database hypothesis
    - Worker service (billing-worker) receives a queue hypothesis
    """
    # 1. Non-DB service incident
    proxy_incident = make_test_incident(
        incident_id="inc_proxy_1",
        service="external-proxy",
        severity=IncidentSeverity.HIGH,
        symptom="Connection timeouts on edge proxy"
    )
    proxy_hypotheses = HypothesisGenerator.generate_candidate_hypotheses(proxy_incident)
    proxy_categories = [h.category for h in proxy_hypotheses.hypotheses]

    assert HypothesisCategory.DATABASE not in proxy_categories, "Non-DB proxy must not receive database hypothesis"
    assert HypothesisCategory.RESOURCE in proxy_categories, "Generic resource hypothesis must be present"
    assert HypothesisCategory.DEPLOYMENT in proxy_categories, "Generic deployment hypothesis must be present"
    assert HypothesisCategory.DEPENDENCY in proxy_categories, "Generic dependency hypothesis must be present"

    # 2. Database service incident
    db_incident = make_test_incident(
        incident_id="inc_db_1",
        service="store-postgres",
        severity=IncidentSeverity.CRITICAL,
        symptom="Query execution time spike above 500ms"
    )
    db_hypotheses = HypothesisGenerator.generate_candidate_hypotheses(db_incident)
    db_categories = [h.category for h in db_hypotheses.hypotheses]

    assert HypothesisCategory.DATABASE in db_categories, "DB service must receive database hypothesis"

    # 3. Worker service incident
    worker_incident = make_test_incident(
        incident_id="inc_worker_1",
        service="billing-worker",
        severity=IncidentSeverity.HIGH,
        symptom="Job processing lag growing unboundedly"
    )
    worker_hypotheses = HypothesisGenerator.generate_candidate_hypotheses(worker_incident)
    worker_categories = [h.category for h in worker_hypotheses.hypotheses]

    assert HypothesisCategory.QUEUE in worker_categories, "Worker service must receive queue backlog hypothesis"


def test_playbook_candidate_filtering_and_safety_gating(custom_discovered_topology):
    """
    Verifies that optimize_db_index is never offered or accepted for non-DB services,
    and that proposals for unrecognized or obsolete hardcoded services are rejected.
    """
    catalogue = PlaybookCatalogue()

    # 1. Verify candidate playbooks for non-DB service
    proxy_candidates = catalogue.get_candidate_playbooks_for_service("external-proxy")
    proxy_action_names = [p.name for p in proxy_candidates]
    assert "optimize_db_index" not in proxy_action_names
    assert "restart_service" in proxy_action_names
    assert "scale_replicas" in proxy_action_names

    # 2. Verify candidate playbooks for DB service
    db_candidates = catalogue.get_candidate_playbooks_for_service("store-postgres")
    db_action_names = [p.name for p in db_candidates]
    assert "optimize_db_index" in db_action_names

    # 3. Deterministic Safety Gate rejection for non-DB service
    is_valid, err = catalogue.validate_playbook_selection(
        action="optimize_db_index",
        target="external-proxy",
        params={"table": "users"}
    )
    assert is_valid is False
    assert "not applicable" in err.lower()

    # 4. Deterministic Safety Gate acceptance for DB service
    is_valid, err = catalogue.validate_playbook_selection(
        action="optimize_db_index",
        target="store-postgres",
        params={"table": "orders"}
    )
    assert is_valid is True
    assert err is None

    # 5. Unknown service rejection (e.g. old hardcoded name 'api-gateway')
    is_valid, err = catalogue.validate_playbook_selection(
        action="restart_service",
        target="api-gateway",
        params={"service": "api-gateway"}
    )
    assert is_valid is False
    assert "not recognized in active microservice topology" in err

def test_end_to_end_reasoning_loop_on_discovered_topology(custom_discovered_topology):
    """
    Executes a complete end-to-end diagnosis and remediation proposal loop
    against a discovered microservice topology (storefront-api), verifying:
    - ActiveInvestigator evaluates evidence against storefront-api
    - RootCauseVerifier outputs decision referencing storefront-api
    - PlaybookSelector selects valid playbook for storefront-api
    - PolicyEngine approves the proposal against discovered topology
    """
    class MockStorefrontMetricsTool(BaseTool):
        name: str = "query_metrics"
        description: str = "Query CPU and memory metrics"
        def execute(self, **kwargs) -> ToolResult:
            ev = NormalizedEvidence(
                evidence_id="ev_storefront_cpu",
                incident_id="inc_sf_1",
                source=EvidenceSource.METRICS,
                evidence_type=EvidenceType.METRIC_SERIES,
                summary="storefront-api CPU utilization at 98% under traffic spike",
                data={"metric": "cpu_utilization", "value": 0.98, "service": "storefront-api"},
                provenance=EvidenceProvenance(
                    collector="prometheus_probe",
                    query="container_cpu_utilization",
                    hash_signature="hash_sf_cpu_123"
                ),
                reliability=0.95
            )
            return ToolResult(tool_name="query_metrics", status=ToolExecutionStatus.SUCCESS, evidence=[ev])

    class MockStorefrontDeployTool(BaseTool):
        name: str = "inspect_deployment_history"
        description: str = "Inspect deployment logs"
        def execute(self, **kwargs) -> ToolResult:
            ev = NormalizedEvidence(
                evidence_id="ev_storefront_dep",
                incident_id="inc_sf_1",
                source=EvidenceSource.LOGS,
                evidence_type=EvidenceType.DEPLOYMENT_EVENT,
                summary="storefront-api stable version 1.0.0 deployed 14 days ago",
                data={"version": "1.0.0", "change_description": "Initial base release"},
                provenance=EvidenceProvenance(
                    collector="git_log",
                    query="git_rev",
                    hash_signature="hash_sf_dep_456"
                ),
                reliability=0.90
            )
            return ToolResult(tool_name="inspect_deployment_history", status=ToolExecutionStatus.SUCCESS, evidence=[ev])


    registry = ToolRegistry()

    registry.register_tool(MockStorefrontMetricsTool())
    registry.register_tool(MockStorefrontDeployTool())

    investigator = ActiveInvestigator(tool_registry=registry, max_tool_calls=5, confidence_threshold=0.70)
    incident = make_test_incident(
        incident_id="inc_sf_1",
        service="storefront-api",
        severity=IncidentSeverity.CRITICAL,
        symptom="Severe request queuing and HTTP 504 on storefront-api"
    )

    state = investigator.run_investigation(incident)
    assert state.is_completed is True
    assert state.final_root_cause_hypothesis is not None
    assert state.final_root_cause_hypothesis.target_service == "storefront-api"
    assert state.final_root_cause_hypothesis.category == HypothesisCategory.RESOURCE

    # Run Root Cause Verifier
    verifier = RootCauseVerifier()
    decision = verifier.verify_and_generate_decision(state)
    assert decision.is_unknown is False
    assert decision.root_cause_service == "storefront-api"
    assert decision.root_cause_category == HypothesisCategory.RESOURCE

    # Run Playbook Selector
    selector = PlaybookSelector()
    proposal, err = selector.select_playbook(decision=decision, incident=incident)
    assert err is None
    assert proposal is not None
    assert proposal.target_service == "storefront-api"
    assert proposal.action_type in [RemediationActionType.SCALE_REPLICAS, RemediationActionType.RESTART_SERVICE]

    # Run Policy Gate Validation
    policy_engine = PolicyEngine()
    policy_result = policy_engine.evaluate_proposal(proposal)
    assert policy_result.is_allowed is True, f"Policy Engine must allow valid remediation on discovered service: {policy_result.rejection_reason}"

def test_remediation_proposal_for_obsolete_service_is_denied(custom_discovered_topology):
    """
    Verifies that when running in discovered topology mode, remediation proposals
    targeting obsolete hardcoded service names are rejected.
    """
    policy_engine = PolicyEngine()

    obsolete_proposal = RemediationProposal(
        incident_id="inc_obs_1",
        action_type=RemediationActionType.RESTART_SERVICE,
        target_service="order-service", # Not in custom_discovered_topology
        parameters={"service": "order-service"},
        rationale="Restart order-service container"
    )

    res = policy_engine.evaluate_proposal(obsolete_proposal)
    assert res.is_allowed is False
    assert res.policy_code == "DENIED_UNKNOWN_SERVICE"
    assert "order-service" in res.rejection_reason

