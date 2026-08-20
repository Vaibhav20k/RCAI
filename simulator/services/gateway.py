# API Gateway Service
import time
import httpx
from typing import Dict, Any, Optional
from fastapi import Request, Response
from simulator.services.base import BaseService

class ApiGateway(BaseService):
    def __init__(
        self,
        port: int = 8000,
        version: str = "1.0.0",
        order_service_url: str = "http://localhost:8001",
        payment_service_url: str = "http://localhost:8002",
        client: Optional[httpx.Client] = None
    ):
        super().__init__(
            service_name="api-gateway",
            version=version,
            config_version="v1",
            port=port
        )
        self.order_service_url = order_service_url
        self.payment_service_url = payment_service_url
        self._http_client = client or httpx.Client(timeout=15.0)
        self._register_routes()

    def _register_routes(self) -> None:
        @self.app.post("/api/orders")
        async def create_order_route(request: Request):
            body = await request.json()
            t0 = time.perf_counter()
            url = f"{self.order_service_url}/api/v1/orders"
            headers = {
                "X-Request-ID": request.state.request_id,
                "X-Trace-ID": request.state.trace_id
            }
            try:
                resp = self._http_client.post(url, json=body, headers=headers)
                self.dependency_duration_seconds.labels(
                    service=self.service_name,
                    dependency="order_service"
                ).observe(time.perf_counter() - t0)
                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    media_type="application/json"
                )
            except Exception as exc:
                self.dependency_duration_seconds.labels(
                    service=self.service_name,
                    dependency="order_service"
                ).observe(time.perf_counter() - t0)
                return Response(
                    content=f"{{\"error\": \"GatewayForwardError\", \"message\": \"{str(exc)}\"}}",
                    status_code=502,
                    media_type="application/json"
                )

        @self.app.post("/api/payments")
        async def create_payment_route(request: Request):
            body = await request.json()
            t0 = time.perf_counter()
            url = f"{self.payment_service_url}/api/v1/payments/process"
            headers = {
                "X-Request-ID": request.state.request_id,
                "X-Trace-ID": request.state.trace_id
            }
            try:
                resp = self._http_client.post(url, json=body, headers=headers)
                self.dependency_duration_seconds.labels(
                    service=self.service_name,
                    dependency="payment_service"
                ).observe(time.perf_counter() - t0)
                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    media_type="application/json"
                )
            except Exception as exc:
                self.dependency_duration_seconds.labels(
                    service=self.service_name,
                    dependency="payment_service"
                ).observe(time.perf_counter() - t0)
                return Response(
                    content=f"{{\"error\": \"GatewayForwardError\", \"message\": \"{str(exc)}\"}}",
                    status_code=502,
                    media_type="application/json"
                )

app = ApiGateway().app
