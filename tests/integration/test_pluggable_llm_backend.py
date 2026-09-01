# Integration Tests for Pluggable LLM Backend & Ollama Integration (Stage 2)
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from backend.config import Settings, get_settings, reset_settings
from agent.llm.models import (
    HypothesisItemSchema,
    HypothesisGenerationResponseSchema,
    PlaybookSelectionSchema,
    RootCauseDiagnosisSchema,
    LLMInferenceResult
)
from agent.llm.interface import (
    BaseLLMBackend,
    llm_infer,
    extract_json_from_text
)
from agent.llm.backends.rule_based import RuleBasedLLMBackend
from agent.llm.backends.ollama import OllamaBackend
from agent.llm.backends.hosted import HostedLLMBackend
from agent.llm.factory import get_llm_backend
from agent.hypothesis.generator import HypothesisGenerator
from agent.hypothesis.models import HypothesisCategory, HypothesisSet
from backend.incidents.models import AgentIncidentView, IncidentSeverity, IncidentStatus
from benchmark.evaluators.llm_benchmark import LLMBenchmarkRunner, ModelBenchmarkReport
from benchmark.scenarios.registry import ALL_SCENARIOS

@pytest.fixture(autouse=True)
def reset_cfg():
    reset_settings()
    yield
    reset_settings()

def test_extract_json_from_text_formats():
    # 1. Plain clean JSON
    s1 = '{"key": "value", "count": 10}'
    assert extract_json_from_text(s1) == {"key": "value", "count": 10}

    # 2. Markdown code block
    s2 = '```json\n{"action": "rollback_version", "target": "payment-service"}\n```'
    assert extract_json_from_text(s2) == {"action": "rollback_version", "target": "payment-service"}

    # 3. JSON surrounded by prose
    s3 = 'Here is the diagnosis JSON:\n{"root_cause_service": "order-service"}\nPlease execute.'
    assert extract_json_from_text(s3) == {"root_cause_service": "order-service"}

    # 4. Invalid text
    s4 = 'This is plain text with no json'
    assert extract_json_from_text(s4) is None

def test_rule_based_llm_backend_structured_schemas():
    backend = RuleBasedLLMBackend()

    # 1. Hypothesis schema
    res_hypo = backend.infer(
        prompt="Order service database query latency spiked above 100ms",
        schema=HypothesisGenerationResponseSchema
    )
    assert res_hypo.is_valid is True
    assert res_hypo.attempts == 1
    assert isinstance(res_hypo.parsed_data, HypothesisGenerationResponseSchema)
    assert len(res_hypo.parsed_data.hypotheses) == 5
    assert any(h.category == HypothesisCategory.DATABASE for h in res_hypo.parsed_data.hypotheses)

    # 2. Playbook selection schema
    res_play = backend.infer(
        prompt="Bad deployment on payment-service version 2.4.1",
        schema=PlaybookSelectionSchema
    )
    assert res_play.is_valid is True
    assert isinstance(res_play.parsed_data, PlaybookSelectionSchema)
    assert res_play.parsed_data.action == "rollback_version"
    assert res_play.parsed_data.target == "payment-service"

    # 3. Root cause schema
    res_rc = backend.infer(
        prompt="Partner bank dependency 503 timeout on payment-service",
        schema=RootCauseDiagnosisSchema
    )
    assert res_rc.is_valid is True
    assert isinstance(res_rc.parsed_data, RootCauseDiagnosisSchema)
    assert res_rc.parsed_data.root_cause_category == HypothesisCategory.DEPENDENCY

def test_reject_and_retry_logic_recovers_on_second_attempt():
    class FailsOnceBackend(BaseLLMBackend):
        name = "mock_flaky"
        model_name = "flaky-v1"
        call_count = 0

        def _call_model_raw(self, prompt, system_prompt=None, json_schema=None):
            self.call_count += 1
            if self.call_count == 1:
                # Malformed JSON on attempt 1
                return "I think the error is bad deployment, but this is not JSON"
            # Valid schema JSON on attempt 2
            return json.dumps({
                "action": "scale_workers",
                "target": "worker-service",
                "params": {"replicas": 4},
                "rationale": "Queue backlog detected",
                "risk_level": "LOW"
            })

    backend = FailsOnceBackend()
    res = backend.infer(
        prompt="Worker queue backlog growing",
        schema=PlaybookSelectionSchema,
        max_retries=1
    )

    assert res.is_valid is True
    assert res.attempts == 2
    assert backend.call_count == 2
    assert isinstance(res.parsed_data, PlaybookSelectionSchema)
    assert res.parsed_data.action == "scale_workers"

def test_reject_and_retry_fails_gracefully_when_unrecoverable():
    class AlwaysFailsBackend(BaseLLMBackend):
        name = "mock_bad"
        model_name = "bad-v1"
        call_count = 0

        def _call_model_raw(self, prompt, system_prompt=None, json_schema=None):
            self.call_count += 1
            return "Completely invalid text"

    backend = AlwaysFailsBackend()
    res = backend.infer(
        prompt="Investigate outage",
        schema=PlaybookSelectionSchema,
        max_retries=1
    )

    assert res.is_valid is False
    assert res.attempts == 2
    assert res.parsed_data is None
    assert "Schema validation failed" in res.error_message

def test_ollama_backend_mocked_http_inference():
    mock_ollama_resp = {
        "message": {
            "content": json.dumps({
                "reasoning": "Database lock contention causes order service transaction queueing",
                "hypotheses": [
                    {
                        "target_service": "order-service",
                        "category": "database",
                        "description": "Row level lock contention on order table",
                        "confidence": 0.85,
                        "next_action": "query_db_metrics"
                    }
                ]
            })
        }
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_ollama_resp
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        backend = OllamaBackend(base_url="http://localhost:11434", model_name="llama3:8b")
        res = backend.infer(
            prompt="Order service 90ms latency",
            schema=HypothesisGenerationResponseSchema
        )

        assert res.is_valid is True
        assert res.backend_name == "ollama"
        assert res.model_name == "llama3:8b"
        assert isinstance(res.parsed_data, HypothesisGenerationResponseSchema)
        assert res.parsed_data.hypotheses[0].category == HypothesisCategory.DATABASE

def test_hosted_backend_mocked_http_inference():
    mock_hosted_resp = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "action": "rollback_version",
                        "target": "order-service",
                        "params": {"target_version": "1.0.0"},
                        "rationale": "Faulty canary deployment v2.4.1 detected",
                        "risk_level": "LOW"
                    })
                }
            }
        ]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_hosted_resp
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        backend = HostedLLMBackend(
            base_url="https://api.openai.com/v1",
            model_name="gpt-4o",
            api_key="sk-test-key-123"
        )
        res = backend.infer(
            prompt="Order service bad deployment",
            schema=PlaybookSelectionSchema
        )

        assert res.is_valid is True
        assert res.backend_name == "hosted"
        assert res.model_name == "gpt-4o"
        assert isinstance(res.parsed_data, PlaybookSelectionSchema)
        assert res.parsed_data.action == "rollback_version"

def test_llm_factory_and_env_swapping():
    with patch.dict(os.environ, {"LLM_BACKEND": "rule_based"}):
        reset_settings()
        b1 = get_llm_backend()
        assert isinstance(b1, RuleBasedLLMBackend)
        assert b1.name == "rule_based"

    with patch.dict(os.environ, {"LLM_BACKEND": "ollama", "OLLAMA_MODEL": "mistral:7b"}):
        reset_settings()
        b2 = get_llm_backend()
        assert isinstance(b2, OllamaBackend)
        assert b2.name == "ollama"
        assert b2.model_name == "mistral:7b"

    with patch.dict(os.environ, {"LLM_BACKEND": "hosted", "HOSTED_LLM_MODEL": "claude-3.5-sonnet"}):
        reset_settings()
        b3 = get_llm_backend()
        assert isinstance(b3, HostedLLMBackend)
        assert b3.name == "hosted"

def test_hypothesis_generator_with_pluggable_backend():
    backend = RuleBasedLLMBackend()
    now = 1700000000.0
    incident = AgentIncidentView(
        incident_id="inc_test_llm_gen",
        scenario_id="scenario_db_regression_order",
        started_at=now - 60,
        detected_at=now,
        severity=IncidentSeverity.HIGH,
        service="order-service",
        symptom="Order service database latency regression",
        status=IncidentStatus.DETECTED,
        incident_window={"start_ts": now - 300, "end_ts": now}
    )

    hypo_set = HypothesisGenerator.generate_candidate_hypotheses(
        incident=incident,
        llm_backend=backend
    )

    assert isinstance(hypo_set, HypothesisSet)
    assert len(hypo_set.hypotheses) >= 5
    top_h = hypo_set.get_top_hypothesis()
    assert top_h is not None
    assert top_h.category == HypothesisCategory.DATABASE

def test_llm_benchmark_runner_partition_eval():
    runner = LLMBenchmarkRunner()
    # Evaluate across a subset of scenarios
    test_scenarios = ALL_SCENARIOS[:6]
    report = runner.evaluate_model_backend(RuleBasedLLMBackend(), test_scenarios)

    assert isinstance(report, ModelBenchmarkReport)
    assert report.total_scenarios == 6
    assert report.overall_accuracy >= 0.0
    assert report.false_diagnosis_rate <= 1.0
    assert len(report.partition_scores) > 0
