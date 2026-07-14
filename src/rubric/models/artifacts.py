"""Artifacts produced during workflow execution."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """Types of artifacts produced by agents."""

    # Inception
    STORY_BRIEF = "story_brief"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"

    # Planning
    TASK_BREAKDOWN = "task_breakdown"
    SPRINT_PLAN = "sprint_plan"

    # Design
    ARCHITECTURE_DIAGRAM = "architecture_diagram"
    API_SPEC = "api_spec"
    DATA_MODEL = "data_model"
    TECH_DESIGN = "tech_design"

    # Implementation
    SOURCE_CODE = "source_code"
    MIGRATION = "migration"
    CONFIG = "config"

    # Review
    REVIEW_FEEDBACK = "review_feedback"
    REFACTOR_SUGGESTION = "refactor_suggestion"

    # Testing
    TEST_PLAN = "test_plan"
    TEST_CODE = "test_code"
    TEST_REPORT = "test_report"

    # Integration
    DEPLOYMENT_CONFIG = "deployment_config"
    CI_CONFIG = "ci_config"

    # Delivery
    CHANGELOG = "changelog"
    DOCUMENTATION = "documentation"
    RELEASE_NOTES = "release_notes"


class Artifact(BaseModel):
    """A deliverable produced by an agent during the workflow."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    artifact_type: ArtifactType
    name: str
    content: Any = None  # Flexible — can be text, dict, code, etc.
    produced_by: str | None = None  # Agent ID
    story_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def summary(self) -> str:
        """Human-readable summary of this artifact."""
        preview = ""
        if isinstance(self.content, str):
            preview = self.content[:100]
        elif isinstance(self.content, dict):
            preview = str(list(self.content.keys()))
        elif self.content is not None:
            preview = str(type(self.content).__name__)
        return f"[{self.artifact_type.value}] {self.name}: {preview}"
