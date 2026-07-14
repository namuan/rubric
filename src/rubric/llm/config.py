"""Loading and validation for Rubric's provider-neutral LLM configuration."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Global rubric config path ──────────────────────────────────────
_GLOBAL_RUBRIC_CONFIG = Path.home() / ".config" / "rubric" / "rubric.json"


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


def default_config_path() -> Path | None:
    """Find an LLM configuration file.

    Priority order:

    1. ``RUBRIC_LLM_CONFIG`` environment variable
    2. ``~/.config/rubric/rubric.json`` (global user config)
    3. ``config/llm_config.json`` in the current working directory
    4. ``config/llm_config.json`` shipped with the package
    """
    if configured_path := os.getenv("RUBRIC_LLM_CONFIG"):
        return Path(configured_path)

    if _GLOBAL_RUBRIC_CONFIG.is_file():
        return _GLOBAL_RUBRIC_CONFIG

    config_directories = [
        Path.cwd() / "config",
        Path(__file__).resolve().parents[3] / "config",
    ]
    for directory in config_directories:
        candidate = directory / "llm_config.json"
        if candidate.is_file():
            return candidate
    return None


def load_llm_config(path: str | Path | None = None) -> LLMConfig | None:
    """Load LLM settings from a configuration file.

    When *path* is ``None`` the loader looks first at the
    ``RUBRIC_LLM_CONFIG`` environment variable, then at the local
    ``config/llm_config.json`` file, and finally at
    ``~/.config/rubric/rubric.json`` (extracting the ``llm`` key).
    """
    config_path = Path(path) if path is not None else default_config_path()
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

    # If this is a rubric.json (has a top-level "version" key with the
    # llm settings nested under "llm"), unwrap the LLM section.
    if isinstance(raw_config.get("version"), int) and "llm" in raw_config:
        raw_config = raw_config["llm"]

    raw_config = {
        key: value for key, value in raw_config.items() if not key.startswith("//")
    }
    try:
        return LLMConfig.model_validate(raw_config)
    except ValueError as error:
        raise ValueError(f"Invalid LLM config in {config_path}: {error}") from error
