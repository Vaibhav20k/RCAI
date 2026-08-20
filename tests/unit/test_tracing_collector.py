# Unit Tests for Distributed Trace Collector
import time
import pytest
from observability.tracing.collector import global_trace_collector, Span

@pytest.fixture(autouse=True)
def clean_traces():
    global_trace_collector.clear()
    yield
    global_trace_collector.clear()

def test_trace_collector_query():
    t = time.time()
    global_trace_collector.record_span(
        Span(trace_id="tr_100", service_name="api-gateway", operation="POST /api/orders", start_time=t, end_time=t+0.05, duration_ms=50.0)
    )
    global_trace_collector.record_span(
        Span(trace_id="tr_100", service_name="order-service", operation="POST /api/v1/orders", start_time=t+0.01, end_time=t+0.04, duration_ms=30.0)
    )
    global_trace_collector.record_span(
        Span(trace_id="tr_200", service_name="payment-service", operation="POST /api/v1/payments", start_time=t+0.1, end_time=t+0.3, duration_ms=200.0, status_code=500, error_message="InternalError")
    )

    # Get single trace spans
    spans_100 = global_trace_collector.get_trace("tr_100")
    assert len(spans_100) == 2

    # Query slow spans (>100ms)
    slow_spans = global_trace_collector.query_spans(min_duration_ms=100.0)
    assert len(slow_spans) == 1
    assert slow_spans[0].trace_id == "tr_200"

    # Query error spans
    err_spans = global_trace_collector.query_spans(only_errors=True)
    assert len(err_spans) == 1
    assert err_spans[0].service_name == "payment-service"
