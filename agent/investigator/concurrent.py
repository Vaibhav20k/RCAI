# Multi-Incident Concurrent Investigator Pool
import concurrent.futures
from typing import List, Dict, Any, Optional
from backend.incidents.models import AgentIncidentView
from agent.investigator.loop import ActiveInvestigator
from agent.verification.engine import RootCauseVerifier
from agent.verification.models import RootCauseDecision, IncidentReport
from tools.registry import ToolRegistry

class ConcurrentInvestigatorPool:
    def __init__(self, tool_registry: ToolRegistry, max_workers: int = 4):
        self.tool_registry = tool_registry
        self.max_workers = max_workers
        self.investigator = ActiveInvestigator(tool_registry=tool_registry)
        self.verifier = RootCauseVerifier()

    def investigate_batch(self, incidents: List[AgentIncidentView]) -> List[IncidentReport]:
        reports: List[IncidentReport] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_inc = {
                executor.submit(self._investigate_single, inc): inc
                for inc in incidents
            }
            for future in concurrent.futures.as_completed(future_to_inc):
                reports.append(future.result())
        return reports

    def _investigate_single(self, inc: AgentIncidentView) -> IncidentReport:
        state = self.investigator.run_investigation(inc)
        return self.verifier.generate_incident_report(state)
