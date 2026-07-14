"""Developer agent — follows Red-Green-Refactor for each task step."""

from __future__ import annotations

from rubric.agents.base import BaseAgent
from rubric.models.agent import Role
from rubric.models.story import Task, TaskStep, TaskStepType, Story
from rubric.models.artifacts import Artifact, ArtifactType


class DeveloperAgent(BaseAgent):
    """The Developer implements features using TDD (Red-Green-Refactor).

    For each task, the planner decomposes the work into small steps.
    The developer executes each step in order:
      1. RED    — write a failing test for one specific behavior
      2. GREEN  — write minimum code to make that test pass
      3. REFACTOR — clean up while keeping all tests green

    Each step is small enough that the developer doesn't need to
    hold the full story context — just the one behavior being worked on.
    """

    def __init__(self, name: str = "Developer", **kwargs):
        super().__init__(
            name=name,
            role=Role.DEVELOPER,
            capabilities=[
                "tdd",
                "coding",
                "migrations",
                "configuration",
                "refactoring",
            ],
            **kwargs,
        )

    def execute_step(self, step: TaskStep, task: Task, story: Story) -> Artifact:
        """Execute a single TDD substep and return the produced artifact.

        This is the granular method — each call handles ONE small step
        so the agent doesn't need to remember a lot of context.
        """
        if step.step_type == TaskStepType.RED:
            return self._write_failing_test(step, task, story)
        elif step.step_type == TaskStepType.GREEN:
            return self._write_minimum_code(step, task, story)
        elif step.step_type == TaskStepType.REFACTOR:
            return self._refactor(step, task, story)
        raise ValueError(f"Unknown step type: {step.step_type}")

    def execute(self, task: Task, story: Story) -> list[Artifact]:
        """Execute all TDD steps for a task (fallback for legacy interface)."""
        artifacts = []
        title_lower = task.title.lower()

        # Handle non-TDD tasks (migrations, configs)
        if "migrat" in title_lower:
            migration = self._create_migration(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.MIGRATION,
                    f"Migration: {story.title}",
                    migration,
                    story,
                    task,
                )
            )
        elif "config" in title_lower or "setup" in title_lower:
            config = self._create_config(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.CONFIG,
                    f"Config: {story.title}",
                    config,
                    story,
                    task,
                )
            )
        else:
            # Default: run through TDD substeps
            for step in task.steps:
                artifact = self.execute_step(step, task, story)
                artifacts.append(artifact)

        return artifacts

    def _write_failing_test(self, step: TaskStep, task: Task, story: Story) -> Artifact:
        """RED: Write a failing test for one specific behavior."""
        slug = story.title.lower().replace(" ", "_").replace("-", "_")
        test_code = (
            f'"""RED: Failing test for {step.title}"""\n'
            f"\n"
            f"import pytest\n"
            f"\n"
            f"\n"
            f"def test_{slug}():\n"
            f'    """\n'
            f"    Step: {step.title}\n"
            f"    {step.description}\n"
            f"    Expected: This test should FAIL until green step is done.\n"
            f'    """\n'
            f"    result = do_{slug}_thing()\n"
            f"    assert result == 'expected'  # Will fail — not implemented yet\n"
        )
        artifact = self.produce_artifact(
            ArtifactType.TEST_CODE,
            f"RED: {step.title}",
            test_code,
            story,
            task,
        )
        step.complete(artifact.id)
        return artifact

    def _write_minimum_code(self, step: TaskStep, task: Task, story: Story) -> Artifact:
        """GREEN: Write the minimum code to make the test pass."""
        slug = story.title.lower().replace(" ", "_").replace("-", "_")
        code = (
            f'"""GREEN: Implementation for {step.title}"""\n'
            f"\n"
            f"\n"
            f"def do_{slug}_thing():\n"
            f'    """Minimum implementation to pass the test."""\n'
            f"    # {step.description}\n"
            f"    return 'expected'\n"
        )
        artifact = self.produce_artifact(
            ArtifactType.SOURCE_CODE,
            f"GREEN: {step.title}",
            code,
            story,
            task,
        )
        step.complete(artifact.id)
        return artifact

    def _refactor(self, step: TaskStep, task: Task, story: Story) -> Artifact:
        """REFACTOR: Clean up while keeping all tests green."""
        slug = story.title.lower().replace(" ", "_").replace("-", "_")
        code = (
            f'"""REFACTOR: Clean implementation for {step.title}"""\n'
            f"\n"
            f"\n"
            f"def do_{slug}_thing():\n"
            f'    """Refactored implementation — all tests still green."""\n'
            f"    # {step.description}\n"
            f"    # Improved naming, extracted helpers, removed duplication\n"
            f"    return 'expected'\n"
        )
        artifact = self.produce_artifact(
            ArtifactType.SOURCE_CODE,
            f"REFACTOR: {step.title}",
            code,
            story,
            task,
        )
        step.complete(artifact.id)
        return artifact

    def _create_migration(self, story: Story) -> dict:
        return {
            "version": f"001_{story.id}",
            "operations": [
                {"type": "create_table", "name": story.title.lower().replace(" ", "_")},
            ],
            "rollback": f"DROP TABLE IF EXISTS {story.title.lower().replace(' ', '_')}",
        }

    def _create_config(self, story: Story) -> dict:
        return {
            "service": story.title.lower().replace(" ", "_"),
            "version": "1.0.0",
            "settings": {
                "log_level": "INFO",
                "max_retries": 3,
                "timeout_seconds": 30,
            },
        }
