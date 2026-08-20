# Structured Hypothesis State Models
import uuid
import time
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class HypothesisCategory(str, Enum):
    DATABASE = "database"
    DEPLOYMENT = "deployment"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    QUEUE = "queue"
    CONFIG = "config"
    UNKNOWN = "unknown"

class HypothesisStatus(str, Enum):
    OPEN = "OPEN"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    REJECTED = "REJECTED"
    CONFIRMED = "CONFIRMED"

class Hypothesis(BaseModel):
    hypothesis_id: str = Field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:8]}")
    incident_id: str
    target_service: str
    category: HypothesisCategory
    description: str
    confidence: float = Field(default=0.2, ge=0.0, le=1.0)
    status: HypothesisStatus = HypothesisStatus.OPEN
    supporting_evidence: List[str] = Field(default_factory=list, description="List of supporting evidence IDs")
    contradicting_evidence: List[str] = Field(default_factory=list, description="List of contradicting evidence IDs")
    next_action: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def add_supporting_evidence(self, evidence_id: str, weight: float = 0.2) -> None:
        if evidence_id not in self.supporting_evidence:
            self.supporting_evidence.append(evidence_id)
        self.confidence = min(1.0, round(self.confidence + weight, 3))
        self.updated_at = time.time()
        self._recalculate_status()

    def add_contradicting_evidence(self, evidence_id: str, weight: float = 0.25) -> None:
        if evidence_id not in self.contradicting_evidence:
            self.contradicting_evidence.append(evidence_id)
        self.confidence = max(0.0, round(self.confidence - weight, 3))
        self.updated_at = time.time()
        self._recalculate_status()

    def reject(self, reason_evidence_id: Optional[str] = None) -> None:
        if reason_evidence_id and reason_evidence_id not in self.contradicting_evidence:
            self.contradicting_evidence.append(reason_evidence_id)
        self.confidence = 0.0
        self.status = HypothesisStatus.REJECTED
        self.updated_at = time.time()

    def confirm(self) -> None:
        self.confidence = max(self.confidence, 0.85)
        self.status = HypothesisStatus.CONFIRMED
        self.updated_at = time.time()

    def _recalculate_status(self) -> None:
        if self.status == HypothesisStatus.REJECTED or self.confidence <= 0.05:
            self.status = HypothesisStatus.REJECTED
        elif self.confidence >= 0.75 and len(self.contradicting_evidence) == 0:
            self.status = HypothesisStatus.SUPPORTED
        elif len(self.contradicting_evidence) > len(self.supporting_evidence):
            self.status = HypothesisStatus.WEAKENED
        elif self.confidence >= 0.4:
            self.status = HypothesisStatus.SUPPORTED
        else:
            self.status = HypothesisStatus.OPEN

class HypothesisSet(BaseModel):
    incident_id: str
    hypotheses: List[Hypothesis] = Field(default_factory=list)

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        # Prevent duplicates for the same service + category
        for existing in self.hypotheses:
            if existing.target_service == hypothesis.target_service and existing.category == hypothesis.category:
                return
        self.hypotheses.append(hypothesis)

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        for h in self.hypotheses:
            if h.hypothesis_id == hypothesis_id:
                return h
        return None

    def get_active_hypotheses(self) -> List[Hypothesis]:
        return [h for h in self.hypotheses if h.status != HypothesisStatus.REJECTED]

    def get_top_hypothesis(self) -> Optional[Hypothesis]:
        active = self.get_active_hypotheses()
        if not active:
            return None
        return max(active, key=lambda h: h.confidence)

    def get_ranked_hypotheses(self) -> List[Hypothesis]:
        return sorted(self.hypotheses, key=lambda h: (h.status != HypothesisStatus.REJECTED, h.confidence), reverse=True)
