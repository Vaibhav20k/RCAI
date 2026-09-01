# Phase 0 Foundation Tests
import os
import pathlib
import pytest

def test_directory_structure_exists():
    required_dirs = [
        "agent/investigator",
        "agent/hypothesis",
        "agent/evidence",
        "agent/routing",
        "agent/verification",
        "agent/memory",
        "agent/policies",
        "tools/logs",
        "tools/metrics",
        "tools/traces",
        "tools/deployments",
        "tools/database",
        "tools/remediation",
        "simulator/services",
        "simulator/faults",
        "simulator/scenarios",
        "simulator/traffic",
        "benchmark/datasets",
        "benchmark/scenarios",
        "benchmark/evaluators",
        "benchmark/baselines",
        "benchmark/reports",
        "backend/api",
        "backend/incidents",
        "backend/audit",
        "backend/models",
        "observability/prometheus",
        "observability/logs",
        "observability/tracing",
        "docs",
        "tests/unit",
        "tests/contracts",
        "tests/integration",
    ]
    for d in required_dirs:
        assert os.path.isdir(d), f"Missing directory: {d}"

def test_essential_documentation_exists():
    required_docs = [
        "README.md",
        "docs/README.md",
        "docs/PHASES.md",
        "docs/architecture.md",
        "docs/research.md",
        "docs/evaluation.md",
        "docs/safety.md",
        "docs/decisions.md",
        ".env.example",
        "pyproject.toml",
        "docker-compose.yml",
    ]
    for doc in required_docs:
        assert os.path.isfile(doc), f"Missing required file: {doc}"
        assert os.path.getsize(doc) > 0, f"File is empty: {doc}"

def test_no_emojis_in_source_or_docs():
    emoji_ranges = [
        (0x1F600, 0x1F64F), # Emoticons
        (0x1F300, 0x1F5FF), # Misc Symbols and Pictographs
        (0x1F680, 0x1F6FF), # Transport and Map
        (0x1F700, 0x1F77F), # Alchemical Symbols
        (0x1F780, 0x1F7FF), # Geometric Shapes Extended
        (0x1F800, 0x1F8FF), # Supplemental Arrows-C
        (0x1F900, 0x1F9FF), # Supplemental Symbols and Pictographs
        (0x1FA00, 0x1FA6F), # Chess Symbols
        (0x1FA70, 0x1FAFF), # Symbols and Pictographs Extended-A
        (0x2600, 0x26FF),   # Misc symbols
        (0x2700, 0x27BF),   # Dingbats
    ]
    
    scan_extensions = [".py", ".md", ".toml", ".yml", ".yaml", ".json"]
    repo_root = pathlib.Path(".")
    
    # Exclude .git and .pytest_cache
    for path in repo_root.rglob("*"):
        if path.is_file() and path.suffix in scan_extensions:
            if any(p.startswith(".venv") or p in {".git", ".pytest_cache", "venv", "env", "__pycache__"} for p in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for char in text:
                code_pt = ord(char)
                for start, end in emoji_ranges:
                    assert not (start <= code_pt <= end), (
                        f"Found prohibited emoji in {path}: U+{code_pt:04X} ({char})"
                    )

def test_configuration_keys_defined():
    env_text = pathlib.Path(".env.example").read_text(encoding="utf-8")
    expected_vars = [
        "ENVIRONMENT",
        "API_GATEWAY_PORT",
        "ORDER_SERVICE_PORT",
        "PAYMENT_SERVICE_PORT",
        "POSTGRES_HOST",
        "PROMETHEUS_URL",
        "MAX_INVESTIGATION_TIME_SECONDS",
        "MAX_TOOL_CALLS_PER_INVESTIGATION",
        "MAX_HYPOTHESES",
    ]
    for var in expected_vars:
        assert f"{var}=" in env_text, f"Missing env var: {var}"
