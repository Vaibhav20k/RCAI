# Thread-Safe Fault Injector Interceptor
import time
import random
import threading
from typing import Dict, Optional, List
from simulator.faults.models import FaultConfig, FaultType

class FaultInjector:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._lock = threading.Lock()
        self._active_faults: Dict[FaultType, FaultConfig] = {}

    def set_fault(self, fault: FaultConfig) -> None:
        with self._lock:
            if fault.enabled:
                self._active_faults[fault.fault_type] = fault
            else:
                self._active_faults.pop(fault.fault_type, None)

    def clear_faults(self) -> None:
        with self._lock:
            self._active_faults.clear()

    def get_active_faults(self) -> List[FaultConfig]:
        with self._lock:
            return list(self._active_faults.values())

    def apply_pre_request_faults(self) -> Optional[int]:
        # Returns HTTP error status code if error fault triggers, else None
        with self._lock:
            faults = list(self._active_faults.values())

        for fault in faults:
            if not fault.enabled:
                continue

            # Injected latency
            if fault.latency_ms > 0:
                time.sleep(fault.latency_ms / 1000.0)

            # CPU Burn simulation
            if fault.cpu_burn_ms > 0:
                end_time = time.perf_counter() + (fault.cpu_burn_ms / 1000.0)
                while time.perf_counter() < end_time:
                    pass  # Active spin to consume CPU cycle

            # Error injection
            if fault.error_rate > 0:
                if random.random() < fault.error_rate:
                    return int(fault.parameters.get("http_status", 500))

        return None

    def get_db_delay_seconds(self) -> float:
        with self._lock:
            for fault in self._active_faults.values():
                if fault.enabled and fault.fault_type == FaultType.DATABASE_REGRESSION:
                    return fault.db_query_delay_ms / 1000.0
        return 0.0
