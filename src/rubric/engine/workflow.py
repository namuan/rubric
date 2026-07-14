"""Workflow engine — the state machine that drives stories through their lifecycle."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from rubric.models.story import Story, StoryState, Task, TaskStatus, TaskStepStatus
from rubric.models.agent import Agent, Role
from rubric.models.artifacts import Artifact, ArtifactType
from rubric.engine.scheduler import TaskScheduler
from rubric.engine.transitions import validate_transition
from rubric.engine.event_logger import EventLogger
from rubric.context.manager import ContextManager
from rubric.persistence import JsonWorkflowStore, WorkflowSnapshot

logger = logging.getLogger(__name__)


class WorkflowEvent:
    """An event emitted during workflow execution."""

    def __init__(
        self, event_type: str, story_id: str, data: dict[str, Any] | None = None
    ):
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

    def __init__(
        self,
        max_execution_attempts: int = 3,
        persistence_path: str | Path | None = None,
        event_log_path: str | Path | None = None,
        work_dir: str | Path | None = None,
    ) -> None:
        if max_execution_attempts < 1:
            raise ValueError("max_execution_attempts must be at least 1")
        self.scheduler = TaskScheduler()
        self.context = ContextManager()
        self.stories: dict[str, Story] = {}
        self.artifacts: dict[str, Artifact] = {}
        self.agents: dict[str, Agent] = {}
        self.event_handlers: list[EventHandler] = []
        self._log: list[WorkflowEvent] = []
        self.max_execution_attempts = max_execution_attempts
        self.work_dir: Path | None = Path(work_dir) if work_dir else None
        self._files_written: int = 0
        state_path = persistence_path or os.getenv("RUBRIC_STATE_FILE")
        self.persistence = JsonWorkflowStore(state_path) if state_path else None
        self._restore_state()

        log_path = event_log_path or os.getenv("RUBRIC_EVENT_LOG")
        if log_path:
            self.on_event(EventLogger(log_path))

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
        self._autosave()
        return story

    def get_story(self, story_id: str) -> Story:
        if story_id not in self.stories:
            raise KeyError(f"Story {story_id} not found")
        return self.stories[story_id]

    # ── Artifact Management ───────────────────────────────────────────

    def add_artifact(self, artifact: Artifact) -> None:
        """Register an artifact once and associate it with its story."""
        if artifact.id in self.artifacts:
            logger.debug(
                "Artifact %s is already registered; skipping duplicate", artifact.id
            )
            return

        self.artifacts[artifact.id] = artifact
        if artifact.story_id:
            story = self.stories.get(artifact.story_id)
            if story and artifact.id not in story.artifacts:
                story.artifacts.append(artifact.id)
        self._emit(
            "artifact_produced",
            artifact.story_id or "",
            {"artifact_id": artifact.id, "type": artifact.artifact_type.value},
        )
        logger.info(f"Artifact produced: {artifact.summary()}")

        if self.work_dir:
            self._write_artifact(artifact)

    # ── File output ────────────────────────────────────────────────────

    # Extension per artifact type (applied after slugified name).
    _EXTENSIONS: dict[ArtifactType, str] = {
        ArtifactType.SOURCE_CODE: ".py",
        ArtifactType.TEST_CODE: ".py",
        ArtifactType.MIGRATION: ".py",
        ArtifactType.CONFIG: ".yml",
        ArtifactType.CI_CONFIG: ".yml",
        ArtifactType.DEPLOYMENT_CONFIG: ".yml",
        ArtifactType.API_SPEC: ".json",
        ArtifactType.DATA_MODEL: ".json",
        ArtifactType.TASK_BREAKDOWN: ".json",
        ArtifactType.SPRINT_PLAN: ".json",
        ArtifactType.TEST_PLAN: ".json",
        ArtifactType.TEST_REPORT: ".json",
    }

    _DEFAULT_EXT = ".md"

    # Stage subdirectory for each artifact type.
    _STAGE_DIRS: dict[ArtifactType, str] = {
        ArtifactType.STORY_BRIEF: "inception",
        ArtifactType.ACCEPTANCE_CRITERIA: "inception",
        ArtifactType.TASK_BREAKDOWN: "planning",
        ArtifactType.SPRINT_PLAN: "planning",
        ArtifactType.ARCHITECTURE_DIAGRAM: "design",
        ArtifactType.API_SPEC: "design",
        ArtifactType.DATA_MODEL: "design",
        ArtifactType.TECH_DESIGN: "design",
        ArtifactType.SOURCE_CODE: "implementation",
        ArtifactType.MIGRATION: "implementation",
        ArtifactType.CONFIG: "implementation",
        ArtifactType.TEST_CODE: "implementation",
        ArtifactType.REVIEW_FEEDBACK: "review",
        ArtifactType.REFACTOR_SUGGESTION: "review",
        ArtifactType.TEST_PLAN: "acceptance",
        ArtifactType.TEST_REPORT: "acceptance",
        ArtifactType.CI_CONFIG: "integration",
        ArtifactType.DEPLOYMENT_CONFIG: "integration",
        ArtifactType.CHANGELOG: "delivery",
        ArtifactType.DOCUMENTATION: "delivery",
        ArtifactType.RELEASE_NOTES: "delivery",
    }

    @staticmethod
    def _slugify(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "artifact"

    def _write_artifact(self, artifact: Artifact) -> None:
        assert self.work_dir is not None
        stage = self._STAGE_DIRS.get(artifact.artifact_type, "misc")
        # When a story exists, resolve the TDD test stage so the Test
        # Writer's acceptance tests land in the acceptance directory.
        if (
            artifact.story_id
            and artifact.artifact_type == ArtifactType.TEST_CODE
            and artifact.story_id in self.stories
        ):
            story_state = self.stories[artifact.story_id].state
            if story_state == StoryState.ACCEPTANCE:
                stage = "acceptance"
        ext = self._EXTENSIONS.get(artifact.artifact_type, self._DEFAULT_EXT)
        slug = self._slugify(artifact.name)
        target_dir = self.work_dir / stage
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{slug}{ext}"

        content = artifact.content
        if isinstance(content, (dict, list)):
            content = json.dumps(content, indent=2)
        elif content is None:
            content = ""
        else:
            content = str(content)
        path.write_text(content, encoding="utf-8")
        self._files_written += 1
        print(f"    wrote {path}", file=sys.stderr)

    # ── Story queries ──────────────────────────────────────────────────

    def get_artifacts_for_story(self, story_id: str) -> list[Artifact]:
        story = self.get_story(story_id)
        return [self.artifacts[aid] for aid in story.artifacts if aid in self.artifacts]

    # ── Event System ──────────────────────────────────────────────────

    def on_event(self, handler: EventHandler) -> None:
        self.event_handlers.append(handler)

    def _emit(
        self, event_type: str, story_id: str, data: dict[str, Any] | None = None
    ) -> None:
        event = WorkflowEvent(event_type, story_id, data)
        self._log.append(event)
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception:
                # Observability must not make the delivery pipeline fail.
                logger.exception("Workflow event handler failed for %s", event)

    # ── Stage Transitions ─────────────────────────────────────────────

    def transition_story(
        self, story_id: str, new_state: StoryState, reason: str = ""
    ) -> bool:
        """Transition a story, enforcing gates and safely containing failures.

        Gate failures and invalid transitions leave the story in ``BLOCKED``
        whenever the state machine allows it.  The boolean result lets callers
        halt a pipeline cleanly instead of continuing after a failed change.
        """
        try:
            story = self.get_story(story_id)
        except KeyError:
            logger.exception("Cannot transition missing story %s", story_id)
            return False

        old_state = story.state
        if old_state == new_state:
            return True

        if new_state != StoryState.BLOCKED:
            gates_passed, failures = validate_transition(story, new_state)
            if not gates_passed:
                failure_reason = (
                    f"Quality gates failed before {new_state.value}: "
                    + "; ".join(failures)
                )
                logger.warning("Story %s: %s", story_id, failure_reason)
                self._emit(
                    "transition_gate_failed",
                    story_id,
                    {
                        "from": old_state.value,
                        "to": new_state.value,
                        "failures": failures,
                    },
                )
                self._block_story(story, failure_reason)
                return False

        try:
            story.transition(new_state, reason)
        except ValueError as error:
            failure_reason = f"Transition failed: {error}"
            logger.exception("Story %s: %s", story_id, failure_reason)
            self._emit(
                "transition_failed",
                story_id,
                {
                    "from": old_state.value,
                    "to": new_state.value,
                    "reason": failure_reason,
                },
            )
            if new_state != StoryState.BLOCKED:
                self._block_story(story, failure_reason)
            return False

        self.context.set(f"story:{story_id}:state", new_state.value)
        self._emit(
            "story_transition",
            story_id,
            {
                "from": old_state.value,
                "to": new_state.value,
                "reason": reason,
            },
        )
        logger.info(f"Story {story_id}: {old_state.value} -> {new_state.value}")
        self._autosave()
        return True

    def block_story(self, story_id: str, reason: str) -> bool:
        """Move a story to BLOCKED without allowing a secondary error to escape."""
        try:
            story = self.get_story(story_id)
        except KeyError:
            logger.exception("Cannot block missing story %s", story_id)
            return False
        return self._block_story(story, reason)

    def _block_story(self, story: Story, reason: str) -> bool:
        if story.state == StoryState.BLOCKED:
            return True

        old_state = story.state
        try:
            story.transition(StoryState.BLOCKED, reason)
        except ValueError:
            logger.exception(
                "Story %s could not transition from %s to blocked: %s",
                story.id,
                old_state.value,
                reason,
            )
            self._emit("story_blocking_failed", story.id, {"reason": reason})
            return False

        self.context.set(f"story:{story.id}:state", StoryState.BLOCKED.value)
        self._emit(
            "story_transition",
            story.id,
            {
                "from": old_state.value,
                "to": StoryState.BLOCKED.value,
                "reason": reason,
            },
        )
        self._emit("story_blocked", story.id, {"reason": reason})
        logger.error("Story %s blocked: %s", story.id, reason)
        self._autosave()
        return True

    # ── Task + TDD Step Execution ─────────────────────────────────────

    def execute_agent_task(
        self,
        story_id: str,
        task_id: str,
        agent_handler: Any,
        executor: Callable[[Any, Task, Story], list[Artifact]] | None = None,
    ) -> list[Artifact] | None:
        """Execute a non-TDD task with retries and block it on exhaustion."""
        story, task = self._get_story_task(story_id, task_id)
        execute = executor or (
            lambda handler, current_task, current_story: handler.execute(
                current_task,
                current_story,
            )
        )
        return self._execute_with_retries(
            story,
            task,
            lambda: execute(agent_handler, task, story),
        )

    def execute_task_tdd(
        self, story_id: str, task_id: str, agent_handler: Any
    ) -> list[Artifact] | None:
        """Execute a task through its TDD substeps using the provided agent handler.

        This drives the Red→Green→Refactor cycle for a single task.
        The agent handler executes each step through its standard ``execute``
        interface.

        Returns all artifacts produced during the cycle.
        """
        story, task = self._get_story_task(story_id, task_id)
        return self._execute_with_retries(
            story,
            task,
            lambda: self._execute_tdd_steps(story, task, agent_handler),
        )

    def _execute_tdd_steps(
        self, story: Story, task: Task, agent_handler: Any
    ) -> list[Artifact]:
        """Execute uncompleted TDD steps once; retry policy lives above this method."""
        all_artifacts: list[Artifact] = []

        for step in task.steps:
            if step.status == TaskStepStatus.DONE:
                continue

            step.status = TaskStepStatus.IN_PROGRESS
            step.updated_at = datetime.now(timezone.utc)

            self._emit(
                "step_started",
                story.id,
                {
                    "task_id": task.id,
                    "step_id": step.id,
                    "step_type": step.step_type.value,
                    "step_title": step.title,
                },
            )

            artifacts = agent_handler.execute(task, story, step=step)
            if len(artifacts) != 1:
                raise RuntimeError(
                    f"Developer returned {len(artifacts)} artifacts for TDD step {step.id}"
                )
            artifact = artifacts[0]
            # Preserve successful steps if a later step fails and is retried.
            self.add_artifact(artifact)
            all_artifacts.append(artifact)

            self._emit(
                "step_completed",
                story.id,
                {
                    "task_id": task.id,
                    "step_id": step.id,
                    "step_type": step.step_type.value,
                },
            )
            logger.info(f"  [{step.step_type.value:9s}] {step.title}")

        return all_artifacts

    def _execute_with_retries(
        self,
        story: Story,
        task: Task,
        execute: Callable[[], list[Artifact]],
    ) -> list[Artifact] | None:
        """Run agent work, retrying failures and retaining a clear blocker."""
        last_error: Exception | None = None

        for attempt in range(1, self.max_execution_attempts + 1):
            try:
                artifacts = execute()
                if artifacts is None:
                    raise RuntimeError("Agent returned no artifact collection")
                for artifact in artifacts:
                    self.add_artifact(artifact)
                self.complete_task(story.id, task.id)
                return artifacts
            except Exception as error:
                last_error = error
                logger.exception(
                    "Task %s execution failed (attempt %d/%d)",
                    task.id,
                    attempt,
                    self.max_execution_attempts,
                )
                self._emit(
                    "task_execution_failed",
                    story.id,
                    {
                        "task_id": task.id,
                        "attempt": attempt,
                        "max_attempts": self.max_execution_attempts,
                        "error": str(error),
                    },
                )

        reason = (
            f"Execution failed after {self.max_execution_attempts} attempts: "
            f"{last_error}"
        )
        self.block_task(story.id, task.id, reason)
        return None

    def _get_story_task(self, story_id: str, task_id: str) -> tuple[Story, Task]:
        story = self.get_story(story_id)
        task = next((task for task in story.tasks if task.id == task_id), None)
        if task is None:
            raise KeyError(f"Task {task_id} not found in story {story_id}")
        return story, task

    def complete_task(self, story_id: str, task_id: str) -> Task:
        story, task = self._get_story_task(story_id, task_id)
        if task.status == TaskStatus.BLOCKED:
            raise RuntimeError(f"Cannot complete blocked task {task_id}")
        if not task.all_steps_done():
            raise ValueError(
                f"Cannot complete task {task_id} with unfinished TDD steps"
            )

        task.complete()

        if task.assigned_agent and task.assigned_agent in self.agents:
            agent = self.agents[task.assigned_agent]
            agent.finish_task(task_id)

        self._emit(
            "task_completed",
            story_id,
            {
                "task_id": task_id,
                "progress": story.progress,
            },
        )
        logger.info(f"Task completed: {task.title} (progress: {story.progress:.0%})")
        self._autosave()
        return task

    def block_task(self, story_id: str, task_id: str, reason: str) -> Task:
        """Mark unfinished work as blocked and release any assigned agent."""
        story, task = self._get_story_task(story_id, task_id)
        if task.status == TaskStatus.DONE:
            logger.warning("Refusing to block completed task %s", task_id)
            return task

        if task.assigned_agent and task.assigned_agent in self.agents:
            self.agents[task.assigned_agent].finish_task(task_id)
        task.block(reason)
        self._emit(
            "task_blocked",
            story_id,
            {
                "task_id": task.id,
                "reason": reason,
            },
        )
        logger.warning("Task blocked: %s — %s", task.title, reason)
        self._autosave()
        return task

    # ── Persistence ──────────────────────────────────────────────────

    def _restore_state(self) -> None:
        if self.persistence is None:
            return
        try:
            snapshot = self.persistence.load()
        except (OSError, ValueError):
            logger.exception(
                "Could not restore workflow state from %s", self.persistence.path
            )
            return
        if snapshot is None:
            return

        self.stories = snapshot.stories
        self.artifacts = snapshot.artifacts
        self.context.restore(snapshot.context)
        logger.info(
            "Restored %d stories from %s", len(self.stories), self.persistence.path
        )

    def _autosave(self) -> None:
        if self.persistence is None:
            return
        snapshot = WorkflowSnapshot(
            stories=self.stories,
            artifacts=self.artifacts,
            context=self.context.snapshot(),
        )
        try:
            self.persistence.save(snapshot)
        except Exception:
            # Persistence is optional and must not turn completed work into a
            # failed pipeline when an artifact cannot be serialized or saved.
            logger.exception(
                "Could not save workflow state to %s", self.persistence.path
            )

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
            "files_written": self._files_written,
            "work_dir": str(self.work_dir) if self.work_dir else None,
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
            "transitions": len(story.history),
            "history": story.history,
        }
