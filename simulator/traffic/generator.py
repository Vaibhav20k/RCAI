# Deterministic Traffic Generator for Incident Simulation
import time
import random
import statistics
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TrafficStats(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    latencies_ms: List[float] = Field(default_factory=list)
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

class TrafficGenerator:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        client: Optional[httpx.Client] = None,
        seed: int = 42
    ):
        self.base_url = base_url
        self._client = client or httpx.Client(base_url=base_url, timeout=10.0)
        self.seed = seed
        self._rng = random.Random(seed)

    def generate_batch(self, count: int = 20, delay_between_reqs_ms: float = 0.0) -> TrafficStats:
        latencies: List[float] = []
        success_count = 0
        fail_count = 0

        endpoints = [
            ("/api/orders", lambda: {
                "user_id": f"usr_{self._rng.randint(100, 999)}",
                "items": ["item_alpha", "item_beta"],
                "total_amount": round(self._rng.uniform(10.0, 500.0), 2),
                "currency": "INR"
            }),
            ("/api/payments", lambda: {
                "order_id": f"ord_direct_{self._rng.randint(1000, 9999)}",
                "user_id": f"usr_{self._rng.randint(100, 999)}",
                "amount": round(self._rng.uniform(20.0, 300.0), 2),
                "currency": "INR",
                "payment_method": "UPI"
            })
        ]

        for _ in range(count):
            endpoint, payload_fn = self._rng.choice(endpoints)
            payload = payload_fn()
            
            t0 = time.perf_counter()
            try:
                resp = self._client.post(
                    endpoint,
                    json=payload,
                    headers={"X-Request-ID": f"req_gen_{int(time.time()*1000)}_{self._rng.randint(10, 99)}"}
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(latency_ms)
                if 200 <= resp.status_code < 400:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception:
                latency_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(latency_ms)
                fail_count += 1

            if delay_between_reqs_ms > 0:
                time.sleep(delay_between_reqs_ms / 1000.0)

        total = success_count + fail_count
        p50 = statistics.median(latencies) if latencies else 0.0
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0.0)
        p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else (max(latencies) if latencies else 0.0)

        return TrafficStats(
            total_requests=total,
            successful_requests=success_count,
            failed_requests=fail_count,
            error_rate=round(fail_count / total, 4) if total > 0 else 0.0,
            latencies_ms=latencies,
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            p99_latency_ms=round(p99, 2)
        )
