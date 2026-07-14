"""Tests for the workflow engine (v2 — TDD + Test Writer)."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rubric.models.story import (
    Story, Task, TaskStep, TaskStepType, TaskStepStatus,
    StoryState, TaskStatus, TaskPriority, VALID_TRANSITIONS,
)
from rubric.models.agent import Agent, Role
from rubric.models.artifacts import Artifact, ArtifactType
from rubric.engine.workflow import WorkflowEngine
from rubric.engine.scheduler import TaskScheduler
from rubric.engine.transitions import validate_transition, ALL_TASKS_COMPLETE
from rubric.context.manager import ContextManager
from rubric.agents import (
    ProductOwnerAgent,
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent,
    TestWriterAgent,
    DevOpsAgent,
    ScrumMasterAgent,
)
from rubric.orchestrator import run_full_pipeline, create_default_team


# ── Story Model Tests ─────────────────────────────────────────────────


class TestStory:
    def test_create_story(self):
        story = Story(title="Test", description="A test story")
        assert story.state == StoryState.INCEPTION
        assert story.title == "Test"
        assert len(story.id) == 8

    def test_valid_transition(self):
        story = Story(title="Test", description="Test")
        story.transition(StoryState.PLANNING, "Moving to planning")
        assert story.state == StoryState.PLANNING
        assert len(story.history) == 1
        assert story.history[0]["from"] == "inception"
        assert story.history[0]["to"] == "planning"

    def test_invalid_transition_raises(self):
        story = Story(title="Test", description="Test")
        with pytest.raises(ValueError, match="Invalid transition"):
            story.transition(StoryState.DELIVERY, "Skip to delivery")

    def test_full_lifecycle_transitions(self):
        """Verify the complete happy-path transition chain."""
        story = Story(title="Test", description="Test")
        chain = [
            StoryState.PLANNING, StoryState.DESIGN, StoryState.IMPLEMENTATION,
            StoryState.REVIEW, StoryState.ACCEPTANCE, StoryState.INTEGRATION,
            StoryState.DELIVERY, StoryState.DONE,
        ]
        for state in chain:
            story.transition(state, f"Moving to {state.value}")
        assert story.state == StoryState.DONE
        assert len(story.history) == 8

    def test_progress_based_on_steps(self):
        """Progress should reflect TDD step completion."""
        story = Story(title="Test", description="Test")
        t1 = Task(title="T1")
        t1.steps = [
            TaskStep(step_type=TaskStepType.RED, title="RED"),
            TaskStep(step_type=TaskStepType.GREEN, title="GREEN"),
            TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR"),
        ]
        story.tasks = [t1]

        assert story.progress == 0.0

        t1.steps[0].status = TaskStepStatus.DONE
        assert story.progress == pytest.approx(1 / 3)

        t1.steps[1].status = TaskStepStatus.DONE
        assert story.progress == pytest.approx(2 / 3)

        t1.steps[2].status = TaskStepStatus.DONE
        assert story.progress == 1.0

    def test_ready_tasks(self):
        story = Story(title="Test", description="Test")
        t1 = Task(title="Task 1")
        t2 = Task(title="Task 2", dependencies=[t1.id])
        t3 = Task(title="Task 3", dependencies=[t2.id])
        story.tasks = [t1, t2, t3]

        ready = story.ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == t1.id

        t1.status = TaskStatus.DONE
        ready = story.ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == t2.id


# ── Task + TaskStep Tests ─────────────────────────────────────────────


class TestTask:
    def test_task_dependencies(self):
        t1 = Task(title="T1")
        t2 = Task(title="T2", dependencies=[t1.id])
        assert not t2.is_ready(set())
        assert t2.is_ready({t1.id})

    def test_task_tdd_steps(self):
        task = Task(title="Implement auth")
        task.steps = [
            TaskStep(step_type=TaskStepType.RED, title="RED: Write test"),
            TaskStep(step_type=TaskStepType.GREEN, title="GREEN: Implement"),
            TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR: Clean up"),
        ]
        assert task.total_steps == 3
        assert task.completed_steps == 0
        assert task.step_progress == 0.0

    def test_task_step_progression(self):
        task = Task(title="T")
        red = TaskStep(step_type=TaskStepType.RED, title="RED")
        green = TaskStep(step_type=TaskStepType.GREEN, title="GREEN")
        refactor = TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR")
        task.steps = [red, green, refactor]

        # First step should be current
        current = task.current_step
        assert current is not None
        assert current.step_type == TaskStepType.RED

        # Complete steps one by one
        red.status = TaskStepStatus.DONE
        assert task.completed_steps == 1
        assert task.current_step.step_type == TaskStepType.GREEN

        green.status = TaskStepStatus.DONE
        assert task.current_step.step_type == TaskStepType.REFACTOR

        refactor.status = TaskStepStatus.DONE
        assert task.current_step is None
        assert task.all_steps_done()

    def test_task_complete(self):
        t = Task(title="T1")
        t.assign("agent-1")
        t.complete()
        assert t.status == TaskStatus.DONE


class TestTaskStep:
    def test_step_complete(self):
        step = TaskStep(step_type=TaskStepType.RED, title="Write failing test")
        assert step.status == TaskStepStatus.PENDING
        step.complete(artifact_id="art-123")
        assert step.status == TaskStepStatus.DONE
        assert step.artifact_id == "art-123"


# ── Agent Model Tests ─────────────────────────────────────────────────


class TestAgent:
    def test_agent_availability(self):
        agent = Agent(name="Test", role=Role.DEVELOPER, max_concurrent_tasks=2)
        assert agent.available
        agent.pick_up_task("t1")
        assert agent.available
        agent.pick_up_task("t2")
        assert not agent.available

    def test_agent_role_matching(self):
        dev = Agent(name="Dev", role=Role.DEVELOPER)
        assert dev.can_handle("developer")
        assert not dev.can_handle("architect")
        assert dev.can_handle(None)

    def test_agent_utilization(self):
        agent = Agent(name="Test", role=Role.DEVELOPER, max_concurrent_tasks=4)
        assert agent.utilization == 0.0
        agent.pick_up_task("t1")
        agent.pick_up_task("t2")
        assert agent.utilization == 0.5

    def test_test_writer_role(self):
        """Verify TEST_WRITER role exists and works."""
        tw = Agent(name="TW", role=Role.TEST_WRITER)
        assert tw.can_handle("test_writer")
        assert not tw.can_handle("developer")


# ── Scheduler Tests ───────────────────────────────────────────────────


class TestScheduler:
    def test_find_agent_by_role(self):
        scheduler = TaskScheduler()
        dev = Agent(name="Dev", role=Role.DEVELOPER)
        arch = Agent(name="Arch", role=Role.ARCHITECT)
        task = Task(title="Code it", required_role="developer")
        agent = scheduler.find_best_agent(task, [dev, arch])
        assert agent is not None
        assert agent.role == Role.DEVELOPER

    def test_no_available_agent(self):
        scheduler = TaskScheduler()
        dev = Agent(name="Dev", role=Role.DEVELOPER, max_concurrent_tasks=1)
        dev.pick_up_task("t1")
        task = Task(title="Code it", required_role="developer")
        agent = scheduler.find_best_agent(task, [dev])
        assert agent is None

    def test_load_balancing(self):
        scheduler = TaskScheduler()
        dev1 = Agent(name="Dev1", role=Role.DEVELOPER, max_concurrent_tasks=2)
        dev2 = Agent(name="Dev2", role=Role.DEVELOPER, max_concurrent_tasks=2)
        dev1.pick_up_task("t1")
        task = Task(title="New task", required_role="developer")
        agent = scheduler.find_best_agent(task, [dev1, dev2])
        assert agent is not None
        assert agent.name == "Dev2"


# ── Context Manager Tests ─────────────────────────────────────────────


class TestContextManager:
    def test_set_and_get(self):
        ctx = ContextManager()
        ctx.set("key1", "value1")
        assert ctx.get("key1") == "value1"
        assert ctx.get("missing", "default") == "default"

    def test_prefix_filtering(self):
        ctx = ContextManager()
        ctx.set("story:s1:state", "planning")
        ctx.set("story:s1:title", "Test")
        ctx.set("story:s2:state", "inception")
        keys = ctx.keys("story:s1:")
        assert len(keys) == 2

    def test_story_context(self):
        ctx = ContextManager()
        ctx.set("story:s1:state", "design")
        ctx.set("story:s1:title", "Auth")
        ctx.set("story:s2:state", "inception")
        s1_ctx = ctx.story_context("s1")
        assert s1_ctx["state"] == "design"
        assert s1_ctx["title"] == "Auth"

    def test_history(self):
        ctx = ContextManager()
        ctx.set("a", 1)
        ctx.set("a", 2)
        assert len(ctx.history) == 2
        assert ctx.history[0]["new"] == 1
        assert ctx.history[1]["old"] == 1


# ── Transition Gate Tests ─────────────────────────────────────────────


class TestTransitions:
    def test_all_tasks_complete_gate(self):
        story = Story(title="T", description="D", acceptance_criteria=["C1"])
        t1 = Task(title="T1")
        story.tasks = [t1]

        # PLANNING gate is ALL_TASKS_COMPLETE — force into PLANNING
        story.state = StoryState.PLANNING
        ok, reasons = validate_transition(story, StoryState.DESIGN)
        assert not ok
        assert any("all_tasks_complete" in r for r in reasons)

        t1.status = TaskStatus.DONE
        ok, reasons = validate_transition(story, StoryState.DESIGN)
        assert ok

    def test_acceptance_criteria_gate(self):
        story = Story(title="T", description="D")
        ok, reasons = validate_transition(story, StoryState.PLANNING)
        assert not ok  # No acceptance criteria

        story.acceptance_criteria = ["Something"]
        ok, reasons = validate_transition(story, StoryState.PLANNING)
        assert ok


# ── Workflow Engine Tests ─────────────────────────────────────────────


class TestWorkflowEngine:
    def test_create_and_transition(self):
        engine = WorkflowEngine()
        story = engine.create_story("Test", "Description")
        assert story.state == StoryState.INCEPTION
        engine.transition_story(story.id, StoryState.PLANNING)
        assert story.state == StoryState.PLANNING

    def test_register_agents(self):
        engine = WorkflowEngine()
        dev = Agent(name="Dev", role=Role.DEVELOPER)
        engine.register_agent(dev)
        assert len(engine.agents) == 1

    def test_event_emission(self):
        engine = WorkflowEngine()
        events = []
        engine.on_event(lambda e: events.append(e))
        engine.create_story("Test", "Desc")
        assert len(events) == 1
        assert events[0].event_type == "story_created"

    def test_status(self):
        engine = WorkflowEngine()
        engine.create_story("S1", "D1")
        engine.create_story("S2", "D2")
        status = engine.status()
        assert status["total_stories"] == 2

    def test_execute_task_tdd(self):
        """Test that TDD substeps are executed in order."""
        engine = WorkflowEngine()
        dev_agent = DeveloperAgent(name="Dev")
        dev_agent.bind(engine)

        story = engine.create_story("Test", "Desc")
        task = Task(title="Implement auth", required_role="developer")
        task.steps = [
            TaskStep(step_type=TaskStepType.RED, title="RED: test"),
            TaskStep(step_type=TaskStepType.GREEN, title="GREEN: code"),
            TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR: clean"),
        ]
        story.tasks = [task]
        engine.scheduler.assign_task(task, dev_agent.agent)

        artifacts = engine.execute_task_tdd(story.id, task.id, dev_agent)
        assert len(artifacts) == 3
        assert task.status == TaskStatus.DONE
        assert all(s.status == TaskStepStatus.DONE for s in task.steps)


# ── Agent Execution Tests ─────────────────────────────────────────────


class TestAgentExecution:
    def _make_context(self):
        engine = WorkflowEngine()
        story = engine.create_story("Test Feature", "A test feature")
        story.acceptance_criteria = ["Criteria 1", "Criteria 2"]
        t = Task(title="Test task")
        story.tasks = [t]
        return engine, story, t

    def test_product_owner(self):
        engine, story, t = self._make_context()
        t.title = "Define story scope"
        po = ProductOwnerAgent(name="PO")
        po.bind(engine)
        artifacts = po.execute(t, story)
        assert len(artifacts) > 0
        assert any(a.artifact_type == ArtifactType.STORY_BRIEF for a in artifacts)

    def test_architect(self):
        engine, story, t = self._make_context()
        t.title = "Design architecture"
        arch = ArchitectAgent(name="Arch")
        arch.bind(engine)
        artifacts = arch.execute(t, story)
        assert len(artifacts) > 0

    def test_developer_tdd_steps(self):
        """Test developer executing TDD substeps."""
        engine, story, t = self._make_context()
        t.title = "Implement feature"
        t.steps = [
            TaskStep(step_type=TaskStepType.RED, title="RED: Write test"),
            TaskStep(step_type=TaskStepType.GREEN, title="GREEN: Implement"),
            TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR: Clean"),
        ]
        dev = DeveloperAgent(name="Dev")
        dev.bind(engine)

        # Execute each step
        for step in t.steps:
            step.status = TaskStepStatus.IN_PROGRESS
            artifact = dev.execute_step(step, t, story)
            assert artifact is not None
            assert step.status == TaskStepStatus.DONE

    def test_test_writer(self):
        engine, story, t = self._make_context()
        t.title = "Write and run acceptance tests"
        tw = TestWriterAgent(name="TW")
        tw.bind(engine)
        artifacts = tw.execute(t, story)
        assert len(artifacts) > 0
        assert any(a.artifact_type == ArtifactType.TEST_REPORT for a in artifacts)

    def test_devops(self):
        engine, story, t = self._make_context()
        t.title = "Set up CI pipeline"
        do = DevOpsAgent(name="DO")
        do.bind(engine)
        artifacts = do.execute(t, story)
        assert len(artifacts) > 0

    def test_scrum_master_planner(self):
        """Test that the Scrum Master produces a granular plan with TDD steps."""
        engine, story, t = self._make_context()
        story.acceptance_criteria = ["Criterion A", "Criterion B"]
        sm = ScrumMasterAgent(name="SM")
        sm.bind(engine)

        planned_tasks = sm.plan_story(story)
        # 2 criteria → 2 tasks + 1 integration task
        assert len(planned_tasks) == 3
        # Each task should have TDD steps
        for task in planned_tasks:
            assert len(task.steps) == 3
            assert task.steps[0].step_type == TaskStepType.RED
            assert task.steps[1].step_type == TaskStepType.GREEN
            assert task.steps[2].step_type == TaskStepType.REFACTOR


# ── Full Pipeline Integration Test ────────────────────────────────────


class TestFullPipeline:
    def test_run_full_pipeline(self):
        result = run_full_pipeline(
            title="Test Feature",
            description="A test feature for integration testing",
            acceptance_criteria=["Works correctly", "Has tests"],
        )
        assert result["story"]["state"] == "done"
        assert result["story"]["progress"] == "100%"
        assert result["story"]["tasks_completed"] > 0
        assert result["story"]["tdd_steps_total"] > 0
        assert result["story"]["tdd_steps_completed"] == result["story"]["tdd_steps_total"]
        assert len(result["artifacts"]) > 0

    def test_pipeline_produces_tdd_artifacts(self):
        result = run_full_pipeline(
            title="Auth Feature",
            description="JWT authentication",
            acceptance_criteria=["Register", "Login", "Token refresh"],
        )
        artifacts = result["artifacts"]
        # Should have RED, GREEN, REFACTOR artifacts from developer
        reds = [a for a in artifacts if a.startswith("[test_code] RED:")]
        greens = [a for a in artifacts if a.startswith("[source_code] GREEN:")]
        refactors = [a for a in artifacts if a.startswith("[source_code] REFACTOR:")]
        assert len(reds) >= 1
        assert len(greens) >= 1
        assert len(refactors) >= 1

    def test_pipeline_includes_acceptance_tests(self):
        result = run_full_pipeline(
            title="Checkout",
            description="E-commerce checkout",
            acceptance_criteria=["Pay with card"],
        )
        artifacts = result["artifacts"]
        acceptance = [a for a in artifacts if "Acceptance" in a or "acceptance" in a]
        assert len(acceptance) >= 1
