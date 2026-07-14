"""Product Owner agent — defines stories, acceptance criteria, and priorities."""

from __future__ import annotations

from rubric.agents.base import BaseAgent
from rubric.models.agent import Role
from rubric.models.story import Task, Story, TaskPriority
from rubric.models.artifacts import Artifact, ArtifactType


class ProductOwnerAgent(BaseAgent):
    """The Product Owner defines what needs to be built and why.

    Responsibilities:
    - Write stories with clear descriptions
    - Define acceptance criteria
    - Prioritize tasks
    - Validate delivered features against criteria
    """

    def __init__(self, name: str = "Product Owner", **kwargs):
        super().__init__(
            name=name,
            role=Role.PRODUCT_OWNER,
            capabilities=["story_writing", "acceptance_criteria", "prioritization"],
            **kwargs,
        )

    def execute(self, task: Task, story: Story) -> list[Artifact]:
        artifacts = []

        # Enrich story description if this is an inception task
        if task.title.startswith("Define"):
            enriched_description = self._enrich_description(story)
            story.description = enriched_description
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.STORY_BRIEF,
                    f"Story Brief: {story.title}",
                    enriched_description,
                    story,
                    task,
                )
            )

        # Define acceptance criteria
        if task.title.startswith("Define") or "criteria" in task.title.lower():
            criteria = self._define_acceptance_criteria(story)
            story.acceptance_criteria = criteria
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.ACCEPTANCE_CRITERIA,
                    f"Acceptance Criteria: {story.title}",
                    {"criteria": criteria},
                    story,
                    task,
                )
            )

        return artifacts

    def _enrich_description(self, story: Story) -> str:
        """Produce a richer story description."""
        return (
            f"{story.description}\n\n"
            f"## User Story\n"
            f"As a user, I want {story.title.lower()} so that I can achieve my goal.\n\n"
            f"## Business Value\n"
            f"This feature delivers value by addressing the core need described above."
        )

    def _define_acceptance_criteria(self, story: Story) -> list[str]:
        """Generate acceptance criteria for the story."""
        if story.acceptance_criteria:
            return story.acceptance_criteria
        return [
            f"Feature for '{story.title}' is fully implemented",
            "All edge cases are handled",
            "Documentation is updated",
            "Tests pass with >80% coverage",
        ]
