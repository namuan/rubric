"""Tests for workflow data models."""

import pytest

from rubric.models.agent import Agent, Role
from rubric.models.story import (
    Story,
    StoryState,
    Task,
    TaskStep,
    TaskStepStatus,
    TaskStepType,
    TaskStatus,
)


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
        assert story.history[0]["from"] == "inception"
        assert story.history[0]["to"] == "planning"

    def test_invalid_transition_raises(self):
        story = Story(title="Test", description="Test")
        with pytest.raises(ValueError, match="Invalid transition"):
            story.transition(StoryState.DELIVERY, "Skip to delivery")

    def test_full_lifecycle_transitions(self):
        story = Story(title="Test", description="Test")
        for state in [
            StoryState.PLANNING,
            StoryState.DESIGN,
            StoryState.IMPLEMENTATION,
            StoryState.REVIEW,
            StoryState.ACCEPTANCE,
            StoryState.INTEGRATION,
            StoryState.DELIVERY,
            StoryState.DONE,
        ]:
            story.transition(state)
        assert story.state == StoryState.DONE
        assert len(story.history) == 8

    def test_backtracking_transition_is_valid(self):
        story = Story(title="Test", description="Test")
        story.transition(StoryState.PLANNING)
        story.transition(StoryState.DESIGN)
        story.transition(StoryState.PLANNING, "Requirements changed")
        assert story.state == StoryState.PLANNING
        assert story.history[-1]["reason"] == "Requirements changed"

    def test_progress_based_on_steps(self):
        story = Story(title="Test", description="Test")
        task = Task(
            title="T1",
            steps=[
                TaskStep(step_type=TaskStepType.RED, title="RED"),
                TaskStep(step_type=TaskStepType.GREEN, title="GREEN"),
                TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR"),
            ],
        )
        story.tasks = [task]
        task.steps[0].status = TaskStepStatus.DONE
        assert story.progress == pytest.approx(1 / 3)
        task.steps[1].status = TaskStepStatus.DONE
        assert story.progress == pytest.approx(2 / 3)
        task.steps[2].status = TaskStepStatus.DONE
        assert story.progress == 1.0

    def test_ready_tasks(self):
        story = Story(title="Test", description="Test")
        first = Task(title="Task 1")
        second = Task(title="Task 2", dependencies=[first.id])
        story.tasks = [first, second]
        assert story.ready_tasks() == [first]
        first.status = TaskStatus.DONE
        assert story.ready_tasks() == [second]


class TestTask:
    def test_task_dependencies(self):
        first = Task(title="T1")
        second = Task(title="T2", dependencies=[first.id])
        assert not second.is_ready(set())
        assert second.is_ready({first.id})

    def test_task_tdd_steps(self):
        task = Task(
            title="Implement auth",
            steps=[
                TaskStep(step_type=TaskStepType.RED, title="RED"),
                TaskStep(step_type=TaskStepType.GREEN, title="GREEN"),
                TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR"),
            ],
        )
        assert task.total_steps == 3
        assert task.completed_steps == 0
        assert task.step_progress == 0.0

    def test_task_step_progression(self):
        task = Task(
            title="T",
            steps=[
                TaskStep(step_type=TaskStepType.RED, title="RED"),
                TaskStep(step_type=TaskStepType.GREEN, title="GREEN"),
                TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR"),
            ],
        )
        assert task.current_step.step_type == TaskStepType.RED
        task.steps[0].status = TaskStepStatus.DONE
        assert task.current_step.step_type == TaskStepType.GREEN
        task.steps[1].status = TaskStepStatus.DONE
        assert task.current_step.step_type == TaskStepType.REFACTOR
        task.steps[2].status = TaskStepStatus.DONE
        assert task.current_step is None
        assert task.all_steps_done()

    def test_task_complete(self):
        task = Task(title="T1")
        task.assign("agent-1")
        task.complete()
        assert task.status == TaskStatus.DONE

    def test_block_retains_reason(self):
        task = Task(title="T1")
        task.block("waiting on dependency")
        assert task.status == TaskStatus.BLOCKED
        assert task.blocker_reason == "waiting on dependency"


class TestTaskStep:
    def test_step_complete(self):
        step = TaskStep(step_type=TaskStepType.RED, title="Write failing test")
        step.complete(artifact_id="art-123")
        assert step.status == TaskStepStatus.DONE
        assert step.artifact_id == "art-123"


class TestAgent:
    def test_agent_availability(self):
        agent = Agent(name="Test", role=Role.DEVELOPER, max_concurrent_tasks=2)
        agent.pick_up_task("t1")
        assert agent.available
        agent.pick_up_task("t2")
        assert not agent.available

    def test_agent_role_matching(self):
        developer = Agent(name="Dev", role=Role.DEVELOPER)
        assert developer.can_handle("developer")
        assert not developer.can_handle("architect")
        assert developer.can_handle(None)

    def test_agent_utilization(self):
        agent = Agent(name="Test", role=Role.DEVELOPER, max_concurrent_tasks=4)
        agent.pick_up_task("t1")
        agent.pick_up_task("t2")
        assert agent.utilization == 0.5

    def test_test_writer_role(self):
        writer = Agent(name="TW", role=Role.TEST_WRITER)
        assert writer.can_handle("test_writer")
        assert not writer.can_handle("developer")
