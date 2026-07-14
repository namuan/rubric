# Orchestrator — Phase 5: Trace

**Status**: 🔄 In Progress  
**Current Phase**: 5/6 (Trace)  
**Previous Phase**: ✅ Architecture (completed)  
**Next Agent**: Trace Agent  

---

## Objective

Trace the execution path of a story through the full pipeline. Identify concrete call chains, state transitions, object lifecycles, and where things can go wrong.

## Context from Previous Phases

- **Architecture**: Strict layered DAG with 8-stage pipeline; quality gates disconnected; orchestrator bypasses engine's `run_story()`
- **Feature**: 81 features, 4 "Deep", 33 "Moderate", 33 "Shallow", 11 "Stub"
- **Key gap**: Zero error handling in production code path

## Trace Requirements

Trace a complete `run_full_pipeline()` call from entry to exit:

1. **CLI entry** → arg parsing → `run_full_pipeline()`
2. **Engine setup** → WorkflowEngine creation → agent binding
3. **Each stage** (8 stages) → task creation → scheduling → execution → completion → transition
4. **TDD cycle** → Scrum Master planning → Developer RED/GREEN/REFACTOR → artifact production
5. **Finalization** → DONE transition → result collection → output formatting

For each step, document:
- Function called
- Objects created/modified
- Data dependencies
- Potential failure points
- Whether the step is exercised by tests

## Output

Write findings to `docs/code-analysis/trace-report.md`
