# RCAI Centralized Configuration
import os
from dotenv import load_dotenv
load_dotenv()
from typing import Optional, List
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # Core environment
    ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    
    # Microservice ports
    API_GATEWAY_PORT: int = Field(default_factory=lambda: int(os.getenv("API_GATEWAY_PORT", "8000")))
    ORDER_SERVICE_PORT: int = Field(default_factory=lambda: int(os.getenv("ORDER_SERVICE_PORT", "8001")))
    PAYMENT_SERVICE_PORT: int = Field(default_factory=lambda: int(os.getenv("PAYMENT_SERVICE_PORT", "8002")))
    POSTGRES_HOST: str = Field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    
    # Telemetry data source configuration: "simulator" or "live"
    DATA_SOURCE: str = Field(default_factory=lambda: os.getenv("DATA_SOURCE", "simulator").lower())
    
    # Prometheus live endpoint and credential authentication
    PROMETHEUS_URL: str = Field(default_factory=lambda: os.getenv("PROMETHEUS_URL", "http://localhost:9090"))
    PROMETHEUS_BEARER_TOKEN: Optional[str] = Field(default_factory=lambda: os.getenv("PROMETHEUS_BEARER_TOKEN"))
    PROMETHEUS_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("PROMETHEUS_API_KEY"))
    
    # OpenTelemetry Collector live endpoint and credentials
    OTEL_COLLECTOR_URL: str = Field(default_factory=lambda: os.getenv("OTEL_COLLECTOR_URL", "http://localhost:4318"))
    OTEL_AUTH_TOKEN: Optional[str] = Field(default_factory=lambda: os.getenv("OTEL_AUTH_TOKEN"))
    
    # Centralized Log Service live endpoint and credentials (e.g. Loki / Elasticsearch)
    LOG_SERVICE_URL: str = Field(default_factory=lambda: os.getenv("LOG_SERVICE_URL", "http://localhost:3100"))
    LOG_SERVICE_AUTH_TOKEN: Optional[str] = Field(default_factory=lambda: os.getenv("LOG_SERVICE_AUTH_TOKEN"))
    
    # TODO (Security / Transport): For production deployments requiring mutual TLS (mTLS)
    # with client certificate verification or custom CA bundles, configure TLS cert path
    # environment variables (e.g., PROMETHEUS_CLIENT_CERT_PATH, PROMETHEUS_CLIENT_KEY_PATH).
    
    # Investigation budgets and thresholds
    MAX_INVESTIGATION_TIME_SECONDS: float = Field(default_factory=lambda: float(os.getenv("MAX_INVESTIGATION_TIME_SECONDS", "120")))
    MAX_TOOL_CALLS_PER_INVESTIGATION: int = Field(default_factory=lambda: int(os.getenv("MAX_TOOL_CALLS_PER_INVESTIGATION", "10")))
    MAX_HYPOTHESES: int = Field(default_factory=lambda: int(os.getenv("MAX_HYPOTHESES", "5")))
    INVESTIGATION_CONFIDENCE_THRESHOLD: float = Field(default_factory=lambda: float(os.getenv("INVESTIGATION_CONFIDENCE_THRESHOLD", "0.70")))
    
    # Pluggable LLM Backend: "rule_based" (default), "ollama", or "hosted"
    LLM_BACKEND: str = Field(default_factory=lambda: os.getenv("LLM_BACKEND", "rule_based").lower())
    OLLAMA_BASE_URL: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    OLLAMA_MODEL: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3:4b"))
    OLLAMA_CONTEXT_WINDOW: int = Field(default_factory=lambda: int(os.getenv("OLLAMA_CONTEXT_WINDOW", "8192")))
    HOSTED_LLM_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("HOSTED_LLM_API_KEY"))
    HOSTED_LLM_BASE_URL: str = Field(default_factory=lambda: os.getenv("HOSTED_LLM_BASE_URL", "https://api.openai.com/v1"))
    HOSTED_LLM_MODEL: str = Field(default_factory=lambda: os.getenv("HOSTED_LLM_MODEL", "gpt-4o"))
    
    # Stage 4: Real Infrastructure Remediation Execution Target ("simulated", "kubernetes", "docker", "webhook")
    REMEDIATION_EXECUTION_TARGET: str = Field(default_factory=lambda: os.getenv("REMEDIATION_EXECUTION_TARGET", "simulated").lower())
    KUBERNETES_NAMESPACE: str = Field(default_factory=lambda: os.getenv("KUBERNETES_NAMESPACE", "default"))
    KUBECTL_BINARY_PATH: str = Field(default_factory=lambda: os.getenv("KUBECTL_BINARY_PATH", "kubectl"))
    DOCKER_BINARY_PATH: str = Field(default_factory=lambda: os.getenv("DOCKER_BINARY_PATH", "docker"))
    REMEDIATION_WEBHOOK_URL: Optional[str] = Field(default_factory=lambda: os.getenv("REMEDIATION_WEBHOOK_URL"))
    REMEDIATION_WEBHOOK_SECRET: Optional[str] = Field(default_factory=lambda: os.getenv("REMEDIATION_WEBHOOK_SECRET"))
    
    # Stage 4: Live Outcome Verification Parameters
    VERIFICATION_TIMEOUT_SECONDS: float = Field(default_factory=lambda: float(os.getenv("VERIFICATION_TIMEOUT_SECONDS", "180.0")))
    VERIFICATION_POLL_INTERVAL_SECONDS: float = Field(default_factory=lambda: float(os.getenv("VERIFICATION_POLL_INTERVAL_SECONDS", "5.0")))
    VERIFICATION_MAX_ERROR_RATE: float = Field(default_factory=lambda: float(os.getenv("VERIFICATION_MAX_ERROR_RATE", "0.05")))
    VERIFICATION_MAX_P99_MS: float = Field(default_factory=lambda: float(os.getenv("VERIFICATION_MAX_P99_MS", "150.0")))
    
    # Stage 5: Live Incident Webhook Ingestion & On-Call Escalation
    ALERTMANAGER_WEBHOOK_SECRET: Optional[str] = Field(default_factory=lambda: os.getenv("ALERTMANAGER_WEBHOOK_SECRET"))
    AUTO_START_INVESTIGATION_ON_ALERT: bool = Field(default_factory=lambda: os.getenv("AUTO_START_INVESTIGATION_ON_ALERT", "true").lower() == "true")
    SLACK_WEBHOOK_URL: Optional[str] = Field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL"))
    PAGERDUTY_WEBHOOK_URL: Optional[str] = Field(default_factory=lambda: os.getenv("PAGERDUTY_WEBHOOK_URL"))
    
    # Stage 6: Pre-Authorized Playbook Auto-Execution Parameters
    AUTO_EXECUTE_ENABLED: bool = Field(default_factory=lambda: os.getenv("AUTO_EXECUTE_ENABLED", "false").lower() == "true")
    AUTO_EXECUTE_PLAYBOOKS: List[str] = Field(
        default_factory=lambda: [
            p.strip()
            for p in os.getenv(
                "AUTO_EXECUTE_PLAYBOOKS",
                "optimize_db_index,restart_service,restart_workers,flush_cache"
            ).split(",")
            if p.strip()
        ]
    )
    AUTO_EXECUTE_CONFIDENCE_THRESHOLD: float = Field(default_factory=lambda: float(os.getenv("AUTO_EXECUTE_CONFIDENCE_THRESHOLD", "0.90")))
    AUTO_EXECUTE_REQUIRE_PROVENANCE: bool = Field(default_factory=lambda: os.getenv("AUTO_EXECUTE_REQUIRE_PROVENANCE", "true").lower() == "true")
    
    # Allowed CORS Origins
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv(
                "ALLOWED_ORIGINS",
                "https://rcai-console.vercel.app,http://localhost:3000,http://127.0.0.1:8000"
            ).split(",")
            if o.strip()
        ]
    )

    # Stage A: Drop-In Auto-Discovery Mode ("none" or "docker")
    RCAI_DISCOVERY_MODE: str = Field(default_factory=lambda: os.getenv("RCAI_DISCOVERY_MODE", "none").lower())
    DOCKER_SOCKET_PATH: str = Field(default_factory=lambda: os.getenv("DOCKER_SOCKET_PATH", "/var/run/docker.sock"))

    def is_live_mode(self) -> bool:
        return self.DATA_SOURCE == "live"

    def is_discovery_enabled(self) -> bool:
        return self.RCAI_DISCOVERY_MODE == "docker"

_global_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _global_settings
    if _global_settings is None:
        _global_settings = Settings()
    return _global_settings

def reset_settings() -> None:
    global _global_settings
    _global_settings = None
