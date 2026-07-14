# Scout Report — Rubric Codebase Topographical Map

**Generated:** 2026-07-14  
**Analyzed by:** Scout Agent (pipeline stage 1)  
**Repository root:** `/Users/nnn/temp/rubric`

---

## 1. Directory Topography

```
/Users/nnn/temp/rubric/
├── .git/
├── .gitignore
├── .pytest_cache/
├── pyproject.toml              (28 lines)
├── README.md
├── config/
│   └── llm_config.json         (94 lines)
├── docs/
│   └── code-analysis/
│       └── scout-report.md     ← this file
├── examples/
│   └── basic_story.py          (84 lines)
├── src/
│   └── rubric/
│       ├── __init__.py         (20 lines)
│       ├── cli.py              (106 lines)
│       ├── orchestrator.py     (264 lines)
│       ├── agents/
│       │   ├── __init__.py     (19 lines)
│       │   ├── base.py         (66 lines)
│       │   ├── architect.py    (150 lines)
│       │   ├── developer.py    (179 lines)
│       │   ├── devops.py       (114 lines)
│       │   ├── product_owner.py (81 lines)
│       │   ├── reviewer.py     (88 lines)
│       │   ├── scrum_master.py (208 lines)
│       │   └── test_writer.py  (167 lines)
│       ├── context/
│       │   ├── __init__.py     (3 lines)
│       │   └── manager.py      (75 lines)
│       ├── engine/
│       │   ├── __init__.py     (11 lines)
│       │   ├── scheduler.py    (82 lines)
│       │   ├── transitions.py  (84 lines)
│       │   └── workflow.py     (302 lines)
│       ├── models/
│       │   ├── __init__.py     (28 lines)
│       │   ├── agent.py        (73 lines)
│       │   ├── artifacts.py    (76 lines)
│       │   └── story.py        (231 lines)
└── tests/
    ├── __init__.py             (0 lines)
    └── test_rubric.py          (473 lines)
```

**Total Python files:** 24  
**Total lines of Python:** 2,984  

---

## 2. Entry Points

### 2.1 CLI Entry Point
- **Command:** `rubric` (registered in `pyproject.toml` under `[project.scripts]`)
- **Module:** `rubric.cli:main`
- **File:** `src/rubric/cli.py`
- **Subcommands:** `rubric run <title> [--description] [--criteria] [--output json|text] [--verbose]`

### 2.2 Python API Surface
- **`rubric.orchestrator.run_full_pipeline(title, description, acceptance_criteria)`** — the main public API for running a complete story through all 8 stages.
- **`rubric.orchestrator.create_default_team()`** — creates one agent of each role.
- **`rubric.orchestrator.find_agent_obj(agents, agent_id)`** — utility to look up a bound agent by ID.

### 2.3 Public Exports from `__init__.py` Files

| `__init__.py` location | Exported names |
|---|---|
| `src/rubric/__init__.py` | `Story`, `Task`, `TaskStep`, `StoryState`, `Agent`, `Role`, `Artifact`, `ArtifactType`, `WorkflowEngine`, `ContextManager` |
| `src/rubric/models/__init__.py` | `Story`, `Task`, `TaskStep`, `TaskStepType`, `TaskStepStatus`, `StoryState`, `TaskStatus`, `TaskPriority`, `Agent`, `Role`, `STAGE_RESPONSIBILITIES`, `Artifact`, `ArtifactType` |
| `src/rubric/engine/__init__.py` | `WorkflowEngine`, `WorkflowEvent`, `TaskScheduler`, `TransitionGate`, `validate_transition` |
| `src/rubric/agents/__init__.py` | `BaseAgent`, `ProductOwnerAgent`, `ArchitectAgent`, `DeveloperAgent`, `ReviewerAgent`, `TestWriterAgent`, `DevOpsAgent`, `ScrumMasterAgent` |
| `src/rubric/context/__init__.py` | `ContextManager` |

---

## 3. Package Dependencies

Source: `pyproject.toml`

### Build System
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Runtime Dependencies
| Package | Constraint |
|---|---|
| `pydantic` | `>=2.0` |

Only **one runtime dependency** — Pydantic v2 for all data models (`BaseModel`, `Field`).

### Dev/Optional Dependencies
| Package | Constraint |
|---|---|
| `pytest` | `>=7.0` |
| `pytest-asyncio` | `>=0.21` |

Two dev dependencies — pytest for the test suite, plus asyncio support (even though the codebase is currently synchronous).

### Python Version
- **Requires:** `>=3.11` (uses `str` `Enum`, `removeprefix`, `datetime` UTC features, `from __future__ import annotations`)

### Packaging
- **Tool:** Hatchling
- **Wheel packages:** `["src/rubric"]`
- **No `setup.py` or `setup.cfg`** — pure pyproject.toml build.

---

## 4. File Inventory

| Area | `.py` files | Lines of code |
|---|---|---|
| `src/rubric/` (package root) | 3 (`__init__.py`, `cli.py`, `orchestrator.py`) | 390 |
| `src/rubric/models/` | 4 | 408 |
| `src/rubric/engine/` | 4 | 479 |
| `src/rubric/agents/` | 9 | 1,072 |
| `src/rubric/context/` | 2 | 78 |
| **src/ total** | **22** | **2,427** |
| `tests/` | 2 | 473 |
| `examples/` | 1 | 84 |
| **Grand total** | **25** | **2,984** |

Non-Python files in repo:
| File | Lines | Purpose |
|---|---|---|
| `pyproject.toml` | 28 | Build config, dependencies, CLI entry |
| `config/llm_config.json` | 94 | LLM configuration (for downstream LLM agent implementations) |
| `README.md` | — | Project readme |

---

## 5. Module Line Counts

| Module | Files | Lines | % of codebase |
|---|---|---|---|
| `agents/` | 9 | 1,072 | 36% |
| `engine/` | 4 | 479 | 16% |
| `models/` | 4 | 408 | 14% |
| `orchestrator.py` | 1 | 264 | 9% |
| `cli.py` | 1 | 106 | 4% |
| `context/` | 2 | 78 | 3% |
| Package root (`__init__.py`) | 1 | 20 | <1% |
| **src/ total** | **22** | **2,427** | **81%** |
| `tests/` | 2 | 473 | 16% |
| `examples/` | 1 | 84 | 3% |

### Individual file sizes (largest first)

| File | Lines |
|---|---|
| `tests/test_rubric.py` | 473 |
| `src/rubric/engine/workflow.py` | 302 |
| `src/rubric/orchestrator.py` | 264 |
| `src/rubric/models/story.py` | 231 |
| `src/rubric/agents/scrum_master.py` | 208 |
| `src/rubric/agents/developer.py` | 179 |
| `src/rubric/agents/test_writer.py` | 167 |
| `src/rubric/agents/architect.py` | 150 |
| `src/rubric/agents/devops.py` | 114 |
| `src/rubric/cli.py` | 106 |
| `src/rubric/agents/reviewer.py` | 88 |
| `src/rubric/engine/transitions.py` | 84 |
| `examples/basic_story.py` | 84 |
| `src/rubric/engine/scheduler.py` | 82 |
| `src/rubric/agents/product_owner.py` | 81 |
| `src/rubric/models/artifacts.py` | 76 |
| `src/rubric/context/manager.py` | 75 |
| `src/rubric/models/agent.py` | 73 |
| `src/rubric/agents/base.py` | 66 |
| `src/rubric/models/__init__.py` | 28 |
| `src/rubric/__init__.py` | 20 |
| `src/rubric/agents/__init__.py` | 19 |
| `src/rubric/engine/__init__.py` | 11 |
| `src/rubric/context/__init__.py` | 3 |
| `tests/__init__.py` | 0 |

---

## 6. Naming Conventions

### Modules & Packages — `snake_case`
All modules use lowercase with underscores:
- `story.py`, `agent.py`, `artifacts.py`
- `workflow.py`, `scheduler.py`, `transitions.py`
- `product_owner.py`, `scrum_master.py`, `test_writer.py`
- `orchestrator.py`, `cli.py`

### Classes — `PascalCase`
Every class follows PascalCase:
- `Story`, `Task`, `TaskStep`, `StoryState`, `TaskStatus`, `TaskPriority`, `TaskStepType`, `TaskStepStatus`
- `Agent`, `Role`
- `Artifact`, `ArtifactType`
- `WorkflowEngine`, `WorkflowEvent`
- `TaskScheduler`
- `TransitionGate`
- `ContextManager`
- `BaseAgent` (abstract base)
- `ProductOwnerAgent`, `ArchitectAgent`, `DeveloperAgent`, `ReviewerAgent`, `TestWriterAgent`, `DevOpsAgent`, `ScrumMasterAgent`

### Functions & Methods — `snake_case`
All functions and methods use lowercase with underscores:
- `run_full_pipeline()`, `create_default_team()`, `find_agent_obj()`
- `transition()`, `complete()`, `is_ready()`, `assign()`, `pick_up_task()`, `finish_task()`
- `main()`, `_print_text()`
- `find_best_agent()`, `assign_task()`, `get_workload()`
- `validate_transition()`, `evaluate()`
- `execute()`, `execute_step()`, `bind()`, `produce_artifact()`
- `plan_story()`, `_create_task_from_criterion()`, `_tdd_steps()`

### Constants — `UPPER_CASE`
- `STAGE_RESPONSIBILITIES` (module-level dict)
- `VALID_TRANSITIONS` (module-level dict)
- `DEFAULT_STAGE_GATES` (module-level dict)
- `ALL_TASKS_COMPLETE`, `HAS_ARTIFACTS`, `HAS_ACCEPTANCE_CRITERIA`, `MIN_PROGRESS` (module-level `TransitionGate` instances)

### Deviations / Noteworthy Patterns
1. **`EventHandler` type alias** — uses PascalCase for a type alias (`Callable[[WorkflowEvent], None]`). This is conventional for Python type aliases, but worth noting.
2. **`__test__ = False` on `TestWriterAgent`** — this class attribute prevents pytest from collecting it as a test class, since its name starts with "Test". This is a legitimate workaround.
3. **`__all__`** — defined in every `__init__.py` to restrict public exports.
4. **Leading underscores** — internal/private methods use `_` prefix consistently: `_emit()`, `_enrich_description()`, `_design_architecture()`, `_write_failing_test()`, `_review_code()`, etc.
5. **No `camelCase`** anywhere — consistent snake_case throughout.

---

## 7. Test Coverage Surface

### Test file: `tests/test_rubric.py` (473 lines)

| Test Class | What it covers | Modules touched |
|---|---|---|
| `TestStory` | Story creation, state transitions, lifecycle chain, progress calculation, ready_tasks dependency resolution | `models/story.py` |
| `TestTask` | Task dependencies, TDD step creation, step progression, task completion | `models/story.py` |
| `TestTaskStep` | Step completion, artifact ID assignment | `models/story.py` |
| `TestAgent` | Agent availability, role matching, utilization calculation, TEST_WRITER role | `models/agent.py` |
| `TestScheduler` | Agent finding by role, no-available-agent case, load balancing | `engine/scheduler.py` |
| `TestContextManager` | set/get, prefix filtering, story_context extraction, history tracking | `context/manager.py` |
| `TestTransitions` | ALL_TASKS_COMPLETE gate, acceptance criteria gate validation | `engine/transitions.py`, `models/story.py` |
| `TestWorkflowEngine` | Story creation, transitions, agent registration, event emission, status reporting, TDD task execution | `engine/workflow.py`, `agents/developer.py` |
| `TestAgentExecution` | ProductOwner, Architect, Developer (TDD steps), TestWriter, DevOps, ScrumMaster (planning) execution | All 7 agent classes in `agents/`, `engine/workflow.py` |
| `TestFullPipeline` | End-to-end `run_full_pipeline()`, TDD artifact verification, acceptance test artifact verification | `orchestrator.py`, all agents, engine |

### Modules with dedicated test coverage:
| Module | File | Covered by |
|---|---|---|
| `models/story.py` | ✅ | `TestStory`, `TestTask`, `TestTaskStep`, `TestTransitions` |
| `models/agent.py` | ✅ | `TestAgent` |
| `models/artifacts.py` | ✅ | Indirectly via agent execution tests |
| `engine/workflow.py` | ✅ | `TestWorkflowEngine`, `TestAgentExecution`, `TestFullPipeline` |
| `engine/scheduler.py` | ✅ | `TestScheduler` |
| `engine/transitions.py` | ✅ | `TestTransitions` |
| `context/manager.py` | ✅ | `TestContextManager` |
| `agents/base.py` | ✅ | Indirectly (all agents derive from it) |
| `agents/product_owner.py` | ✅ | `TestAgentExecution::test_product_owner` |
| `agents/architect.py` | ✅ | `TestAgentExecution::test_architect` |
| `agents/developer.py` | ✅ | `TestAgentExecution::test_developer_tdd_steps`, `TestWorkflowEngine::test_execute_task_tdd` |
| `agents/reviewer.py` | ✅ | `TestAgentExecution` (reviewer covered in pipeline tests) |
| `agents/test_writer.py` | ✅ | `TestAgentExecution::test_test_writer` |
| `agents/devops.py` | ✅ | `TestAgentExecution::test_devops` |
| `agents/scrum_master.py` | ✅ | `TestAgentExecution::test_scrum_master_planner` |
| `orchestrator.py` | ✅ | `TestFullPipeline`, some `TestAgentExecution` tests |
| `cli.py` | ❌ | **No CLI unit tests** (argparse is not tested) |

### Summary
- **17 out of 22** source files have direct test coverage.
- **1 source file untested:** `cli.py` (106 lines) — no tests for argument parsing or the `_print_text` formatter.
- The test file is a single monolithic file (473 lines) rather than a per-module test structure.
- The full integration pipeline is tested end-to-end with 3 variants.
- No `conftest.py`, no fixtures module, no `mocks/` directory.

---

## Architecture Summary (at a glance)

```
CLI (cli.py)
  │
  └──run_full_pipeline()──► orchestrator.py
                                │
                  ┌─────────────┼────────────────┐
                  │             │                 │
             WorkflowEngine   agents/*.py     models/*.py
             (engine/)        (8 agents)     (Story, Task,
                  │                           Agent, Artifact)
             TaskScheduler
             ContextManager
             TransitionGate
```

**8-stage pipeline:** INCEPTION → PLANNING → DESIGN → IMPLEMENTATION (TDD) → REVIEW → ACCEPTANCE → INTEGRATION → DELIVERY → DONE

**7 agent roles:** ProductOwner, Architect, ScrumMaster, Developer, Reviewer, TestWriter, DevOps

**TDD mechanics:** Each task is decomposed into 3 substeps (RED → GREEN → REFACTOR). The Developer agent executes each substep individually, producing artifacts at each stage.
