"""Tests for command-line parsing and output."""

import json
import logging
from pathlib import Path

from rubric import cli
from rubric.settings import DEFAULT_CONFIG


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


def _write_minimal_config(path: Path, output_format: str = "text") -> None:
    """Write a small valid rubric config for test use."""
    config = {"version": 1, "cli": {"default_output": output_format}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config))


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

    def test_parse_run_with_config_arg(self):
        args = cli.parse_args(["run", "Feature", "--config", "/tmp/r.json"])
        assert args.config == "/tmp/r.json"

    def test_parse_config_init_args(self):
        args = cli.parse_args(["config", "init", "--output", "/tmp/out.json"])
        assert args.command == "config"
        assert args.config_command == "init"
        assert args.output == "/tmp/out.json"

    def test_parse_config_no_subcommand(self):
        args = cli.parse_args(["config"])
        assert args.command == "config"
        assert args.config_command is None


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

    def test_output_from_config_file(self, monkeypatch, capsys, tmp_path):
        """--output defaults to config's cli.default_output when no CLI flag."""
        monkeypatch.setattr(cli, "run_full_pipeline", lambda **_: _result())
        config_path = tmp_path / "rubric.json"
        _write_minimal_config(config_path, output_format="json")

        cli.main(["run", "Feature", "--config", str(config_path)])
        out = capsys.readouterr().out
        assert json.loads(out)["story"]["state"] == "done"

    def test_cli_flag_overrides_config_output(self, monkeypatch, capsys, tmp_path):
        """Explicit --output text wins over config's json default."""
        monkeypatch.setattr(cli, "run_full_pipeline", lambda **_: _result())
        config_path = tmp_path / "rubric.json"
        _write_minimal_config(config_path, output_format="json")

        cli.main(
            ["run", "Feature", "--config", str(config_path), "--output", "text"]
        )
        out = capsys.readouterr().out
        assert "Final State:     done" in out


class TestConfigCommand:
    def test_config_init_writes_file(self, tmp_path):
        target = tmp_path / "rubric.json"
        cli.main(["config", "init", "--output", str(target)])
        assert target.is_file()
        loaded = json.loads(target.read_text())
        assert loaded["version"] == 1
        assert "llm" in loaded
        assert "cli" in loaded

    def test_config_init_structure_matches_template(self, tmp_path):
        target = tmp_path / "rubric.json"
        cli.main(["config", "init", "--output", str(target)])
        loaded = json.loads(target.read_text())
        assert loaded["llm"]["default_provider"] == DEFAULT_CONFIG["llm"]["default_provider"]
        assert "openai" in loaded["llm"]["providers"]
        assert "product_owner" in loaded["llm"]["agents"]

    def test_config_init_output_message(self, capsys, tmp_path):
        target = tmp_path / "rubric.json"
        cli.main(["config", "init", "--output", str(target)])
        out = capsys.readouterr().out
        assert str(target) in out

    def test_config_status_no_config(self, monkeypatch, capsys):
        """`rubric config` shows not-found message when no config exists."""
        monkeypatch.setattr(cli, "load_rubric_config", lambda *a, **kw: None)
        monkeypatch.setattr(cli, "DEFAULT_CONFIG_FILE", Path("/nonexistent/config.json"))
        cli.main(["config"])
        out = capsys.readouterr().out
        assert "not found" in out
        assert "rubric config init" in out
