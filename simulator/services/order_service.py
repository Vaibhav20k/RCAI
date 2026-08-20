# Order Microservice
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from simulator.services.base import BaseService

class OrderCreateRequest(BaseModel):
    user_id: str
    items: List[str] = Field(default_factory=lambda: ["item_1"])
    total_amount: float = Field(gt=0)
    currency: str = "INR"

class OrderService(BaseService):
    def __init__(
        self,
        port: int = 8001,
        version: str = "1.0.0",
        payment_service_url: str = "http://localhost:8002",
        client: Optional[Any] = None
    ):
        super().__init__(
            service_name="order-service",
            version=version,
            config_version="v1",
            port=port
        )
        self.payment_service_url = payment_service_url
        self._http_client = client
        self._orders_db: Dict[str, Dict[str, Any]] = {}
        self._register_routes()

    def _register_routes(self) -> None:
        @self.app.post("/api/v1/orders")
        def create_order(req: OrderCreateRequest):
            order_id = f"ord_{int(time.time()*1000)}"
            
            # Database query latency with injected regression
            t0 = time.perf_counter()
            db_delay = 0.008 + self.fault_injector.get_db_delay_seconds()
            time.sleep(db_delay)
            self.db_query_duration_seconds.labels(
                service=self.service_name,
                operation="create_order"
            ).observe(time.perf_counter() - t0)

            # Call Payment Service
            t_pay = time.perf_counter()
            endpoint = "/api/v1/payments/process"
            try:
                if self._http_client is not None:
                    resp = self._http_client.post(
                        endpoint,
                        json={
                            "order_id": order_id,
                            "user_id": req.user_id,
                            "amount": req.total_amount,
                            "currency": req.currency
                        }
                    )
                    self.dependency_duration_seconds.labels(
                        service=self.service_name,
                        dependency="payment_service"
                    ).observe(time.perf_counter() - t_pay)
                    
                    pay_result = resp.json() if resp.status_code == 200 else {"status": "FAILED"}
                else:
                    pay_result = {"status": "SUCCESS"}
            except Exception as exc:
                self.dependency_duration_seconds.labels(
                    service=self.service_name,
                    dependency="payment_service"
                ).observe(time.perf_counter() - t_pay)
                pay_result = {"status": "FAILED", "error": str(exc)}

            order_record = {
                "order_id": order_id,
                "user_id": req.user_id,
                "items": req.items,
                "total_amount": req.total_amount,
                "payment_status": pay_result.get("status", "UNKNOWN"),
                "created_at": time.time()
            }
            self._orders_db[order_id] = order_record

            return {
                "status": "CREATED" if order_record["payment_status"] == "SUCCESS" else "PAYMENT_FAILED",
                "order": order_record
            }

        @self.app.get("/api/v1/orders/{order_id}")
        def get_order(order_id: str):
            t0 = time.perf_counter()
            db_delay = 0.005 + self.fault_injector.get_db_delay_seconds()
            time.sleep(db_delay)
            self.db_query_duration_seconds.labels(
                service=self.service_name,
                operation="get_order_by_id"
            ).observe(time.perf_counter() - t0)
            
            if order_id not in self._orders_db:
                return {"error": "NotFound", "order_id": order_id}
            return {"order": self._orders_db[order_id]}

app = OrderService().app
