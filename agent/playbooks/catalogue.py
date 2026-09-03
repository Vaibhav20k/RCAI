# Fixed, Versioned Deterministic Remediation Playbook Catalogue
from typing import Dict, Any, List, Optional, Tuple
from agent.playbooks.models import PlaybookDefinition
from agent.policies.models import RemediationActionType, RemediationRiskLevel
from agent.hypothesis.models import HypothesisCategory
from discovery.registry import get_current_topology_services, is_service_db_related

class PlaybookCatalogue:

    def __init__(self):
        self._catalogue: Dict[str, PlaybookDefinition] = {}
        self._register_default_playbooks()

    def _register_default_playbooks(self) -> None:
        # 1. Database Index Optimization
        self.register_playbook(
            PlaybookDefinition(
                name="optimize_db_index",
                version="1.0.0",
                description="Rebuild and optimize query execution plans and database indexes on the target service schema to resolve slow query regressions.",
                action_type=RemediationActionType.OPTIMIZE_DB_INDEX,
                required_parameters=["service"],
                optional_parameters={},
                risk_level=RemediationRiskLevel.LOW,
                applicable_categories=[HypothesisCategory.DATABASE],
                reversal_procedure="Drop newly generated temporary index and restore previous planner statistics."
            )
        )

        # 2. Rollback Deployment (Canonical & Alias)
        self.register_playbook(
            PlaybookDefinition(
                name="rollback_deploy",
                version="1.0.0",
                description="Rollback container deployment and release configuration on the target service to the previous verified stable release version.",
                action_type=RemediationActionType.ROLLBACK_DEPLOY,
                required_parameters=["service"],
                optional_parameters={"target_version": "1.0.0"},
                risk_level=RemediationRiskLevel.MEDIUM,
                applicable_categories=[HypothesisCategory.DEPLOYMENT, HypothesisCategory.CONFIG],
                reversal_procedure="Re-deploy the previous release artifact version via CI/CD deployment pipeline."
            )
        )
        self.register_playbook(
            PlaybookDefinition(
                name="rollback_version",
                version="1.0.0",
                description="Alias for rollback_deploy: Revert active software release version on target service to baseline.",
                action_type=RemediationActionType.ROLLBACK_VERSION,
                required_parameters=["service"],
                optional_parameters={"target_version": "1.0.0"},
                risk_level=RemediationRiskLevel.MEDIUM,
                applicable_categories=[HypothesisCategory.DEPLOYMENT, HypothesisCategory.CONFIG],
                reversal_procedure="Re-apply target release version."
            )
        )

        # 3. Restart Service / Worker Processes
        self.register_playbook(
            PlaybookDefinition(
                name="restart_service",
                version="1.0.0",
                description="Gracefully restart container instances or worker processes on the target service to clear memory leaks or thread starvation.",
                action_type=RemediationActionType.RESTART_SERVICE,
                required_parameters=["service"],
                optional_parameters={},
                risk_level=RemediationRiskLevel.LOW,
                applicable_categories=[HypothesisCategory.RESOURCE, HypothesisCategory.QUEUE],
                reversal_procedure="No state rollback required. Run post-restart health check."
            )
        )
        self.register_playbook(
            PlaybookDefinition(
                name="restart_workers",
                version="1.0.0",
                description="Alias for restart_service: Restart worker execution pool on target service.",
                action_type=RemediationActionType.RESTART_WORKERS,
                required_parameters=["service"],
                optional_parameters={},
                risk_level=RemediationRiskLevel.LOW,
                applicable_categories=[HypothesisCategory.RESOURCE, HypothesisCategory.QUEUE],
                reversal_procedure="Run post-restart health check."
            )
        )

        # 4. Scale Replicas / Consumers
        self.register_playbook(
            PlaybookDefinition(
                name="scale_replicas",
                version="1.0.0",
                description="Scale replica count or async message queue consumer concurrency to drain traffic surges and processing backlogs.",
                action_type=RemediationActionType.SCALE_REPLICAS,
                required_parameters=["service"],
                optional_parameters={"replicas": 3},
                risk_level=RemediationRiskLevel.LOW,
                applicable_categories=[HypothesisCategory.QUEUE, HypothesisCategory.RESOURCE],
                reversal_procedure="Scale replica count back down to standard baseline pool allocation."
            )
        )
        self.register_playbook(
            PlaybookDefinition(
                name="scale_workers",
                version="1.0.0",
                description="Alias for scale_replicas: Expand background worker concurrency pool.",
                action_type=RemediationActionType.SCALE_WORKERS,
                required_parameters=["service"],
                optional_parameters={"replicas": 3},
                risk_level=RemediationRiskLevel.LOW,
                applicable_categories=[HypothesisCategory.QUEUE, HypothesisCategory.RESOURCE],
                reversal_procedure="Scale worker replica count back to 1."
            )
        )

        # 5. Dependency Circuit Breaker
        self.register_playbook(
            PlaybookDefinition(
                name="circuit_breaker",
                version="1.0.0",
                description="Engage fast-fail circuit breaker trip thresholds for failing downstream third-party partner dependencies.",
                action_type=RemediationActionType.CIRCUIT_BREAKER,
                required_parameters=["service"],
                optional_parameters={"trip_threshold": 5},
                risk_level=RemediationRiskLevel.MEDIUM,
                applicable_categories=[HypothesisCategory.DEPENDENCY],
                reversal_procedure="Reset circuit breaker to CLOSED state to resume live upstream dependency calls."
            )
        )

        # 6. Flush Cache
        self.register_playbook(
            PlaybookDefinition(
                name="flush_cache",
                version="1.0.0",
                description="Flush stale or corrupted cache partitions and connection handles for the target service.",
                action_type=RemediationActionType.FLUSH_CACHE,
                required_parameters=["service"],
                optional_parameters={},
                risk_level=RemediationRiskLevel.LOW,
                applicable_categories=[HypothesisCategory.DATABASE, HypothesisCategory.RESOURCE],
                reversal_procedure="Re-populate cache entries on subsequent read requests."
            )
        )

        # 7. Toggle Feature Flag
        self.register_playbook(
            PlaybookDefinition(
                name="toggle_feature_flag",
                version="1.0.0",
                description="Toggle runtime feature flag state to disable newly introduced experimental code paths.",
                action_type=RemediationActionType.TOGGLE_FEATURE_FLAG,
                required_parameters=["service", "flag_name"],
                optional_parameters={"state": False},
                risk_level=RemediationRiskLevel.MEDIUM,
                applicable_categories=[HypothesisCategory.DEPLOYMENT, HypothesisCategory.CONFIG],
                reversal_procedure="Revert feature flag state to original setting."
            )
        )

    def register_playbook(self, playbook: PlaybookDefinition) -> None:
        self._catalogue[playbook.name] = playbook

    def get_playbook(self, name: str) -> Optional[PlaybookDefinition]:
        return self._catalogue.get(name)

    def list_playbooks(self) -> List[PlaybookDefinition]:
        return list(self._catalogue.values())

    def get_candidate_playbooks_for_service(self, target_service: str) -> List[PlaybookDefinition]:
        """
        Returns playbooks applicable to the specific target service based on
        its discovered capabilities (e.g. database-related vs generic service).
        """
        is_db = is_service_db_related(target_service)
        candidates = []
        for p in self._catalogue.values():
            if p.name == "optimize_db_index" and not is_db:
                # Explicitly exclude database index optimization for non-DB services
                continue
            candidates.append(p)
        return candidates

    def validate_playbook_selection(
        self,
        action: str,
        target: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        playbook = self.get_playbook(action)
        if not playbook:
            return False, f"Action '{action}' is not in the approved remediation playbook catalogue"

        if not target or target.strip() == "":
            return False, "Target service must be specified for playbook remediation"

        # Validate target service against active topology
        valid_services = get_current_topology_services()
        if target not in valid_services:
            return False, f"Target service '{target}' is not recognized in active microservice topology"

        # Explicit Safety Gate: optimize_db_index must only target services with a DB component
        if action == "optimize_db_index" and not is_service_db_related(target):
            return False, f"Playbook 'optimize_db_index' is not applicable to service '{target}' because it has no database component or signal"

        # Check required parameters (service is provided as target)
        for param in playbook.required_parameters:
            if param == "service":
                continue
            if param not in params:
                return False, f"Playbook '{action}' missing required parameter: '{param}'"

        return True, None

    def get_catalogue_prompt_description(self, target_service: Optional[str] = None) -> str:
        lines = ["Approved Remediation Playbook Catalogue (Select ONLY from this list):"]
        playbooks = self.get_candidate_playbooks_for_service(target_service) if target_service else list(self._catalogue.values())
        for p in playbooks:
            req = ", ".join(p.required_parameters)
            lines.append(f"- {p.name}: {p.description} [Required params: {req}] [Risk: {p.risk_level.value}]")
        return "\n".join(lines)


global_playbook_catalogue = PlaybookCatalogue()
