# Generic Pluggable LLM Inference Interface with Schema Validation and Reject-and-Retry Logic
import json
import re
import time
from typing import Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
from agent.llm.models import LLMInferenceResult

T = TypeVar("T", bound=BaseModel)

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    # 1. Direct parse attempt
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Markdown fenced block extraction
    match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # 3. First balanced curly braces extraction
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass

    return None

class BaseLLMBackend:
    name: str = "base"
    model_name: str = "default"

    def _call_model_raw(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None
    ) -> str:
        raise NotImplementedError("Subclasses must implement _call_model_raw")

    def infer(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        max_retries: int = 1
    ) -> LLMInferenceResult:
        t0 = time.perf_counter()
        schema_def = schema.model_json_schema()
        schema_json_str = json.dumps(schema_def, indent=2)

        base_system = system_prompt or "You are an autonomous SRE root-cause investigator AI."
        enhanced_system = (
            f"{base_system}\n"
            f"You MUST format your entire response as a valid JSON object matching the JSON Schema below.\n"
            f"Do NOT include conversational preambles or markdown code fences. Output raw JSON only.\n\n"
            f"JSON Schema:\n{schema_json_str}"
        )

        current_prompt = prompt
        attempts = 0
        last_raw = ""
        last_error = ""

        while attempts <= max_retries:
            attempts += 1
            try:
                raw_response = self._call_model_raw(
                    prompt=current_prompt,
                    system_prompt=enhanced_system,
                    json_schema=schema_def
                )
                last_raw = raw_response
                json_data = extract_json_from_text(raw_response)

                if json_data is None:
                    raise ValueError(f"Model output is not valid JSON. Received: {raw_response[:200]}")

                # Validate against target Pydantic schema
                parsed_obj = schema.model_validate(json_data)
                duration_ms = (time.perf_counter() - t0) * 1000.0

                return LLMInferenceResult(
                    raw_text=raw_response,
                    parsed_data=parsed_obj,
                    is_valid=True,
                    attempts=attempts,
                    backend_name=self.name,
                    model_name=self.model_name,
                    duration_ms=duration_ms,
                    error_message=None
                )

            except (ValidationError, ValueError, Exception) as exc:
                last_error = str(exc)
                if attempts <= max_retries:
                    current_prompt = (
                        f"{prompt}\n\n"
                        f"[SCHEMA_VALIDATION_ERROR on Attempt {attempts}]: Your previous response failed schema validation: {last_error}.\n"
                        f"Output ONLY valid JSON strictly conforming to the requested schema."
                    )

        duration_ms = (time.perf_counter() - t0) * 1000.0
        return LLMInferenceResult(
            raw_text=last_raw,
            parsed_data=None,
            is_valid=False,
            attempts=attempts,
            backend_name=self.name,
            model_name=self.model_name,
            duration_ms=duration_ms,
            error_message=f"Schema validation failed after {attempts} attempts: {last_error}"
        )

def llm_infer(
    prompt: str,
    schema: Type[T],
    system_prompt: Optional[str] = None,
    backend: Optional[BaseLLMBackend] = None,
    max_retries: int = 1
) -> LLMInferenceResult:
    if backend is None:
        from agent.llm.factory import get_llm_backend
        backend = get_llm_backend()
    return backend.infer(prompt=prompt, schema=schema, system_prompt=system_prompt, max_retries=max_retries)
