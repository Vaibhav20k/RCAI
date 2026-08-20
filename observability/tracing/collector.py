# Distributed Tracing Collector and Span Store
import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class Span(BaseModel):
    span_id: str = Field(default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}")
    trace_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    operation: str
    start_time: float
    end_time: float
    duration_ms: float
    status_code: int = 200
    attributes: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

class TraceCollector:
    def __init__(self, max_spans: int = 5000):
        self.max_spans = max_spans
        self._spans: List[Span] = []
        self._lock = threading.Lock()

    def record_span(self, span: Span) -> None:
        with self._lock:
            if len(self._spans) >= self.max_spans:
                self._spans.pop(0)
            self._spans.append(span)

    def get_trace(self, trace_id: str) -> List[Span]:
        with self._lock:
            return [s for s in self._spans if s.trace_id == trace_id]

    def query_spans(
        self,
        service: Optional[str] = None,
        min_duration_ms: Optional[float] = None,
        only_errors: bool = False,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
        limit: int = 100
    ) -> List[Span]:
        with self._lock:
            matched: List[Span] = []
            for s in reversed(self._spans):
                if service and s.service_name != service:
                    continue
                if min_duration_ms is not None and s.duration_ms < min_duration_ms:
                    continue
                if only_errors and (s.status_code < 400 and not s.error_message):
                    continue
                if start_ts is not None and s.start_time < start_ts:
                    continue
                if end_ts is not None and s.end_time > end_ts:
                    continue
                matched.append(s)
                if len(matched) >= limit:
                    break
            return matched

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()

global_trace_collector = TraceCollector()
