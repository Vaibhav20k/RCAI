# Machine-Readable Benchmark Scenario Taxonomy and Category Registry for RCAI v2
from enum import Enum
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

class ScenarioFamily(str, Enum):
    DATABASE = "database"
    DEPLOYMENT = "deployment"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    QUEUE = "queue"
    PAYMENT = "payment"
    ADVERSARIAL = "adversarial"

class ScenarioDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    ADVERSARIAL = "ADVERSARIAL"

class DatasetSplit(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    VALIDATION = "VALIDATION"
    HELD_OUT_TEST = "HELD_OUT_TEST"

class TaxonomyEntry(BaseModel):
    scenario_id: str
    family: ScenarioFamily
    variant: str
    difficulty: ScenarioDifficulty
    split: DatasetSplit = DatasetSplit.DEVELOPMENT
    ground_truth_root_cause: str
    root_cause_service: str
    root_cause_category: str
    required_evidence: List[str] = Field(default_factory=list)
    allowed_actions: List[str] = Field(default_factory=list)
    expected_outcome: str = "RESOLVED"
    payment_domain: bool = False
    adversarial: bool = False

class TaxonomyRegistry:
    def __init__(self):
        self._entries: Dict[str, TaxonomyEntry] = {}

    def register(self, entry: TaxonomyEntry) -> None:
        if entry.scenario_id in self._entries:
            raise ValueError(f"Duplicate scenario_id: {entry.scenario_id}")
        self._entries[entry.scenario_id] = entry

    def get(self, scenario_id: str) -> Optional[TaxonomyEntry]:
        return self._entries.get(scenario_id)

    def list_all(self) -> List[TaxonomyEntry]:
        return list(self._entries.values())

    def get_by_family(self, family: ScenarioFamily) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.family == family]

    def get_by_split(self, split: DatasetSplit = DatasetSplit.DEVELOPMENT) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.split == split]

    def get_payment_scenarios(self) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.payment_domain]

    def get_adversarial_scenarios(self) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.adversarial]

    def get_held_out_scenarios(self) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.split == DatasetSplit.HELD_OUT_TEST]

    def validate_integrity(self) -> None:
        seen_ids: Set[str] = set()
        for e in self._entries.values():
            if e.scenario_id in seen_ids:
                raise ValueError(f"Duplicate ID: {e.scenario_id}")
            seen_ids.add(e.scenario_id)

global_taxonomy = TaxonomyRegistry()

# 1. DATABASE FAMILY (5)
for sid, var, diff, srv in [
    ("scenario_db_regression_order", "unindexed_query_latency", ScenarioDifficulty.EASY, "order-service"),
    ("scenario_db_pool_exhaustion", "connection_pool_exhaustion", ScenarioDifficulty.MEDIUM, "payment-service"),
    ("scenario_db_lock_contention", "row_level_lock_contention", ScenarioDifficulty.HARD, "order-service"),
    ("scenario_db_connection_timeout", "tcp_socket_timeout", ScenarioDifficulty.HARD, "payment-service"),
    ("scenario_db_partial_degradation", "read_replica_lag", ScenarioDifficulty.MEDIUM, "order-service"),
]:
    global_taxonomy.register(TaxonomyEntry(
        scenario_id=sid, family=ScenarioFamily.DATABASE, variant=var, difficulty=diff,
        split=DatasetSplit.DEVELOPMENT, ground_truth_root_cause=f"Database fault on {srv}",
        root_cause_service=srv, root_cause_category="database",
        required_evidence=["query_db_metrics"], allowed_actions=["optimize_db_index", "restart_workers"],
        expected_outcome="RESOLVED", payment_domain=("payment" in srv), adversarial=False
    ))

# 2. DEPLOYMENT FAMILY (5)
for sid, var, diff, srv in [
    ("scenario_bad_deploy_payment", "bad_release_v241", ScenarioDifficulty.EASY, "payment-service"),
    ("scenario_deploy_partial_canary", "canary_rollout_failure", ScenarioDifficulty.MEDIUM, "payment-service"),
    ("scenario_deploy_config_drift", "bad_environment_variable", ScenarioDifficulty.HARD, "order-service"),
    ("scenario_deploy_feature_flag_regression", "feature_flag_activation_error", ScenarioDifficulty.MEDIUM, "order-service"),
    ("scenario_deploy_schema_migration_mismatch", "orm_schema_mismatch", ScenarioDifficulty.HARD, "payment-service"),
]:
    global_taxonomy.register(TaxonomyEntry(
        scenario_id=sid, family=ScenarioFamily.DEPLOYMENT, variant=var, difficulty=diff,
        split=DatasetSplit.DEVELOPMENT, ground_truth_root_cause=f"Deployment regression on {srv}",
        root_cause_service=srv, root_cause_category="deployment",
        required_evidence=["inspect_deployment_history", "compare_versions"], allowed_actions=["rollback_version"],
        expected_outcome="RESOLVED", payment_domain=("payment" in srv), adversarial=False
    ))

# 3. DEPENDENCY FAMILY (5)
for sid, var, diff, srv in [
    ("scenario_dependency_latency_bank", "partner_bank_latency", ScenarioDifficulty.EASY, "dependency-service"),
    ("scenario_dependency_timeout", "partner_hard_timeout", ScenarioDifficulty.MEDIUM, "dependency-service"),
    ("scenario_dependency_503_flap", "intermittent_503_flapping", ScenarioDifficulty.HARD, "dependency-service"),
    ("scenario_dependency_retry_storm", "retry_storm_amplification", ScenarioDifficulty.HARD, "dependency-service"),
    ("scenario_dependency_circuit_breaker_open", "fast_fail_circuit_breaker", ScenarioDifficulty.MEDIUM, "dependency-service"),
]:
    global_taxonomy.register(TaxonomyEntry(
        scenario_id=sid, family=ScenarioFamily.DEPENDENCY, variant=var, difficulty=diff,
        split=DatasetSplit.DEVELOPMENT, ground_truth_root_cause=f"Dependency fault on {srv}",
        root_cause_service=srv, root_cause_category="dependency",
        required_evidence=["inspect_dependency_health"], allowed_actions=["circuit_breaker"],
        expected_outcome="RESOLVED", payment_domain=True, adversarial=False
    ))

# 4. RESOURCE FAMILY (5)
for sid, var, diff, srv in [
    ("scenario_resource_saturation_gateway", "cpu_saturation", ScenarioDifficulty.EASY, "api-gateway"),
    ("scenario_resource_memory_leak", "heap_memory_leak", ScenarioDifficulty.MEDIUM, "api-gateway"),
    ("scenario_resource_thread_starvation", "thread_pool_starvation", ScenarioDifficulty.HARD, "api-gateway"),
    ("scenario_resource_io_throttling", "disk_io_throttling", ScenarioDifficulty.MEDIUM, "api-gateway"),
    ("scenario_resource_fd_exhaustion", "file_descriptor_exhaustion", ScenarioDifficulty.HARD, "api-gateway"),
]:
    global_taxonomy.register(TaxonomyEntry(
        scenario_id=sid, family=ScenarioFamily.RESOURCE, variant=var, difficulty=diff,
        split=DatasetSplit.DEVELOPMENT, ground_truth_root_cause=f"Resource saturation on {srv}",
        root_cause_service=srv, root_cause_category="resource",
        required_evidence=["query_metrics"], allowed_actions=["scale_workers", "restart_workers"],
        expected_outcome="RESOLVED", payment_domain=False, adversarial=False
    ))

# 5. QUEUE FAMILY (5)
for sid, var, diff, srv in [
    ("scenario_queue_backlog_worker", "consumer_backlog", ScenarioDifficulty.EASY, "worker-service"),
    ("scenario_queue_poison_pill", "poison_pill_deadletter", ScenarioDifficulty.HARD, "worker-service"),
    ("scenario_queue_burst_backlog", "producer_burst_spike", ScenarioDifficulty.MEDIUM, "worker-service"),
    ("scenario_queue_stuck_consumer", "consumer_thread_deadlock", ScenarioDifficulty.HARD, "worker-service"),
    ("scenario_queue_partition_lag", "partition_rebalance_lag", ScenarioDifficulty.MEDIUM, "worker-service"),
]:
    global_taxonomy.register(TaxonomyEntry(
        scenario_id=sid, family=ScenarioFamily.QUEUE, variant=var, difficulty=diff,
        split=DatasetSplit.DEVELOPMENT, ground_truth_root_cause=f"Queue backlog on {srv}",
        root_cause_service=srv, root_cause_category="queue",
        required_evidence=["inspect_service_health"], allowed_actions=["restart_workers", "scale_workers"],
        expected_outcome="RESOLVED", payment_domain=False, adversarial=False
    ))
