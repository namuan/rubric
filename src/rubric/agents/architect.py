"""Architect agent — designs system architecture and technical approach."""

from __future__ import annotations

from rubric.agents.base import BaseAgent
from rubric.models.agent import Role
from rubric.models.story import Task, Story
from rubric.models.artifacts import Artifact, ArtifactType


class ArchitectAgent(BaseAgent):
    """The Architect designs the technical approach and system structure.

    Responsibilities:
    - Design system architecture
    - Define API contracts
    - Create data models
    - Make technology decisions
    - Write technical design docs
    """

    def __init__(self, name: str = "Architect", **kwargs):
        super().__init__(
            name=name,
            role=Role.ARCHITECT,
            capabilities=[
                "architecture_design",
                "api_design",
                "data_modeling",
                "tech_design",
            ],
            **kwargs,
        )

    def execute(self, task: Task, story: Story) -> list[Artifact]:
        artifacts = []

        if "architecture" in task.title.lower() or "design" in task.title.lower():
            architecture = self._design_architecture(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.ARCHITECTURE_DIAGRAM,
                    f"Architecture: {story.title}",
                    architecture,
                    story,
                    task,
                )
            )
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.TECH_DESIGN,
                    f"Technical Design: {story.title}",
                    self._write_tech_design(story, architecture),
                    story,
                    task,
                )
            )

        if "api" in task.title.lower():
            api_spec = self._design_api(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.API_SPEC,
                    f"API Spec: {story.title}",
                    api_spec,
                    story,
                    task,
                )
            )

        if "data" in task.title.lower() or "model" in task.title.lower():
            data_model = self._design_data_model(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.DATA_MODEL,
                    f"Data Model: {story.title}",
                    data_model,
                    story,
                    task,
                )
            )

        return artifacts

    def _design_architecture(self, story: Story) -> dict:
        """Produce an architecture design."""
        return {
            "pattern": "layered_architecture",
            "layers": [
                {"name": "presentation", "description": "API/CLI interface"},
                {"name": "application", "description": "Business logic orchestration"},
                {"name": "domain", "description": "Core domain models and rules"},
                {"name": "infrastructure", "description": "Persistence, messaging, external services"},
            ],
            "components": [
                f"Module for: {story.title}",
            ],
            "decisions": [
                "Use dependency injection for testability",
                "Separate read/write paths where possible",
                "Event-driven communication between layers",
            ],
        }

    def _write_tech_design(self, story: Story, architecture: dict) -> dict:
        """Write a technical design document."""
        return {
            "title": f"Technical Design: {story.title}",
            "overview": story.description,
            "architecture_pattern": architecture.get("pattern", "unknown"),
            "modules": architecture.get("layers", []),
            "key_decisions": architecture.get("decisions", []),
            "risks": ["Complexity may increase if requirements change"],
            "estimated_effort": "Medium",
        }

    def _design_api(self, story: Story) -> dict:
        """Design API endpoints."""
        slug = story.title.lower().replace(" ", "_").replace("-", "_")
        return {
            "endpoints": [
                {"method": "GET", "path": f"/api/v1/{slug}", "description": f"List {story.title}"},
                {"method": "POST", "path": f"/api/v1/{slug}", "description": f"Create {story.title}"},
                {"method": "GET", "path": f"/api/v1/{slug}/{{id}}", "description": f"Get {story.title} by ID"},
                {"method": "PUT", "path": f"/api/v1/{slug}/{{id}}", "description": f"Update {story.title}"},
                {"method": "DELETE", "path": f"/api/v1/{slug}/{{id}}", "description": f"Delete {story.title}"},
            ],
            "authentication": "Bearer token",
            "response_format": "JSON",
        }

    def _design_data_model(self, story: Story) -> dict:
        """Design the data model."""
        slug = story.title.lower().replace(" ", "_").replace("-", "_")
        return {
            "entities": [
                {
                    "name": slug,
                    "fields": [
                        {"name": "id", "type": "UUID", "primary_key": True},
                        {"name": "name", "type": "string", "required": True},
                        {"name": "description", "type": "text", "required": False},
                        {"name": "created_at", "type": "timestamp"},
                        {"name": "updated_at", "type": "timestamp"},
                    ],
                    "indexes": ["id", "created_at"],
                }
            ],
            "relationships": [],
        }
