"""Rubric CLI — multi-agent workflow engine for large-scale application delivery."""

from __future__ import annotations

import argparse
import json
import logging

from rubric.orchestrator import run_full_pipeline


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
        default="text",
        help="Output format",
    )
    run_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    run_parser.add_argument(
        "--state-file",
        help="Persist workflow state to this JSON file",
    )
    run_parser.add_argument(
        "--event-log",
        help="Append workflow events to this JSON-lines file",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse Rubric CLI arguments."""
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.command == "run":
        if args.verbose:
            logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

        criteria = args.criteria if args.criteria else None
        result = run_full_pipeline(
            title=args.title,
            description=args.description,
            acceptance_criteria=criteria,
            persistence_path=args.state_file,
            event_log_path=args.event_log,
        )

        if args.output == "json":
            print(json.dumps(result, indent=2))
        else:
            _print_text(result)
    else:
        build_parser().print_help()


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


if __name__ == "__main__":
    main()
