# Payment Domain Core Data Models for RCAI v2
import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class PaymentStatus(str, Enum):
    INITIATED = "INITIATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class WebhookStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class PaymentTransaction(BaseModel):
    transaction_id: str = Field(default_factory=lambda: f"pay_tx_{uuid.uuid4().hex[:8]}")
    order_id: str
    merchant_id: str = "mer_razorpay_default"
    amount: float
    currency: str = "INR"
    status: PaymentStatus = PaymentStatus.INITIATED
    gateway_route: str = "hdfc_upi_primary"
    psp_reference: Optional[str] = None
    idempotency_key: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

class WebhookDelivery(BaseModel):
    delivery_id: str = Field(default_factory=lambda: f"wh_{uuid.uuid4().hex[:8]}")
    transaction_id: str
    event_type: str = "payment.captured"
    target_url: str = "https://merchant.example.com/webhooks"
    status: WebhookStatus = WebhookStatus.PENDING
    attempt_count: int = 0
    max_retries: int = 3
    last_http_status: Optional[int] = None
    created_at: float = Field(default_factory=time.time)

class LedgerEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: f"ledg_{uuid.uuid4().hex[:8]}")
    transaction_id: str
    account_id: str
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    balance_after: float = 0.0
    timestamp: float = Field(default_factory=time.time)

class SettlementBatch(BaseModel):
    batch_id: str = Field(default_factory=lambda: f"set_{uuid.uuid4().hex[:8]}")
    merchant_id: str
    total_amount: float = 0.0
    fee_amount: float = 0.0
    net_payout: float = 0.0
    transaction_ids: List[str] = Field(default_factory=list)
    status: str = "OPEN"
    created_at: float = Field(default_factory=time.time)
