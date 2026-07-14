"""Agent and Role definitions."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Agent roles in the workflow."""

    PRODUCT_OWNER = "product_owner"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    TEST_WRITER = "test_writer"  # Writes end-user acceptance tests
    DEVOPS = "devops"
    SCRUM_MASTER = "scrum_master"


# Maps workflow stages to which roles are primary actors
STAGE_RESPONSIBILITIES: dict[str, list[Role]] = {
    "inception": [Role.PRODUCT_OWNER],
    "planning": [Role.PRODUCT_OWNER, Role.ARCHITECT, Role.SCRUM_MASTER],
    "design": [Role.ARCHITECT, Role.DEVELOPER],
    "implementation": [Role.DEVELOPER],  # Developer does TDD: Red→Green→Refactor
    "review": [Role.REVIEWER],
    "acceptance": [Role.TEST_WRITER],  # End-user acceptance tests
    "integration": [Role.DEVOPS, Role.DEVELOPER],
    "delivery": [Role.DEVOPS, Role.PRODUCT_OWNER],
}


class Agent(BaseModel):
    """An agent that can pick up and execute tasks."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    role: Role
    capabilities: list[str] = Field(default_factory=list)
    max_concurrent_tasks: int = 1
    active_tasks: list[str] = Field(default_factory=list)
    completed_tasks: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def available(self) -> bool:
        return len(self.active_tasks) < self.max_concurrent_tasks

    @property
    def utilization(self) -> float:
        if self.max_concurrent_tasks == 0:
            return 0.0
        return len(self.active_tasks) / self.max_concurrent_tasks

    def can_handle(self, required_role: str | None = None) -> bool:
        """Check if this agent can handle a task with a given role requirement."""
        if required_role is None:
            return True
        return self.role.value == required_role

    def pick_up_task(self, task_id: str) -> None:
        if not self.available:
            raise RuntimeError(f"Agent {self.name} is at capacity")
        self.active_tasks.append(task_id)

    def finish_task(self, task_id: str) -> None:
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)
            self.completed_tasks += 1
