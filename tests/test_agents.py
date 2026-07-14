"""Tests for role-specific agent behaviour."""

from rubric.agents import (
    ArchitectAgent,
    DeveloperAgent,
    DevOpsAgent,
    ProductOwnerAgent,
    ScrumMasterAgent,
    TestWriterAgent,
)
from rubric.llm import LLMRequest, load_llm_config
from rubric.models.artifacts import ArtifactType
from rubric.models.story import TaskStep, TaskStepStatus, TaskStepType


class RecordingProvider:
    def __init__(self):
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> str:
        self.requests.append(request)
        return "LLM guidance"


class TestAgentExecution:
    def test_loads_base_llm_configuration(self):
        config = load_llm_config()
        assert config is not None
        assert config.agents["developer"].provider == "anthropic"
        assert config.agents["product_owner"].provider == "openai"
        assert not config.global_settings.enabled

    def test_llm_config_has_required_providers(self):
        config = load_llm_config()
        assert config is not None
        assert "openai" in config.providers
        assert "anthropic" in config.providers
        assert "ollama" in config.providers

    def test_product_owner(self, agent_context):
        engine, story, task = agent_context
        task.title = "Define story scope"
        agent = ProductOwnerAgent(name="PO")
        agent.bind(engine)
        assert agent.registry is engine
        artifacts = agent.execute(task, story)
        assert any(
            artifact.artifact_type == ArtifactType.STORY_BRIEF for artifact in artifacts
        )

    def test_architect(self, agent_context):
        engine, story, task = agent_context
        task.title = "Design architecture"
        agent = ArchitectAgent(name="Arch")
        agent.bind(engine)
        assert agent.execute(task, story)

    def test_developer_uses_one_execute_interface(self, agent_context):
        engine, story, task = agent_context
        task.steps = [
            TaskStep(step_type=TaskStepType.RED, title="RED"),
            TaskStep(step_type=TaskStepType.GREEN, title="GREEN"),
            TaskStep(step_type=TaskStepType.REFACTOR, title="REFACTOR"),
        ]
        agent = DeveloperAgent(name="Dev")
        agent.bind(engine)
        for step in task.steps:
            step.status = TaskStepStatus.IN_PROGRESS
            assert agent.execute(task, story, step=step)[0]
            assert step.status == TaskStepStatus.DONE

    def test_test_writer(self, agent_context):
        engine, story, task = agent_context
        task.title = "Write and run acceptance tests"
        agent = TestWriterAgent(name="TW")
        agent.bind(engine)
        artifacts = agent.execute(task, story)
        assert any(
            artifact.artifact_type == ArtifactType.TEST_REPORT for artifact in artifacts
        )

    def test_devops_produces_all_delivery_artifacts(self, agent_context):
        engine, story, task = agent_context
        task.title = "Create release notes and documentation"
        agent = DevOpsAgent(name="DO")
        agent.bind(engine)
        artifact_types = {
            artifact.artifact_type for artifact in agent.execute(task, story)
        }
        assert {ArtifactType.CHANGELOG, ArtifactType.DOCUMENTATION} <= artifact_types

    def test_scrum_master_planner_and_sprint_plan(self, agent_context):
        engine, story, task = agent_context
        task.title = "Break down into tasks"
        agent = ScrumMasterAgent(name="SM")
        agent.bind(engine)
        planned_tasks = agent.plan_story(story)
        artifacts = agent.execute(task, story)
        assert len(planned_tasks) == 3
        assert all(len(planned_task.steps) == 3 for planned_task in planned_tasks)
        assert any(
            artifact.artifact_type == ArtifactType.SPRINT_PLAN for artifact in artifacts
        )

    def test_injected_llm_provider_is_used_and_recorded(self, agent_context):
        engine, story, task = agent_context
        task.title = "Define story scope"
        provider = RecordingProvider()
        agent = ProductOwnerAgent(name="PO", llm_provider=provider)
        agent.bind(engine)
        artifacts = agent.execute(task, story)
        cached_response = agent.prepare_execution(task, story, "Repeat guidance")
        assert len(provider.requests) == 1
        assert cached_response == "LLM guidance"
        assert provider.requests[0].role == "product_owner"
        assert artifacts[0].metadata["llm"]["response"] == "LLM guidance"
