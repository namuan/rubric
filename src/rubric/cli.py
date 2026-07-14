"""Rubric CLI — multi-agent workflow engine for large-scale application delivery."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from rubric.llm.config import default_config_path as llm_config_path
from rubric.orchestrator import run_full_pipeline
from rubric.settings import DEFAULT_CONFIG_FILE, load_rubric_config, write_default_config


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for reuse in tests and integrations."""
    parser = argparse.ArgumentParser(
        prog="rubric",
        description="Rubric — multi-agent workflow engine for large-scale application delivery",
    )
    sub = parser.add_subparsers(dest="command")

    # ── run command ────────────────────────────────────────────────────
    run_parser = sub.add_parser("run", help="Run a story through the full pipeline")
    run_parser.add_argument("title", help="Story title")
    run_parser.add_argument("--description", "-d", default="", help="Story description")
    run_parser.add_argument(
        "--criteria",
        "-c",
        action="append",
        default=[],
        help="Acceptance criteria (repeatable)",
    )
    run_parser.add_argument(
        "--output",
        "-o",
        choices=["json", "text"],
        default=None,
        help="Output format (default: text)",
    )
    run_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    run_parser.add_argument(
        "--config",
        help=f"Path to rubric config file (default: {DEFAULT_CONFIG_FILE})",
    )
    run_parser.add_argument(
        "--state-file",
        help="Persist workflow state to this JSON file",
    )
    run_parser.add_argument(
        "--event-log",
        help="Append workflow events to this JSON-lines file",
    )

    # ── config command ─────────────────────────────────────────────────
    config_parser = sub.add_parser("config", help="Manage Rubric configuration")
    config_sub = config_parser.add_subparsers(dest="config_command")

    # config init
    init_parser = config_sub.add_parser("init", help="Generate an example config file")
    init_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help=f"Output path (default: {DEFAULT_CONFIG_FILE})",
    )

    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse Rubric CLI arguments."""
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.command == "run":
        _handle_run(args)
    elif args.command == "config":
        _handle_config(args)
    else:
        build_parser().print_help()


# ── Run handler ─────────────────────────────────────────────────────
def _handle_run(args: argparse.Namespace) -> None:
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    # Load global config
    config = load_rubric_config(args.config)

    # Resolve output format: CLI flag > config > default
    output_format: str = args.output or "text"
    if args.output is None and config is not None:
        output_format = config.cli.default_output

    # ── Startup info ──────────────────────────────────────────────────
    llm_source = llm_config_path()
    llm_info = _describe_llm_status()

    if output_format == "text":
        print(f"Config : {llm_source or 'none (using defaults)'}", file=sys.stderr)
        print(f"LLM    : {llm_info}", file=sys.stderr)
        print(file=sys.stderr)

    criteria = args.criteria if args.criteria else None
    result = run_full_pipeline(
        title=args.title,
        description=args.description,
        acceptance_criteria=criteria,
        persistence_path=args.state_file,
        event_log_path=args.event_log,
    )

    if output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        _print_text(result)


# ── Config handler ──────────────────────────────────────────────────
def _handle_config(args: argparse.Namespace) -> None:
    if args.config_command == "init":
        target = write_default_config(args.output)
        print(f"Config written to {target}")
    else:
        _print_config_status()


def _print_config_status() -> None:
    """Print the current global config location and status."""
    config = load_rubric_config()
    print(f"Global config path: {DEFAULT_CONFIG_FILE}")
    if config is None:
        print("Status:   not found")
        print()
        print("Run 'rubric config init' to generate an example config file.")
    else:
        print(f"Status:   loaded (version {config.version})")
        print(f"Default output: {config.cli.default_output}")
        if config.llm is not None:
            print(f"LLM enabled:    {config.llm.global_settings.enabled}")
        else:
            print("LLM enabled:    false (no LLM config section)")


# ── Output ──────────────────────────────────────────────────────────
def _print_text(result: dict) -> None:
    """Pretty-print results as human-readable text."""
    story = result["story"]
    print()
    print("=" * 60)
    print(f"  STORY: {story['title']}")
    print(f"  ID:    {story['id']}")
    print("=" * 60)
    print()
    print(f"  Final State:     {story['state']}")
    print(f"  Progress:        {story['progress']}")
    print(f"  Tasks:           {story['tasks_completed']}/{story['tasks_total']}")
    print(
        f"  TDD Steps:       {story['tdd_steps_completed']}/{story['tdd_steps_total']}"
    )
    print(f"  Artifacts:       {story['artifacts']}")
    print(f"  Transitions:     {story['transitions']}")
    print()

    if result["artifacts"]:
        print("  ARTIFACTS PRODUCED:")
        print("  " + "-" * 40)
        for art in result["artifacts"]:
            print(f"    - {art}")
        print()

    status = result["engine_status"]
    print("  ENGINE STATUS:")
    print("  " + "-" * 40)
    print(f"    Stories:   {status['total_stories']}")
    print(f"    Agents:    {status['total_agents']}")
    print(f"    Artifacts: {status['total_artifacts']}")
    print()

    if status.get("agent_utilization"):
        print("  AGENT UTILIZATION:")
        print("  " + "-" * 40)
        for name, util in status["agent_utilization"].items():
            print(f"    {name:20s} {util}")
    print()
    print("=" * 60)
    print()


# ── Helpers ─────────────────────────────────────────────────────────
def _describe_llm_status() -> str:
    """Return a human-readable description of the current LLM configuration."""
    from rubric.llm.config import load_llm_config as load_llm

    llm = load_llm()
    if llm is None:
        return "disabled (no config found)"
    if not llm.global_settings.enabled:
        return f"disabled (enable by setting global.enabled or RUBRIC_ENABLE_LLM=1)"
    active_agents = [
        role for role, cfg in llm.agents.items()
    ]
    if not active_agents:
        return "enabled but no agents configured"
    return f"enabled ({len(active_agents)} agents, default: {llm.default_provider})"


if __name__ == "__main__":
    main()
