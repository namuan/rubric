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

### Run several stories

Use `run_multiple_pipelines()` for sequential work. Use `run_multiple_pipelines_async()` to run independent stories concurrently. Each story gets its own engine and agent team.

```python
import asyncio

from rubric.orchestrator import StoryRequest, run_multiple_pipelines_async

results = asyncio.run(run_multiple_pipelines_async([
    StoryRequest("Product search", "Find products", ["Shows matching products"]),
    StoryRequest("Checkout", "Pay for products", ["Accepts payment"]),
]))
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

All 60 tests should pass with zero warnings.

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
│       ├── llm/                # Provider-neutral LLM configuration and clients
│       ├── persistence/        # JSON workflow state storage
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
    ├── test_models.py
    ├── test_engine.py
    ├── test_agents.py
    ├── test_orchestrator.py
    └── test_cli.py
```

---

## CLI Reference

```bash
rubric run <title> \
  --description <text> \
  --criteria <text> \
  --output json|text \
  --verbose \
  --state-file <path> \
  --event-log <path>
```

| Flag | Short | Description |
|------|-------|-------------|
| `title` | | Story title (required, positional) |
| `--description` | `-d` | Story description |
| `--criteria` | `-c` | Acceptance criteria (repeatable) |
| `--output` | `-o` | Output format: `json` or `text` (default: text) |
| `--verbose` | `-v` | Enable detailed logging |
| `--state-file` | | Save and restore workflow state in this JSON file |
| `--event-log` | | Append workflow events to this JSON-lines file |

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

## Using real LLMs

Agents load the provider and model for their role from `config/llm_config.json`. They use deterministic template artifacts by default.

To enable live provider calls, set `global.enabled` to `true` in the configuration or set `RUBRIC_ENABLE_LLM=1`. Set the provider API key environment variable named in the configuration before you run the pipeline.

Set `APP_ENV` or `ENV` to select an environment. Rubric first looks for `llm_config.<environment>.json`. It then applies any matching `environments` override in the base configuration. The included development configuration uses Ollama. Production keeps the configured cloud providers.

Rubric supports OpenAI-compatible APIs, Anthropic and Google providers. You can also inject an `LLMProvider` when you create an agent for custom integrations.

## Save workflow state and events

Use `--state-file` to save the workflow after every transition and completed task. Start another engine with the same path to restore its stories, artifacts and context. Register a live agent team after restoring the engine.

Use `--event-log` to write one JSON event per line for monitoring or audit tools.
