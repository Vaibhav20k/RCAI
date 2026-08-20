# Payment Microservice
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from simulator.services.base import BaseService

class PaymentProcessRequest(BaseModel):
    order_id: str
    user_id: str
    amount: float = Field(gt=0)
    currency: str = "INR"
    payment_method: str = "UPI"

class PaymentService(BaseService):
    def __init__(
        self,
        port: int = 8002,
        version: str = "1.0.0",
        dependency_service_url: str = "http://localhost:8003",
        client: Optional[Any] = None
    ):
        super().__init__(
            service_name="payment-service",
            version=version,
            config_version="v1",
            port=port
        )
        self.dependency_service_url = dependency_service_url
        self._http_client = client
        self._register_routes()

    def _register_routes(self) -> None:
        @self.app.post("/api/v1/payments/process")
        def process_payment(req: PaymentProcessRequest):
            # Database write simulation
            db_delay = 0.01 + self.fault_injector.get_db_delay_seconds()
            t0 = time.perf_counter()
            time.sleep(db_delay)
            self.db_query_duration_seconds.labels(
                service=self.service_name,
                operation="insert_payment_record"
            ).observe(time.perf_counter() - t0)

            # Call downstream dependency (Bank API)
            t_dep = time.perf_counter()
            endpoint = "/api/v1/bank/verify"
            try:
                if self._http_client is not None:
                    resp = self._http_client.post(
                        endpoint,
                        json={"account_id": req.user_id, "amount": req.amount, "currency": req.currency},
                        headers={"X-Request-ID": "internal_trace"}
                    )
                    self.dependency_duration_seconds.labels(
                        service=self.service_name,
                        dependency="bank_gateway"
                    ).observe(time.perf_counter() - t_dep)
                    
                    if resp.status_code != 200:
                        return {
                            "status": "FAILED",
                            "order_id": req.order_id,
                            "reason": f"Downstream dependency returned HTTP {resp.status_code}"
                        }
                    dep_data = resp.json()
                else:
                    dep_data = {"auth_code": "AUTH_STANDALONE"}
            except Exception as exc:
                self.dependency_duration_seconds.labels(
                    service=self.service_name,
                    dependency="bank_gateway"
                ).observe(time.perf_counter() - t_dep)
                return {
                    "status": "FAILED",
                    "order_id": req.order_id,
                    "reason": f"Downstream dependency error: {str(exc)}"
                }

            return {
                "status": "SUCCESS",
                "payment_id": f"pay_{req.order_id}_{int(time.time())}",
                "order_id": req.order_id,
                "amount": req.amount,
                "auth_code": dep_data.get("auth_code", "SUCCESS")
            }

app = PaymentService().app
