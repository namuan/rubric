"""Workflow engine — the state machine that drives stories through their lifecycle."""

from __future__ import annotations

import logging
from typing import Any, Callable

from rubric.models.story import (
    Story, StoryState, Task, TaskStep, TaskStepType, TaskStepStatus, TaskStatus,
)
from rubric.models.agent import Agent, Role, STAGE_RESPONSIBILITIES
from rubric.models.artifacts import Artifact, ArtifactType
from rubric.engine.scheduler import TaskScheduler
from rubric.context.manager import ContextManager

logger = logging.getLogger(__name__)


class WorkflowEvent:
    """An event emitted during workflow execution."""

    def __init__(self, event_type: str, story_id: str, data: dict[str, Any] | None = None):
        self.event_type = event_type
        self.story_id = story_id
        self.data = data or {}

    def __repr__(self) -> str:
        return f"WorkflowEvent({self.event_type}, story={self.story_id})"


EventHandler = Callable[[WorkflowEvent], None]


class WorkflowEngine:
    """Orchestrates the flow of stories through the delivery pipeline.

    The engine:
    1. Manages story lifecycle transitions
    2. Drives TDD substeps (Red→Green→Refactor) within each task
    3. Schedules tasks to agents based on role and availability
    4. Coordinates artifact production between stages
    5. Emits events for observability
    6. Handles blockers and backtracking
    """

    def __init__(self) -> None:
        self.scheduler = TaskScheduler()
        self.context = ContextManager()
        self.stories: dict[str, Story] = {}
        self.artifacts: dict[str, Artifact] = {}
        self.agents: dict[str, Agent] = {}
        self.event_handlers: list[EventHandler] = []
        self._log: list[WorkflowEvent] = []

    # ── Agent Management ──────────────────────────────────────────────

    def register_agent(self, agent: Agent) -> None:
        self.agents[agent.id] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.role.value})")

    def get_agents_by_role(self, role: Role) -> list[Agent]:
        return [a for a in self.agents.values() if a.role == role]

    # ── Story Management ──────────────────────────────────────────────

    def create_story(self, title: str, description: str, **kwargs: Any) -> Story:
        story = Story(title=title, description=description, **kwargs)
        self.stories[story.id] = story
        self.context.set(f"story:{story.id}:state", story.state.value)
        self._emit("story_created", story.id, {"title": title})
        logger.info(f"Created story: {story.id} — {title}")
        return story

    def get_story(self, story_id: str) -> Story:
        if story_id not in self.stories:
            raise KeyError(f"Story {story_id} not found")
        return self.stories[story_id]

    # ── Artifact Management ───────────────────────────────────────────

    def add_artifact(self, artifact: Artifact) -> None:
        self.artifacts[artifact.id] = artifact
        if artifact.story_id:
            story = self.stories.get(artifact.story_id)
            if story:
                story.artifacts.append(artifact.id)
        self._emit(
            "artifact_produced",
            artifact.story_id or "",
            {"artifact_id": artifact.id, "type": artifact.artifact_type.value},
        )
        logger.info(f"Artifact produced: {artifact.summary()}")

    def get_artifacts_for_story(self, story_id: str) -> list[Artifact]:
        story = self.get_story(story_id)
        return [self.artifacts[aid] for aid in story.artifacts if aid in self.artifacts]

    # ── Event System ──────────────────────────────────────────────────

    def on_event(self, handler: EventHandler) -> None:
        self.event_handlers.append(handler)

    def _emit(self, event_type: str, story_id: str, data: dict[str, Any] | None = None) -> None:
        event = WorkflowEvent(event_type, story_id, data)
        self._log.append(event)
        for handler in self.event_handlers:
            handler(event)

    # ── Stage Transitions ─────────────────────────────────────────────

    def transition_story(self, story_id: str, new_state: StoryState, reason: str = "") -> None:
        story = self.get_story(story_id)
        old_state = story.state
        story.transition(new_state, reason)
        self.context.set(f"story:{story_id}:state", new_state.value)
        self._emit("story_transition", story_id, {
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
        })
        logger.info(f"Story {story_id}: {old_state.value} -> {new_state.value}")

    # ── Task + TDD Step Execution ─────────────────────────────────────

    def assign_tasks_for_stage(self, story_id: str) -> list[tuple[Task, Agent]]:
        """Find ready tasks for a story and assign them to available agents."""
        story = self.get_story(story_id)
        ready = story.ready_tasks()
        assignments = []

        for task in ready:
            agent = self.scheduler.find_best_agent(
                task=task,
                agents=list(self.agents.values()),
                stage=story.state.value,
            )
            if agent:
                self.scheduler.assign_task(task, agent)
                assignments.append((task, agent))
                self._emit("task_assigned", story_id, {
                    "task_id": task.id,
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                })
                logger.info(f"Assigned task '{task.title}' to {agent.name}")

        return assignments

    def execute_task_tdd(self, story_id: str, task_id: str, agent_handler: Any) -> list[Artifact]:
        """Execute a task through its TDD substeps using the provided agent handler.

        This drives the Red→Green→Refactor cycle for a single task.
        The agent_handler is a BaseAgent subclass that implements execute_step().

        Returns all artifacts produced during the cycle.
        """
        story = self.get_story(story_id)
        task = next((t for t in story.tasks if t.id == task_id), None)
        if task is None:
            raise KeyError(f"Task {task_id} not found in story {story_id}")

        all_artifacts = []

        for step in task.steps:
            if step.status == TaskStepStatus.DONE:
                continue

            step.status = TaskStepStatus.IN_PROGRESS
            step.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

            self._emit("step_started", story_id, {
                "task_id": task_id,
                "step_id": step.id,
                "step_type": step.step_type.value,
                "step_title": step.title,
            })

            artifact = agent_handler.execute_step(step, task, story)
            self.add_artifact(artifact)
            all_artifacts.append(artifact)

            self._emit("step_completed", story_id, {
                "task_id": task_id,
                "step_id": step.id,
                "step_type": step.step_type.value,
            })
            logger.info(f"  [{step.step_type.value:9s}] {step.title}")

        # All steps done — mark task complete
        if task.all_steps_done():
            self.complete_task(story_id, task_id)

        return all_artifacts

    def complete_task(self, story_id: str, task_id: str) -> Task:
        story = self.get_story(story_id)
        task = next((t for t in story.tasks if t.id == task_id), None)
        if task is None:
            raise KeyError(f"Task {task_id} not found in story {story_id}")

        task.complete()

        if task.assigned_agent and task.assigned_agent in self.agents:
            agent = self.agents[task.assigned_agent]
            agent.finish_task(task_id)

        self._emit("task_completed", story_id, {
            "task_id": task_id,
            "progress": story.progress,
        })
        logger.info(f"Task completed: {task.title} (progress: {story.progress:.0%})")
        return task

    def check_stage_complete(self, story_id: str) -> bool:
        story = self.get_story(story_id)
        if not story.tasks:
            return True
        return all(t.status == TaskStatus.DONE for t in story.tasks)

    def advance_story(self, story_id: str, reason: str = "") -> StoryState | None:
        story = self.get_story(story_id)
        if not self.check_stage_complete(story_id):
            return None

        from rubric.models.story import VALID_TRANSITIONS
        possible = VALID_TRANSITIONS.get(story.state, [])
        forward = [s for s in possible if s != StoryState.BLOCKED]
        stage_order = [
            StoryState.INCEPTION, StoryState.PLANNING, StoryState.DESIGN,
            StoryState.IMPLEMENTATION, StoryState.REVIEW, StoryState.ACCEPTANCE,
            StoryState.INTEGRATION, StoryState.DELIVERY, StoryState.DONE,
        ]
        current_idx = stage_order.index(story.state) if story.state in stage_order else -1
        next_states = [s for s in forward if stage_order.index(s) > current_idx] if current_idx >= 0 else forward

        if next_states:
            next_state = next_states[0]
            self.transition_story(story_id, next_state, reason or f"Stage {story.state.value} complete")
            return next_state
        return None

    # ── Full Pipeline Run ─────────────────────────────────────────────

    def run_story(self, story_id: str, max_iterations: int = 200) -> Story:
        """Run a story through the full pipeline."""
        story = self.get_story(story_id)
        iterations = 0

        while story.state != StoryState.DONE and story.state != StoryState.BLOCKED:
            if iterations >= max_iterations:
                logger.warning(f"Story {story_id} hit max iterations ({max_iterations})")
                break

            assignments = self.assign_tasks_for_stage(story_id)
            for task, agent in assignments:
                self.complete_task(story_id, task.id)

            result = self.advance_story(story_id)
            if result is None and not story.ready_tasks() and story.tasks:
                logger.warning(f"Story {story_id} is stuck at {story.state.value}")
                break

            iterations += 1

        logger.info(f"Story {story_id} finished at state: {story.state.value}")
        return story

    # ── Status / Reporting ────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        stories_by_state = {}
        for story in self.stories.values():
            state = story.state.value
            stories_by_state.setdefault(state, []).append(story.id)

        return {
            "total_stories": len(self.stories),
            "total_agents": len(self.agents),
            "total_artifacts": len(self.artifacts),
            "stories_by_state": stories_by_state,
            "agent_utilization": {
                a.name: f"{a.utilization:.0%}" for a in self.agents.values()
            },
            "events_logged": len(self._log),
        }

    def story_summary(self, story_id: str) -> dict[str, Any]:
        story = self.get_story(story_id)
        total_steps = sum(t.total_steps for t in story.tasks)
        done_steps = sum(t.completed_steps for t in story.tasks)
        return {
            "id": story.id,
            "title": story.title,
            "state": story.state.value,
            "progress": f"{story.progress:.0%}",
            "tasks_completed": story.completed_tasks,
            "tasks_total": story.total_tasks,
            "tdd_steps_total": total_steps,
            "tdd_steps_completed": done_steps,
            "artifacts": len(story.artifacts),
            "history": story.history,
        }
