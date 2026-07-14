"""Provider protocol and standard-library HTTP adapters for configured LLMs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from rubric.llm.config import LLMConfig, ProviderSettings


class LLMUnavailableError(RuntimeError):
    """Raised when a configured provider cannot be called locally."""


@dataclass(frozen=True)
class LLMRequest:
    role: str
    model: str
    system_prompt: str
    prompt: str
    temperature: float
    max_tokens: int


class LLMProvider(Protocol):
    """Minimal provider contract used by every Rubric agent."""

    def generate(self, request: LLMRequest) -> str:
        """Generate a text response for one agent task."""


class UnavailableLLMProvider:
    def __init__(self, reason: str):
        self.reason = reason

    def generate(self, request: LLMRequest) -> str:
        raise LLMUnavailableError(self.reason)


class OpenAICompatibleProvider:
    """Adapter for OpenAI-compatible chat completion APIs."""

    def __init__(self, settings: ProviderSettings, timeout_seconds: float):
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def generate(self, request: LLMRequest) -> str:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        response = _post_json(
            f"{self.settings.base_url.rstrip('/')}/chat/completions",
            payload,
            self.settings.api_key_env,
            self.timeout_seconds,
        )
        try:
            return str(response["choices"][0]["message"]["content"])
        except (IndexError, KeyError, TypeError) as error:
            raise RuntimeError(
                "Provider response did not contain a chat completion"
            ) from error


class AnthropicProvider:
    def __init__(self, settings: ProviderSettings, timeout_seconds: float):
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def generate(self, request: LLMRequest) -> str:
        payload = {
            "model": request.model,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        response = _post_json(
            f"{self.settings.base_url.rstrip('/')}/messages",
            payload,
            self.settings.api_key_env,
            self.timeout_seconds,
            extra_headers={"anthropic-version": "2023-06-01"},
        )
        try:
            return str(response["content"][0]["text"])
        except (IndexError, KeyError, TypeError) as error:
            raise RuntimeError(
                "Provider response did not contain Anthropic text"
            ) from error


class GoogleProvider:
    def __init__(self, settings: ProviderSettings, timeout_seconds: float):
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def generate(self, request: LLMRequest) -> str:
        api_key = _api_key(self.settings.api_key_env)
        endpoint = f"{self.settings.base_url.rstrip('/')}/models/{request.model}:generateContent"
        response = _post_json(
            endpoint,
            {
                "systemInstruction": {"parts": [{"text": request.system_prompt}]},
                "contents": [{"parts": [{"text": request.prompt}]}],
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                },
            },
            "",
            self.timeout_seconds,
            extra_headers={"x-goog-api-key": api_key},
        )
        try:
            return str(response["candidates"][0]["content"]["parts"][0]["text"])
        except (IndexError, KeyError, TypeError) as error:
            raise RuntimeError(
                "Provider response did not contain Google text"
            ) from error


def create_provider(config: LLMConfig | None, role: str) -> LLMProvider | None:
    """Build the configured provider for an agent role without requiring SDKs."""
    if config is None:
        return None
    enabled_by_environment = os.getenv("RUBRIC_ENABLE_LLM", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not config.global_settings.enabled and not enabled_by_environment:
        return None
    agent_settings = config.agents.get(role)
    if agent_settings is None:
        return None
    provider_settings = config.providers.get(agent_settings.provider)
    if provider_settings is None:
        return UnavailableLLMProvider(
            f"Provider '{agent_settings.provider}' is not configured"
        )
    if provider_settings.api_key_env and not os.getenv(provider_settings.api_key_env):
        return UnavailableLLMProvider(
            f"Environment variable {provider_settings.api_key_env} is not set"
        )

    timeout = config.global_settings.timeout_seconds
    if agent_settings.provider == "anthropic":
        return AnthropicProvider(provider_settings, timeout)
    if agent_settings.provider in {"google", "gemini"}:
        return GoogleProvider(provider_settings, timeout)
    return OpenAICompatibleProvider(provider_settings, timeout)


def _api_key(key_env: str) -> str:
    if not key_env:
        return ""
    api_key = os.getenv(key_env)
    if not api_key:
        raise LLMUnavailableError(f"Environment variable {key_env} is not set")
    return api_key


def _post_json(
    url: str,
    payload: dict[str, Any],
    api_key_env: str,
    timeout_seconds: float,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json", **(extra_headers or {})}
    if api_key := _api_key(api_key_env):
        headers["Authorization"] = f"Bearer {api_key}"
        headers.setdefault("x-api-key", api_key)
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"LLM request failed: {error}") from error
