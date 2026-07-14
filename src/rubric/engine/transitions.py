"""Stage transition rules and gates."""

from __future__ import annotations

from typing import Any

from rubric.models.story import Story, StoryState, TaskStatus


class TransitionGate:
    """A condition that must be satisfied before a story can transition.

    Gates allow enforcing quality checks at stage boundaries —
    e.g., all tasks complete, minimum artifacts produced, etc.
    """

    def __init__(self, name: str, check: Any, description: str = ""):
        self.name = name
        self._check = check  # Callable[[Story], bool]
        self.description = description or name

    def evaluate(self, story: Story) -> bool:
        return self._check(story)

    def __repr__(self) -> str:
        return f"TransitionGate({self.name})"


# ── Built-in Gates ────────────────────────────────────────────────────

ALL_TASKS_COMPLETE = TransitionGate(
    name="all_tasks_complete",
    check=lambda story: all(t.status == TaskStatus.DONE for t in story.tasks) if story.tasks else True,
    description="All tasks for the current stage must be complete",
)

HAS_ARTIFACTS = TransitionGate(
    name="has_artifacts",
    check=lambda story: len(story.artifacts) > 0,
    description="Story must have at least one artifact",
)

HAS_ACCEPTANCE_CRITERIA = TransitionGate(
    name="has_acceptance_criteria",
    check=lambda story: len(story.acceptance_criteria) > 0,
    description="Story must have acceptance criteria defined",
)

MIN_PROGRESS = TransitionGate(
    name="min_progress",
    check=lambda story: story.progress >= 0.5,
    description="At least 50% of tasks must be complete",
)


# ── Stage Gate Configuration ──────────────────────────────────────────

DEFAULT_STAGE_GATES: dict[StoryState, list[TransitionGate]] = {
    StoryState.INCEPTION: [HAS_ACCEPTANCE_CRITERIA],
    StoryState.PLANNING: [ALL_TASKS_COMPLETE],
    StoryState.DESIGN: [ALL_TASKS_COMPLETE, HAS_ARTIFACTS],
    StoryState.IMPLEMENTATION: [ALL_TASKS_COMPLETE],
    StoryState.REVIEW: [ALL_TASKS_COMPLETE],
    StoryState.ACCEPTANCE: [ALL_TASKS_COMPLETE],
    StoryState.INTEGRATION: [ALL_TASKS_COMPLETE],
    StoryState.DELIVERY: [ALL_TASKS_COMPLETE, HAS_ARTIFACTS],
}


def validate_transition(
    story: Story,
    target_state: StoryState,
    gates: dict[StoryState, list[TransitionGate]] | None = None,
) -> tuple[bool, list[str]]:
    """Validate whether a story can transition, returning (ok, failure_reasons)."""
    gates = gates or DEFAULT_STAGE_GATES
    required = gates.get(story.state, [])
    failures = []

    for gate in required:
        if not gate.evaluate(story):
            failures.append(f"Gate '{gate.name}' failed: {gate.description}")

    return (len(failures) == 0, failures)
