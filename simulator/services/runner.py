# Microservice Cluster In-Process Runner for Deterministic Testing & Local Execution
from starlette.testclient import TestClient
from simulator.services.dependency_service import DependencyService
from simulator.services.payment_service import PaymentService
from simulator.services.order_service import OrderService
from simulator.services.gateway import ApiGateway
from simulator.services.worker_service import WorkerService

class InProcessCluster:
    def __init__(self):
        # 1. Initialize services
        self.dependency_service = DependencyService(port=8003)
        self.dep_client = TestClient(self.dependency_service.app, base_url="http://localhost:8003")

        self.payment_service = PaymentService(
            port=8002,
            dependency_service_url="http://localhost:8003",
            client=self.dep_client
        )
        self.payment_client = TestClient(self.payment_service.app, base_url="http://localhost:8002")

        self.order_service = OrderService(
            port=8001,
            payment_service_url="http://localhost:8002",
            client=self.payment_client
        )
        self.order_client = TestClient(self.order_service.app, base_url="http://localhost:8001")

        # Custom forwarder client for API gateway to route to order & payment apps
        class GatewayForwarderClient:
            def __init__(self, order_app, payment_app):
                self.order_client = TestClient(order_app)
                self.payment_client = TestClient(payment_app)

            def post(self, url, json=None, headers=None):
                if "/api/v1/orders" in url:
                    # Strip base url if any
                    path = url.split("8001")[-1] if "8001" in url else url
                    return self.order_client.post(path, json=json, headers=headers)
                else:
                    path = url.split("8002")[-1] if "8002" in url else url
                    return self.payment_client.post(path, json=json, headers=headers)

        self.gw_forwarder = GatewayForwarderClient(
            self.order_service.app,
            self.payment_service.app
        )

        self.gateway_service = ApiGateway(
            port=8000,
            order_service_url="http://localhost:8001",
            payment_service_url="http://localhost:8002",
            client=self.gw_forwarder
        )
        self.gateway_client = TestClient(self.gateway_service.app, base_url="http://localhost:8000")

        self.worker_service = WorkerService(port=8004)
        self.worker_client = TestClient(self.worker_service.app, base_url="http://localhost:8004")

    def clear_all_faults(self) -> None:
        self.gateway_service.fault_injector.clear_faults()
        self.order_service.fault_injector.clear_faults()
        self.payment_service.fault_injector.clear_faults()
        self.dependency_service.fault_injector.clear_faults()
        self.worker_service.fault_injector.clear_faults()

    def get_service_map(self):
        return {
            "api-gateway": self.gateway_service,
            "order-service": self.order_service,
            "payment-service": self.payment_service,
            "dependency-service": self.dependency_service,
            "worker-service": self.worker_service,
        }
