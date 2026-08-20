# Metrics Collector & Query Engine
import time
from typing import Dict, Any, List, Optional
from prometheus_client import CollectorRegistry
from simulator.services.runner import InProcessCluster

class MetricsCollector:
    def __init__(self, cluster: Optional[InProcessCluster] = None):
        self.cluster = cluster

    def set_cluster(self, cluster: InProcessCluster) -> None:
        self.cluster = cluster

    def query_service_metrics(self, service_name: str) -> Dict[str, Any]:
        if not self.cluster:
            return {"error": "Cluster not bound"}
        service_map = self.cluster.get_service_map()
        if service_name not in service_map:
            return {"error": f"Unknown service: {service_name}"}
        
        service_obj = service_map[service_name]
        
        # Synchronize active fault gauge before collecting
        active_count = len(service_obj.fault_injector.get_active_faults())
        service_obj.active_faults_gauge.labels(service=service_name).set(active_count)

        metric_families = list(service_obj.registry.collect())
        parsed_metrics: Dict[str, Any] = {
            "service": service_name,
            "timestamp": time.time(),
            "counters": {},
            "histograms": {},
            "gauges": {}
        }
        
        for family in metric_families:
            for sample in family.samples:
                name = sample.name
                labels = sample.labels
                val = sample.value
                
                if family.type == "counter":
                    parsed_metrics["counters"][name] = {"value": val, "labels": labels}
                elif family.type == "gauge":
                    parsed_metrics["gauges"][name] = {"value": val, "labels": labels}
                elif family.type == "histogram":
                    if name not in parsed_metrics["histograms"]:
                        parsed_metrics["histograms"][name] = []
                    parsed_metrics["histograms"][name].append({"value": val, "labels": labels})
                    
        return parsed_metrics

    def calculate_service_health_stats(self, service_name: str) -> Dict[str, Any]:
        raw = self.query_service_metrics(service_name)
        if "error" in raw:
            return raw

        total_reqs = 0.0
        error_reqs = 0.0
        
        for k, v in raw.get("counters", {}).items():
            if "http_requests_total" in k:
                total_reqs += v.get("value", 0.0)
                status = str(v.get("labels", {}).get("status_code", "200"))
                if status.startswith("5") or status.startswith("4"):
                    error_reqs += v.get("value", 0.0)

        error_rate = round(error_reqs / total_reqs, 4) if total_reqs > 0 else 0.0
        active_faults = raw.get("gauges", {}).get("active_faults_count", {}).get("value", 0.0)
        
        return {
            "service": service_name,
            "total_requests": total_reqs,
            "error_requests": error_reqs,
            "error_rate": error_rate,
            "active_faults": active_faults
        }
