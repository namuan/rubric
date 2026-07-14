"""Protocols shared across layers without coupling them to the engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from rubric.models.agent import Agent
    from rubric.models.artifacts import Artifact


class ArtifactRegistry(Protocol):
    """The engine capabilities agents need to bind and publish work."""

    def add_artifact(self, artifact: Artifact) -> None:
        """Register an artifact produced by an agent."""

    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the workflow."""
