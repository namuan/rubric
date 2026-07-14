"""Tests for rubric.settings — global config loading and generation."""

import json
from pathlib import Path

from rubric.settings import (
    RubricConfig,
    load_rubric_config,
    write_default_config,
)


class TestWriteDefaultConfig:
    def test_writes_to_custom_path(self, tmp_path):
        target = tmp_path / "custom-config.json"
        result = write_default_config(target)
        assert result == target
        assert target.is_file()

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "deep" / "nested" / "rubric.json"
        write_default_config(target)
        assert target.is_file()

    def test_writes_valid_json(self, tmp_path):
        target = tmp_path / "rubric.json"
        write_default_config(target)
        loaded = json.loads(target.read_text())
        assert isinstance(loaded, dict)
        assert loaded["version"] == 1

    def test_writes_valid_config_that_passes_validation(self, tmp_path):
        target = tmp_path / "rubric.json"
        write_default_config(target)
        config = load_rubric_config(target)
        assert config is not None
        assert config.version == 1


class TestLoadRubricConfig:
    def test_loads_from_explicit_path(self, tmp_path):
        target = tmp_path / "test.json"
        target.write_text(json.dumps({"version": 1, "cli": {"default_output": "json"}}))
        config = load_rubric_config(target)
        assert config is not None
        assert config.cli.default_output == "json"

    def test_loads_from_env_var(self, monkeypatch, tmp_path):
        target = tmp_path / "env-config.json"
        target.write_text(json.dumps({"version": 1, "cli": {"default_output": "text"}}))
        monkeypatch.setenv("RUBRIC_CONFIG", str(target))
        config = load_rubric_config()
        assert config is not None
        assert config.cli.default_output == "text"

    def test_returns_none_for_missing_file(self, tmp_path):
        config = load_rubric_config(tmp_path / "does-not-exist.json")
        assert config is None

    def test_returns_none_for_invalid_json(self, tmp_path):
        target = tmp_path / "bad.json"
        target.write_text("not json at all")
        config = load_rubric_config(target)
        assert config is None

    def test_returns_none_when_env_var_points_to_missing_file(self, monkeypatch):
        monkeypatch.setenv("RUBRIC_CONFIG", "/tmp/absolutely-does-not-exist.json")
        config = load_rubric_config()
        assert config is None

    def test_loads_full_llm_config(self, tmp_path):
        target = tmp_path / "full.json"
        target.write_text(json.dumps({
            "version": 1,
            "cli": {"default_output": "text"},
            "llm": {
                "default_provider": "anthropic",
                "providers": {
                    "anthropic": {
                        "api_key_env": "KEY",
                        "base_url": "https://api.example.com",
                        "default_model": "claude-1",
                    }
                },
                "agents": {
                    "dev": {
                        "provider": "anthropic",
                        "model": "claude-1",
                        "temperature": 0.5,
                    }
                },
                "global": {
                    "enabled": True,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
            },
        }))
        config = load_rubric_config(target)
        assert config is not None
        assert config.llm is not None
        assert config.llm.default_provider == "anthropic"
        assert config.llm.global_settings.enabled is True
        assert config.llm.agents["dev"].temperature == 0.5

    def test_minimal_config_without_llm(self, tmp_path):
        target = tmp_path / "minimal.json"
        target.write_text(json.dumps({"version": 1}))
        config = load_rubric_config(target)
        assert config is not None
        assert config.llm is None
        assert config.cli.default_output == "text"

    def test_strips_comment_keys(self, tmp_path):
        target = tmp_path / "with-comments.json"
        target.write_text(json.dumps({
            "version": 1,
            "//": "a comment",
            "//_": "another comment",
            "cli": {"default_output": "json"},
        }))
        config = load_rubric_config(target)
        assert config is not None
        assert config.cli.default_output == "json"


class TestRubricConfigModel:
    def test_defaults(self):
        cfg = RubricConfig(version=1)
        assert cfg.cli.default_output == "text"
        assert cfg.llm is None

    def test_roundtrip(self):
        original = RubricConfig(version=2, cli={"default_output": "json"})
        data = original.model_dump(by_alias=True)
        reloaded = RubricConfig.model_validate(data)
        assert reloaded.version == 2
        assert reloaded.cli.default_output == "json"
