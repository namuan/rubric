"""JSON-file persistence for the in-memory workflow engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from rubric.models.artifacts import Artifact
from rubric.models.story import Story


class WorkflowSnapshot(BaseModel):
    """A complete, Pydantic-validated engine state snapshot."""

    stories: dict[str, Story] = Field(default_factory=dict)
    artifacts: dict[str, Artifact] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class JsonWorkflowStore:
    """Save and restore validated workflow snapshots atomically."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def save(self, snapshot: WorkflowSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        temporary_path.replace(self.path)

    def load(self) -> WorkflowSnapshot | None:
        if not self.path.is_file():
            return None
        return WorkflowSnapshot.model_validate_json(
            self.path.read_text(encoding="utf-8")
        )
