# Formal Scenario Taxonomy & Machine-Readable Registry for RCAI v2
from enum import Enum
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

class ScenarioFamily(str, Enum):
    DATABASE = "DATABASE"
    DEPLOYMENT = "DEPLOYMENT"
    DEPENDENCY = "DEPENDENCY"
    RESOURCE = "RESOURCE"
    QUEUE = "QUEUE"
    PAYMENT = "PAYMENT"
    ADVERSARIAL = "ADVERSARIAL"

class ScenarioDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    COMPOSITIONAL = "COMPOSITIONAL"
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

    def get_entry(self, scenario_id: str) -> Optional[TaxonomyEntry]:
        return self._entries.get(scenario_id)

    def list_all(self) -> List[TaxonomyEntry]:
        return list(self._entries.values())

    def get_by_family(self, family: ScenarioFamily) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.family == family]

    def get_by_split(self, split: DatasetSplit) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.split == split]

    def get_payment_scenarios(self) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.payment_domain]

    def get_adversarial_scenarios(self) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.adversarial]

    def get_held_out_scenarios(self) -> List[TaxonomyEntry]:
        return [e for e in self._entries.values() if e.split == DatasetSplit.HELD_OUT_TEST]

    def validate_integrity(self) -> None:
        seen_ids: Set[str] = set()
        seen_ground_truths: Set[str] = set()
        for e in self._entries.values():
            if e.scenario_id in seen_ids:
                raise ValueError(f"Duplicate ID: {e.scenario_id}")
            seen_ids.add(e.scenario_id)
            gt_key = f"{e.root_cause_service}:{e.root_cause_category}:{e.variant}"
            if gt_key in seen_ground_truths:
                raise ValueError(f"Duplicate ground truth variant: {gt_key}")
            seen_ground_truths.add(gt_key)

# Global Taxonomy Registry Instance
global_taxonomy = TaxonomyRegistry()

# Register initial v1 baseline scenarios
global_taxonomy.register(TaxonomyEntry(
    scenario_id="scenario_db_regression_order",
    family=ScenarioFamily.DATABASE,
    variant="unindexed_query_latency",
    difficulty=ScenarioDifficulty.EASY,
    split=DatasetSplit.DEVELOPMENT,
    ground_truth_root_cause="Database query latency regression in order_service",
    root_cause_service="order-service",
    root_cause_category="database",
    required_evidence=["query_db_metrics"],
    allowed_actions=["optimize_db_index"],
    expected_outcome="RESOLVED",
    payment_domain=False,
    adversarial=False
))

global_taxonomy.register(TaxonomyEntry(
    scenario_id="scenario_bad_deploy_payment",
    family=ScenarioFamily.DEPLOYMENT,
    variant="bad_release_v241_runtime_exception",
    difficulty=ScenarioDifficulty.EASY,
    split=DatasetSplit.DEVELOPMENT,
    ground_truth_root_cause="Buggy deployment v2.4.1 in payment-service causing 100% failure rate",
    root_cause_service="payment-service",
    root_cause_category="deployment",
    required_evidence=["inspect_deployment_history", "compare_versions"],
    allowed_actions=["rollback_version"],
    expected_outcome="RESOLVED",
    payment_domain=True,
    adversarial=False
))

global_taxonomy.register(TaxonomyEntry(
    scenario_id="scenario_dependency_latency_bank",
    family=ScenarioFamily.DEPENDENCY,
    variant="downstream_bank_partner_latency",
    difficulty=ScenarioDifficulty.MEDIUM,
    split=DatasetSplit.DEVELOPMENT,
    ground_truth_root_cause="Downstream partner bank gateway latency degradation",
    root_cause_service="dependency-service",
    root_cause_category="dependency",
    required_evidence=["inspect_dependency_health"],
    allowed_actions=["circuit_breaker"],
    expected_outcome="RESOLVED",
    payment_domain=True,
    adversarial=False
))

global_taxonomy.register(TaxonomyEntry(
    scenario_id="scenario_resource_saturation_gateway",
    family=ScenarioFamily.RESOURCE,
    variant="cpu_burn_spinlock",
    difficulty=ScenarioDifficulty.MEDIUM,
    split=DatasetSplit.DEVELOPMENT,
    ground_truth_root_cause="CPU burn spinlock in api-gateway",
    root_cause_service="api-gateway",
    root_cause_category="resource",
    required_evidence=["query_metrics"],
    allowed_actions=["restart_workers"],
    expected_outcome="RESOLVED",
    payment_domain=False,
    adversarial=False
))

global_taxonomy.register(TaxonomyEntry(
    scenario_id="scenario_queue_backlog_worker",
    family=ScenarioFamily.QUEUE,
    variant="consumer_starvation_backlog",
    difficulty=ScenarioDifficulty.MEDIUM,
    split=DatasetSplit.DEVELOPMENT,
    ground_truth_root_cause="Async worker task queue message accumulation",
    root_cause_service="worker-service",
    root_cause_category="queue",
    required_evidence=["inspect_service_health"],
    allowed_actions=["scale_workers"],
    expected_outcome="RESOLVED",
    payment_domain=False,
    adversarial=False
))
