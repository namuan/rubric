"""Test Writer agent — writes end-user acceptance tests for a story."""

from __future__ import annotations

from rubric.agents.base import BaseAgent
from rubric.models.agent import Role
from rubric.models.story import Task, Story
from rubric.models.artifacts import Artifact, ArtifactType


class TestWriterAgent(BaseAgent):
    """The Test Writer creates end-user acceptance tests.

    These are NOT unit tests or internal quality checks.
    They are user-facing tests that verify the feature works
    from the end user's perspective — like E2E or acceptance tests.

    Responsibilities:
    - Write acceptance test plans based on acceptance criteria
    - Produce end-user test code (e.g. Playwright, pytest-bdd, etc.)
    - Run acceptance tests and produce reports
    - Validate that the delivered feature meets user expectations
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(self, name: str = "Test Writer", **kwargs):
        super().__init__(
            name=name,
            role=Role.TEST_WRITER,
            capabilities=[
                "acceptance_testing",
                "e2e_testing",
                "test_planning",
                "user_story_validation",
            ],
            **kwargs,
        )

    def execute(self, task: Task, story: Story) -> list[Artifact]:
        artifacts = []

        title_lower = task.title.lower()

        # Write end-user acceptance test plan
        if "acceptance" in title_lower or "plan" in title_lower or "test" in title_lower:
            plan = self._write_acceptance_plan(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.TEST_PLAN,
                    f"Acceptance Test Plan: {story.title}",
                    plan,
                    story,
                    task,
                )
            )

        # Write end-user test code
        if "test" in title_lower or "write" in title_lower:
            test_code = self._write_acceptance_tests(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.TEST_CODE,
                    f"Acceptance Tests: {story.title}",
                    test_code,
                    story,
                    task,
                )
            )

        # Run tests and produce report
        if "run" in title_lower or "report" in title_lower or not artifacts:
            report = self._run_acceptance_tests(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.TEST_REPORT,
                    f"Acceptance Report: {story.title}",
                    report,
                    story,
                    task,
                )
            )

        return artifacts

    def _write_acceptance_plan(self, story: Story) -> dict:
        """Produce an end-user acceptance test plan based on acceptance criteria."""
        return {
            "story_id": story.id,
            "title": story.title,
            "test_perspective": "end_user",
            "approach": "Given/When/Then scenarios based on acceptance criteria",
            "scenarios": [
                {
                    "id": f"AC-{i+1}",
                    "criterion": criterion,
                    "given": f"The user is in the application context for '{story.title}'",
                    "when": f"The user performs the action described in: {criterion}",
                    "then": f"The expected outcome is: {criterion}",
                    "type": "acceptance",
                }
                for i, criterion in enumerate(story.acceptance_criteria)
            ]
            or [
                {
                    "id": "AC-1",
                    "criterion": f"Basic functionality for {story.title} works end-to-end",
                    "given": "The user is in the application",
                    "when": "The user uses the feature",
                    "then": "The feature works as expected",
                    "type": "acceptance",
                }
            ],
            "environment": "staging",
            "tools": ["playwright", "pytest-bdd"],
        }

    def _write_acceptance_tests(self, story: Story) -> str:
        """Produce end-user acceptance test code."""
        slug = story.title.lower().replace(" ", "_").replace("-", "_")
        criteria_blocks = "\n\n".join(
            f'    def test_acceptance_criterion_{i+1}(self):\n'
            f'        """\n'
            f'        Criterion: {criterion}\n'
            f'        Given the user is in the application\n'
            f'        When the user performs the required action\n'
            f'        Then the expected outcome is achieved\n'
            f'        """\n'
            f"        # End-user acceptance test for: {criterion}\n"
            f"        assert True  # Will be replaced with actual E2E steps"
            for i, criterion in enumerate(story.acceptance_criteria)
        ) or (
            '    def test_feature_works_end_to_end(self):\n'
            f'        """Verify {story.title} works from the user perspective."""\n'
            f"        assert True  # Placeholder for E2E test"
        )

        return (
            f'"""End-User Acceptance Tests for {story.title}"""\n'
            f"\n"
            f"import pytest\n"
            f"\n"
            f"\n"
            f"class Test{slug.replace('_', ' ').title().replace(' ', '')}Acceptance:\n"
            f'    """\n'
            f"    End-user acceptance tests.\n"
            f"    These verify the feature works from the user's perspective.\n"
            f"    NOT unit tests — these are full user-flow validations.\n"
            f'    """\n'
            f"\n"
            f"{criteria_blocks}\n"
        )

    def _run_acceptance_tests(self, story: Story) -> dict:
        """Simulate running end-user acceptance tests."""
        total = max(len(story.acceptance_criteria), 1)
        return {
            "story_id": story.id,
            "perspective": "end_user",
            "total": total,
            "passed": total,
            "failed": 0,
            "skipped": 0,
            "result": "ALL ACCEPTANCE CRITERIA MET",
            "duration_ms": 3200,
            "environment": "staging",
        }
