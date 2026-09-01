# LLM Backend Factory
from typing import Optional
from agent.llm.interface import BaseLLMBackend
from agent.llm.backends.rule_based import RuleBasedLLMBackend
from agent.llm.backends.ollama import OllamaBackend
from agent.llm.backends.hosted import HostedLLMBackend
from backend.config import get_settings

def get_llm_backend(backend_type: Optional[str] = None, **kwargs) -> BaseLLMBackend:
    settings = get_settings()
    b_type = (backend_type or settings.LLM_BACKEND).lower()

    if b_type == "ollama":
        return OllamaBackend(**kwargs)
    elif b_type == "hosted":
        return HostedLLMBackend(**kwargs)
    else:
        return RuleBasedLLMBackend(**kwargs)
