"""DevOps agent — handles deployment, CI/CD, and infrastructure."""

from __future__ import annotations

from rubric.agents.base import BaseAgent
from rubric.models.agent import Role
from rubric.models.story import Task, Story
from rubric.models.artifacts import Artifact, ArtifactType


class DevOpsAgent(BaseAgent):
    """The DevOps agent manages deployment pipelines and infrastructure.

    Responsibilities:
    - Set up CI/CD pipelines
    - Configure deployment
    - Create infrastructure configs
    - Manage releases
    """

    def __init__(self, name: str = "DevOps", **kwargs):
        super().__init__(
            name=name,
            role=Role.DEVOPS,
            capabilities=["ci_cd", "deployment", "infrastructure", "release_management"],
            **kwargs,
        )

    def execute(self, task: Task, story: Story) -> list[Artifact]:
        artifacts = []

        title_lower = task.title.lower()

        if "deploy" in title_lower or "ci" in title_lower or "pipeline" in title_lower:
            ci_config = self._create_ci_config(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.CI_CONFIG,
                    f"CI Pipeline: {story.title}",
                    ci_config,
                    story,
                    task,
                )
            )
            deploy_config = self._create_deployment_config(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.DEPLOYMENT_CONFIG,
                    f"Deployment: {story.title}",
                    deploy_config,
                    story,
                    task,
                )
            )

        if "release" in title_lower:
            release = self._create_release(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.RELEASE_NOTES,
                    f"Release: {story.title}",
                    release,
                    story,
                    task,
                )
            )

        # Default
        if not artifacts:
            ci_config = self._create_ci_config(story)
            artifacts.append(
                self.produce_artifact(
                    ArtifactType.CI_CONFIG,
                    f"CI Pipeline: {story.title}",
                    ci_config,
                    story,
                    task,
                )
            )

        return artifacts

    def _create_ci_config(self, story: Story) -> dict:
        return {
            "pipeline": f"{story.title.lower().replace(' ', '-')}-pipeline",
            "triggers": ["push_to_main", "pull_request"],
            "stages": [
                {"name": "lint", "command": "ruff check ."},
                {"name": "test", "command": "pytest tests/"},
                {"name": "build", "command": "python -m build"},
                {"name": "deploy_staging", "command": "deploy --env staging"},
            ],
            "notifications": {"slack": "#deploys", "email": "team@example.com"},
        }

    def _create_deployment_config(self, story: Story) -> dict:
        return {
            "service": story.title.lower().replace(" ", "-"),
            "environments": {
                "staging": {"replicas": 1, "cpu": "0.5", "memory": "512Mi"},
                "production": {"replicas": 3, "cpu": "1.0", "memory": "1Gi"},
            },
            "health_check": "/health",
            "rollback_strategy": "automatic",
        }

    def _create_release(self, story: Story) -> dict:
        return {
            "version": "1.0.0",
            "title": story.title,
            "changes": [story.description],
            "breaking_changes": [],
            "migration_required": False,
        }
