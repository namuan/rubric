"""Global Rubric configuration — loads from ~/.config/rubric/rubric.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "rubric"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "rubric.json"


# ── Models ─────────────────────────────────────────────────────────
class ProviderSettings(BaseModel):
    api_key_env: str = ""
    base_url: str
    default_model: str


class AgentLLMSettings(BaseModel):
    provider: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 4096
    system_prompt: str = ""


class GlobalLLMSettings(BaseModel):
    enabled: bool = False
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout_seconds: float = 120
    max_retries: int = 3
    retry_delay_seconds: float = 2


class LLMConfig(BaseModel):
    default_provider: str
    providers: dict[str, ProviderSettings]
    agents: dict[str, AgentLLMSettings]
    global_settings: GlobalLLMSettings = Field(alias="global")


class CLISettings(BaseModel):
    default_output: str = "text"


class RubricConfig(BaseModel):
    version: int = 1
    llm: LLMConfig | None = None
    cli: CLISettings = Field(default_factory=CLISettings)


# ── Default config template ────────────────────────────────────────
DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "//": "Rubric configuration — edit and place at ~/.config/rubric/rubric.json",
    "cli": {
        "default_output": "text",
    },
    "llm": {
        "default_provider": "openai",
        "providers": {
            "openai": {
                "api_key_env": "OPENAI_API_KEY",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4o",
            },
            "anthropic": {
                "api_key_env": "ANTHROPIC_API_KEY",
                "base_url": "https://api.anthropic.com/v1",
                "default_model": "claude-sonnet-4-20250514",
            },
            "openrouter": {
                "api_key_env": "OPENROUTER_API_KEY",
                "base_url": "https://openrouter.ai/api/v1",
                "default_model": "anthropic/claude-sonnet-4",
            },
            "ollama": {
                "api_key_env": "",
                "base_url": "http://localhost:11434/v1",
                "default_model": "llama3.3-70b",
            },
            "vllm": {
                "api_key_env": "VLLM_API_KEY",
                "base_url": "http://localhost:8000/v1",
                "default_model": "Qwen/Qwen2.5-72B-Instruct",
            },
        },
        "agents": {
            "product_owner": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.7,
                "max_tokens": 2048,
                "system_prompt": (
                    "You are a Product Owner. Write clear user stories with "
                    "acceptance criteria. Focus on business value and user needs."
                ),
            },
            "architect": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.3,
                "max_tokens": 4096,
                "system_prompt": (
                    "You are a Software Architect. Design clean, scalable system "
                    "architectures. Produce API specs, data models, and technical "
                    "design documents."
                ),
            },
            "developer": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.2,
                "max_tokens": 8192,
                "system_prompt": (
                    "You are a Developer practicing Test-Driven Development. "
                    "Follow Red-Green-Refactor strictly. Write the minimum code "
                    "to pass each test, then refactor."
                ),
            },
            "reviewer": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.3,
                "max_tokens": 4096,
                "system_prompt": (
                    "You are a Code Reviewer. Check for correctness, readability, "
                    "testability, security, and performance. Suggest concrete "
                    "improvements."
                ),
            },
            "test_writer": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.4,
                "max_tokens": 4096,
                "system_prompt": (
                    "You are a Test Writer focused on end-user acceptance testing. "
                    "Write Given/When/Then scenarios from the user's perspective. "
                    "Use tools like Playwright or pytest-bdd."
                ),
            },
            "devops": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.2,
                "max_tokens": 4096,
                "system_prompt": (
                    "You are a DevOps engineer. Create CI/CD pipelines, deployment "
                    "configurations, and infrastructure-as-code. Prioritise "
                    "reliability and observability."
                ),
            },
            "scrum_master": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.5,
                "max_tokens": 2048,
                "system_prompt": (
                    "You are a Scrum Master and Planner. Break stories into small, "
                    "focused tasks. Each task must be small enough that one agent "
                    "can complete it without needing the full story context."
                ),
            },
        },
        "global": {
            "enabled": False,
            "temperature": 0.3,
            "max_tokens": 4096,
            "timeout_seconds": 120,
            "max_retries": 3,
            "retry_delay_seconds": 2,
        },
    },
}


# ── Public API ─────────────────────────────────────────────────────
def write_default_config(path: str | Path | None = None) -> Path:
    """Write the default config template to *path*.

    If *path* is not given the file is written to
    ``~/.config/rubric/rubric.json``.  The parent directories are created
    as needed.
    """
    target = Path(path) if path is not None else DEFAULT_CONFIG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(DEFAULT_CONFIG, indent=2) + "\n"
    target.write_text(content, encoding="utf-8")
    logger.info("Wrote default config to %s", target)
    return target


def load_rubric_config(
    path: str | Path | None = None,
) -> RubricConfig | None:
    """Load rubric configuration from *path*.

    When *path* is ``None`` the loader looks first at
    ``RUBRIC_CONFIG`` and then at ``~/.config/rubric/rubric.json``.
    Returns ``None`` when no config file exists.
    """
    import os

    resolved: Path | None = None
    if path is not None:
        resolved = Path(path)
    elif env_path := os.getenv("RUBRIC_CONFIG"):
        resolved = Path(env_path)
    elif DEFAULT_CONFIG_FILE.is_file():
        resolved = DEFAULT_CONFIG_FILE

    if resolved is None:
        return None

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load rubric config from %s: %s", resolved, exc)
        return None

    raw = {key: value for key, value in raw.items() if not key.startswith("//")}
    try:
        return RubricConfig.model_validate(raw)
    except ValueError as exc:
        logger.warning("Invalid rubric config in %s: %s", resolved, exc)
        return None
