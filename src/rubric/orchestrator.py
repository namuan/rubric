"""Orchestrator — wires agents, stories, and the engine into a delivery pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from rubric.agents import (
    ArchitectAgent,
    DeveloperAgent,
    DevOpsAgent,
    ProductOwnerAgent,
    ReviewerAgent,
    ScrumMasterAgent,
    TestWriterAgent,
)
from rubric.engine.workflow import WorkflowEngine
from rubric.models.artifacts import Artifact
from rubric.models.story import Story, StoryState, Task, TaskPriority

logger = logging.getLogger(__name__)

TaskExecutor = Callable[[Any, Task, Story], list[Artifact]]


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


def _task(
    title: str,
    description: str,
    required_role: str,
    priority: TaskPriority,
    stage: StoryState,
) -> Task:
    return Task(
        title=title,
        description=description,
        required_role=required_role,
        priority=priority,
        stage=stage.value,
    )


def _planning_executor(agent: Any, task: Task, story: Story) -> list[Artifact]:
    """Plan implementation work once, then produce the planning artifact."""
    implementation_tasks = [
        current_task
        for current_task in story.tasks
        if current_task.stage == StoryState.IMPLEMENTATION.value
    ]
    if not implementation_tasks:
        story.tasks.extend(agent.plan_story(story))
    return agent.execute(task, story)


def _run_stage(
    engine: WorkflowEngine,
    agents: list[Any],
    story: Story,
    target_state: StoryState,
    next_state: StoryState | None,
    agent_type: type[Any],
    task_config: Task | list[Task],
    executor: TaskExecutor | None = None,
) -> bool:
    """Run one stage, including assignment, execution, and its exit transition."""
    if story.state != target_state:
        if not engine.transition_story(
            story.id,
            target_state,
            f"Entering {target_state.value} stage",
        ):
            return False

    tasks = task_config if isinstance(task_config, list) else [task_config]
    for task in tasks:
        if not any(existing_task.id == task.id for existing_task in story.tasks):
            story.tasks.append(task)

    for task in tasks:
        agent = engine.scheduler.find_best_agent(
            task,
            list(engine.agents.values()),
            target_state.value,
        )
        if agent is None:
            reason = f"No available agent for {target_state.value} task '{task.title}'"
            logger.warning(reason)
            engine.block_task(story.id, task.id, reason)
            engine.block_story(story.id, reason)
            return False

        agent_handler = find_agent_obj(agents, agent.id)
        if agent_handler is None or not isinstance(agent_handler, agent_type):
            reason = (
                f"No compatible {agent_type.__name__} handler for "
                f"{target_state.value} task '{task.title}'"
            )
            logger.warning(reason)
            engine.block_task(story.id, task.id, reason)
            engine.block_story(story.id, reason)
            return False

        try:
            engine.scheduler.assign_task(task, agent)
        except Exception as error:
            reason = f"Could not assign task '{task.title}': {error}"
            logger.exception(reason)
            engine.block_task(story.id, task.id, reason)
            engine.block_story(story.id, reason)
            return False

        if isinstance(agent_handler, DeveloperAgent) and task.steps:
            artifacts = engine.execute_task_tdd(story.id, task.id, agent_handler)
        else:
            artifacts = engine.execute_agent_task(
                story.id,
                task.id,
                agent_handler,
                executor,
            )
        if artifacts is None:
            reason = f"{target_state.value} task '{task.title}' could not be completed"
            engine.block_story(story.id, reason)
            return False

    if next_state is None:
        return True
    return engine.transition_story(
        story.id,
        next_state,
        f"{target_state.value.capitalize()} stage complete",
    )


def _pipeline_result(engine: WorkflowEngine, story: Story) -> dict[str, Any]:
    return {
        "story": engine.story_summary(story.id),
        "artifacts": [
            artifact.summary()
            for artifact in engine.get_artifacts_for_story(story.id)
        ],
        "engine_status": engine.status(),
    }


def run_full_pipeline(
    title: str,
    description: str,
    acceptance_criteria: list[str] | None = None,
) -> dict[str, Any]:
    """Run a story from inception through delivery.

    Every stage is executed by the same guarded runner.  A missing agent,
    assignment failure, exhausted execution retry, failed quality gate, or
    unexpected exception leaves the story in a visible blocked state rather
    than reporting unperformed work as complete.
    """
    engine = WorkflowEngine()
    story: Story | None = None

    try:
        agents = create_default_team()
        for agent in agents:
            agent.bind(engine)

        story = engine.create_story(title=title, description=description)
        if acceptance_criteria:
            story.acceptance_criteria = acceptance_criteria

        if not _run_stage(
            engine,
            agents,
            story,
            StoryState.INCEPTION,
            StoryState.PLANNING,
            ProductOwnerAgent,
            _task(
                "Define acceptance criteria",
                "Product Owner defines what done looks like",
                "product_owner",
                TaskPriority.HIGH,
                StoryState.INCEPTION,
            ),
        ):
            return _pipeline_result(engine, story)

        if not _run_stage(
            engine,
            agents,
            story,
            StoryState.PLANNING,
            StoryState.DESIGN,
            ScrumMasterAgent,
            _task(
                "Break down into tasks",
                "Decompose into small TDD tasks",
                "scrum_master",
                TaskPriority.HIGH,
                StoryState.PLANNING,
            ),
            _planning_executor,
        ):
            return _pipeline_result(engine, story)

        if not _run_stage(
            engine,
            agents,
            story,
            StoryState.DESIGN,
            StoryState.IMPLEMENTATION,
            ArchitectAgent,
            [
                _task(
                    "Design system architecture",
                    "Architect designs the system architecture",
                    "architect",
                    TaskPriority.HIGH,
                    StoryState.DESIGN,
                ),
                _task(
                    "Design API endpoints",
                    "Architect defines the API contract",
                    "architect",
                    TaskPriority.MEDIUM,
                    StoryState.DESIGN,
                ),
                _task(
                    "Design data model",
                    "Architect designs the data model and relationships",
                    "architect",
                    TaskPriority.MEDIUM,
                    StoryState.DESIGN,
                ),
            ],
        ):
            return _pipeline_result(engine, story)

        implementation_tasks = [
            task
            for task in story.tasks
            if task.stage == StoryState.IMPLEMENTATION.value
        ]
        if not _run_stage(
            engine,
            agents,
            story,
            StoryState.IMPLEMENTATION,
            StoryState.REVIEW,
            DeveloperAgent,
            implementation_tasks,
        ):
            return _pipeline_result(engine, story)

        if not _run_stage(
            engine,
            agents,
            story,
            StoryState.REVIEW,
            StoryState.ACCEPTANCE,
            ReviewerAgent,
            _task(
                "Code review",
                "Reviewer performs code review on all implementation",
                "reviewer",
                TaskPriority.HIGH,
                StoryState.REVIEW,
            ),
        ):
            return _pipeline_result(engine, story)

        if not _run_stage(
            engine,
            agents,
            story,
            StoryState.ACCEPTANCE,
            StoryState.INTEGRATION,
            TestWriterAgent,
            _task(
                "Write and run end-user acceptance tests",
                "Test Writer validates feature from user perspective",
                "test_writer",
                TaskPriority.HIGH,
                StoryState.ACCEPTANCE,
            ),
        ):
            return _pipeline_result(engine, story)

        if not _run_stage(
            engine,
            agents,
            story,
            StoryState.INTEGRATION,
            StoryState.DELIVERY,
            DevOpsAgent,
            _task(
                "Set up CI pipeline and deploy to staging",
                "DevOps creates CI/CD pipeline and deploys to staging",
                "devops",
                TaskPriority.HIGH,
                StoryState.INTEGRATION,
            ),
        ):
            return _pipeline_result(engine, story)

        if not _run_stage(
            engine,
            agents,
            story,
            StoryState.DELIVERY,
            StoryState.DONE,
            DevOpsAgent,
            _task(
                "Create release notes and documentation",
                "DevOps creates release documentation",
                "devops",
                TaskPriority.MEDIUM,
                StoryState.DELIVERY,
            ),
        ):
            return _pipeline_result(engine, story)
    except Exception as error:
        logger.exception("Pipeline failed; preserving the last known story state")
        if story is not None:
            engine.block_story(story.id, f"Pipeline error: {type(error).__name__}: {error}")

    if story is None:
        # This is only reachable if story creation itself fails.
        return {"story": None, "artifacts": [], "engine_status": engine.status()}
    return _pipeline_result(engine, story)
