# Payment Infrastructure Microservice Cluster for RCAI v2
import time
import uuid
from typing import Dict, Any, List, Optional
from simulator.payment.models import (
    PaymentTransaction, PaymentStatus, WebhookDelivery, WebhookStatus,
    LedgerEntry, SettlementBatch
)
from simulator.faults.injector import FaultInjector
from simulator.faults.models import FaultConfig, FaultType

class PaymentDomainCluster:
    def __init__(self):
        self.transactions: Dict[str, PaymentTransaction] = {}
        self.idempotency_records: Dict[str, str] = {} # key -> transaction_id
        self.webhooks: Dict[str, WebhookDelivery] = {}
        self.ledger: List[LedgerEntry] = []
        self.settlement_batches: Dict[str, SettlementBatch] = {}
        
        # Dedicated Fault Injectors per Payment Subsystem
        self.gateway_fault_injector = FaultInjector("payment-gateway")
        self.webhook_fault_injector = FaultInjector("webhook-service")
        self.ledger_fault_injector = FaultInjector("ledger-service")
        self.settlement_fault_injector = FaultInjector("settlement-service")

    def process_payment(
        self,
        order_id: str,
        amount: float,
        idempotency_key: str,
        route: str = "hdfc_upi_primary",
        merchant_id: str = "mer_default"
    ) -> PaymentTransaction:
        # 1. Idempotency Check
        if idempotency_key in self.idempotency_records:
            existing_id = self.idempotency_records[idempotency_key]
            return self.transactions[existing_id]

        # 2. Check Gateway Faults
        err_status = self.gateway_fault_injector.apply_pre_request_faults()
        if err_status and err_status >= 500:
            tx = PaymentTransaction(
                order_id=order_id,
                merchant_id=merchant_id,
                amount=amount,
                idempotency_key=idempotency_key,
                gateway_route=route,
                status=PaymentStatus.FAILED,
                error_code="GATEWAY_UNAVAILABLE",
                error_message=f"HTTP {err_status} from upstream PSP route {route}"
            )
            self.transactions[tx.transaction_id] = tx
            self.idempotency_records[idempotency_key] = tx.transaction_id
            return tx

        # 3. Successful Authorization & Capture
        tx = PaymentTransaction(
            order_id=order_id,
            merchant_id=merchant_id,
            amount=amount,
            idempotency_key=idempotency_key,
            gateway_route=route,
            psp_reference=f"psp_ref_{uuid.uuid4().hex[:10]}",
            status=PaymentStatus.CAPTURED
        )
        self.transactions[tx.transaction_id] = tx
        self.idempotency_records[idempotency_key] = tx.transaction_id

        # 4. Dispatch Webhook
        self._dispatch_webhook(tx)

        # 5. Record Ledger Entry
        self._record_ledger(tx)

        # 6. Add to Settlement Batch
        self._batch_settlement(tx)

        return tx

    def _dispatch_webhook(self, tx: PaymentTransaction) -> WebhookDelivery:
        wh = WebhookDelivery(transaction_id=tx.transaction_id)
        wh_err = self.webhook_fault_injector.apply_pre_request_faults()
        if wh_err and wh_err >= 500:
            wh.status = WebhookStatus.FAILED
            wh.last_http_status = wh_err
            wh.attempt_count = 1
        else:
            wh.status = WebhookStatus.DELIVERED
            wh.last_http_status = 200
            wh.attempt_count = 1
        self.webhooks[wh.delivery_id] = wh
        return wh

    def _record_ledger(self, tx: PaymentTransaction) -> None:
        self.ledger.append(LedgerEntry(
            transaction_id=tx.transaction_id,
            account_id="acc_merchant_payable",
            credit_amount=tx.amount,
            balance_after=tx.amount
        ))

    def _batch_settlement(self, tx: PaymentTransaction) -> None:
        batch = self.settlement_batches.get(tx.merchant_id)
        if not batch:
            batch = SettlementBatch(merchant_id=tx.merchant_id)
            self.settlement_batches[tx.merchant_id] = batch
        batch.total_amount += tx.amount
        batch.fee_amount += (tx.amount * 0.02)
        batch.net_payout += (tx.amount * 0.98)
        batch.transaction_ids.append(tx.transaction_id)

    def clear_all_faults(self) -> None:
        self.gateway_fault_injector.clear_faults()
        self.webhook_fault_injector.clear_faults()
        self.ledger_fault_injector.clear_faults()
        self.settlement_fault_injector.clear_faults()
