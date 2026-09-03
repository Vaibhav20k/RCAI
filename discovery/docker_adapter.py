# Docker Compose Service Auto-Discovery Adapter (Strictly Read-Only)
import os
import re
import time
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
import httpx
from discovery.models import TopologyNode, DiscoveredTopology
from discovery.heuristics import detect_is_db_related
from backend.config import get_settings

logger = logging.getLogger("rcai.discovery.docker")

class DockerDiscoveryAdapter:
    """
    Discovers microservices dynamically by connecting to the local Docker daemon
    via a read-only Unix Domain Socket (/var/run/docker.sock).
    
    NON-NEGOTIABLE SAFETY GUARANTEES:
    - STRICTLY READ-ONLY: Only HTTP GET requests to `/containers/json` and
      `/containers/{id}/json` are ever issued.
    - Zero mutation endpoints: Contains no create, start, stop, kill, exec, or delete calls.
    - Graceful fallback: If the Docker socket is absent, unmounted, or raises permission
      errors, discovery gracefully logs a warning and returns an empty topology.
    """

    def __init__(
        self,
        socket_path: Optional[str] = None,
        timeout_seconds: float = 3.0,
        custom_client: Optional[httpx.Client] = None
    ):
        settings = get_settings()
        self.socket_path = socket_path or settings.DOCKER_SOCKET_PATH
        self.timeout_seconds = timeout_seconds
        self._custom_client = custom_client

    def _get_docker_client(self) -> httpx.Client:
        if self._custom_client is not None:
            return self._custom_client

        if not os.path.exists(self.socket_path):
            raise FileNotFoundError(f"Docker Unix domain socket not found at: {self.socket_path}")

        transport = httpx.HTTPTransport(uds=self.socket_path)
        return httpx.Client(
            transport=transport,
            base_url="http://docker",
            timeout=self.timeout_seconds
        )

    def probe_prometheus_metrics(
        self,
        target_ip: str,
        ports: List[int],
        metrics_path: str = "/metrics",
        probe_client: Optional[httpx.Client] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Probes candidate container ports to determine if a valid Prometheus metrics
        endpoint is actively serving data.
        
        Validation criteria:
        1. HTTP 200 response from GET http://{ip}:{port}{path}
        2. Content-Type containing 'text/plain' or body containing '# HELP' / '# TYPE'
        """
        if not ports or not target_ip:
            return False, None

        # Filter out common DB-only ports from HTTP metrics probing to avoid noisy connection drops
        excluded_ports = {5432, 3306, 6379, 27017, 11211}
        candidate_ports = [p for p in ports if p not in excluded_ports]
        if not candidate_ports:
            candidate_ports = ports

        for port in candidate_ports:
            url = f"http://{target_ip}:{port}{metrics_path}"
            try:
                if probe_client:
                    resp = probe_client.get(url, timeout=2.0)
                else:
                    with httpx.Client(timeout=2.0) as client:
                        resp = client.get(url)

                if resp.status_code == 200:
                    text_sample = resp.text[:1024]
                    if "# HELP" in text_sample or "# TYPE" in text_sample or "promhttp" in text_sample:
                        return True, port
            except Exception:
                continue

        return False, None

    def discover(
        self,
        project_filter: Optional[str] = None,
        probe_metrics: bool = True,
        probe_client: Optional[httpx.Client] = None
    ) -> DiscoveredTopology:
        """
        Enumerates running containers via the Docker Engine API and constructs
        a DiscoveredTopology snapshot.
        """
        try:
            with self._get_docker_client() as client:
                # Strictly READ-ONLY GET request
                resp = client.get("/containers/json?all=false")
                resp.raise_for_status()
                containers = resp.json()
        except Exception as exc:
            logger.warning(f"Docker discovery failed to query socket at {self.socket_path}: {exc}")
            return DiscoveredTopology(nodes={}, discovery_mode="docker")

        discovered_nodes: Dict[str, TopologyNode] = {}

        for c in containers:
            labels = c.get("Labels", {})
            container_id = c.get("Id", "")[:12]
            raw_names = c.get("Names", [])
            container_name = raw_names[0].lstrip("/") if raw_names else container_id
            image_name = c.get("Image", "")

            # Compose service name resolution:
            # 1. Look for standard Docker Compose label 'com.docker.compose.service'
            # 2. Fall back to container name
            service_id = labels.get("com.docker.compose.service")
            if not service_id:
                # Remove common compose suffix e.g. 'myproj_orderservice_1' -> 'orderservice'
                service_id = re.sub(r"^[^_]+_", "", container_name)
                service_id = re.sub(r"_[0-9]+$", "", service_id)

            # Optional project filter (e.g. only discover containers in current compose project)
            c_project = labels.get("com.docker.compose.project")
            if project_filter and c_project and c_project != project_filter:
                continue

            # Extract exposed ports
            exposed_ports: List[int] = []
            for p in c.get("Ports", []):
                private_port = p.get("PrivatePort")
                if private_port and private_port not in exposed_ports:
                    exposed_ports.append(int(private_port))

            # Extract internal container IP address across networks
            net_settings = c.get("NetworkSettings", {}).get("Networks", {})
            container_ip: Optional[str] = None
            for net_name, net_data in net_settings.items():
                ip = net_data.get("IPAddress")
                if ip:
                    container_ip = ip
                    break

            # Infer role and database heuristic
            is_db = detect_is_db_related(
                service_name=service_id,
                container_name=container_name,
                image_name=image_name,
                ports=exposed_ports
            )

            service_type = "service"
            if is_db:
                service_type = "database"
            elif any(g in service_id.lower() for g in ["gateway", "proxy", "ingress", "router"]):
                service_type = "gateway"
            elif any(w in service_id.lower() for w in ["worker", "consumer", "job"]):
                service_type = "worker"

            # Probe for Prometheus metrics if requested and IP is available
            has_metrics = False
            metrics_port = None
            if probe_metrics and container_ip and exposed_ports:
                has_metrics, metrics_port = self.probe_prometheus_metrics(
                    target_ip=container_ip,
                    ports=exposed_ports,
                    metrics_path="/metrics",
                    probe_client=probe_client
                )

            # Format clean human display name
            display_name = " ".join([word.capitalize() for word in service_id.replace("-", " ").replace("_", " ").split()])

            node = TopologyNode(
                service_id=service_id,
                name=display_name,
                service_type=service_type,
                container_id=container_id,
                container_name=container_name,
                ip_address=container_ip,
                ports=exposed_ports,
                metrics_port=metrics_port,
                metrics_path="/metrics",
                has_metrics=has_metrics,
                is_db_related=is_db,
                labels=labels,
                has_fault=False,
                status="HEALTHY"
            )

            discovered_nodes[service_id] = node

        return DiscoveredTopology(
            nodes=discovered_nodes,
            discovery_mode="docker",
            discovered_at=time.time()
        )

    def generate_prometheus_scrape_config(
        self,
        topology: DiscoveredTopology,
        job_name: str = "rcai-discovered-services"
    ) -> str:
        """
        Direct delegate to generate standard Prometheus scrape configuration
        from the discovered topology.
        """
        return topology.generate_prometheus_scrape_config(job_name=job_name)
