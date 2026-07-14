"""Tests for scheduling, workflow execution, events, and persistence."""

import json

from rubric.agents import DeveloperAgent, ProductOwnerAgent
from rubric.context.manager import ContextManager
from rubric.engine.scheduler import TaskScheduler
from rubric.engine.transitions import validate_transition
from rubric.engine.workflow import WorkflowEngine
from rubric.models.agent import Agent, Role
from rubric.models.story import (
    Story,
    StoryState,
    Task,
    TaskStatus,
    TaskStep,
    TaskStepStatus,
    TaskStepType,
)


class TestScheduler:
    def test_find_agent_by_role(self):
        scheduler = TaskScheduler()
        developer = Agent(name="Dev", role=Role.DEVELOPER)
        architect = Agent(name="Arch", role=Role.ARCHITECT)
        agent = scheduler.find_best_agent(
            Task(title="Code", required_role="developer"), [developer, architect]
        )
        assert agent == developer

    def test_no_available_agent(self):
        scheduler = TaskScheduler()
        developer = Agent(name="Dev", role=Role.DEVELOPER, max_concurrent_tasks=1)
        developer.pick_up_task("t1")
        assert (
            scheduler.find_best_agent(
                Task(title="Code", required_role="developer"), [developer]
            )
            is None
        )

    def test_load_balancing(self):
        scheduler = TaskScheduler()
        busy = Agent(name="Busy", role=Role.DEVELOPER, max_concurrent_tasks=2)
        free = Agent(name="Free", role=Role.DEVELOPER, max_concurrent_tasks=2)
        busy.pick_up_task("t1")
        assert (
            scheduler.find_best_agent(
                Task(title="Code", required_role="developer"), [busy, free]
            )
            == free
        )


class TestContextManager:
    def test_set_get_and_restore(self):
        context = ContextManager()
        context.set("story:s1:state", "planning")
        snapshot = context.snapshot()
        context.clear()
        context.restore(snapshot)
        assert context.get("story:s1:state") == "planning"

    def test_prefix_and_story_context(self):
        context = ContextManager()
        context.set("story:s1:state", "design")
        context.set("story:s1:title", "Auth")
        assert len(context.keys("story:s1:")) == 2
        assert context.story_context("s1") == {"state": "design", "title": "Auth"}


class TestTransitions:
    def test_all_tasks_complete_gate(self):
        story = Story(
            title="T",
            description="D",
            acceptance_criteria=["C1"],
            state=StoryState.PLANNING,
        )
        task = Task(title="T1")
        story.tasks = [task]
        ok, reasons = validate_transition(story, StoryState.DESIGN)
        assert not ok
        assert any("all_tasks_complete" in reason for reason in reasons)
        task.status = TaskStatus.DONE
        assert validate_transition(story, StoryState.DESIGN)[0]

    def test_acceptance_criteria_gate(self):
        story = Story(title="T", description="D")
        assert not validate_transition(story, StoryState.PLANNING)[0]
        story.acceptance_criteria = ["Something"]
        assert validate_transition(story, StoryState.PLANNING)[0]


class TestWorkflowEngine:
    def test_create_and_transition(self, workflow_engine):
        story = workflow_engine.create_story("Test", "Description")
        story.acceptance_criteria = ["A criterion"]
        assert workflow_engine.transition_story(story.id, StoryState.PLANNING)
        assert story.state == StoryState.PLANNING

    def test_register_agents_and_status(self, workflow_engine):
        workflow_engine.register_agent(Agent(name="Dev", role=Role.DEVELOPER))
        workflow_engine.create_story("S1", "D1")
        assert workflow_engine.status()["total_agents"] == 1
        assert workflow_engine.status()["total_stories"] == 1

    def test_event_emission(self, workflow_engine):
        events = []
        workflow_engine.on_event(events.append)
        workflow_engine.create_story("Test", "Desc")
        assert events[0].event_type == "story_created"

    def test_execute_task_tdd(self, workflow_engine):
        developer = DeveloperAgent(name="Dev")
        developer.bind(workflow_engine)
        story = workflow_engine.create_story("Test", "Desc")
        task = Task(
            title="Implement auth",
            required_role="developer",
            steps=[
                TaskStep(step_type=TaskStepType.RED, title="RED"),
                TaskStep(step_type=TaskStepType.GREEN, title="GREEN"),
                TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR"),
            ],
        )
        story.tasks = [task]
        workflow_engine.scheduler.assign_task(task, developer.agent)
        artifacts = workflow_engine.execute_task_tdd(story.id, task.id, developer)
        assert len(artifacts) == 3
        assert task.status == TaskStatus.DONE
        assert all(step.status == TaskStepStatus.DONE for step in task.steps)

    def test_tdd_retry_preserves_artifacts_from_completed_steps(self):
        class FlakyDeveloper(DeveloperAgent):
            failed_once = False

            def execute(self, task, story, *, step=None):
                if (
                    step is not None
                    and step.step_type == TaskStepType.GREEN
                    and not self.failed_once
                ):
                    self.failed_once = True
                    raise RuntimeError("temporary failure")
                return super().execute(task, story, step=step)

        engine = WorkflowEngine(max_execution_attempts=2)
        developer = FlakyDeveloper(name="Dev")
        developer.bind(engine)
        story = engine.create_story("Test", "Desc")
        task = Task(
            title="Implement auth",
            required_role="developer",
            steps=[
                TaskStep(step_type=TaskStepType.RED, title="RED"),
                TaskStep(step_type=TaskStepType.GREEN, title="GREEN"),
                TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR"),
            ],
        )
        story.tasks = [task]
        engine.scheduler.assign_task(task, developer.agent)

        assert engine.execute_task_tdd(story.id, task.id, developer) is not None
        assert task.status == TaskStatus.DONE
        assert len(engine.get_artifacts_for_story(story.id)) == 3

    def test_artifact_registration_is_owned_by_engine_and_idempotent(
        self, workflow_engine
    ):
        story = workflow_engine.create_story("Test", "Desc")
        task = Task(title="Define acceptance criteria")
        story.tasks = [task]
        agent = ProductOwnerAgent(name="PO")
        agent.bind(workflow_engine)
        artifact = agent.execute(task, story)[0]
        assert artifact.id not in workflow_engine.artifacts
        workflow_engine.add_artifact(artifact)
        workflow_engine.add_artifact(artifact)
        assert list(workflow_engine.artifacts) == [artifact.id]
        assert story.artifacts == [artifact.id]

    def test_gate_failure_blocks_story_with_reason(self, workflow_engine):
        story = workflow_engine.create_story("Test", "Desc")
        assert not workflow_engine.transition_story(story.id, StoryState.PLANNING)
        assert story.state == StoryState.BLOCKED
        assert "has_acceptance_criteria" in story.history[-1]["reason"]

    def test_invalid_transition_blocks_story_instead_of_raising(self, workflow_engine):
        story = workflow_engine.create_story("Test", "Desc")
        story.acceptance_criteria = ["A criterion"]
        assert not workflow_engine.transition_story(story.id, StoryState.DELIVERY)
        assert story.state == StoryState.BLOCKED
        assert "Invalid transition" in story.history[-1]["reason"]

    def test_execution_retries_then_blocks_task(self, workflow_engine):
        class FailingAgent:
            attempts = 0

            def execute(self, task, story):
                self.attempts += 1
                raise RuntimeError("provider unavailable")

        workflow_engine.max_execution_attempts = 2
        story = workflow_engine.create_story("Test", "Desc")
        task = Task(title="Work item")
        story.tasks = [task]
        agent = FailingAgent()
        assert workflow_engine.execute_agent_task(story.id, task.id, agent) is None
        assert agent.attempts == 2
        assert task.status == TaskStatus.BLOCKED

    def test_persistence_restores_story_after_task_completion(self, tmp_path):
        state_file = tmp_path / "workflow.json"
        engine = WorkflowEngine(persistence_path=state_file)
        story = engine.create_story("Persisted", "Description")
        task = Task(title="Done")
        story.tasks = [task]
        engine.complete_task(story.id, task.id)

        restored = WorkflowEngine(persistence_path=state_file)
        loaded_story = restored.get_story(story.id)
        assert loaded_story.tasks[0].status == TaskStatus.DONE
        assert restored.context.get(f"story:{story.id}:state") == "inception"

    def test_event_logger_writes_consumer_output(self, tmp_path):
        event_file = tmp_path / "events.jsonl"
        engine = WorkflowEngine(event_log_path=event_file)
        engine.create_story("Observable", "Description")
        record = json.loads(event_file.read_text().strip())
        assert record["event_type"] == "story_created"
