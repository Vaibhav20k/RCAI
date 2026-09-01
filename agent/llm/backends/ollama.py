# Local Ollama LLM Backend (OpenAI-Compatible / Native JSON API)
import json
from typing import Dict, Any, Optional
import httpx
from agent.llm.interface import BaseLLMBackend, extract_json_from_text
from backend.config import get_settings

class OllamaBackend(BaseLLMBackend):
    name: str = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        context_window: Optional[int] = None,
        timeout_seconds: float = 180.0
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.context_window = context_window or settings.OLLAMA_CONTEXT_WINDOW
        self.timeout_seconds = timeout_seconds

    def check_health(self) -> bool:
        try:
            with httpx.Client(base_url=self.base_url, timeout=3.0) as client:
                resp = client.get("/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def _call_model_raw(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None
    ) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "You are an SRE incident root-cause diagnosis AI. Respond strictly in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_ctx": self.context_window
            }
        }

        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                resp = client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                msg = data.get("message", {})
                content = msg.get("content", "")
                if content:
                    return content
                # Fallback: if reasoning model stored output in thinking field
                thinking = msg.get("thinking", "")
                if thinking:
                    extracted = extract_json_from_text(thinking)
                    if extracted:
                        return json.dumps(extracted)
                raise ValueError(f"Ollama returned empty response content: {data}")

        except httpx.ConnectError as exc:
            raise ConnectionError(f"Could not connect to Ollama server at {self.base_url}: {str(exc)}")
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"Ollama API returned HTTP {exc.response.status_code}: {exc.response.text}")
        except Exception as exc:
            raise RuntimeError(f"Ollama inference failed: {str(exc)}")
