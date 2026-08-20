# Unit Tests for Payment Domain Diagnostic Evidence Tools
import pytest
from tools.payment.tools import (
    GetPaymentStateTool,
    GetGatewayResponseTool,
    GetWebhookDeliveryTool,
    GetLedgerEntryTool,
    GetSettlementBatchTool,
    GetPaymentRouteHealthTool
)
from simulator.payment.cluster import PaymentDomainCluster
from tools.base import ToolExecutionStatus, ToolPermission

@pytest.fixture
def payment_cluster():
    cluster = PaymentDomainCluster()
    cluster.process_payment(
        order_id="ord_test_tool",
        amount=500.0,
        idempotency_key="idemp_test_tool"
    )
    return cluster

def test_all_payment_tools_are_read_only(payment_cluster):
    tools = [
        GetPaymentStateTool(payment_cluster),
        GetGatewayResponseTool(payment_cluster),
        GetWebhookDeliveryTool(payment_cluster),
        GetLedgerEntryTool(payment_cluster),
        GetSettlementBatchTool(payment_cluster),
        GetPaymentRouteHealthTool(payment_cluster)
    ]
    for t in tools:
        assert t.permission_level == ToolPermission.READ_ONLY
        res = t.execute()
        assert res.status == ToolExecutionStatus.SUCCESS
        assert len(res.evidence) > 0
        ev = res.evidence[0]
        assert ev.provenance is not None
        assert len(ev.provenance.hash_signature) >= 8

def test_get_payment_state_tool(payment_cluster):
    tool = GetPaymentStateTool(payment_cluster)
    res = tool.execute(order_id="ord_test_tool")
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.raw_output["order_id"] == "ord_test_tool"
    assert res.raw_output["status"] == "CAPTURED"
