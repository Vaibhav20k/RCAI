# Investigation Tool Registry - RCAI v2
from typing import Dict, List, Optional
from tools.base import BaseTool, ToolPermission
from tools.logs.query_logs import QueryLogsTool
from tools.metrics.query_metrics import QueryMetricsTool
from tools.traces.query_traces import QueryTracesTool
from tools.deployments.inspect_deployments import InspectDeploymentHistoryTool
from tools.deployments.compare_versions import CompareVersionsTool
from tools.database.query_db import QueryDatabaseMetricsTool
from tools.health.inspect_health import InspectServiceHealthTool, InspectDependencyHealthTool
from tools.payment.tools import (
    GetPaymentStateTool,
    GetGatewayResponseTool,
    GetWebhookDeliveryTool,
    GetLedgerEntryTool,
    GetSettlementBatchTool,
    GetPaymentRouteHealthTool
)
from simulator.services.runner import InProcessCluster
from observability.metrics.collector import MetricsCollector

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self, permission_filter: Optional[ToolPermission] = None) -> List[BaseTool]:
        if permission_filter:
            return [t for t in self._tools.values() if t.permission_level == permission_filter]
        return list(self._tools.values())

def create_default_investigation_tools(
    cluster: Optional[InProcessCluster] = None,
    metrics_collector: Optional[MetricsCollector] = None
) -> ToolRegistry:
    reg = ToolRegistry()

    if cluster and not metrics_collector:
        metrics_collector = MetricsCollector(cluster)

    reg.register_tool(QueryLogsTool())
    reg.register_tool(QueryMetricsTool(metrics_collector))
    reg.register_tool(QueryTracesTool())
    reg.register_tool(InspectDeploymentHistoryTool())
    reg.register_tool(CompareVersionsTool())
    reg.register_tool(QueryDatabaseMetricsTool(metrics_collector))
    reg.register_tool(InspectServiceHealthTool(cluster))
    reg.register_tool(InspectDependencyHealthTool(cluster))

    # Register v2 Payment Evidence Tools
    reg.register_tool(GetPaymentStateTool())
    reg.register_tool(GetGatewayResponseTool())
    reg.register_tool(GetWebhookDeliveryTool())
    reg.register_tool(GetLedgerEntryTool())
    reg.register_tool(GetSettlementBatchTool())
    reg.register_tool(GetPaymentRouteHealthTool())

    return reg
