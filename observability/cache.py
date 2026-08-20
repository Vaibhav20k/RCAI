# High-Performance TTL Telemetry Cache
import time
from typing import Dict, Any, Optional, Tuple

class TelemetryCache:
    def __init__(self, ttl_seconds: float = 2.0):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp <= self.ttl_seconds:
                return data
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        self._cache.clear()

global_telemetry_cache = TelemetryCache()
