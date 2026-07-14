"""Scrum Master / Planner — breaks stories into small, atomic tasks with TDD substeps."""

from __future__ import annotations

import logging

from rubric.agents.base import BaseAgent
from rubric.models.agent import Role
from rubric.models.story import (
    Task,
    TaskStep,
    TaskStepType,
    TaskPriority,
    Story,
)
from rubric.models.artifacts import Artifact, ArtifactType

logger = logging.getLogger(__name__)


class ScrumMasterAgent(BaseAgent):
    """The Scrum Master is the planner — decomposes stories into small tasks.

    Key principle: break work into pieces small enough that each agent
    can execute a single step without needing to hold a lot of context.
    Each task gets pre-generated TDD substeps (Red → Green → Refactor).

    Responsibilities:
    - Break stories into small, atomic tasks
    - Generate TDD substeps for each task
    - Set dependencies between tasks
    - Track progress and identify blockers
    """

    def __init__(self, name: str = "Scrum Master", **kwargs):
        super().__init__(
            name=name,
            role=Role.SCRUM_MASTER,
            capabilities=[
                "planning",
                "task_decomposition",
                "tdd_planning",
                "facilitation",
                "blocker_resolution",
            ],
            **kwargs,
        )

    def plan_story(self, story: Story) -> list[Task]:
        """Decompose a story into small tasks, each with TDD substeps.

        This is the core planning logic. It takes a story and produces
        a list of granular tasks where:
        - Each task is a single, focused behavior
        - Each task has Red→Green→Refactor substeps pre-generated
        - Dependencies are wired up so tasks flow in order
        """
        tasks = []
        criteria = story.acceptance_criteria or [f"Feature: {story.title}"]

        # For each acceptance criterion, create a focused task
        for i, criterion in enumerate(criteria):
            task = self._create_task_from_criterion(criterion, i, story)
            tasks.append(task)

        # Wire dependencies: each task depends on the previous
        for idx in range(1, len(tasks)):
            tasks[idx].dependencies = [tasks[idx - 1].id]

        # Add a final integration task that ties everything together
        integration_task = Task(
            title="Integration verification",
            description="Verify all pieces work together end-to-end",
            required_role="developer",
            priority=TaskPriority.HIGH,
            steps=self._tdd_steps("Integration verification", "Verify all pieces work together"),
        )
        if tasks:
            integration_task.dependencies = [tasks[-1].id]
        tasks.append(integration_task)

        logger.info(
            f"Planned {len(tasks)} tasks for story '{story.title}' "
            f"({sum(t.total_steps for t in tasks)} total substeps)"
        )
        return tasks

    def _create_task_from_criterion(
        self, criterion: str, index: int, story: Story
    ) -> Task:
        """Create a single focused task from one acceptance criterion.

        The task is small enough that an agent can execute it
        without needing the full story context.
        """
        # Make the title action-focused and specific
        title = self._derive_task_title(criterion)
        description = (
            f"Implement and verify: {criterion}\n\n"
            f"This is a focused task. Follow the Red→Green→Refactor cycle:"
        )

        task = Task(
            title=title,
            description=description,
            required_role="developer",
            priority=TaskPriority.HIGH,
        )

        # Generate TDD substeps
        task.steps = self._tdd_steps(title, criterion)

        return task

    def _derive_task_title(self, criterion: str) -> str:
        """Turn an acceptance criterion into an action-focused task title."""
        # Keep it short and actionable
        title = criterion.strip()
        # Truncate if too long
        if len(title) > 60:
            title = title[:57] + "..."
        return title

    def _tdd_steps(self, title: str, behavior: str) -> list[TaskStep]:
        """Generate Red→Green→Refactor substeps for a task.

        Each step is atomic — one specific behavior, one test, one change.
        """
        return [
            TaskStep(
                step_type=TaskStepType.RED,
                title=f"RED: Write failing test for '{title}'",
                description=(
                    f"Write a single failing test that captures this behavior:\n"
                    f"  {behavior}\n"
                    f"The test should fail because the behavior is not yet implemented."
                ),
            ),
            TaskStep(
                step_type=TaskStepType.GREEN,
                title=f"GREEN: Implement '{title}'",
                description=(
                    f"Write the minimum code to make the test pass.\n"
                    f"Do not over-engineer — just enough to satisfy:\n"
                    f"  {behavior}"
                ),
            ),
            TaskStep(
                step_type=TaskStepType.REFACTOR,
                title=f"REFACTOR: Clean up '{title}'",
                description=(
                    f"Clean up the code while keeping all tests green.\n"
                    f"Improve naming, extract helpers, remove duplication.\n"
                    f"Behavior: {behavior}"
                ),
            ),
        ]

    def execute(self, task: Task, story: Story) -> list[Artifact]:
        """Execute a planning task — produce task breakdown artifact."""
        artifacts = []

        if "break" in task.title.lower() or "plan" in task.title.lower():
            report = self._status_report(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.TASK_BREAKDOWN,
                    f"Task Breakdown: {story.title}",
                    report,
                    story,
                    task,
                )
            )
        else:
            report = self._status_report(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.STORY_BRIEF,
                    f"Status Report: {story.title}",
                    report,
                    story,
                    task,
                )
            )

        return artifacts

    def _status_report(self, story: Story) -> dict:
        total_steps = sum(t.total_steps for t in story.tasks)
        done_steps = sum(t.completed_steps for t in story.tasks)
        return {
            "story_id": story.id,
            "title": story.title,
            "current_state": story.state.value,
            "progress": f"{story.progress:.0%}",
            "tasks": {
                "total": story.total_tasks,
                "completed": story.completed_tasks,
                "remaining": story.total_tasks - story.completed_tasks,
            },
            "tdd_steps": {
                "total": total_steps,
                "completed": done_steps,
                "remaining": total_steps - done_steps,
            },
            "artifacts_produced": len(story.artifacts),
            "blockers": [],
        }
