# Unit Tests for Log Collector
import time
import pytest
from observability.logs.collector import global_log_collector, LogEntry

@pytest.fixture(autouse=True)
def clean_logs():
    global_log_collector.clear()
    yield
    global_log_collector.clear()

def test_log_collector_filtering():
    t0 = time.time()
    global_log_collector.record_log(
        LogEntry(service="order-service", level="INFO", event="order_created", message="Order 101 created", timestamp=t0)
    )
    global_log_collector.record_log(
        LogEntry(service="order-service", level="ERROR", event="db_error", message="Failed query", timestamp=t0+1)
    )
    global_log_collector.record_log(
        LogEntry(service="payment-service", level="WARN", event="high_latency", message="Bank slow", timestamp=t0+2)
    )

    # Filter by service
    orders = global_log_collector.query_logs(service="order-service")
    assert len(orders) == 2

    # Filter by level
    errors = global_log_collector.query_logs(level="ERROR")
    assert len(errors) == 1
    assert errors[0].event == "db_error"

    # Filter by keyword
    bank_logs = global_log_collector.query_logs(keyword="Bank")
    assert len(bank_logs) == 1
