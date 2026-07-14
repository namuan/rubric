"""Core data models: Story, Task, TaskStep, and StoryState."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StoryState(str, Enum):
    """Lifecycle states a story flows through."""

    INCEPTION = "inception"
    PLANNING = "planning"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    ACCEPTANCE = "acceptance"  # End-user tests run here
    INTEGRATION = "integration"
    DELIVERY = "delivery"
    BLOCKED = "blocked"
    DONE = "done"


# Valid transitions: which states can move to which
VALID_TRANSITIONS: dict[StoryState, list[StoryState]] = {
    StoryState.INCEPTION: [StoryState.PLANNING, StoryState.BLOCKED],
    StoryState.PLANNING: [StoryState.DESIGN, StoryState.INCEPTION, StoryState.BLOCKED],
    StoryState.DESIGN: [StoryState.IMPLEMENTATION, StoryState.PLANNING, StoryState.BLOCKED],
    StoryState.IMPLEMENTATION: [StoryState.REVIEW, StoryState.DESIGN, StoryState.BLOCKED],
    StoryState.REVIEW: [StoryState.ACCEPTANCE, StoryState.IMPLEMENTATION, StoryState.BLOCKED],
    StoryState.ACCEPTANCE: [StoryState.INTEGRATION, StoryState.IMPLEMENTATION, StoryState.BLOCKED],
    StoryState.INTEGRATION: [StoryState.DELIVERY, StoryState.ACCEPTANCE, StoryState.BLOCKED],
    StoryState.DELIVERY: [StoryState.DONE, StoryState.INTEGRATION, StoryState.BLOCKED],
    StoryState.BLOCKED: [
        StoryState.INCEPTION,
        StoryState.PLANNING,
        StoryState.DESIGN,
        StoryState.IMPLEMENTATION,
        StoryState.REVIEW,
        StoryState.ACCEPTANCE,
        StoryState.INTEGRATION,
        StoryState.DELIVERY,
    ],
    StoryState.DONE: [],  # Terminal state
}


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskStepType(str, Enum):
    """TDD substep: Red → Green → Refactor."""

    RED = "red"        # Write a failing test
    GREEN = "green"    # Write minimum code to pass
    REFACTOR = "refactor"  # Clean up, keep tests green


class TaskStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskStep(BaseModel):
    """An atomic TDD substep within a task.

    Each task is decomposed into small steps so that an agent
    only needs to focus on one behavior at a time:
      1. RED    — write a failing test for one specific behavior
      2. GREEN  — write the minimum code to make that test pass
      3. REFACTOR — clean up while keeping all tests green
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    step_type: TaskStepType
    title: str
    description: str = ""
    status: TaskStepStatus = TaskStepStatus.PENDING
    assigned_agent: str | None = None
    artifact_id: str | None = None  # Produced artifact (test file, code, etc.)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def complete(self, artifact_id: str | None = None) -> None:
        self.status = TaskStepStatus.DONE
        self.artifact_id = artifact_id
        self.updated_at = datetime.now(timezone.utc)


class Task(BaseModel):
    """A discrete unit of work within a story, decomposed into TDD substeps.

    The planner breaks each task into small enough pieces that an agent
    can execute each step without needing to hold a lot of context.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    stage: str | None = None
    assigned_agent: str | None = None
    blocker_reason: str | None = None
    required_role: str | None = None
    dependencies: list[str] = Field(default_factory=list)  # Task IDs
    steps: list[TaskStep] = Field(default_factory=list)  # TDD substeps
    outputs: list[str] = Field(default_factory=list)  # Artifact IDs
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_ready(self, completed_task_ids: set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        return set(self.dependencies).issubset(completed_task_ids)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == TaskStepStatus.DONE)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def step_progress(self) -> float:
        if not self.steps:
            return 0.0
        return self.completed_steps / self.total_steps

    @property
    def current_step(self) -> TaskStep | None:
        """Get the next pending step, if any."""
        for step in self.steps:
            if step.status == TaskStepStatus.PENDING:
                return step
        return None

    def next_step(self) -> TaskStep | None:
        """Get and advance to the next pending step."""
        step = self.current_step
        if step:
            step.status = TaskStepStatus.IN_PROGRESS
            step.updated_at = datetime.now(timezone.utc)
        return step

    def assign(self, agent_id: str) -> None:
        self.assigned_agent = agent_id
        self.status = TaskStatus.IN_PROGRESS
        self.updated_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        self.status = TaskStatus.DONE
        self.blocker_reason = None
        self.updated_at = datetime.now(timezone.utc)

    def block(self, reason: str) -> None:
        """Mark the task as blocked and retain the reason for operators."""
        self.status = TaskStatus.BLOCKED
        self.blocker_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def all_steps_done(self) -> bool:
        return all(s.status == TaskStepStatus.DONE for s in self.steps) if self.steps else True


class Story(BaseModel):
    """The primary unit of work flowing through the workflow."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    state: StoryState = StoryState.INCEPTION
    tasks: list[Task] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)  # Artifact IDs
    metadata: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def transition(self, new_state: StoryState, reason: str = "") -> None:
        """Move the story to a new state with validation."""
        if new_state not in VALID_TRANSITIONS.get(self.state, []):
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {new_state.value}. "
                f"Valid targets: {[s.value for s in VALID_TRANSITIONS.get(self.state, [])]}"
            )
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        self.history.append({
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "timestamp": self.updated_at.isoformat(),
        })

    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == TaskStatus.DONE)

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def progress(self) -> float:
        """Progress based on completed steps across all tasks."""
        total_steps = sum(t.total_steps for t in self.tasks)
        if total_steps == 0:
            # Fall back to task-level counting
            return 1.0 if self.tasks and self.completed_tasks == self.total_tasks else 0.0
        done_steps = sum(t.completed_steps for t in self.tasks)
        return done_steps / total_steps

    def ready_tasks(self) -> list[Task]:
        """Get tasks that are ready to be worked on (dependencies met, not done)."""
        done_ids = {t.id for t in self.tasks if t.status == TaskStatus.DONE}
        return [
            t
            for t in self.tasks
            if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
            and t.is_ready(done_ids)
        ]
