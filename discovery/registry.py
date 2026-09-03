# RCAI Centralized Topology Registry & Discovery Dispatcher
import time
from typing import Set, Dict, Optional
from discovery.models import TopologyNode, DiscoveredTopology
from discovery.docker_adapter import DockerDiscoveryAdapter
from backend.config import get_settings

# Default static 5-service topology for zero-setup simulator and offline benchmark runs
DEFAULT_SIMULATOR_NODES: Dict[str, TopologyNode] = {
    "api-gateway": TopologyNode(
        service_id="api-gateway",
        name="API Gateway",
        service_type="gateway",
        ports=[8000],
        metrics_port=8000,
        has_metrics=True,
        is_db_related=False,
        depends_on=["order-service", "payment-service"]
    ),
    "order-service": TopologyNode(
        service_id="order-service",
        name="Order Service",
        service_type="service",
        ports=[8001],
        metrics_port=8001,
        has_metrics=True,
        is_db_related=False,
        depends_on=["payment-service", "worker-service", "database"]
    ),
    "payment-service": TopologyNode(
        service_id="payment-service",
        name="Payment Service",
        service_type="service",
        ports=[8002],
        metrics_port=8002,
        has_metrics=True,
        is_db_related=False,
        depends_on=["dependency-service", "database"]
    ),
    "dependency-service": TopologyNode(
        service_id="dependency-service",
        name="Partner Bank API",
        service_type="dependency",
        ports=[8003],
        metrics_port=8003,
        has_metrics=True,
        is_db_related=False,
        depends_on=[]
    ),
    "worker-service": TopologyNode(
        service_id="worker-service",
        name="Worker Queue",
        service_type="worker",
        ports=[8004],
        metrics_port=8004,
        has_metrics=True,
        is_db_related=False,
        depends_on=["queue"]
    ),
    "database": TopologyNode(
        service_id="database",
        name="Postgres DB",
        service_type="database",
        ports=[5432],
        metrics_port=None,
        has_metrics=False,
        is_db_related=True,
        depends_on=[]
    ),
    "queue": TopologyNode(
        service_id="queue",
        name="Redis Stream",
        service_type="infrastructure",
        ports=[6379],
        metrics_port=None,
        has_metrics=False,
        is_db_related=True,
        depends_on=[]
    )
}

_active_topology: Optional[DiscoveredTopology] = None

def get_default_simulator_topology() -> DiscoveredTopology:
    """Constructs the standard default simulator topology."""
    return DiscoveredTopology(
        nodes=dict(DEFAULT_SIMULATOR_NODES),
        discovery_mode="simulator",
        discovered_at=time.time()
    )

def get_current_topology() -> DiscoveredTopology:
    """
    Returns the active system topology according to the configured RCAI_DISCOVERY_MODE.
    - 'docker': Dynamically queries Docker daemon if no cached topology exists.
    - 'none' (default): Returns the simulator / baseline 5-service topology.
    """
    global _active_topology
    if _active_topology is not None:
        return _active_topology

    settings = get_settings()
    if settings.RCAI_DISCOVERY_MODE == "docker":
        adapter = DockerDiscoveryAdapter()
        discovered = adapter.discover()
        if discovered.nodes:
            _active_topology = discovered
            return _active_topology

    return get_default_simulator_topology()

def get_current_topology_services() -> Set[str]:
    """
    Returns the set of recognized service identifiers from the current topology.
    Acts as the single source of truth for Policy Gate validation and Alert Ingestion.
    """
    return get_current_topology().get_service_names()

def set_active_topology(topology: DiscoveredTopology) -> None:
    """Overrides the active topology (used in tests and dynamic discovery refresh)."""
    global _active_topology
    _active_topology = topology

def reset_active_topology() -> None:
    """Resets the cached active topology to default."""
    global _active_topology
    _active_topology = None

def is_service_db_related(service_name: str) -> bool:
    """
    Determines whether a service has database or datastore capabilities/dependencies
    in the active topology. Used to gate optimize_db_index playbook proposal.
    """
    if not service_name:
        return False
    topo = get_current_topology()
    node = topo.get_node(service_name)
    if node:
        if node.is_db_related:
            return True
        if any("database" in dep or "db" in dep for dep in node.depends_on):
            return True

    # Simulator defaults: order-service and payment-service interact directly with PostgreSQL
    if service_name in ["database", "postgres", "order-service", "payment-service"]:
        return True

    return False

def is_service_queue_related(service_name: str) -> bool:
    """
    Determines whether a service is asynchronous worker or message queue related
    in the active topology. Used for queue backlog hypothesis seeding.
    """
    if not service_name:
        return False
    topo = get_current_topology()
    node = topo.get_node(service_name)
    if node:
        if node.service_type == "worker":
            return True
        if any("queue" in dep or "stream" in dep for dep in node.depends_on):
            return True

    # Simulator defaults: worker-service and order-service interact with Redis stream
    if service_name in ["worker-service", "queue", "order-service"]:
        return True

    return False

