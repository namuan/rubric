"""Shared fixtures and import setup for Rubric tests."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rubric.engine.workflow import WorkflowEngine
from rubric.models.story import Story, Task


@pytest.fixture
def workflow_engine() -> WorkflowEngine:
    return WorkflowEngine()


@pytest.fixture
def story(workflow_engine: WorkflowEngine) -> Story:
    return workflow_engine.create_story("Test Feature", "A test feature")


@pytest.fixture
def agent_context(workflow_engine: WorkflowEngine, story: Story):
    story.acceptance_criteria = ["Criteria 1", "Criteria 2"]
    task = Task(title="Test task")
    story.tasks = [task]
    return workflow_engine, story, task
