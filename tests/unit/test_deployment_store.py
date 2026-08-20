# Unit Tests for Deployment Store
import time
import pytest
from observability.deployments.store import global_deployment_store, DeploymentRecord

def test_deployment_store_queries():
    rec = DeploymentRecord(
        deployment_id="dep_order_v2",
        service="order-service",
        version="2.0.0",
        previous_version="1.0.0",
        config_version="v2",
        deployed_at=time.time(),
        status="DEPLOYED",
        change_description="Upgraded Postgres query plan"
    )
    global_deployment_store.record_deployment(rec)

    latest = global_deployment_store.get_latest_deployment("order-service")
    assert latest is not None
    assert latest.version == "2.0.0"

    history = global_deployment_store.get_service_history("order-service")
    assert len(history) >= 2
