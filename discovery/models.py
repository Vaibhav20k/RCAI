# RCAI Auto-Discovery Topology Models
import time
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field

class TopologyNode(BaseModel):
    """
    Generic representation of a service node in the system topology.
    Can originate from Docker Compose auto-discovery, Kubernetes discovery,
    or the in-process fallback simulator.
    """
    service_id: str = Field(description="Canonical unique identifier for the service (e.g. 'order-service')")
    name: str = Field(description="Human-readable display name for UI presentation")
    service_type: str = Field(default="service", description="Role: 'gateway', 'service', 'worker', 'database', 'infrastructure', 'dependency'")
    container_id: Optional[str] = Field(default=None, description="Docker container ID if discovered via Docker")
    container_name: Optional[str] = Field(default=None, description="Docker container name if discovered via Docker")
    ip_address: Optional[str] = Field(default=None, description="Internal network IP address")
    ports: List[int] = Field(default_factory=list, description="All exposed or mapped ports")
    metrics_port: Optional[int] = Field(default=None, description="Port exposing Prometheus metrics")
    metrics_path: str = Field(default="/metrics", description="HTTP path for scraping metrics")
    has_metrics: bool = Field(default=False, description="True if a valid Prometheus format (# HELP/# TYPE) endpoint was verified")
    is_db_related: bool = Field(default=False, description="True if detected as database or cache engine (gates optimize_db_index)")
    depends_on: List[str] = Field(default_factory=list, description="Downstream service dependencies if known")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metadata tags / Docker Compose labels")
    has_fault: bool = Field(default=False, description="True if active incident/fault is present on this node")
    status: str = Field(default="HEALTHY", description="'HEALTHY', 'FAULT', or 'DEGRADED'")

    @property
    def is_instrumented(self) -> bool:
        """Alias indicating whether this node has verified scrapeable telemetry."""
        return self.has_metrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.service_id,
            "name": self.name,
            "type": self.service_type,
            "container_id": self.container_id,
            "container_name": self.container_name,
            "ip_address": self.ip_address,
            "ports": self.ports,
            "metrics_port": self.metrics_port,
            "metrics_path": self.metrics_path,
            "has_metrics": self.has_metrics,
            "is_instrumented": self.is_instrumented,
            "is_db_related": self.is_db_related,
            "depends_on": self.depends_on,
            "labels": self.labels,
            "has_fault": self.has_fault,
            "status": self.status
        }

class DiscoveredTopology(BaseModel):
    """
    Immutable snapshot of the system's discovered infrastructure topology.
    """
    nodes: Dict[str, TopologyNode] = Field(default_factory=dict)
    discovery_mode: str = Field(default="none", description="'docker', 'kubernetes', or 'none'")
    discovered_at: float = Field(default_factory=time.time)

    def get_service_names(self) -> Set[str]:
        """Returns the set of all recognized service identifiers."""
        return set(self.nodes.keys())

    def get_node(self, service_id: str) -> Optional[TopologyNode]:
        return self.nodes.get(service_id)

    def get_instrumented_nodes(self) -> List[TopologyNode]:
        """Returns all nodes that expose a verified scrapeable metrics endpoint."""
        return [node for node in self.nodes.values() if node.has_metrics]

    def get_uninstrumented_nodes(self) -> List[TopologyNode]:
        """Returns nodes discovered but lacking Prometheus telemetry."""
        return [node for node in self.nodes.values() if not node.has_metrics]

    def generate_prometheus_scrape_config(self, job_name: str = "rcai-discovered-services") -> str:
        """
        Auto-generates a standard Prometheus scrape_configs YAML snippet
        from all instrumented nodes in this topology.
        """
        instrumented = self.get_instrumented_nodes()
        if not instrumented:
            return f"""# No instrumented services discovered
scrape_configs:
  - job_name: '{job_name}'
    static_configs: []
"""

        lines = [
            f"# RCAI Auto-Generated Prometheus Scrape Config ({len(instrumented)} targets)",
            "scrape_configs:",
            f"  - job_name: '{job_name}'",
            "    metrics_path: '/metrics'",
            "    static_configs:"
        ]

        for node in instrumented:
            target_host = node.ip_address or "127.0.0.1"
            target_port = node.metrics_port or (node.ports[0] if node.ports else 80)
            lines.append(f"      - targets: ['{target_host}:{target_port}']")
            lines.append("        labels:")
            lines.append(f"          service: '{node.service_id}'")
            lines.append(f"          rcai_discovered: 'true'")
            if node.is_db_related:
                lines.append("          role: 'database'")

        return "\n".join(lines) + "\n"
