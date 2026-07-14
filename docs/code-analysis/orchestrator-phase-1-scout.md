# Orchestrator — Phase 1: Scout

**Status**: 🔄 In Progress  
**Current Phase**: 1/6 (Scout)  
**Next Agent**: Scout  
**Files Requested**: `pyproject.toml`, `README.md`, `src/rubric/*.py`, `src/rubric/**/*.py`

---

## Objective

Establish a topographical map of the codebase: file counts, directory structure, entry points, package dependencies, and surface-level metrics.

## Delegation — Scout Agent

Proceed to explore the repo at `/Users/nnn/temp/rubric` and report back on:

1. **Directory tree** — full `src/` structure with file sizes
2. **Entry points** — CLI entry (`cli.py`), public API (`orchestrator.py`), `__init__.py` exports
3. **Package dependencies** — from `pyproject.toml` (runtime + dev)
4. **File inventory** — count of Python files, test files, config files
5. **Naming conventions** — module naming, class naming, function naming
6. **Test coverage surface** — what's tested vs not (from `tests/test_rubric.py`)
7. **Code size estimates** — total lines per major module (models, engine, agents, context)

## Files Scout Should Read

- `pyproject.toml` (done — already read)
- `src/rubric/__init__.py`
- `src/rubric/models/__init__.py`
- `src/rubric/engine/__init__.py`
- `src/rubric/agents/__init__.py`
- `src/rubric/context/__init__.py`
- `examples/basic_story.py`

## Output Format

Write findings to `docs/code-analysis/scout-report.md`
