"""JSON-lines event consumer for workflow observability."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rubric.engine.workflow import WorkflowEvent


class EventLogger:
    """Append each workflow event to a durable JSON-lines file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def __call__(self, event: WorkflowEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event.event_type,
            "story_id": event.story_id,
            "data": event.data,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
