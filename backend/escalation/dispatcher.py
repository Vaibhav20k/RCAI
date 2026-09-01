# SRE Escalation Dispatcher (Slack, PagerDuty, Webhooks)
import time
from typing import Dict, Any, List, Optional
import httpx
from backend.incidents.models import Incident, IncidentStatus, IncidentSeverity
from agent.investigator.state import InvestigationState
from agent.verification.models import IncidentReport
from backend.escalation.models import EscalationBrief
from backend.config import get_settings

class EscalationDispatcher:
    def __init__(
        self,
        slack_webhook_url: Optional[str] = None,
        pagerduty_webhook_url: Optional[str] = None
    ):
        settings = get_settings()
        self.slack_webhook_url = slack_webhook_url or settings.SLACK_WEBHOOK_URL
        self.pagerduty_webhook_url = pagerduty_webhook_url or settings.PAGERDUTY_WEBHOOK_URL
        self.active_escalations: Dict[str, EscalationBrief] = {}

    def build_brief(
        self,
        incident: Incident,
        investigation_state: Optional[InvestigationState] = None,
        incident_report: Optional[IncidentReport] = None,
        reason: str = "Automated investigation confidence insufficient"
    ) -> EscalationBrief:
        top_hypotheses = []
        if investigation_state and investigation_state.hypothesis_set:
            for h in investigation_state.hypothesis_set.hypotheses[:3]:
                top_hypotheses.append({
                    "target_service": h.target_service,
                    "category": h.category.value,
                    "description": h.description,
                    "confidence": round(h.confidence, 3),
                    "status": h.status.value
                })

        evidence_items = []
        if investigation_state:
            for ev_id, ev in list(investigation_state.evidence_store.items())[:5]:
                evidence_items.append({
                    "source": ev.source.value,
                    "summary": ev.summary,
                    "collector": ev.provenance.collector if ev.provenance else "Unknown",
                    "reliability": ev.reliability
                })

        rec_actions = [
            f"1. Check live service dashboard and logs for {incident.service}",
            f"2. Validate recent deployment revisions and downstream dependency latencies",
            f"3. Manually execute approved playbook if root cause is identified by on-call SRE"
        ]

        if incident_report and incident_report.recommended_action:
            rec_actions.insert(0, f"RCAI Recommended Playbook: {incident_report.recommended_action}")

        brief = EscalationBrief(
            incident_id=incident.incident_id,
            service=incident.service,
            severity=incident.severity,
            symptom=incident.symptom,
            escalation_reason=reason,
            top_hypotheses=top_hypotheses,
            evidence_gathered=evidence_items,
            recommended_sre_actions=rec_actions,
            escalated_at=time.time()
        )

        return brief

    def dispatch_escalation(
        self,
        brief: EscalationBrief,
        incident: Optional[Incident] = None
    ) -> Dict[str, Any]:
        if incident:
            incident.status = IncidentStatus.ESCALATED

        self.active_escalations[brief.incident_id] = brief
        channels_notified = []

        # 1. Dispatch to Slack Webhook
        if self.slack_webhook_url:
            slack_payload = {
                "text": f"[ESCALATION] RCAI Incident Escalation [{brief.severity.value}] on `{brief.service}`\n"
                        f"*Symptom:* {brief.symptom}\n"
                        f"*Reason for Escalation:* {brief.escalation_reason}\n"
                        f"*Evidence Items:* {len(brief.evidence_gathered)} provenanced items collected",
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"[ALERT] RCAI Escalation: {brief.service}"}
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Severity:* {brief.severity.value}"},
                            {"type": "mrkdwn", "text": f"*Incident ID:* `{brief.incident_id}`"},
                            {"type": "mrkdwn", "text": f"*Reason:* {brief.escalation_reason}"},
                            {"type": "mrkdwn", "text": f"*Top Hypo:* {brief.top_hypotheses[0]['category'] if brief.top_hypotheses else 'None'}"}
                        ]
                    }
                ]
            }
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(self.slack_webhook_url, json=slack_payload)
                    if resp.status_code == 200:
                        channels_notified.append("slack")
            except Exception:
                pass

        # 2. Dispatch to PagerDuty Events API
        if self.pagerduty_webhook_url:
            pd_payload = {
                "routing_key": "rcai-alerts",
                "event_action": "trigger",
                "payload": {
                    "summary": f"[{brief.severity.value}] Incident Escalation on {brief.service}: {brief.symptom}",
                    "severity": brief.severity.value.lower(),
                    "source": "rcai-autonomous-pipeline",
                    "custom_details": {
                        "incident_id": brief.incident_id,
                        "escalation_reason": brief.escalation_reason,
                        "top_hypotheses": brief.top_hypotheses
                    }
                }
            }
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(self.pagerduty_webhook_url, json=pd_payload)
                    if resp.status_code in [200, 202]:
                        channels_notified.append("pagerduty")
            except Exception:
                pass

        if not channels_notified:
            channels_notified.append("ui_console_in_memory")

        brief.notification_channels = channels_notified
        brief.dispatch_status = "DISPATCHED"

        return {
            "status": "DISPATCHED",
            "brief_id": brief.brief_id,
            "incident_id": brief.incident_id,
            "channels": channels_notified
        }

global_escalation_dispatcher = EscalationDispatcher()
