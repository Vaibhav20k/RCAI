# Asynchronous Queue Worker Service
import time
import threading
from typing import Dict, Any, List
from pydantic import BaseModel
from simulator.services.base import BaseService
from prometheus_client import Gauge

class QueueItem(BaseModel):
    task_id: str
    task_type: str
    payload: Dict[str, Any]

class WorkerService(BaseService):
    def __init__(self, port: int = 8004, version: str = "1.0.0"):
        super().__init__(
            service_name="worker-service",
            version=version,
            config_version="v1",
            port=port
        )
        self.queue_depth_gauge = Gauge(
            "queue_backlog_depth",
            "Current depth of background task queue",
            ["queue_name"],
            registry=self.registry
        )
        self.queue: List[QueueItem] = []
        self._queue_lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._register_routes()

    def _register_routes(self) -> None:
        @self.app.post("/api/v1/queue/push")
        def push_item(item: QueueItem):
            with self._queue_lock:
                self.queue.append(item)
                self.queue_depth_gauge.labels(queue_name="default").set(len(self.queue))
            return {"status": "QUEUED", "task_id": item.task_id, "depth": len(self.queue)}

        @self.app.get("/api/v1/queue/status")
        def queue_status():
            with self._queue_lock:
                return {
                    "service": self.service_name,
                    "queue_depth": len(self.queue),
                    "is_processing": self._running
                }

app = WorkerService().app
