"""Orchestrator — wires up agents, stories, and the engine for full pipeline execution."""

from __future__ import annotations

import logging
from typing import Any

from rubric.engine.workflow import WorkflowEngine
from rubric.models.story import (
    Story, Task, StoryState, TaskPriority, TaskStatus,
)
from rubric.models.agent import Role
from rubric.models.artifacts import ArtifactType
from rubric.agents import (
    ProductOwnerAgent,
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent,
    TestWriterAgent,
    DevOpsAgent,
    ScrumMasterAgent,
)

logger = logging.getLogger(__name__)


def create_default_team() -> list[Any]:
    """Create the default team of agents with one of each role."""
    return [
        ProductOwnerAgent(name="Alice PO"),
        ArchitectAgent(name="Bob Architect"),
        ScrumMasterAgent(name="Grace Planner"),
        DeveloperAgent(name="Charlie Dev"),
        ReviewerAgent(name="Diana Reviewer"),
        TestWriterAgent(name="Eve TestWriter"),
        DevOpsAgent(name="Frank DevOps"),
    ]


def find_agent_obj(agents: list[Any], agent_id: str) -> Any | None:
    """Find the BaseAgent wrapper for a given agent ID."""
    for agent_obj in agents:
        if agent_obj.agent.id == agent_id:
            return agent_obj
    return None


def run_full_pipeline(
    title: str,
    description: str,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    """Run a complete story through the full delivery pipeline.

    The flow:
    1. INCEPTION   — PO defines story + acceptance criteria
    2. PLANNING    — Scrum Master decomposes into small tasks with TDD substeps
    3. DESIGN      — Architect designs architecture, API, data model
    4. IMPLEMENTATION — Developer follows Red→Green→Refactor for each task
    5. REVIEW      — Reviewer performs code review
    6. ACCEPTANCE  — Test Writer runs end-user acceptance tests
    7. INTEGRATION — DevOps sets up CI/CD and deploys
    8. DELIVERY    — Release notes and documentation
    """
    # 1. Create engine and team
    engine = WorkflowEngine()
    agents = create_default_team()
    for agent in agents:
        agent.bind(engine)

    # 2. Create story
    story = engine.create_story(title=title, description=description)
    if acceptance_criteria:
        story.acceptance_criteria = acceptance_criteria

    # ── INCEPTION ─────────────────────────────────────────────────────
    engine.transition_story(story.id, StoryState.PLANNING, "Story created, entering planning")

    # PO defines acceptance criteria
    po_agent = next(a for a in agents if isinstance(a, ProductOwnerAgent))
    inception_task = Task(
        title="Define acceptance criteria",
        description="Product Owner defines what done looks like",
        required_role="product_owner",
        priority=TaskPriority.HIGH,
    )
    story.tasks = [inception_task]
    agent = engine.scheduler.find_best_agent(inception_task, list(engine.agents.values()), "inception")
    if agent:
        engine.scheduler.assign_task(inception_task, agent)
        artifacts = po_agent.execute(inception_task, story)
        for art in artifacts:
            engine.add_artifact(art)
    engine.complete_task(story.id, inception_task.id)

    # ── PLANNING ──────────────────────────────────────────────────────
    # Scrum Master decomposes story into small tasks with TDD substeps
    planner = next(a for a in agents if isinstance(a, ScrumMasterAgent))
    planning_task = Task(
        title="Break down into tasks",
        description="Decompose into small TDD tasks",
        required_role="scrum_master",
        priority=TaskPriority.HIGH,
    )
    story.tasks.append(planning_task)
    agent = engine.scheduler.find_best_agent(planning_task, list(engine.agents.values()), "planning")
    if agent:
        engine.scheduler.assign_task(planning_task, agent)
        # Scrum Master plans the story — produces granular tasks
        planned_tasks = planner.plan_story(story)
        # Replace the placeholder tasks with the planned ones
        story.tasks = [planning_task] + planned_tasks
        artifacts = planner.execute(planning_task, story)
        for art in artifacts:
            engine.add_artifact(art)
    engine.complete_task(story.id, planning_task.id)

    logger.info(
        f"Planning complete: {len(story.tasks)} tasks, "
        f"{sum(t.total_steps for t in story.tasks)} TDD substeps"
    )

    # ── DESIGN ────────────────────────────────────────────────────────
    if story.state != StoryState.DESIGN:
        engine.transition_story(story.id, StoryState.DESIGN, "Entering design stage")

    architect = next(a for a in agents if isinstance(a, ArchitectAgent))
    design_tasks = [
        Task(
            title="Design system architecture",
            description="Architect designs the system architecture",
            required_role="architect",
            priority=TaskPriority.HIGH,
        ),
        Task(
            title="Design API endpoints",
            description="Architect defines the API contract",
            required_role="architect",
            priority=TaskPriority.MEDIUM,
        ),
        Task(
            title="Design data model",
            description="Architect designs the data model and relationships",
            required_role="architect",
            priority=TaskPriority.MEDIUM,
        ),
    ]
    story.tasks.extend(design_tasks)
    for dt in design_tasks:
        agent = engine.scheduler.find_best_agent(dt, list(engine.agents.values()), "design")
        if agent:
            engine.scheduler.assign_task(dt, agent)
            artifacts = architect.execute(dt, story)
            for art in artifacts:
                engine.add_artifact(art)
        engine.complete_task(story.id, dt.id)

    # ── IMPLEMENTATION (TDD) ──────────────────────────────────────────
    if story.state != StoryState.IMPLEMENTATION:
        engine.transition_story(story.id, StoryState.IMPLEMENTATION, "Entering implementation stage")

    developer = next(a for a in agents if isinstance(a, DeveloperAgent))
    # Execute each task through its TDD substeps
    for task in story.tasks:
        if task.status == TaskStatus.DONE:
            continue
        if task.required_role != "developer":
            continue
        if not task.steps:
            continue

        agent = engine.scheduler.find_best_agent(task, list(engine.agents.values()), "implementation")
        if agent:
            engine.scheduler.assign_task(task, agent)
            # Drive Red→Green→Refactor for this task
            artifacts = engine.execute_task_tdd(story.id, task.id, developer)

    # ── REVIEW ────────────────────────────────────────────────────────
    if story.state != StoryState.REVIEW:
        engine.transition_story(story.id, StoryState.REVIEW, "Entering review stage")

    reviewer = next(a for a in agents if isinstance(a, ReviewerAgent))
    review_task = Task(
        title="Code review",
        description="Reviewer performs code review on all implementation",
        required_role="reviewer",
        priority=TaskPriority.HIGH,
    )
    story.tasks.append(review_task)
    agent = engine.scheduler.find_best_agent(review_task, list(engine.agents.values()), "review")
    if agent:
        engine.scheduler.assign_task(review_task, agent)
        artifacts = reviewer.execute(review_task, story)
        for art in artifacts:
            engine.add_artifact(art)
    engine.complete_task(story.id, review_task.id)

    # ── ACCEPTANCE ────────────────────────────────────────────────────
    if story.state != StoryState.ACCEPTANCE:
        engine.transition_story(story.id, StoryState.ACCEPTANCE, "Entering acceptance stage")

    test_writer = next(a for a in agents if isinstance(a, TestWriterAgent))
    acceptance_task = Task(
        title="Write and run end-user acceptance tests",
        description="Test Writer validates feature from user perspective",
        required_role="test_writer",
        priority=TaskPriority.HIGH,
    )
    story.tasks.append(acceptance_task)
    agent = engine.scheduler.find_best_agent(acceptance_task, list(engine.agents.values()), "acceptance")
    if agent:
        engine.scheduler.assign_task(acceptance_task, agent)
        artifacts = test_writer.execute(acceptance_task, story)
        for art in artifacts:
            engine.add_artifact(art)
    engine.complete_task(story.id, acceptance_task.id)

    # ── INTEGRATION ───────────────────────────────────────────────────
    if story.state != StoryState.INTEGRATION:
        engine.transition_story(story.id, StoryState.INTEGRATION, "Entering integration stage")

    devops = next(a for a in agents if isinstance(a, DevOpsAgent))
    integration_task = Task(
        title="Set up CI pipeline and deploy to staging",
        description="DevOps creates CI/CD pipeline and deploys to staging",
        required_role="devops",
        priority=TaskPriority.HIGH,
    )
    story.tasks.append(integration_task)
    agent = engine.scheduler.find_best_agent(integration_task, list(engine.agents.values()), "integration")
    if agent:
        engine.scheduler.assign_task(integration_task, agent)
        artifacts = devops.execute(integration_task, story)
        for art in artifacts:
            engine.add_artifact(art)
    engine.complete_task(story.id, integration_task.id)

    # ── DELIVERY ──────────────────────────────────────────────────────
    if story.state != StoryState.DELIVERY:
        engine.transition_story(story.id, StoryState.DELIVERY, "Entering delivery stage")

    delivery_task = Task(
        title="Create release notes and documentation",
        description="DevOps and PO create release documentation",
        required_role="devops",
        priority=TaskPriority.MEDIUM,
    )
    story.tasks.append(delivery_task)
    agent = engine.scheduler.find_best_agent(delivery_task, list(engine.agents.values()), "delivery")
    if agent:
        engine.scheduler.assign_task(delivery_task, agent)
        artifacts = devops.execute(delivery_task, story)
        for art in artifacts:
            engine.add_artifact(art)
    engine.complete_task(story.id, delivery_task.id)

    # ── DONE ──────────────────────────────────────────────────────────
    engine.transition_story(story.id, StoryState.DONE, "All stages complete")

    return {
        "story": engine.story_summary(story.id),
        "artifacts": [a.summary() for a in engine.get_artifacts_for_story(story.id)],
        "engine_status": engine.status(),
    }
