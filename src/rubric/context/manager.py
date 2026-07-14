"""Context manager — shared state across the workflow engine."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages shared context and state for the workflow.

    The context is a key-value store that agents and the engine use
    to share state, intermediate results, and cross-cutting concerns.

    Key conventions:
    - Story-specific: "story:{id}:{field}"
    - Agent-specific: "agent:{id}:{field}"
    - Global: "config:{key}", "shared:{key}"
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._history: list[dict[str, Any]] = []

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from context."""
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in context."""
        old = self._store.get(key)
        self._store[key] = value
        self._history.append({
            "key": key,
            "old": old,
            "new": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.debug(f"Context set: {key} = {value}")

    def delete(self, key: str) -> None:
        """Remove a key from context."""
        self._store.pop(key, None)

    def keys(self, prefix: str | None = None) -> list[str]:
        """List all keys, optionally filtered by prefix."""
        keys = list(self._store.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    def snapshot(self) -> dict[str, Any]:
        """Get a snapshot of the entire context."""
        return dict(self._store)

    def story_context(self, story_id: str) -> dict[str, Any]:
        """Get all context entries for a specific story."""
        prefix = f"story:{story_id}:"
        return {
            k.removeprefix(prefix): v
            for k, v in self._store.items()
            if k.startswith(prefix)
        }

    def clear(self) -> None:
        """Clear all context."""
        self._store.clear()
        self._history.clear()

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)
