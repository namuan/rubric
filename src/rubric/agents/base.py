"""Base agent class — foundation for all role-specific agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from rubric.models.agent import Agent, Role
from rubric.models.story import Task, Story
from rubric.models.artifacts import Artifact, ArtifactType
from rubric.models.protocols import ArtifactRegistry
from rubric.llm import (
    AgentLLMSettings,
    LLMConfig,
    LLMProvider,
    LLMRequest,
    create_provider,
    load_llm_config,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for workflow agents.

    Subclass this to implement role-specific behavior.
    The `execute` method is the core — it defines what the agent
    actually does when given a task.
    """

    def __init__(
        self,
        name: str,
        role: Role,
        *,
        llm_provider: LLMProvider | None = None,
        llm_config: LLMConfig | None = None,
        llm_settings: AgentLLMSettings | None = None,
        **kwargs: Any,
    ):
        self.agent = Agent(name=name, role=role, **kwargs)
        self.registry: ArtifactRegistry | None = None
        self.llm_config = llm_config if llm_config is not None else load_llm_config()
        configured_settings = (
            self.llm_config.agents.get(role.value)
            if self.llm_config is not None
            else None
        )
        self.llm_settings = llm_settings or configured_settings
        if llm_provider is not None and self.llm_settings is None:
            self.llm_settings = AgentLLMSettings(provider="custom", model="custom")
        self.llm_provider = (
            llm_provider
            if llm_provider is not None
            else create_provider(self.llm_config, role.value)
        )
        self._llm_metadata: dict[str, dict[str, Any]] = {}

    def bind(self, registry: ArtifactRegistry) -> None:
        """Bind this agent to an artifact registry and register it."""
        self.registry = registry
        registry.register_agent(self.agent)

    @abstractmethod
    def execute(self, task: Task, story: Story) -> list[Artifact]:
        """Execute a task and return produced artifacts.

        Agents can augment their deterministic artifacts with guidance from a
        configured LLM provider.
        """
        ...

    def produce_artifact(
        self,
        artifact_type: ArtifactType,
        name: str,
        content: Any,
        story: Story,
        task: Task,
    ) -> Artifact:
        """Create an artifact for the workflow engine to register.

        Agents are producers only.  Registration is owned by the execution
        layer so one artifact has one authoritative registration point.
        """
        llm_metadata = self._llm_metadata.get(task.id)
        return Artifact(
            artifact_type=artifact_type,
            name=name,
            content=content,
            produced_by=self.agent.id,
            story_id=story.id,
            task_id=task.id,
            metadata={"llm": dict(llm_metadata)} if llm_metadata else {},
        )

    def prepare_execution(self, task: Task, story: Story, objective: str) -> str | None:
        """Ask the configured LLM for task guidance and retain auditable metadata.

        Template artifacts remain the offline fallback when no configured
        provider is available.  Provider failures are intentionally allowed to
        reach the workflow retry wrapper rather than being hidden.
        """
        cached_metadata = self._llm_metadata.get(task.id)
        if cached_metadata is not None:
            response = cached_metadata.get("response")
            return response if isinstance(response, str) else None
        if self.llm_provider is None or self.llm_settings is None:
            return None

        request = LLMRequest(
            role=self.agent.role.value,
            model=self.llm_settings.model,
            system_prompt=self.llm_settings.system_prompt,
            prompt=(
                f"Story: {story.title}\n"
                f"Description: {story.description}\n"
                f"Task: {task.title}\n"
                f"Task description: {task.description}\n"
                f"Objective: {objective}"
            ),
            temperature=self.llm_settings.temperature,
            max_tokens=self.llm_settings.max_tokens,
        )
        response = self.llm_provider.generate(request)
        self._llm_metadata[task.id] = {
            "provider": self.llm_settings.provider,
            "model": self.llm_settings.model,
            "response": response,
        }
        return response

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.agent.name!r}, role={self.agent.role.value})"
