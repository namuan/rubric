"""Tests for command-line parsing and output."""

import json
import logging

from rubric import cli


def _result() -> dict:
    return {
        "story": {
            "title": "Feature",
            "id": "story-1",
            "state": "done",
            "progress": "100%",
            "tasks_completed": 2,
            "tasks_total": 2,
            "tdd_steps_completed": 3,
            "tdd_steps_total": 3,
            "artifacts": 1,
            "transitions": 8,
        },
        "artifacts": ["[story_brief] Story Brief: Feature"],
        "engine_status": {
            "total_stories": 1,
            "total_agents": 7,
            "total_artifacts": 1,
            "agent_utilization": {"Dev": "0%"},
        },
    }


class TestArgumentParsing:
    def test_parse_run_arguments(self):
        args = cli.parse_args(
            [
                "run",
                "Feature",
                "--description",
                "Description",
                "--criteria",
                "Works",
                "--criteria",
                "Tests pass",
                "--output",
                "json",
                "--state-file",
                "state.json",
                "--event-log",
                "events.jsonl",
                "--verbose",
            ]
        )
        assert args.title == "Feature"
        assert args.criteria == ["Works", "Tests pass"]
        assert args.output == "json"
        assert args.state_file == "state.json"
        assert args.event_log == "events.jsonl"
        assert args.verbose


class TestCLIOutput:
    def test_json_output(self, monkeypatch, capsys):
        captured_args = {}

        def fake_pipeline(**kwargs):
            captured_args.update(kwargs)
            return _result()

        monkeypatch.setattr(cli, "run_full_pipeline", fake_pipeline)
        cli.main(["run", "Feature", "--output", "json", "--state-file", "state.json"])
        assert json.loads(capsys.readouterr().out)["story"]["state"] == "done"
        assert captured_args["persistence_path"] == "state.json"

    def test_text_output(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "run_full_pipeline", lambda **_: _result())
        cli.main(["run", "Feature"])
        output = capsys.readouterr().out
        assert "Final State:     done" in output
        assert "ARTIFACTS PRODUCED" in output

    def test_verbose_configures_logging(self, monkeypatch):
        monkeypatch.setattr(cli, "run_full_pipeline", lambda **_: _result())
        calls = []
        monkeypatch.setattr(
            logging, "basicConfig", lambda **kwargs: calls.append(kwargs)
        )
        cli.main(["run", "Feature", "--verbose"])
        assert calls[0]["level"] == logging.INFO

    def test_no_command_prints_help(self, capsys):
        cli.main([])
        assert "usage: rubric" in capsys.readouterr().out
