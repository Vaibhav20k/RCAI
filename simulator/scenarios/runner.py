# Scenario Execution Runner
import time
from typing import Dict, Any, Optional
from benchmark.scenarios.models import ScenarioDefinition
from simulator.services.runner import InProcessCluster
from simulator.traffic.generator import TrafficGenerator
from observability.deployments.store import global_deployment_store, DeploymentRecord

class ScenarioRunner:
    def __init__(self, cluster: InProcessCluster):
        self.cluster = cluster

    def execute_scenario(self, scenario: ScenarioDefinition) -> Dict[str, Any]:
        # 1. Reset cluster and deployment store
        self.cluster.clear_all_faults()
        global_deployment_store.reset()
        start_ts = time.time()

        # 2. Run baseline traffic
        gen = TrafficGenerator(client=self.cluster.gateway_client, seed=42)
        baseline_stats = gen.generate_batch(count=scenario.baseline_traffic_count)

        # 3. Inject deployment event if specified
        if scenario.deployment_event:
            ev_data = scenario.deployment_event
            record = DeploymentRecord(
                deployment_id=ev_data.get("deployment_id", "dep_scenario"),
                service=ev_data["service"],
                version=ev_data.get("version", "2.0.0"),
                previous_version=ev_data.get("previous_version", "1.0.0"),
                config_version="v2",
                deployed_at=time.time(),
                change_description=ev_data.get("change_description", "Scenario deployment")
            )
            global_deployment_store.record_deployment(record)

        # 4. Inject Fault
        target_service = self.cluster.get_service_map().get(scenario.fault_config.service_name)
        if target_service:
            target_service.fault_injector.set_fault(scenario.fault_config)

        # 5. Run incident traffic
        incident_stats = gen.generate_batch(count=scenario.incident_traffic_count)
        end_ts = time.time()

        return {
            "scenario_id": scenario.scenario_id,
            "service": scenario.service,
            "ground_truth": scenario.ground_truth.model_dump(),
            "started_at": start_ts,
            "ended_at": end_ts,
            "baseline_stats": baseline_stats.model_dump(),
            "incident_stats": incident_stats.model_dump()
        }
