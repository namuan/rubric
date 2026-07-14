"""Example: Run a full story through the multi-agent TDD workflow.

Usage:
    python examples/basic_story.py
"""

import json
import logging
import sys
import os

# Ensure src is on the path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rubric.orchestrator import run_full_pipeline
from rubric.engine.workflow import WorkflowEngine
from rubric.orchestrator import create_default_team, find_agent_obj
from rubric.models.story import Task, StoryState, TaskPriority


def example_simple() -> None:
    """Run a story through the full pipeline via the orchestrator."""
    print("\n>>> EXAMPLE 1: Full Pipeline via Orchestrator (TDD + Acceptance Tests)\n")

    result = run_full_pipeline(
        title="User Authentication",
        description="Implement a JWT-based authentication system for the API",
        acceptance_criteria=[
            "Users can register with email and password",
            "Users can log in and receive a JWT token",
            "Protected routes reject requests without a valid token",
        ],
    )

    story = result["story"]
    print(f"  Story:     {story['title']} ({story['id']})")
    print(f"  State:     {story['state']}")
    print(f"  Progress:  {story['progress']}")
    print(f"  Tasks:     {story['tasks_completed']}/{story['tasks_total']}")
    print(f"  TDD Steps: {story['tdd_steps_completed']}/{story['tdd_steps_total']}")
    print(f"  Artifacts: {story['artifacts']}")
    print()
    for art in result["artifacts"]:
        print(f"    - {art}")
    print()


def example_tdd_detail() -> None:
    """Show TDD substep detail for each task."""
    print("\n>>> EXAMPLE 2: TDD Substep Detail\n")

    result = run_full_pipeline(
        title="Shopping Cart",
        description="E-commerce shopping cart with add/remove/checkout",
        acceptance_criteria=[
            "User can add items to cart",
            "User can remove items from cart",
            "Cart shows correct total price",
        ],
    )

    story_result = result["story"]
    print(f"  Story: {story_result['title']}")
    print(f"  TDD Steps: {story_result['tdd_steps_completed']}/{story_result['tdd_steps_total']}")
    print()

    # Show task breakdown with TDD steps
    from rubric.orchestrator import create_default_team
    # The artifacts tell the story — let's show them grouped by type
    artifact_types = {}
    for art_str in result["artifacts"]:
        prefix = art_str.split("]")[0].strip("[")
        artifact_types.setdefault(prefix, []).append(art_str)

    print("  Artifacts by type:")
    for atype, arts in artifact_types.items():
        print(f"    {atype}: {len(arts)}")
    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    example_simple()
    example_tdd_detail()
