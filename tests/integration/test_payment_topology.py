# Integration Test for Payment Infrastructure Topology
import pytest
from simulator.payment.cluster import PaymentDomainCluster
from simulator.payment.models import PaymentStatus, WebhookStatus
from simulator.faults.models import FaultConfig, FaultType

def test_payment_lifecycle_end_to_end():
    cluster = PaymentDomainCluster()
    tx = cluster.process_payment(
        order_id="ord_101",
        amount=1500.0,
        idempotency_key="idemp_101",
        route="hdfc_upi_primary"
    )
    assert tx.status == PaymentStatus.CAPTURED
    assert tx.psp_reference is not None

    # Verify Idempotency
    tx_dup = cluster.process_payment(
        order_id="ord_101",
        amount=1500.0,
        idempotency_key="idemp_101"
    )
    assert tx_dup.transaction_id == tx.transaction_id

    # Verify Webhook Dispatch
    assert len(cluster.webhooks) == 1
    wh = list(cluster.webhooks.values())[0]
    assert wh.status == WebhookStatus.DELIVERED

    # Verify Ledger & Settlement
    assert len(cluster.ledger) == 1
    assert "mer_default" in cluster.settlement_batches
    assert cluster.settlement_batches["mer_default"].total_amount == 1500.0

def test_payment_gateway_fault_injection():
    cluster = PaymentDomainCluster()
    cluster.gateway_fault_injector.set_fault(FaultConfig(
        service_name="payment-gateway",
        fault_type=FaultType.BAD_DEPLOYMENT,
        error_rate=1.0,
        parameters={"http_status": 503}
    ))
    tx = cluster.process_payment(
        order_id="ord_503",
        amount=2000.0,
        idempotency_key="idemp_503"
    )
    assert tx.status == PaymentStatus.FAILED
    assert tx.error_code == "GATEWAY_UNAVAILABLE"
