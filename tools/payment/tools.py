# Read-Only Payment Domain Diagnostic Evidence Tools for RCAI v2 (8 Evidence Tools)
import time
from typing import Dict, Any, List, Optional
from tools.base import BaseTool, ToolResult, ToolExecutionStatus, ToolPermission
from observability.models import NormalizedEvidence, EvidenceSource, EvidenceType
from simulator.payment.cluster import PaymentDomainCluster

class GetPaymentStateTool(BaseTool):
    name: str = "get_payment_state"
    description: str = "Query transaction state from internal payment state store"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, cluster: Optional[PaymentDomainCluster] = None):
        super().__init__(
            name="get_payment_state",
            description="Query transaction state from internal payment state store"
        )
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        tx_id = kwargs.get("transaction_id", "")
        order_id = kwargs.get("order_id", "")
        
        tx = None
        if self._cluster:
            if tx_id and tx_id in self._cluster.transactions:
                tx = self._cluster.transactions[tx_id]
            elif order_id:
                tx = next((t for t in self._cluster.transactions.values() if t.order_id == order_id), None)

        data = tx.model_dump() if tx else {"status": "NOT_FOUND", "order_id": order_id}
        ev = NormalizedEvidence.create(
            source=EvidenceSource.DATABASE,
            evidence_type=EvidenceType.DATABASE_METRIC,
            collector="PaymentStateStore",
            summary=f"Payment transaction status: {data.get('status', 'UNKNOWN')}",
            data=data,
            query=f"get_payment_state(order_id={order_id})",
            reliability=1.0
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output=data
        )

class GetGatewayResponseTool(BaseTool):
    name: str = "get_gateway_response"
    description: str = "Query upstream bank gateway / PSP response logs"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.2

    def __init__(self, cluster: Optional[PaymentDomainCluster] = None):
        super().__init__(
            name="get_gateway_response",
            description="Query upstream bank gateway / PSP response logs"
        )
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        route = kwargs.get("route", "hdfc_upi_primary")
        data = {"gateway_route": route, "status": "200_OK", "p95_latency_ms": 32.0}
        ev = NormalizedEvidence.create(
            source=EvidenceSource.LOGS,
            evidence_type=EvidenceType.LOG_RECORD,
            collector="GatewayLogCollector",
            summary=f"Gateway response metrics on route {route}",
            data=data,
            query=f"get_gateway_response(route={route})",
            reliability=0.95
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output=data
        )

class GetWebhookDeliveryTool(BaseTool):
    name: str = "get_webhook_delivery"
    description: str = "Inspect merchant webhook notification delivery state and retry logs"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, cluster: Optional[PaymentDomainCluster] = None):
        super().__init__(
            name="get_webhook_delivery",
            description="Inspect merchant webhook notification delivery state and retry logs"
        )
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        tx_id = kwargs.get("transaction_id", "")
        wh = None
        if self._cluster:
            wh = next((w for w in self._cluster.webhooks.values() if w.transaction_id == tx_id), None)

        data = wh.model_dump() if wh else {"webhook_status": "DELIVERED", "retry_count": 0}
        ev = NormalizedEvidence.create(
            source=EvidenceSource.LOGS,
            evidence_type=EvidenceType.LOG_RECORD,
            collector="WebhookDeliveryStore",
            summary=f"Webhook delivery status: {data.get('status', 'DELIVERED')}",
            data=data,
            query=f"get_webhook_delivery(transaction_id={tx_id})",
            reliability=1.0
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output=data
        )

class GetEventQueueStateTool(BaseTool):
    name: str = "get_event_queue_state"
    description: str = "Inspect asynchronous payment event queue backlog depth and consumer lag"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, cluster: Optional[PaymentDomainCluster] = None):
        super().__init__(
            name="get_event_queue_state",
            description="Inspect asynchronous payment event queue backlog depth and consumer lag"
        )
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        queue_name = kwargs.get("queue_name", "payment_captured_events")
        data = {"queue_name": queue_name, "pending_count": 0, "consumer_lag_ms": 12.0}
        ev = NormalizedEvidence.create(
            source=EvidenceSource.METRICS,
            evidence_type=EvidenceType.METRIC_SERIES,
            collector="PaymentQueueMonitor",
            summary=f"Payment event queue {queue_name} depth and lag metrics",
            data=data,
            query=f"get_event_queue_state(queue={queue_name})",
            reliability=1.0
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output=data
        )

class GetLedgerEntryTool(BaseTool):
    name: str = "get_ledger_entry"
    description: str = "Query double-entry financial accounting ledger records"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, cluster: Optional[PaymentDomainCluster] = None):
        super().__init__(
            name="get_ledger_entry",
            description="Query double-entry financial accounting ledger records"
        )
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        data = {"entries_count": len(self._cluster.ledger) if self._cluster else 1, "is_balanced": True}
        ev = NormalizedEvidence.create(
            source=EvidenceSource.DATABASE,
            evidence_type=EvidenceType.DATABASE_METRIC,
            collector="LedgerStore",
            summary="Financial ledger journal balance verification",
            data=data,
            query="get_ledger_entry()",
            reliability=1.0
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output=data
        )

class GetSettlementBatchTool(BaseTool):
    name: str = "get_settlement_batch"
    description: str = "Inspect merchant daily payout settlement reconciliation status"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, cluster: Optional[PaymentDomainCluster] = None):
        super().__init__(
            name="get_settlement_batch",
            description="Inspect merchant daily payout settlement reconciliation status"
        )
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        merchant_id = kwargs.get("merchant_id", "mer_default")
        batch = self._cluster.settlement_batches.get(merchant_id) if self._cluster else None
        data = batch.model_dump() if batch else {"merchant_id": merchant_id, "status": "SETTLED"}
        ev = NormalizedEvidence.create(
            source=EvidenceSource.DATABASE,
            evidence_type=EvidenceType.DATABASE_METRIC,
            collector="SettlementReconciliationEngine",
            summary=f"Settlement payout batch status: {data.get('status', 'SETTLED')}",
            data=data,
            query=f"get_settlement_batch(merchant_id={merchant_id})",
            reliability=1.0
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output=data
        )

class GetPaymentRouteHealthTool(BaseTool):
    name: str = "get_payment_route_health"
    description: str = "Query live health and success rate across PSP bank routes"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, cluster: Optional[PaymentDomainCluster] = None):
        super().__init__(
            name="get_payment_route_health",
            description="Query live health and success rate across PSP bank routes"
        )
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        route = kwargs.get("route", "hdfc_upi_primary")
        data = {"route": route, "success_rate": 0.99, "is_healthy": True}
        ev = NormalizedEvidence.create(
            source=EvidenceSource.METRICS,
            evidence_type=EvidenceType.METRIC_SERIES,
            collector="PaymentRouteHealthMonitor",
            summary=f"Payment PSP route health check: {route}",
            data=data,
            query=f"get_payment_route_health(route={route})",
            reliability=1.0
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output=data
        )

class GetReconciliationStateTool(BaseTool):
    name: str = "get_reconciliation_state"
    description: str = "Query internal ledger versus external PSP settlement reconciliation discrepancy state"
    permission_level: ToolPermission = ToolPermission.READ_ONLY
    cost_estimate: float = 1.0

    def __init__(self, cluster: Optional[PaymentDomainCluster] = None):
        super().__init__(
            name="get_reconciliation_state",
            description="Query internal ledger versus external PSP settlement reconciliation discrepancy state"
        )
        self._cluster = cluster

    def execute(self, **kwargs) -> ToolResult:
        data = {"is_reconciled": True, "discrepancy_count": 0, "unsettled_amount": 0.0}
        ev = NormalizedEvidence.create(
            source=EvidenceSource.DATABASE,
            evidence_type=EvidenceType.DATABASE_METRIC,
            collector="ReconciliationEngine",
            summary="Payment reconciliation discrepancy report",
            data=data,
            query="get_reconciliation_state()",
            reliability=1.0
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.SUCCESS,
            evidence=[ev],
            raw_output=data
        )
