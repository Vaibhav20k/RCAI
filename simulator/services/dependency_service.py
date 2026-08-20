# Downstream Dependency Mock Service (e.g., Third-Party Bank Gateway)
import time
import httpx
from typing import Dict, Any
from pydantic import BaseModel, Field
from simulator.services.base import BaseService

class BankVerificationRequest(BaseModel):
    account_id: str
    amount: float = Field(gt=0)
    currency: str = "INR"

class DependencyService(BaseService):
    def __init__(self, port: int = 8003, version: str = "1.0.0"):
        super().__init__(
            service_name="dependency-service",
            version=version,
            config_version="v1",
            port=port
        )
        self._register_routes()

    def _register_routes(self) -> None:
        @self.app.post("/api/v1/bank/verify")
        def verify_bank_account(req: BankVerificationRequest):
            # Base processing simulation
            time.sleep(0.015)
            return {
                "status": "APPROVED",
                "account_id": req.account_id,
                "amount": req.amount,
                "currency": req.currency,
                "auth_code": "AUTH_MOCK_9921"
            }

        @self.app.get("/api/v1/bank/status")
        def bank_status():
            return {
                "status": "HEALTHY",
                "partner": "HDFC_MOCK_GATEWAY",
                "availability": 0.999
            }

app = DependencyService().app
