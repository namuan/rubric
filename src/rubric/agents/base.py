"""Base agent class — foundation for all role-specific agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from rubric.models.agent import Agent, Role
from rubric.models.story import Task, Story
from rubric.models.artifacts import Artifact, ArtifactType
from rubric.engine.workflow import WorkflowEngine

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for workflow agents.

    Subclass this to implement role-specific behavior.
    The `execute` method is the core — it defines what the agent
    actually does when given a task.
    """

    def __init__(self, name: str, role: Role, **kwargs: Any):
        self.agent = Agent(name=name, role=role, **kwargs)
        self.engine: WorkflowEngine | None = None

    def bind(self, engine: WorkflowEngine) -> None:
        """Bind this agent to a workflow engine and register it."""
        self.engine = engine
        engine.register_agent(self.agent)

    @abstractmethod
    def execute(self, task: Task, story: Story) -> list[Artifact]:
        """Execute a task and return produced artifacts.

        This is where the actual agent logic lives — in a real system,
        this would call an LLM or other AI backend. For now, agents
        produce template artifacts based on their role.
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
        artifact = Artifact(
            artifact_type=artifact_type,
            name=name,
            content=content,
            produced_by=self.agent.id,
            story_id=story.id,
            task_id=task.id,
        )
        return artifact

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.agent.name!r}, role={self.agent.role.value})"
