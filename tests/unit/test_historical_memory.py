# Unit Tests for Historical Incident Memory
import pytest
from agent.memory.models import HistoricalIncidentExperience
from agent.memory.store import HistoricalMemoryStore
from agent.routing.selector import EvidenceSelector
from agent.hypothesis.models import HypothesisSet, Hypothesis, HypothesisCategory
from tools.registry import create_default_investigation_tools

def test_historical_memory_storage_and_query():
    store = HistoricalMemoryStore()
    
    exp = HistoricalIncidentExperience(
        experience_id="exp_test_01",
        incident_id="inc_001",
        scenario_id="scenario_test",
        service="order-service",
        symptom="High query latency",
        root_cause_service="order-service",
        root_cause_category="database",
        successful_tool_sequence=["query_db_metrics", "compare_versions"],
        successful_remediation_action="optimize_db_index",
        time_to_diagnosis_ms=95.0,
        tool_calls_count=2
    )
    store.record_experience(exp)

    similar = store.query_similar_experiences(service="order-service", symptom="database latency high")
    assert len(similar) > 0
    assert similar[0].service == "order-service"

    recs = store.get_recommended_actions(service="order-service", symptom="database latency high")
    assert "query_db_metrics" in recs

def test_selector_prioritizes_memory_recommended_tools():
    store = HistoricalMemoryStore()
    tools = create_default_investigation_tools()
    selector = EvidenceSelector(tool_registry=tools, memory_store=store, use_memory=True)

    h_set = HypothesisSet(incident_id="inc_mem_test")
    h_set.add_hypothesis(Hypothesis(incident_id="inc_mem_test", target_service="payment-service", category=HypothesisCategory.DEPLOYMENT, description="Deploy"))
    h_set.add_hypothesis(Hypothesis(incident_id="inc_mem_test", target_service="payment-service", category=HypothesisCategory.DATABASE, description="DB"))

    # When symptom matches payment error rate, prior experience prioritizes inspect_deployment_history
    action = selector.select_next_action(
        hypothesis_set=h_set,
        executed_actions=[],
        target_service="payment-service",
        symptom_text="Payment service 100% error rate"
    )
    assert action is not None
    assert action[0] == "inspect_deployment_history"
