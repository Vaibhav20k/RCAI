#!/usr/bin/env python3
"""
RCAI Compose Manifest Inspector
Analyzes a docker-compose.yml manifest to discover services, detect database
components, identify Prometheus metrics endpoints, and generate scrape configurations.
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Set

# Attempt yaml import, with safe fallback
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Import heuristics from RCAI discovery package if available
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from discovery.heuristics import detect_is_db_related
except Exception:
    def detect_is_db_related(service_name: str, image_name: str = "", ports: List[int] = None) -> bool:
        combined = f"{service_name.lower()} {image_name.lower()}"
        db_keywords = ["postgres", "pgsql", "mysql", "mariadb", "mongo", "redis", "memcached", "clickhouse", "cassandra"]
        if any(kw in combined for kw in db_keywords):
            return True
        db_ports = {5432, 3306, 6379, 27017, 11211, 9042}
        if ports and any(p in db_ports for p in ports):
            return True
        return False

def parse_compose_file(file_path: Path) -> Dict[str, Any]:
    """Parses a compose YAML file with PyYAML or a fallback line parser."""
    content = file_path.read_text(encoding="utf-8")
    if HAS_YAML:
        return yaml.safe_load(content) or {}
    
    # Fallback minimal YAML parser for services section
    services = {}
    current_service = None
    in_services = False

    for line in content.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        if line.startswith("services:"):
            in_services = True
            continue
        if in_services and not line.startswith(" ") and not line.startswith("\t"):
            in_services = False
        if in_services:
            indent = len(line) - len(line.lstrip())
            if indent == 2 and trimmed.endswith(":"):
                current_service = trimmed[:-1]
                services[current_service] = {"ports": [], "image": ""}
            elif indent > 2 and current_service:
                if trimmed.startswith("image:"):
                    services[current_service]["image"] = trimmed.split("image:")[1].strip()
                elif "ports:" in trimmed:
                    pass
                elif trimmed.startswith("- ") and ":" in trimmed:
                    # port mapping e.g. - "8080:8080"
                    port_part = trimmed[2:].strip().strip('"').strip("'")
                    try:
                        host_port = int(port_part.split(":")[0])
                        services[current_service]["ports"].append(host_port)
                    except ValueError:
                        pass
    return {"services": services}

def extract_service_ports(service_cfg: Dict[str, Any]) -> List[int]:
    """Extracts numeric ports published or exposed by a compose service."""
    ports: List[int] = []
    raw_ports = service_cfg.get("ports", [])
    if isinstance(raw_ports, list):
        for p in raw_ports:
            if isinstance(p, (int, float)):
                ports.append(int(p))
            elif isinstance(p, str):
                parts = p.split(":")
                try:
                    # If format is "host:container" or "ip:host:container"
                    if len(parts) >= 2:
                        host_port = int(parts[-2].split("/")[-1])
                        container_port = int(parts[-1].split("/")[0])
                        ports.extend([host_port, container_port])
                    else:
                        port_val = int(parts[0].split("/")[0])
                        ports.append(port_val)
                except ValueError:
                    pass
            elif isinstance(p, dict):
                published = p.get("published")
                if published and isinstance(published, int):
                    ports.append(published)
                target = p.get("target")
                if target and isinstance(target, int):
                    ports.append(target)
    # Deduplicate while preserving order (host ports first)
    seen = set()
    result = []
    for p in ports:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result

def analyze_compose(compose_path: Path) -> Dict[str, Any]:
    """Analyzes a compose file and returns discovered topology details."""
    data = parse_compose_file(compose_path)
    raw_services = data.get("services", {}) or {}

    all_services: List[str] = []
    db_services: List[str] = []
    metrics_services: List[str] = []
    service_details: List[Dict[str, Any]] = []

    for svc_name, svc_cfg in raw_services.items():
        if not isinstance(svc_cfg, dict):
            svc_cfg = {}
        all_services.append(svc_name)
        image = str(svc_cfg.get("image", ""))
        ports = extract_service_ports(svc_cfg)

        is_db = detect_is_db_related(service_name=svc_name, image_name=image, ports=ports)
        if is_db:
            db_services.append(svc_name)

        # Check for metrics endpoint candidate
        # Standard Prometheus exporter ports or web services
        has_metrics_candidate = False
        common_metrics_ports = {8000, 8001, 8002, 8080, 9090, 9100, 9102, 9187, 3000, 5000}
        if any(p in common_metrics_ports for p in ports) or "metrics" in str(svc_cfg).lower():
            has_metrics_candidate = True
            metrics_services.append(svc_name)

        service_details.append({
            "service": svc_name,
            "image": image,
            "ports": ports,
            "is_db_related": is_db,
            "has_metrics": has_metrics_candidate
        })

    return {
        "compose_file": str(compose_path),
        "total_services": len(all_services),
        "services": all_services,
        "db_services": db_services,
        "metrics_services": metrics_services,
        "service_details": service_details
    }

def generate_prometheus_yaml(analysis: Dict[str, Any]) -> str:
    """Generates standard Prometheus scrape configuration YAML for discovered services."""
    lines = [
        "global:",
        "  scrape_interval: 15s",
        "  evaluation_interval: 15s",
        "",
        "scrape_configs:"
    ]

    for detail in analysis.get("service_details", []):
        svc = detail["service"]
        ports = detail.get("ports", [])
        port = ports[0] if ports else 8000
        lines.extend([
            f"  - job_name: '{svc}'",
            "    metrics_path: /metrics",
            "    static_configs:",
            f"      - targets: ['{svc}:{port}']",
            "        labels:",
            f"          service: '{svc}'",
            "          app: 'rcai-auto-discovery'"
        ])
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser(description="RCAI Compose Manifest Inspector")
    parser.add_argument("-f", "--file", default="docker-compose.yml", help="Path to compose file")
    parser.add_argument("--json", action="store_true", help="Output analysis as JSON")
    parser.add_argument("--write-scrape-config", help="Path to write generated prometheus.yml")
    args = parser.parse_args()

    compose_file = Path(args.file)
    if not compose_file.is_file():
        print(f"Error: Compose file '{args.file}' not found.", file=sys.stderr)
        sys.exit(1)

    analysis = analyze_compose(compose_file)

    if args.write_scrape_config:
        out_path = Path(args.write_scrape_config)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        scrape_yaml = generate_prometheus_yaml(analysis)
        out_path.write_text(scrape_yaml, encoding="utf-8")

    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print(f"Discovered {analysis['total_services']} services: [{', '.join(analysis['services'])}].")
        print(f"{len(analysis['metrics_services'])} have Prometheus metrics endpoints (/metrics).")
        print(f"Database-like services detected: [{', '.join(analysis['db_services']) if analysis['db_services'] else 'none'}].")

if __name__ == "__main__":
    main()
