# Live Prometheus HTTP Telemetry Client
import os
import time
from typing import Dict, Any, List, Optional
import httpx
from backend.config import get_settings

class PrometheusLiveClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 5.0
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.PROMETHEUS_URL).rstrip("/")
        self.bearer_token = bearer_token or settings.PROMETHEUS_BEARER_TOKEN
        self.api_key = api_key or settings.PROMETHEUS_API_KEY
        self.timeout_seconds = timeout_seconds
        
        # Build headers
        self._headers: Dict[str, str] = {
            "Accept": "application/json"
        }
        if self.bearer_token:
            self._headers["Authorization"] = f"Bearer {self.bearer_token}"
        if self.api_key:
            self._headers["X-API-Key"] = self.api_key

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers=self._headers,
            timeout=self.timeout_seconds
        )

    def check_health(self) -> bool:
        try:
            with self._get_client() as client:
                resp = client.get("/-/healthy")
                return resp.status_code == 200
        except Exception:
            return False

    def query_instant(self, query: str, time_ts: Optional[float] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"query": query}
        if time_ts is not None:
            params["time"] = time_ts

        try:
            with self._get_client() as client:
                resp = client.get("/api/v1/query", params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "errorType": "http_error",
                "error": f"HTTP {exc.response.status_code}: {exc.response.text}"
            }
        except httpx.RequestError as exc:
            return {
                "status": "error",
                "errorType": "connection_error",
                "error": f"Failed to connect to Prometheus at {self.base_url}: {str(exc)}"
            }
        except Exception as exc:
            return {
                "status": "error",
                "errorType": "unexpected_error",
                "error": str(exc)
            }

    def query_range(
        self,
        query: str,
        start_ts: float,
        end_ts: float,
        step_seconds: float = 15.0
    ) -> Dict[str, Any]:
        params = {
            "query": query,
            "start": start_ts,
            "end": end_ts,
            "step": f"{step_seconds}s"
        }
        try:
            with self._get_client() as client:
                resp = client.get("/api/v1/query_range", params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "errorType": "http_error",
                "error": f"HTTP {exc.response.status_code}: {exc.response.text}"
            }
        except httpx.RequestError as exc:
            return {
                "status": "error",
                "errorType": "connection_error",
                "error": f"Failed to connect to Prometheus at {self.base_url}: {str(exc)}"
            }
        except Exception as exc:
            return {
                "status": "error",
                "errorType": "unexpected_error",
                "error": str(exc)
            }

    def query_service_metrics(self, service_name: str) -> Dict[str, float]:
        # Helper to query core service metrics from Prometheus
        metrics_to_query = {
            "total_requests": f'sum(http_requests_total{{service="{service_name}"}})',
            "error_requests": f'sum(http_requests_total{{service="{service_name}",status=~"5.."}})',
            "error_rate": f'sum(rate(http_requests_total{{service="{service_name}",status=~"5.."}}[5m])) / sum(rate(http_requests_total{{service="{service_name}"}}[5m]))',
            "p95_latency_ms": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{service="{service_name}"}}[5m])) by (le)) * 1000',
            "cpu_burn_ms": f'sum(cpu_burn_ms{{service="{service_name}"}})',
            "cpu_utilization": f'avg(cpu_utilization{{service="{service_name}"}})',
            "active_faults_count": f'sum(active_faults_count{{service="{service_name}"}})'
        }
        
        results: Dict[str, float] = {}
        for key, promql in metrics_to_query.items():
            res = self.query_instant(promql)
            if res.get("status") == "success":
                data_result = res.get("data", {}).get("result", [])
                if data_result and len(data_result) > 0:
                    val_tuple = data_result[0].get("value")
                    if val_tuple and len(val_tuple) == 2:
                        try:
                            val = float(val_tuple[1])
                            if not (val != val): # NaN check
                                results[key] = round(val, 4)
                        except (ValueError, TypeError):
                            pass
        return results
