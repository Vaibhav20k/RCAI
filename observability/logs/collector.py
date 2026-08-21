# Centralized Structured Log Collector
import time
import threading
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class LogEntry(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    service: str
    level: str
    event: str
    message: str
    request_id: str = "none"
    trace_id: str = "none"
    version: str = "1.0.0"
    extra: Dict[str, Any] = Field(default_factory=dict)

class LogCollector:
    def __init__(self, max_buffer_size: int = 10000):
        self.max_buffer_size = max_buffer_size
        self._logs: List[LogEntry] = []
        self._lock = threading.Lock()

    def record_log(self, entry: LogEntry) -> None:
        with self._lock:
            if len(self._logs) >= self.max_buffer_size:
                self._logs.pop(0)
            self._logs.append(entry)

    def query_logs(
        self,
        service: Optional[str] = None,
        level: Optional[str] = None,
        trace_id: Optional[str] = None,
        request_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        with self._lock:
            results: List[LogEntry] = []
            for item in reversed(self._logs):
                if service and item.service != service:
                    continue
                if level and item.level.upper() != level.upper():
                    continue
                if trace_id and item.trace_id != trace_id:
                    continue
                if request_id and item.request_id != request_id:
                    continue
                if start_ts is not None and item.timestamp < start_ts:
                    continue
                if end_ts is not None and item.timestamp > end_ts:
                    continue
                if keyword and (keyword.lower() not in item.message.lower() and keyword.lower() not in item.event.lower()):
                    continue
                results.append(item)
                if len(results) >= limit:
                    break
            return results

    def clear(self) -> None:
        with self._lock:
            self._logs.clear()

global_log_collector = LogCollector()
