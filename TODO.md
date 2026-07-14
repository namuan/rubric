# TODO — Rubric v0.1.0

> Generated from the 6-phase code analysis. See `docs/code-analysis/` for full reports.

---

## 🚨 Critical (Bugs & Systemic Risks)

### 1. Fix Duplicate Artifact ID Bug
- **Severity**: High — silent data corruption
- **Source**: Trace Report §Appendix A, Judge Report §2.1
- **Root cause**: `BaseAgent.produce_artifact()` (`src/rubric/agents/base.py:61-62`) calls `engine.add_artifact()` internally AND the orchestrator calls it again when iterating the return value. Every artifact is added twice.
- **Effect**: `story.artifacts` list has duplicate IDs. The `engine.artifacts` dict is keyed so overwrites harmlessly, but downstream consumers see duplicates.
- **Fix**: Remove internal `add_artifact()` from `produce_artifact()` and let the orchestrator own all registration. OR add a guard in `add_artifact()` to skip if ID already exists in `story.artifacts`.

### 2. Fix Premature State Transition
- **Severity**: High — incorrect semantics
- **Source**: Trace Report §Phase 2, Judge Report §2.2
- **Root cause**: Story transitions to `PLANNING` (`src/rubric/orchestrator.py:77`) BEFORE the Product Owner does inception work (`orchestrator.py:91`).
- **Effect**: The story spends the entire INCEPTION phase in `PLANNING` state. Any observer sees the wrong state.
- **Fix**: Move `transition_story(story.id, StoryState.PLANNING, ...)` to after `po_agent.execute()` completes.

### 3. Fix Silent Task Skipping
- **Severity**: High — work silently discarded
- **Source**: Trace Report §5.2, Judge Report §2.3
- **Root cause**: 8 locations in `orchestrator.py` (lines 89, 107, 151, 173, 191, 211, 231, 249) guard execution with `if agent:` but complete the task unconditionally. When `find_best_agent()` returns `None`, the task is marked `DONE` without execution.
- **Effect**: Pipeline stages produce zero artifacts with no warning. User sees all tasks completed but no work was done.
- **Fix**: (1) Log `WARNING` when `find_best_agent()` returns `None`. (2) Don't call `complete_task()` if task was never assigned. (3) Mark task as `BLOCKED` or retry.

### 4. Add Error Handling — Zero Exists Today
- **Severity**: High — any exception crashes the entire pipeline
- **Source**: Architecture Report §8, Judge Report §2.4
- **Root cause**: Zero `try/except` blocks in 2,427 lines of production code.
- **Affected areas**:
  - `next(a for a in agents if isinstance(...))` → `StopIteration` (7 locations)
  - `engine.get_story()` → `KeyError` (15+ locations)
  - `Story.transition()` → `ValueError` (8 locations)
  - `agent.pick_up_task()` → `RuntimeError`
  - `DeveloperAgent.execute_step()` → `ValueError`
- **Fix**: Three levels: (1) Agent execution wrapper with retry + BLOCKED on exhaustion. (2) Transition wrapper — catch `ValueError`, transition to `BLOCKED`. (3) Pipeline safety net — top-level try/except that logs last-known state.

### 5. Wire Quality Gates
- **Severity**: High — designed enforcement mechanism is unused
- **Source**: Feature Report §5.1, Architecture Report §2.4, Judge Report §2.5
- **Root cause**: `engine/transitions.py` has a complete quality-gate framework (`TransitionGate`, `DEFAULT_STAGE_GATES`, `validate_transition()`) but it's never called. Only the state-machine `VALID_TRANSITIONS` adjacency is checked.
- **Effect**: A story with zero tasks, zero artifacts, and empty criteria can transition all the way to `DONE`.
- **Fix**: Call `validate_transition()` inside `WorkflowEngine.transition_story()` (`src/rubric/engine/workflow.py:111`). If gates fail, transition to `BLOCKED` with failure reasons.

### 6. Refactor Monolithic Orchestrator
- **Severity**: Medium — won't scale past 8 stages
- **Source**: Architecture Report §4.2, Judge Report §2.6
- **Root cause**: All 8 stages in `run_full_pipeline()` (`orchestrator.py:77-258`) follow an identical 15-line pattern. ~80% duplication across ~180 lines.
- **Effect**: Adding a stage means copy-pasting. Fixing a bug in the pattern means fixing it in 8 places.
- **Fix**: Extract a `_run_stage(engine, agents, story, target_state, agent_type, task_config)` helper. Each stage becomes a single call. ~200 lines → ~50 lines.

---

## ⚠️ Important (Should Fix)

### 7. Fix BaseAgent → WorkflowEngine Layer Impurity
- **Severity**: Medium
- **Source**: Architecture Report §3.4, §11.4; Judge Report §3.1
- **Root cause**: `agents/base.py:12` imports concrete `WorkflowEngine` — agents know about the layer above them.
- **Fix**: Define an `ArtifactRegistry` protocol in `models/` with `add_artifact()` and `register_agent()`. `BaseAgent` uses `ArtifactRegistry | None` instead.
- **Files**: `src/rubric/agents/base.py`, new `src/rubric/models/protocols.py`

### 8. Load LLM Configuration
- **Severity**: Medium
- **Source**: Feature Report §5.2, Judge Report §3.2
- **Root cause**: `config/llm_config.json` (94 lines) defines a multi-provider schema (OpenAI, Anthropic, Google, Azure, Ollama) but zero runtime code reads it.
- **Fix**: Implement a config loader + `LLMProvider` protocol. Wire each agent's `execute()` to call an LLM using the configured provider/model.
- **Files**: `config/llm_config.json`, new `src/rubric/llm/` module

### 9. Unused Artifact Types — Implement or Remove
- **Severity**: Low-Medium
- **Source**: Feature Report §5.2, Judge Report §3.3
- **Unused**: `SPRINT_PLAN`, `CHANGELOG`, `DOCUMENTATION`, `CONFIG`
- **Fix**: Either assign each to an existing agent (e.g., ScrumMaster → `SPRINT_PLAN`, DevOps → `CHANGELOG`) or remove from the enum.
- **Files**: `src/rubric/models/artifacts.py`

### 10. Split Monolithic Test File
- **Severity**: Medium
- **Source**: Scout Report §7, Judge Report §3.4
- **Root cause**: All 38 tests in `tests/test_rubric.py` (473 lines). No `conftest.py`.
- **Fix**: Split into per-module files: `test_models.py`, `test_engine.py`, `test_agents.py`, `test_orchestrator.py`, `test_cli.py`. Add `conftest.py` with shared fixtures.

### 11. Add CLI Tests
- **Severity**: Medium
- **Source**: Scout Report §7, Judge Report §3.5
- **Root cause**: `cli.py` (106 lines) has zero test coverage — `main()`, argparse, `_print_text()`, JSON output, `--verbose` flag.
- **Fix**: Test argument parsing with `parse_args()`. Test both text and JSON output. Test `--verbose` flag.
- **Files**: `tests/test_cli.py` (new), `src/rubric/cli.py`

### 12. Add Minimum Viable Persistence
- **Severity**: Medium
- **Source**: Architecture Report §11.5, Judge Report §3.6
- **Root cause**: Everything is in-memory dicts. Process restart loses all stories, artifacts, and context.
- **Fix**: JSON-file save/load using Pydantic's `model_dump_json()`/`model_validate_json()`. Auto-save after every transition and task completion.
- **Files**: new `src/rubric/persistence/` module

### 13. Event System — Wire Consumer or Remove
- **Severity**: Low-Medium
- **Source**: Architecture Report §2.3, Judge Report §3.7
- **Root cause**: `WorkflowEngine` implements publish/subscribe events (`WorkflowEvent`, `on_event()`, `_emit()`), but no production code subscribes.
- **Fix**: Add at least one consumer (e.g., `EventLogger` to file) or remove the event system and use direct logging.
- **Files**: `src/rubric/engine/workflow.py`

### 14. Improve DeveloperAgent Interface
- **Severity**: Low-Medium
- **Source**: Architecture Report §2.1, Judge Report §4.6
- **Root cause**: `DeveloperAgent` has both `execute(task, story)` and `execute_step(step, task, story)` — dual interfaces doing overlapping work.
- **Fix**: Consolidate to one interface. Either `execute_task_tdd()` calls `execute()` (which iterates steps internally) OR calls `execute_step()` (granular). Having both is confusing.
- **Files**: `src/rubric/agents/developer.py`, `src/rubric/engine/workflow.py`

---

## 📋 Nice-to-Have

### 15. Add conftest.py with Shared Fixtures
- **Source**: Judge Report §4.1
- **Benefit**: Eliminates test setup duplication across `TestStory`, `TestAgent`, `TestWorkflowEngine`, etc.
- **Effort**: ~2 hours

### 16. Multi-Story Pipeline Support
- **Source**: Feature Report §5.2, Judge Report §4.3
- **Benefit**: Engine supports multiple stories but `run_full_pipeline()` handles exactly one. Add `run_multiple_pipelines()` or `run_batch()`.
- **Effort**: ~1–2 days

### 17. Async Agent Execution
- **Source**: Architecture Report §7.1, Judge Report §4.4
- **Benefit**: Enable parallel agent execution (e.g., review while acceptance tests run). Requires thread-safety audit of engine registries.
- **Effort**: ~3–5 days

### 18. Environment-Aware Configuration
- **Source**: Architecture Report §9.3, Judge Report §4.5
- **Benefit**: Different LLM providers for dev vs prod. `ENV`/`APP_ENV` with environment-specific config loading.
- **Effort**: ~1–2 days

### 19. Remove or Wire Dead Code
- **Source**: Trace Report §Appendix B, Judge Report §4.7
- **Dead code inventory**:
  - `engine/workflow.py:run_story()` (lines 244–267) — never called by orchestrator
  - `engine/workflow.py:assign_tasks_for_stage()` (lines 125–148) — never called
  - `engine/workflow.py:advance_story()` (lines 220–241) — never called
  - `engine/workflow.py:check_stage_complete()` (lines 214–219) — never called
  - `engine/transitions.py:validate_transition()` (lines 70–84) — never called (see #5)
  - `engine/transitions.py:DEFAULT_STAGE_GATES` (lines 58–68) — never evaluated
  - `models/story.py:Task.next_step()` (lines 152–158) — never called
- **Fix**: Either wire into production path or delete.
- **Effort**: ~2–3 hours

### 20. Add Test Coverage for Untested Paths
- **Source**: Trace Report §6
- **15+ untested code paths** including: empty criteria pipeline, missing agents, error paths, backtracking transitions, zero-criteria planning, `--verbose` flag, JSON output.
- **Effort**: ~1–2 days

---

## 📊 Effort Estimates

| Category | Items | Effort |
|----------|-------|:------:|
| Critical (1–6) | Bugs, error handling, gates, refactor | 2–3 days |
| Important (7–14) | Layer fix, LLM, tests, persistence | ~1 week |
| Nice-to-Have (15–20) | Async, multi-story, config, dead code | 2–3 weeks |
| **Total** | **20 items** | **~4–5 weeks** |

## 🔗 Related Resources

- [Full Code Analysis](docs/code-analysis/orchestrator-final-synthesis) — synthesis of all 6 phases
- [Judge Report](docs/code-analysis/judge-report) — scored quality assessment (5.0/10)
- [Architecture Report](docs/code-analysis/architecture-report) — patterns, risks, recommendations
- [Trace Report](docs/code-analysis/trace-report) — execution trace with bug reports
- [GitHub Pages](https://namuan.github.io/rubric/) — published analysis docs
