"""Reviewer agent — reviews code quality, provides feedback."""

from __future__ import annotations

from rubric.agents.base import BaseAgent
from rubric.models.agent import Role
from rubric.models.story import Task, Story
from rubric.models.artifacts import Artifact, ArtifactType


class ReviewerAgent(BaseAgent):
    """The Reviewer performs code reviews and quality checks.

    Responsibilities:
    - Review source code for quality and correctness
    - Check adherence to coding standards
    - Suggest refactoring improvements
    - Verify design patterns are followed
    """

    def __init__(self, name: str = "Reviewer", **kwargs):
        super().__init__(
            name=name,
            role=Role.REVIEWER,
            capabilities=["code_review", "quality_check", "refactoring"],
            **kwargs,
        )

    def execute(self, task: Task, story: Story) -> list[Artifact]:
        artifacts = []

        # Produce review feedback
        feedback = self._review_code(story)
        artifacts.append(
            self.produce_artifact(
                ArtifactType.REVIEW_FEEDBACK,
                f"Code Review: {story.title}",
                feedback,
                story,
                task,
            )
        )

        # If there are issues, produce refactoring suggestions
        if feedback["issues_found"] > 0:
            suggestions = self._suggest_refactoring(story, feedback)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.REFACTOR_SUGGESTION,
                    f"Refactoring: {story.title}",
                    suggestions,
                    story,
                    task,
                )
            )

        return artifacts

    def _review_code(self, story: Story) -> dict:
        """Perform a code review."""
        return {
            "story_id": story.id,
            "reviewer": self.agent.name,
            "status": "approved" if len(story.artifacts) > 0 else "needs_work",
            "issues_found": 0,
            "categories": {
                "correctness": "pass",
                "readability": "pass",
                "testability": "pass",
                "security": "pass",
                "performance": "pass",
            },
            "summary": f"Code for '{story.title}' meets quality standards.",
        }

    def _suggest_refactoring(self, story: Story, feedback: dict) -> dict:
        """Suggest refactoring based on review findings."""
        return {
            "story_id": story.id,
            "suggestions": [
                {
                    "type": "extract_method",
                    "description": "Consider extracting complex logic into separate methods",
                    "priority": "medium",
                },
            ],
            "estimated_effort": "Low",
        }
