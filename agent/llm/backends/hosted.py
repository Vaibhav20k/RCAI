# Hosted LLM Backend (OpenAI / Claude / Hosted Endpoint Compatible)
import json
from typing import Dict, Any, Optional
import httpx
from agent.llm.interface import BaseLLMBackend
from backend.config import get_settings

class HostedLLMBackend(BaseLLMBackend):
    name: str = "hosted"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 5.0
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.HOSTED_LLM_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.HOSTED_LLM_MODEL
        self.api_key = api_key or settings.HOSTED_LLM_API_KEY
        self.timeout_seconds = timeout_seconds

    def _call_model_raw(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None
    ) -> str:
        if not self.api_key:
            raise ValueError("Hosted LLM API key not configured (set HOSTED_LLM_API_KEY environment variable)")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "You are an SRE incident root-cause diagnosis AI. Output valid JSON strictly conforming to the requested schema."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            with httpx.Client(base_url=self.base_url, headers=headers, timeout=self.timeout_seconds) as client:
                resp = client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    content = choices[0].get("message", {}).get("content", "")
                    if content:
                        return content
                raise ValueError(f"Hosted LLM returned empty choices: {data}")

        except httpx.ConnectError as exc:
            raise ConnectionError(f"Could not connect to Hosted LLM endpoint at {self.base_url}: {str(exc)}")
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Hosted LLM API returned HTTP {exc.response.status_code}: {exc.response.text}")
        except Exception as exc:
            raise RuntimeError(f"Hosted LLM inference failed: {str(exc)}")
