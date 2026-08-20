# Base Microservice Framework for RCAI Incident Simulation
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from simulator.faults.injector import FaultInjector
from simulator.faults.models import FaultConfig, FaultType

class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "request_id": getattr(record, "request_id", "none"),
            "trace_id": getattr(record, "trace_id", "none"),
            "event": getattr(record, "event", "application_log"),
            "message": record.getMessage(),
            "version": getattr(record, "version", "1.0.0"),
        }
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_payload)

def setup_service_logger(service_name: str, version: str) -> logging.Logger:
    logger = logging.getLogger(f"rcai.{service_name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    # Remove existing handlers to avoid duplicates
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        
    handler = logging.StreamHandler()
    formatter = JsonLogFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class BaseService:
    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        config_version: str = "v1",
        commit_hash: str = "c5d1fb6",
        port: int = 8000
    ):
        self.service_name = service_name
        self.version = version
        self.config_version = config_version
        self.commit_hash = commit_hash
        self.port = port
        self.start_time = time.time()
        self.logger = setup_service_logger(service_name, version)
        self.fault_injector = FaultInjector(service_name)
        
        # Isolated Prometheus Registry per service
        self.registry = CollectorRegistry()
        
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests handled by the service",
            ["service", "method", "endpoint", "status_code"],
            registry=self.registry
        )
        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency in seconds",
            ["service", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        self.db_query_duration_seconds = Histogram(
            "db_query_duration_seconds",
            "Database query execution latency in seconds",
            ["service", "operation"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
            registry=self.registry
        )
        self.dependency_duration_seconds = Histogram(
            "dependency_duration_seconds",
            "Downstream dependency call latency in seconds",
            ["service", "dependency"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry
        )
        self.active_faults_gauge = Gauge(
            "active_faults_count",
            "Count of currently active injected faults",
            ["service"],
            registry=self.registry
        )

        self.app = FastAPI(title=f"RCAI - {service_name}", version=version)
        self._register_middleware()
        self._register_core_routes()

    def _register_middleware(self) -> None:
        @self.app.middleware("http")
        async def observability_and_fault_middleware(request: Request, call_next):
            req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
            trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
            start_ts = time.perf_counter()
            
            # Attach tracking to request state
            request.state.request_id = req_id
            request.state.trace_id = trace_id

            # Apply injected pre-request faults (latency, cpu, error)
            fault_error_status = self.fault_injector.apply_pre_request_faults()
            if fault_error_status is not None:
                duration = time.perf_counter() - start_ts
                self.http_requests_total.labels(
                    service=self.service_name,
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=str(fault_error_status)
                ).inc()
                self.http_request_duration_seconds.labels(
                    service=self.service_name,
                    endpoint=request.url.path
                ).observe(duration)
                
                resp = JSONResponse(
                    status_code=fault_error_status,
                    content={
                        "error": "InjectedFaultError",
                        "service": self.service_name,
                        "status_code": fault_error_status,
                        "request_id": req_id
                    }
                )
                resp.headers["X-Request-ID"] = req_id
                resp.headers["X-Trace-ID"] = trace_id
                return resp

            try:
                response = await call_next(request)
                status_code = response.status_code
            except Exception as exc:
                status_code = 500
                duration = time.perf_counter() - start_ts
                self.http_requests_total.labels(
                    service=self.service_name,
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=str(status_code)
                ).inc()
                self.http_request_duration_seconds.labels(
                    service=self.service_name,
                    endpoint=request.url.path
                ).observe(duration)
                raise exc

            duration = time.perf_counter() - start_ts
            self.http_requests_total.labels(
                service=self.service_name,
                method=request.method,
                endpoint=request.url.path,
                status_code=str(status_code)
            ).inc()
            self.http_request_duration_seconds.labels(
                service=self.service_name,
                endpoint=request.url.path
            ).observe(duration)

            response.headers["X-Request-ID"] = req_id
            response.headers["X-Trace-ID"] = trace_id
            return response

    def _register_core_routes(self) -> None:
        @self.app.get("/health")
        def get_health():
            return {
                "status": "UP",
                "service": self.service_name,
                "version": self.version,
                "uptime_seconds": round(time.time() - self.start_time, 2)
            }

        @self.app.get("/version")
        def get_version():
            return {
                "service": self.service_name,
                "version": self.version,
                "config_version": self.config_version,
                "commit_hash": self.commit_hash
            }

        @self.app.get("/metrics")
        def get_metrics():
            active_count = len(self.fault_injector.get_active_faults())
            self.active_faults_gauge.labels(service=self.service_name).set(active_count)
            return Response(
                content=generate_latest(self.registry),
                media_type=CONTENT_TYPE_LATEST
            )

        @self.app.post("/admin/faults")
        def set_fault(fault: FaultConfig):
            self.fault_injector.set_fault(fault)
            active_count = len(self.fault_injector.get_active_faults())
            self.active_faults_gauge.labels(service=self.service_name).set(active_count)
            return {
                "status": "fault_configured",
                "service": self.service_name,
                "fault": fault.model_dump()
            }

        @self.app.get("/admin/faults")
        def list_faults():
            return {
                "service": self.service_name,
                "faults": [f.model_dump() for f in self.fault_injector.get_active_faults()]
            }

        @self.app.delete("/admin/faults")
        def clear_faults():
            self.fault_injector.clear_faults()
            self.active_faults_gauge.labels(service=self.service_name).set(0)
            return {
                "status": "faults_cleared",
                "service": self.service_name
            }
