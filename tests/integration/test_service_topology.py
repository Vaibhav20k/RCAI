# Integration Tests for Service Topology Call Chains
import pytest
from simulator.services.runner import InProcessCluster

@pytest.fixture
def cluster():
    c = InProcessCluster()
    yield c
    c.clear_all_faults()

def test_end_to_end_order_creation_topology(cluster):
    # Gateway -> Order -> Payment -> Dependency (Bank)
    resp = cluster.gateway_client.post(
        "/api/orders",
        json={
            "user_id": "usr_integration_1",
            "items": ["laptop_stand", "usb_hub"],
            "total_amount": 2499.0,
            "currency": "INR"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CREATED"
    assert data["order"]["payment_status"] == "SUCCESS"
    assert data["order"]["user_id"] == "usr_integration_1"

def test_end_to_end_payment_processing_topology(cluster):
    # Gateway -> Payment -> Dependency (Bank)
    resp = cluster.gateway_client.post(
        "/api/payments",
        json={
            "order_id": "ord_direct_778",
            "user_id": "usr_integration_2",
            "amount": 499.0,
            "currency": "INR",
            "payment_method": "UPI"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["order_id"] == "ord_direct_778"
    assert "auth_code" in data

def test_worker_queue_service_push_and_status(cluster):
    push_resp = cluster.worker_client.post(
        "/api/v1/queue/push",
        json={
            "task_id": "task_notif_001",
            "task_type": "SEND_RECEIPT",
            "payload": {"email": "user@example.com", "order_id": "ord_123"}
        }
    )
    assert push_resp.status_code == 200
    assert push_resp.json()["status"] == "QUEUED"
    assert push_resp.json()["depth"] == 1

    status_resp = cluster.worker_client.get("/api/v1/queue/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["queue_depth"] == 1
