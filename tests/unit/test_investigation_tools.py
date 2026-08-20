# Unit Tests for Investigation Diagnostic Tools
import time
import pytest
from simulator.services.runner import InProcessCluster
from observability.logs.collector import global_log_collector, LogEntry
from observability.tracing.collector import global_trace_collector, Span
from observability.deployments.store import global_deployment_store, DeploymentRecord
from observability.metrics.collector import MetricsCollector
from tools.registry import create_default_investigation_tools
from tools.base import ToolExecutionStatus

@pytest.fixture
def cluster_and_tools():
    c = InProcessCluster()
    metrics = MetricsCollector(c)
    tools = create_default_investigation_tools(c, metrics)
    global_log_collector.clear()
    global_trace_collector.clear()
    yield c, tools
    c.clear_all_faults()
    global_log_collector.clear()
    global_trace_collector.clear()

def test_query_logs_tool(cluster_and_tools):
    cluster, tools = cluster_and_tools
    log_tool = tools.get_tool("query_logs")
    
    # 1. No logs
    res_empty = log_tool.execute(service="order-service")
    assert res_empty.status == ToolExecutionStatus.NO_EVIDENCE_FOUND

    # 2. Add log
    global_log_collector.record_log(
        LogEntry(service="order-service", level="ERROR", event="db_error", message="Timeout reading orders")
    )
    res_success = log_tool.execute(service="order-service", level="ERROR")
    assert res_success.status == ToolExecutionStatus.SUCCESS
    assert len(res_success.evidence) == 1
    assert "order-service" in res_success.evidence[0].summary

def test_query_metrics_tool(cluster_and_tools):
    cluster, tools = cluster_and_tools
    metrics_tool = tools.get_tool("query_metrics")
    
    cluster.order_client.get("/health")
    res = metrics_tool.execute(service="order-service")
    assert res.status == ToolExecutionStatus.SUCCESS
    assert len(res.evidence) >= 2

def test_query_traces_tool(cluster_and_tools):
    cluster, tools = cluster_and_tools
    traces_tool = tools.get_tool("query_traces")
    
    # Trigger request to generate span
    cluster.gateway_client.post("/api/orders", json={"user_id": "usr_t", "total_amount": 100.0})
    
    res = traces_tool.execute(service="api-gateway")
    assert res.status == ToolExecutionStatus.SUCCESS
    assert len(res.evidence) > 0

def test_inspect_deployment_history_and_compare_versions(cluster_and_tools):
    cluster, tools = cluster_and_tools
    deploy_tool = tools.get_tool("inspect_deployment_history")
    compare_tool = tools.get_tool("compare_versions")

    res_deploy = deploy_tool.execute(service="payment-service")
    assert res_deploy.status == ToolExecutionStatus.SUCCESS
    assert len(res_deploy.evidence) > 0

    res_compare = compare_tool.execute(service="payment-service")
    assert res_compare.status == ToolExecutionStatus.SUCCESS
    assert "payment-service" in res_compare.evidence[0].summary

def test_query_db_metrics_tool(cluster_and_tools):
    cluster, tools = cluster_and_tools
    db_tool = tools.get_tool("query_db_metrics")
    
    res = db_tool.execute(service="order-service")
    assert res.status == ToolExecutionStatus.SUCCESS
    assert len(res.evidence) == 1

def test_inspect_service_and_dependency_health_tools(cluster_and_tools):
    cluster, tools = cluster_and_tools
    health_tool = tools.get_tool("inspect_service_health")
    dep_tool = tools.get_tool("inspect_dependency_health")

    res_health = health_tool.execute(service="api-gateway")
    assert res_health.status == ToolExecutionStatus.SUCCESS
    assert res_health.evidence[0].data["is_up"] is True

    res_dep = dep_tool.execute()
    assert res_dep.status == ToolExecutionStatus.SUCCESS
    assert res_dep.evidence[0].data["data"]["status"] == "HEALTHY"

def test_tool_handles_unbound_collector_gracefully():
    from tools.metrics.query_metrics import QueryMetricsTool
    unbound_tool = QueryMetricsTool(metrics_collector=None)
    res = unbound_tool.execute(service="order-service")
    assert res.status == ToolExecutionStatus.EVIDENCE_SOURCE_UNAVAILABLE
    assert len(res.evidence) == 0
