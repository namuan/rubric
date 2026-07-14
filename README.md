# Rubric

A multi-agent workflow engine for building large-scale applications. Stories flow through a structured lifecycle — inception to delivery — driven by a team of AI agents following Red-Green-Refactor (TDD) for every task.

## Architecture Overview

```
User Story
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│                    RUBRIC                                   │
│                                                              │
│  INCEPTION ──► PLANNING ──► DESIGN ──►                       │
│                                          │                   │
│                                          ▼                   │
│                                  IMPLEMENTATION              │
│                                    (TDD cycle)               │
│                                    ┌─────┐                   │
│                                    │ RED │ (write test)      │
│                                    ├─────┤                   │
│                                    │GREEN│ (write code)      │
│                                    ├─────┤                   │
│                                    │RE-  │ (refactor)        │
│                                    │FACT │                   │
│                                    └─────┘                   │
│                                          │                   │
│                                          ▼                   │
│  REVIEW ──► ACCEPTANCE ──► INTEGRATION ──► DELIVERY ──► DONE│
└──────────────────────────────────────────────────────────────┘
         │            │              │              │
         ▼            ▼              ▼              ▼
    Code Review   End-User E2E    CI/CD +       Release Notes
                   Tests         Deploy
```

### Agent Roles

| Role | Name | Responsibility |
|------|------|----------------|
| Product Owner | Alice PO | Defines stories and acceptance criteria |
| Architect | Bob Architect | Designs architecture, API contracts, data models |
| Scrum Master | Grace Planner | Decomposes stories into small TDD tasks |
| Developer | Charlie Dev | Implements via Red→Green→Refactor |
| Reviewer | Diana Reviewer | Code review and quality feedback |
| Test Writer | Eve TestWriter | End-user acceptance tests (E2E) |
| DevOps | Frank DevOps | CI/CD pipelines, deployment, releases |

### TDD Workflow

Each task follows Red-Green-Refactor:

1. **RED** — Write one failing test for a single specific behavior
2. **GREEN** — Write the minimum code to make the test pass
3. **REFACTOR** — Clean up while keeping all tests green

Each step is small enough that an agent only needs to focus on one thing at a time.

---

## Prerequisites

- **Python 3.11 or later**
- [uv](https://docs.astral.sh/uv/) (package and project manager)

## Installation

### 1. Clone or create the project

```bash
git clone https://github.com/namuan/rubric.git
cd rubric
```

### 2. Install the package

```bash
uv sync
```

This installs Rubric in editable mode with development dependencies (pytest, pytest-asyncio).

### 3. Verify installation

```bash
uv run rubric --help
```

You should see the CLI help output.

---

## Quick Start

### Run a story through the full pipeline

```bash
uv run rubric run "User Authentication" \
  --description "JWT-based authentication system" \
  --criteria "Users can register with email and password" \
  --criteria "Users can log in and receive a JWT token" \
  --criteria "Protected routes reject requests without a valid token"
```

Output shows:
- Final story state (`done`)
- Task completion (e.g. `11/11`)
- TDD step completion (e.g. `12/12`)
- All artifacts produced

### Run from Python

```python
from rubric.orchestrator import run_full_pipeline

result = run_full_pipeline(
    title="Shopping Cart",
    description="E-commerce shopping cart with add/remove/checkout",
    acceptance_criteria=[
        "User can add items to cart",
        "User can remove items from cart",
        "Cart shows correct total price",
    ],
)

print(f"State: {result['story']['state']}")
print(f"Tasks: {result['story']['tasks_completed']}/{result['story']['tasks_total']}")
print(f"TDD Steps: {result['story']['tdd_steps_completed']}/{result['story']['tdd_steps_total']}")
```

### Run the example script

```bash
uv run python examples/basic_story.py
```

---

## Running Tests

```bash
uv run pytest tests/ -v
```

All 38 tests should pass with zero warnings.

---

## Project Structure

```
rubric/
├── pyproject.toml              # Package config
├── README.md
├── config/
│   └── llm_config.json         # Example LLM configuration
├── src/
│   └── rubric/
│       ├── cli.py              # CLI entry point
│       ├── orchestrator.py     # Wires everything together
│       ├── models/
│       │   ├── story.py        # Story, Task, TaskStep, StoryState
│       │   ├── agent.py        # Agent, Role definitions
│       │   └── artifacts.py    # Artifact types and model
│       ├── engine/
│       │   ├── workflow.py     # State machine engine
│       │   ├── scheduler.py    # Task assignment + load balancing
│       │   └── transitions.py  # Quality gates at stage boundaries
│       ├── agents/
│       │   ├── base.py         # Abstract base agent
│       │   ├── product_owner.py
│       │   ├── architect.py
│       │   ├── developer.py    # TDD: Red→Green→Refactor
│       │   ├── reviewer.py
│       │   ├── test_writer.py  # End-user acceptance tests
│       │   ├── devops.py
│       │   └── scrum_master.py # Planner + decomposition
│       └── context/
│           └── manager.py      # Shared state for agents
├── examples/
│   └── basic_story.py          # Two runnable examples
└── tests/
    └── test_rubric.py           # 38 tests
```

---

## CLI Reference

```bash
rubric run <title> \
  --description <text> \
  --criteria <text> \
  --output json|text \
  --verbose
```

| Flag | Short | Description |
|------|-------|-------------|
| `title` | | Story title (required, positional) |
| `--description` | `-d` | Story description |
| `--criteria` | `-c` | Acceptance criteria (repeatable) |
| `--output` | `-o` | Output format: `json` or `text` (default: text) |
| `--verbose` | `-v` | Enable detailed logging |

Example with JSON output:

```bash
uv run rubric run "Feature" --output json | jq .
```

---

## Customisation

### Creating a custom team

```python
from rubric.agents import DeveloperAgent, ReviewerAgent
from rubric.engine.workflow import WorkflowEngine

engine = WorkflowEngine()

# Add your agents
dev = DeveloperAgent(name="Custom Dev", capabilities=["python", "rust"])
reviewer = ReviewerAgent(name="Custom Reviewer")
dev.bind(engine)
reviewer.bind(engine)

# Create a story and run it
story = engine.create_story("My Feature", "Description")
# ... see orchestrator.py for full pipeline logic
```

### Adding a new agent role

1. Add a new `Role` enum value in `models/agent.py`
2. Create a new agent class in `agents/` extending `BaseAgent`
3. Implement `execute(task, story)` to produce artifacts
4. Register it in `agents/__init__.py`
5. Add it to `create_default_team()` in `orchestrator.py`

---

## Connecting to Real LLMs

This engine currently uses template-based agents that produce deterministic artifacts. To connect to real LLMs (OpenAI, Anthropic, local models, etc.), see `config/llm_config.json` for an example configuration structure.

Each agent's `execute()` method can be modified to call an LLM using the configured provider and model settings.
