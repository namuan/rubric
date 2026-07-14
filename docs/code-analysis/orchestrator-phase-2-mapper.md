# Orchestrator — Phase 2: Mapper

**Status**: 🔄 In Progress  
**Current Phase**: 2/6 (Mapper)  
**Previous Phase**: ✅ Scout (completed)  
**Next Agent**: Mapper  

---

## Objective

Map the module dependency graph, data flow, and import relationships across the entire codebase. Understand how modules connect and what depends on what.

## Context from Phase 1

- 22 source files, 2,427 lines across 6 modules
- Entry points: `cli.py` → `orchestrator.py` → `engine/` + `agents/` + `models/`
- All agents inherit from `BaseAgent`
- `WorkflowEngine` is the central hub

## Files Mapper Should Analyze

All source files in `src/rubric/` — already read by orchestrator:

### Must-read for imports:
- `src/rubric/models/__init__.py` — exports
- `src/rubric/engine/__init__.py` — exports
- `src/rubric/agents/__init__.py` — exports
- `src/rubric/context/__init__.py` — exports
- `src/rubric/orchestrator.py` — hub wiring
- `src/rubric/cli.py` — entry point

### All agent files for dependency tracing:
- `agents/base.py`, `product_owner.py`, `architect.py`, `developer.py`, `reviewer.py`, `test_writer.py`, `devops.py`, `scrum_master.py`

### Engine files:
- `engine/workflow.py`, `scheduler.py`, `transitions.py`

### Model files:
- `models/story.py`, `agent.py`, `artifacts.py`

## Output

Write findings to `docs/code-analysis/mapper-report.md`
