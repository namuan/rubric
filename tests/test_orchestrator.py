"""End-to-end tests for sequential and asynchronous delivery pipelines."""

import asyncio

import pytest

import rubric.orchestrator as orchestrator

from rubric.agents import ProductOwnerAgent
from rubric.models.artifacts import ArtifactType
from rubric.models.story import StoryState
from rubric.orchestrator import (
    StoryRequest,
    create_default_team,
    run_full_pipeline,
    run_multiple_pipelines,
    run_multiple_pipelines_async,
)


class TestFullPipeline:
    def test_product_owner_executes_while_story_is_in_inception(self, monkeypatch):
        class RecordingProductOwner(ProductOwnerAgent):
            observed_state = None

            def execute(self, task, story):
                self.observed_state = story.state
                return super().execute(task, story)

        team = create_default_team()
        product_owner = RecordingProductOwner(name="Recording PO")
        team[0] = product_owner
        monkeypatch.setattr(orchestrator, "create_default_team", lambda: team)
        result = orchestrator.run_full_pipeline("Feature", "Description")
        assert product_owner.observed_state == StoryState.INCEPTION
        assert result["story"]["state"] == "done"

    def test_pipeline_blocks_instead_of_completing_an_unassigned_task(
        self, monkeypatch
    ):
        monkeypatch.setattr(orchestrator, "create_default_team", lambda: [])
        result = orchestrator.run_full_pipeline("Feature", "Description")
        assert result["story"]["state"] == "blocked"
        assert result["story"]["tasks_completed"] == 0
        assert result["story"]["tasks_total"] == 1

    def test_run_full_pipeline(self):
        result = run_full_pipeline(
            title="Test Feature",
            description="A test feature for integration testing",
            acceptance_criteria=["Works correctly", "Has tests"],
        )
        assert result["story"]["state"] == "done"
        assert result["story"]["progress"] == "100%"
        assert result["story"]["tdd_steps_total"] > 0
        assert (
            result["story"]["tdd_steps_completed"] == result["story"]["tdd_steps_total"]
        )

    def test_pipeline_creates_criteria_when_none_are_supplied(self):
        result = run_full_pipeline("Feature", "Description")
        assert result["story"]["state"] == "done"
        assert any(
            "Acceptance Criteria" in artifact for artifact in result["artifacts"]
        )

    def test_pipeline_produces_tdd_artifacts(self):
        artifacts = run_full_pipeline("Auth", "JWT", ["Register"])["artifacts"]
        assert any(artifact.startswith("[test_code] RED:") for artifact in artifacts)
        assert any(
            artifact.startswith("[source_code] GREEN:") for artifact in artifacts
        )
        assert any(
            artifact.startswith("[source_code] REFACTOR:") for artifact in artifacts
        )

    def test_pipeline_produces_previously_unused_artifact_types(self):
        result = run_full_pipeline("Checkout", "E-commerce checkout", ["Pay with card"])
        artifact_types = {
            summary.split("]", 1)[0].removeprefix("[")
            for summary in result["artifacts"]
        }
        assert {
            ArtifactType.SPRINT_PLAN.value,
            ArtifactType.CONFIG.value,
            ArtifactType.CHANGELOG.value,
            ArtifactType.DOCUMENTATION.value,
        } <= artifact_types

    def test_pipeline_persists_and_logs_when_paths_are_supplied(self, tmp_path):
        state_file = tmp_path / "state.json"
        event_file = tmp_path / "events.jsonl"
        result = run_full_pipeline(
            "Persistent",
            "Description",
            ["Done"],
            persistence_path=str(state_file),
            event_log_path=str(event_file),
        )
        assert result["story"]["state"] == "done"
        assert state_file.is_file()
        assert event_file.is_file()

    def test_persisted_state_can_be_reused_for_another_pipeline(self, tmp_path):
        state_file = tmp_path / "state.json"
        first = run_full_pipeline(
            "First",
            "Description",
            ["Done"],
            persistence_path=str(state_file),
        )
        second = run_full_pipeline(
            "Second",
            "Description",
            ["Done"],
            persistence_path=str(state_file),
        )
        assert first["story"]["state"] == "done"
        assert second["story"]["state"] == "done"
        assert second["engine_status"]["total_stories"] == 2

    def test_run_multiple_pipelines(self):
        results = run_multiple_pipelines(
            [
                StoryRequest("Search", "Find products", ["Returns products"]),
                StoryRequest("Checkout", "Pay for products", ["Accepts payment"]),
            ]
        )
        assert [result["story"]["title"] for result in results] == [
            "Search",
            "Checkout",
        ]
        assert all(result["story"]["state"] == "done" for result in results)

    def test_run_multiple_pipelines_async(self):
        results = asyncio.run(
            run_multiple_pipelines_async(
                [
                    StoryRequest("Search", "Find products", ["Returns products"]),
                    StoryRequest("Checkout", "Pay for products", ["Accepts payment"]),
                ],
                max_concurrency=2,
            )
        )
        assert [result["story"]["title"] for result in results] == [
            "Search",
            "Checkout",
        ]
        assert all(result["story"]["state"] == "done" for result in results)

    def test_async_batch_rejects_invalid_concurrency(self):
        with pytest.raises(ValueError, match="max_concurrency"):
            asyncio.run(run_multiple_pipelines_async([], max_concurrency=0))
