"""Loading and validation for Rubric's provider-neutral LLM configuration."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
    environment: str = "development"
    default_provider: str
    providers: dict[str, ProviderSettings]
    agents: dict[str, AgentLLMSettings]
    global_settings: GlobalLLMSettings = Field(alias="global")


def active_environment(environment: str | None = None) -> str:
    """Resolve the configured runtime environment."""
    return environment or os.getenv("APP_ENV") or os.getenv("ENV") or "development"


def default_config_path(environment: str | None = None) -> Path | None:
    """Find an environment-specific or repository-local configuration file."""
    if configured_path := os.getenv("RUBRIC_LLM_CONFIG"):
        return Path(configured_path)

    resolved_environment = active_environment(environment)
    config_directories = [
        Path.cwd() / "config",
        Path(__file__).resolve().parents[3] / "config",
    ]
    candidates = (
        [
            directory / f"llm_config.{resolved_environment}.json"
            for directory in config_directories
        ]
        + [
            directory / f"llm_config_{resolved_environment}.json"
            for directory in config_directories
        ]
        + [directory / "llm_config.json" for directory in config_directories]
    )
    return next((path for path in candidates if path.is_file()), None)


def load_llm_config(
    path: str | Path | None = None,
    environment: str | None = None,
) -> LLMConfig | None:
    """Load the selected environment's LLM settings.

    Environment overrides in the base JSON file are applied after the shared
    settings.  A dedicated ``llm_config.<environment>.json`` file takes
    precedence when present.
    """
    resolved_environment = active_environment(environment)
    config_path = (
        Path(path) if path is not None else default_config_path(resolved_environment)
    )
    if config_path is None:
        return None
    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        if path is None:
            logger.warning("Could not load LLM config from %s: %s", config_path, error)
            return None
        raise ValueError(
            f"Could not load LLM config from {config_path}: {error}"
        ) from error

    raw_config = {
        key: value for key, value in raw_config.items() if not key.startswith("//")
    }
    environment_overrides = raw_config.pop("environments", {})
    selected_overrides = environment_overrides.get(resolved_environment, {})
    if not isinstance(selected_overrides, dict):
        raise ValueError(
            f"Invalid LLM environment override for {resolved_environment!r}"
        )
    raw_config = _merge_settings(raw_config, selected_overrides)
    raw_config["environment"] = resolved_environment
    try:
        return LLMConfig.model_validate(raw_config)
    except ValueError as error:
        raise ValueError(f"Invalid LLM config in {config_path}: {error}") from error


def _merge_settings(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge an environment override without mutating its inputs."""
    merged = dict(base)
    for key, override_value in overrides.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = _merge_settings(base_value, override_value)
        else:
            merged[key] = override_value
    return merged
