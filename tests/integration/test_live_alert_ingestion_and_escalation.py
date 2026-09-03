# Integration Tests for Stage 5: Live Incident Ingestion & SRE Escalation Path
import time
import json
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from backend.api.app import app, incidents_db, investigations_db, reports_db
from backend.ingestion.models import AlertmanagerAlert, AlertmanagerPayload, AlertIngestionResult
from backend.ingestion.normalizer import AlertNormalizer
from backend.escalation.models import EscalationBrief
from backend.escalation.dispatcher import EscalationDispatcher, global_escalation_dispatcher
from backend.incidents.models import Incident, IncidentSeverity, IncidentStatus
from agent.investigator.state import InvestigationState
from agent.hypothesis.models import HypothesisSet, Hypothesis, HypothesisCategory
from agent.verification.models import RootCauseDecision, IncidentReport
from backend.config import reset_settings
from discovery.registry import reset_active_topology

@pytest.fixture(autouse=True)
def clean_runtime():
    reset_active_topology()
    reset_settings()
    incidents_db.clear()
    investigations_db.clear()
    reports_db.clear()
    global_escalation_dispatcher.active_escalations.clear()
    yield
    incidents_db.clear()
    investigations_db.clear()
    reports_db.clear()
    global_escalation_dispatcher.active_escalations.clear()
    reset_settings()
    reset_active_topology()

def test_alertmanager_payload_normalization():

    alert = AlertmanagerAlert(
        status="firing",
        labels={
            "alertname": "PaymentServiceElevatedErrors",
            "service": "payment-service",
            "severity": "critical",
            "environment": "production"
        },
        annotations={
            "summary": "High 5xx error rate on payment transactions",
            "description": "5xx error rate exceeded 20% over 5m window"
        },
        startsAt="2026-09-01T20:00:00Z",
        fingerprint="fp_payment_err_01"
    )

    inc = AlertNormalizer.normalize_alertmanager_alert(alert)

    assert inc.service == "payment-service"
    assert inc.severity == IncidentSeverity.CRITICAL
    assert "PaymentServiceElevatedErrors" in inc.symptom
    assert "exceeded 20%" in inc.symptom
    assert inc.status == IncidentStatus.DETECTED
    assert inc.started_at > 0
    assert inc.incident_window["start_ts"] < inc.incident_window["end_ts"]

def test_alertmanager_service_resolution_fallback():
    # Service not in labels, but present in alertname
    alert1 = AlertmanagerAlert(
        status="firing",
        labels={"alertname": "OrderServiceHighLatency", "severity": "high"},
        annotations={"description": "p99 latency > 200ms"}
    )
    assert AlertNormalizer.resolve_target_service(alert1) == "order-service"

    # Service mentioned in description
    alert2 = AlertmanagerAlert(
        status="firing",
        labels={"alertname": "WorkerQueueStalled", "severity": "medium"},
        annotations={"description": "worker-service queue consumer is not processing messages"}
    )
    assert AlertNormalizer.resolve_target_service(alert2) == "worker-service"

def test_alertmanager_webhook_ingestion_and_auto_investigation():
    client = TestClient(app)
    payload = {
        "version": "4",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "DatabaseSlowQueries",
                    "service": "order-service",
                    "severity": "high"
                },
                "annotations": {
                    "summary": "Database latency spiked above 100ms",
                    "description": "Order service database query latency is degrading checkout flow"
                },
                "startsAt": "2026-09-01T21:00:00Z",
                "fingerprint": "fp_db_slow_01"
            }
        ]
    }

    resp = client.post("/api/alerts/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "PROCESSED"
    assert data["total_alerts_received"] == 1
    assert len(data["incidents_created"]) == 1
    assert len(data["investigations_started"]) == 1

    created_id = data["incidents_created"][0]
    assert created_id in incidents_db
    assert created_id in investigations_db
    assert created_id in reports_db

def test_alertmanager_webhook_deduplication():
    client = TestClient(app)
    alert_dict = {
        "status": "firing",
        "labels": {"alertname": "HighCPU", "service": "api-gateway", "severity": "medium"},
        "annotations": {"description": "CPU burn on gateway"},
        "startsAt": "2026-09-01T21:10:00Z"
    }
    payload = {"version": "4", "alerts": [alert_dict]}

    # 1. First alert creates incident
    res1 = client.post("/api/alerts/webhook", json=payload).json()
    assert len(res1["incidents_created"]) == 1
    assert res1["duplicates_skipped"] == 0

    # Mark active
    inc_id = res1["incidents_created"][0]
    incidents_db[inc_id].status = IncidentStatus.INVESTIGATING

    # 2. Second alert for same active service is skipped
    res2 = client.post("/api/alerts/webhook", json=payload).json()
    assert len(res2["incidents_created"]) == 0
    assert res2["duplicates_skipped"] == 1

def test_alertmanager_webhook_authentication_enforcement():
    import os, base64
    client = TestClient(app)
    alert_payload = {
        "version": "4",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "AuthTestAlert", "service": "worker-service"},
                "annotations": {"description": "Worker queue backlog"},
                "startsAt": "2026-09-01T21:15:00Z"
            }
        ]
    }

    with patch.dict(os.environ, {"ALERTMANAGER_WEBHOOK_SECRET": "my-super-secret-token"}):
        reset_settings()

        # 1. Missing auth returns 401 Unauthorized
        res_no_auth = client.post("/api/alerts/webhook", json=alert_payload)
        assert res_no_auth.status_code == 401
        assert "Invalid or missing Alertmanager webhook" in res_no_auth.json()["detail"]

        # 2. Wrong auth returns 401 Unauthorized
        res_wrong = client.post(
            "/api/alerts/webhook",
            json=alert_payload,
            headers={"Authorization": "Bearer wrong-secret"}
        )
        assert res_wrong.status_code == 401

        # 3. Valid Bearer Token header returns 200
        res_bearer = client.post(
            "/api/alerts/webhook",
            json=alert_payload,
            headers={"Authorization": "Bearer my-super-secret-token"}
        )
        assert res_bearer.status_code == 200
        assert res_bearer.json()["total_alerts_received"] == 1

        # 4. Valid Custom Header X-Alertmanager-Secret returns 200
        res_custom = client.post(
            "/api/alerts/webhook",
            json=alert_payload,
            headers={"X-Alertmanager-Secret": "my-super-secret-token"}
        )
        assert res_custom.status_code == 200

        # 5. Valid Basic Auth header returns 200
        basic_creds = base64.b64encode(b"alertmanager:my-super-secret-token").decode()
        res_basic = client.post(
            "/api/alerts/webhook",
            json=alert_payload,
            headers={"Authorization": f"Basic {basic_creds}"}
        )
        assert res_basic.status_code == 200

        # 6. Valid Query Parameter returns 200
        res_query = client.post(
            "/api/alerts/webhook?secret=my-super-secret-token",
            json=alert_payload
        )
        assert res_query.status_code == 200

def test_escalation_dispatcher_slack_and_pagerduty_dispatch():
    dispatcher = EscalationDispatcher(
        slack_webhook_url="https://hooks.slack.com/services/T00/B00/X00",
        pagerduty_webhook_url="https://events.pagerduty.com/v2/enqueue"
    )

    now = time.time()
    inc = Incident(
        incident_id="inc_esc_01",
        scenario_id="sc_01",
        service="payment-service",
        symptom="Payment gateway timeout",
        severity=IncidentSeverity.CRITICAL,
        status=IncidentStatus.INVESTIGATING
    )

    hypo_set = HypothesisSet(incident_id=inc.incident_id)
    hypo_set.add_hypothesis(
        Hypothesis(
            incident_id=inc.incident_id,
            target_service="payment-service",
            category=HypothesisCategory.DEPENDENCY,
            description="Partner bank timeout",
            confidence=0.45
        )
    )

    state = InvestigationState(
        investigation_id="inv_esc_01",
        incident=inc.to_agent_view(),
        hypothesis_set=hypo_set
    )

    brief = dispatcher.build_brief(
        incident=inc,
        investigation_state=state,
        reason="Ambiguous telemetry signals between bank API and payment worker"
    )

    assert brief.incident_id == "inc_esc_01"
    assert brief.service == "payment-service"
    assert len(brief.top_hypotheses) == 1
    assert "Ambiguous telemetry" in brief.escalation_reason

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        dispatch_res = dispatcher.dispatch_escalation(brief, incident=inc)

        assert dispatch_res["status"] == "DISPATCHED"
        assert "slack" in dispatch_res["channels"]
        assert "pagerduty" in dispatch_res["channels"]
        assert inc.status == IncidentStatus.ESCALATED
        assert "inc_esc_01" in dispatcher.active_escalations

def test_escalation_api_endpoints():
    client = TestClient(app)

    # Populate an escalation
    brief = EscalationBrief(
        incident_id="inc_esc_api_test",
        service="order-service",
        severity=IncidentSeverity.HIGH,
        symptom="DB connection pool exhausted",
        escalation_reason="All automated remediation playbooks exhausted",
        recommended_sre_actions=["Inspect DB connection pool metrics", "Kill long-running transactions"]
    )
    global_escalation_dispatcher.active_escalations[brief.incident_id] = brief

    # 1. GET /api/escalations
    res_list = client.get("/api/escalations")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert len(data_list["escalations"]) >= 1
    assert any(e["incident_id"] == "inc_esc_api_test" for e in data_list["escalations"])

    # 2. GET /api/escalations/{incident_id}
    res_single = client.get("/api/escalations/inc_esc_api_test")
    assert res_single.status_code == 200
    assert res_single.json()["service"] == "order-service"
    assert "DB connection pool exhausted" in res_single.json()["symptom"]

    # 3. GET unknown
    res_404 = client.get("/api/escalations/inc_nonexistent")
    assert res_404.status_code == 404
