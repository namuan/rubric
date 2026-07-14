# Trace Report: `run_full_pipeline()`

**Generated:** 2026-07-14
**Command traced:** `rubric run "User Auth" --criteria "Login" --criteria "Register"`
**Commit:** Current working tree

---

## 1. Full Execution Trace

Below is a step-by-step trace of every call made during `rubric run "User Auth" -c "Login" -c "Register"`.

### Phase 0: CLI Parsing (`cli.py`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 0.1 | `main(["run", "User Auth", "-c", "Login", "-c", "Register"])` | cli.py:13 | `argv` = list of strings | `args.command = "run"`, `args.title = "User Auth"`, `args.description = ""`, `args.criteria = ["Login", "Register"]`, `args.output = "text"`, `args.verbose = False` | Untested (CLI entry point) | Incorrect argv |
| 0.2 | `criteria = args.criteria if args.criteria else None` | cli.py:48 | `args.criteria = ["Login", "Register"]` (truthy) | `criteria = ["Login", "Register"]` | Untested | — |
| 0.3 | `run_full_pipeline(title="User Auth", description="", acceptance_criteria=["Login", "Register"])` | cli.py:49-53 | 3 keyword args | See Phase 1 onward | `test_run_full_pipeline` (438-448) | Exception propagates to caller |

### Phase 1: Initialization (`orchestrator.py:66-74`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 1.1 | `engine = WorkflowEngine()` | orchestrator.py:66 | — | `engine.scheduler = TaskScheduler()`, `engine.context = ContextManager()`, `engine.stories = {}`, `engine.artifacts = {}`, `engine.agents = {}`, `engine.event_handlers = []`, `engine._log = []` | `TestWorkflowEngine` (299-326) | — |
| 1.2 | `agents = create_default_team()` | orchestrator.py:67 | — | Returns list of 7 `BaseAgent` subclasses (PO, Architect, SM, Dev, Reviewer, TestWriter, DevOps). Each wraps an `Agent` model with name + role. | `test_run_full_pipeline` (indirectly) | — |
| 1.3 | `agent.bind(engine)` × 7 | orchestrator.py:68-69 | Each agent + engine | Each calls `engine.register_agent(self.agent)` → `engine.agents[agent.id] = agent`. Now `engine.agents` has 7 entries. | `test_register_agents` (307-311) | — |
| 1.4 | `story = engine.create_story(title="User Auth", description="")` | orchestrator.py:72; workflow.py:66 | `title="User Auth"`, `description=""` | Creates `Story` with `state=INCEPTION`. Engine stores `stories[id]=story`. Context: `story:{id}:state = "inception"`. Emits `story_created` event. | `test_create_and_transition` (300-305) | — |
| 1.5 | `story.acceptance_criteria = ["Login", "Register"]` | orchestrator.py:73-74 | Criteria list is truthy | Story's criteria set. If `None`, criteria stays `[]` (default). | `test_run_full_pipeline` (indirectly) | — |

### Phase 2: INCEPTION (`orchestrator.py:76-94`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 2.1 | `engine.transition_story(story.id, StoryState.PLANNING, ...)` | orchestrator.py:77; workflow.py:111 | `story_id`, `new_state=PLANNING` | Validates INCEPTION→PLANNING against `VALID_TRANSITIONS`. Checks pass. Story state → `PLANNING`. Context updated. Event emitted. **Note:** Story moves to PLANNING *before* PO does inception work. | `test_valid_transition` (41-47) | `ValueError` if invalid transition; `KeyError` if story_id missing |
| 2.2 | `po_agent = next(a for a in agents if isinstance(a, ProductOwnerAgent))` | orchestrator.py:80 | 7 agents | Returns "Alice PO" `ProductOwnerAgent` instance | Untested | `StopIteration` if PO not in team |
| 2.3 | `inception_task = Task(title="Define acceptance criteria", ...)` | orchestrator.py:81-86 | — | Creates `Task` with `required_role="product_owner"`, `priority=HIGH`. | Untested (task creation inline) | — |
| 2.4 | `story.tasks = [inception_task]` | orchestrator.py:87 | Inception task | **Replaces** any existing tasks (this is the first assignment, so fine) | Untested | — |
| 2.5 | `engine.scheduler.find_best_agent(inception_task, all_agents, "inception")` | orchestrator.py:88; scheduler.py:24 | Task with `required_role="product_owner"`, 7 agents, stage="inception" | Filters by role → PO agent. Returns Alice PO's `Agent` object. | `test_find_agent_by_role` (202-210), `test_load_balancing` (220-228) | Returns `None` if no agent available |
| 2.6 | `engine.scheduler.assign_task(inception_task, agent)` | orchestrator.py:90; scheduler.py:62 | Task + Agent | `agent.pick_up_task(task.id)` adds to active list. `task.assign(agent.id)` sets status=IN_PROGRESS. | `test_task_complete` (151-155) | `RuntimeError` if agent at capacity |
| 2.7 | `po_agent.execute(inception_task, story)` | orchestrator.py:91; product_owner.py:29 | Task + Story | `_enrich_description()` appends user story template to `story.description`. `_define_acceptance_criteria()` returns existing `["Login", "Register"]` (no change). Returns 2 artifacts: `STORY_BRIEF`, `ACCEPTANCE_CRITERIA`. | `test_product_owner` (362-369) | — |
| 2.8 | `engine.add_artifact(art)` × 2 | orchestrator.py:92-93; workflow.py:81 | 2 Artifact objects | Stored in `engine.artifacts[id]`. `story.artifacts` gets IDs appended. `artifact_produced` events emitted. | `test_execute_task_tdd` (328-347, add_artifact called within) | — |
| 2.9 | `engine.complete_task(story.id, inception_task.id)` | orchestrator.py:94; workflow.py:195 | Story ID + Task ID | Finds task, calls `task.complete()` → `status=DONE`. Finds assigned agent, calls `agent.finish_task()`. Emits `task_completed` event. | `test_execute_task_tdd` (328-347) | `KeyError` if task not found |

### Phase 3: PLANNING (`orchestrator.py:96-121`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 3.1 | `planner = next(a for a in agents if isinstance(a, ScrumMasterAgent))` | orchestrator.py:98 | 7 agents | Returns "Grace Planner" | Untested | `StopIteration` if SM missing |
| 3.2 | `planning_task = Task(title="Break down into tasks", ...)` | orchestrator.py:99-104 | — | New Task, `required_role="scrum_master"` | Untested | — |
| 3.3 | `story.tasks.append(planning_task)` | orchestrator.py:105 | Planning task | `story.tasks = [inception_task(DONE), planning_task(PENDING)]` | Untested | — |
| 3.4 | `find_best_agent(planning_task, all_agents, "planning")` | orchestrator.py:106 | scrum_master role | Returns Grace's Agent | Untested here | Returns `None` |
| 3.5 | `assign_task(planning_task, agent)` | orchestrator.py:108 | Task + Agent | planning_task → IN_PROGRESS | Untested here | `RuntimeError` |
| 3.6 | `planned_tasks = planner.plan_story(story)` | orchestrator.py:110; scrum_master.py:49 | Story with 2 criteria | Creates 3 tasks: `Login` (dev, 3 steps), `Register` (dev, 3 steps, depends on Login), `Integration verification` (dev, 3 steps, depends on Register). Returns list of 3 Tasks. | `test_scrum_master_planner` (415-430) | — |
| 3.7 | `story.tasks = [planning_task] + planned_tasks` | orchestrator.py:112 | 1 + 3 tasks | `story.tasks` = [planning_task, login_task, register_task, integration_task] | Untested | — |
| 3.8 | `planner.execute(planning_task, story)` | orchestrator.py:113; scrum_master.py:159 | Planning task + Story | Title contains "break" → produces `TASK_BREAKDOWN` artifact. | `test_scrum_master_planner` (415-430, but doesn't call execute) | — |
| 3.9 | `add_artifact()` + `complete_task()` | orchestrator.py:114-116 | Same pattern as 2.8-2.9 | planning_task → DONE | Untested here | — |

### Phase 4: DESIGN (`orchestrator.py:123-156`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 4.1 | `transition_story(story.id, DESIGN, ...)` | orchestrator.py:124-125 | PLANNING→DESIGN | Valid: PLANNING→DESIGN is in `VALID_TRANSITIONS`. State → DESIGN. | `test_valid_transition` | `ValueError` if blocked |
| 4.2 | `architect = next(a for a in agents if isinstance(a, ArchitectAgent))` | orchestrator.py:127 | 7 agents | Returns "Bob Architect" | Untested | `StopIteration` |
| 4.3 | Create 3 `design_tasks` | orchestrator.py:128-147 | — | 3 Tasks: "Design system architecture" (architect, HIGH), "Design API endpoints" (architect, MEDIUM), "Design data model" (architect, MEDIUM). No TDD steps. | Untested | — |
| 4.4 | `story.tasks.extend(design_tasks)` | orchestrator.py:148 | 3 tasks | Adds to existing list. Now: 7 tasks total (inception, planning, 3 design, login, register, integration) | Untested | — |
| 4.5 | Loop over 3 design tasks: `find_best_agent` → `assign` → `architect.execute()` → `add_artifact` × N → `complete_task` | orchestrator.py:149-156 | Each design task | Architecture task: produces `ARCHITECTURE_DIAGRAM` + `TECH_DESIGN`. API task: produces `API_SPEC`. Data task: produces `DATA_MODEL`. Each task → DONE. | `test_architect` (371-377) | `StopIteration` / `KeyError` / `None` agent |
| 4.6 | Each `complete_task` call | orchestrator.py:156 | Per task | `agent.finish_task()` called each time. Agent's active_tasks ≠ completed_tasks tracking. | `test_agent_utilization` (185-190) | `KeyError` |

### Phase 5: IMPLEMENTATION (`orchestrator.py:158-176`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 5.1 | `transition_story(story.id, IMPLEMENTATION, ...)` | orchestrator.py:159-160 | DESIGN→IMPLEMENTATION | Valid transition. State → IMPLEMENTATION. | `test_full_lifecycle_transitions` | `ValueError` |
| 5.2 | `developer = next(a for a in agents if isinstance(a, DeveloperAgent))` | orchestrator.py:162 | 7 agents | Returns "Charlie Dev" | Untested | `StopIteration` |
| 5.3 | Loop over `story.tasks` — **skip logic** | orchestrator.py:164-170 | Iterates 7 tasks | Skips: inception (DONE), planning (DONE), 3 design tasks (DONE). **Runs:** login_task (PENDING, dev, has steps), register_task (PENDING, dev, has steps), integration_task (PENDING, dev, has steps). | `test_run_full_pipeline` (438-448, but doesn't verify skips individually) | Task may be skipped incorrectly if status wrong |
| 5.4 | For **login_task**: `find_best_agent` → `assign_task` | orchestrator.py:172-174 | login_task, all_agents, "implementation" | Agent found (Charlie Dev). Task assigned. | `test_execute_task_tdd` (328-347) | Agent may be `None` → task skipped silently |
| 5.5 | `engine.execute_task_tdd(story.id, login_task.id, developer)` | orchestrator.py:176; workflow.py:149 | story_id, task_id, developer handler | Iterates 3 steps. Details in **Step 5.6-5.10** | `test_execute_task_tdd` (328-347) | `KeyError` if task not found |
| 5.6 | **Step RED**: `step.status = IN_PROGRESS`, emit `step_started` | workflow.py:168-176 | Step 1/3 of login_task | Step status set. Event logged. | `test_execute_task_tdd` | — |
| 5.7 | `developer.execute_step(step, task, story)` → `_write_failing_test()` | workflow.py:178; developer.py:88 | RED step + task + story | Produces template `TEST_CODE` artifact string. Calls `step.complete(artifact.id)`. Returns artifact. | `test_developer_tdd_steps` (379-396, calls execute_step directly) | `ValueError` for unknown step_type |
| 5.8 | `add_artifact(artifact)`, emit `step_completed` | workflow.py:179-186 | RED artifact | Stored in engine. | `test_execute_task_tdd` (indirectly) | — |
| 5.9 | **Steps GREEN, REFACTOR**: same loop | workflow.py:164-192 | Steps 2-3 | GREEN → `SOURCE_CODE` artifact. REFACTOR → `SOURCE_CODE` artifact. Each step completes separately. | `test_developer_tdd_steps` | — |
| 5.10 | `task.all_steps_done()` → True → `complete_task()` | workflow.py:190-191 | login_task | 3 of 3 steps DONE → task DONE. Agent finishes task. | `test_execute_task_tdd` (verifies all steps DONE) | Task won't complete if any step not DONE |
| 5.11 | **register_task**: same as 5.5-5.10 | orchestrator.py:176 (2nd iteration) | register_task | 3 more TDD steps, 3 more artifacts (TEST_CODE, SOURCE_CODE, SOURCE_CODE). Task → DONE. | Covered by `test_run_full_pipeline` | Same as above |
| 5.12 | **integration_task**: same as 5.5-5.10 | orchestrator.py:176 (3rd iteration) | integration_task | 3 more TDD steps, 3 more artifacts. Task → DONE. | Not explicitly tested | Same as above |

### Phase 6: REVIEW (`orchestrator.py:178-196`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 6.1 | `transition_story(story.id, REVIEW, ...)` | orchestrator.py:179-180 | IMPLEMENTATION→REVIEW | Valid. State → REVIEW. | `test_full_lifecycle_transitions` | `ValueError` |
| 6.2 | `reviewer = next(a for a in agents if isinstance(a, ReviewerAgent))` | orchestrator.py:182 | 7 agents | Returns "Diana Reviewer" | Untested | `StopIteration` |
| 6.3 | Create `review_task`, `find_best_agent`, `assign` | orchestrator.py:183-192 | reviewer role | Task created, assigned to Diana. | Untested | Agent = `None` |
| 6.4 | `reviewer.execute(review_task, story)` | orchestrator.py:193; reviewer.py:29 | Task + Story | `_review_code()` returns `{"issues_found": 0, "status": "approved", ...}`. Since issues = 0, no refactoring suggestions. Produces `REVIEW_FEEDBACK` artifact only. | Untested (no review test in suite) | — |
| 6.5 | `add_artifact` + `complete_task` | orchestrator.py:194-196 | REVIEW_FEEDBACK | Task → DONE. | Untested | — |

### Phase 7: ACCEPTANCE (`orchestrator.py:198-216`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 7.1 | `transition_story(story.id, ACCEPTANCE, ...)` | orchestrator.py:199-200 | REVIEW→ACCEPTANCE | Valid. State → ACCEPTANCE. | `test_full_lifecycle_transitions` | `ValueError` |
| 7.2 | `test_writer = next(a for a in agents if isinstance(a, TestWriterAgent))` | orchestrator.py:202 | 7 agents | Returns "Eve TestWriter" | Untested | `StopIteration` |
| 7.3 | Create `acceptance_task`, find, assign | orchestrator.py:203-212 | test_writer role | Task: "Write and run end-user acceptance tests". | `test_test_writer` (398-405) | Agent = `None` |
| 7.4 | `test_writer.execute(acceptance_task, story)` | orchestrator.py:213; test_writer.py:40 | Task + Story | Title has "acceptance" and "test" and "write": produces `TEST_PLAN`, `TEST_CODE`, and `TEST_REPORT` artifacts. 3 artifacts total. | `test_test_writer` (398-405, verifies TEST_REPORT) | — |
| 7.5 | `add_artifact` × 3 + `complete_task` | orchestrator.py:214-216 | 3 artifacts | Task → DONE. | `test_pipeline_includes_acceptance_tests` (465-473) | — |

### Phase 8: INTEGRATION (`orchestrator.py:218-236`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 8.1 | `transition_story(story.id, INTEGRATION, ...)` | orchestrator.py:219-220 | ACCEPTANCE→INTEGRATION | Valid. State → INTEGRATION. | `test_full_lifecycle_transitions` | `ValueError` |
| 8.2 | `devops = next(a for a in agents if isinstance(a, DevOpsAgent))` | orchestrator.py:222 | 7 agents | Returns "Frank DevOps" | Untested | `StopIteration` |
| 8.3 | Create `integration_task`, find, assign | orchestrator.py:223-232 | devops role | Task: "Set up CI pipeline and deploy to staging". | `test_devops` (407-413) | Agent = `None` |
| 8.4 | `devops.execute(integration_task, story)` | orchestrator.py:233; devops.py:29 | Task + Story | Title has "deploy" and "ci" and "pipeline": produces `CI_CONFIG` + `DEPLOYMENT_CONFIG`. 2 artifacts. Since title has "release" (no! "set up" doesn't), only CI + deploy. | `test_devops` (407-413) | — |
| 8.5 | `add_artifact` × 2 + `complete_task` | orchestrator.py:234-236 | 2 artifacts | Task → DONE. | Untested | — |

### Phase 9: DELIVERY (`orchestrator.py:238-255`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 9.1 | `transition_story(story.id, DELIVERY, ...)` | orchestrator.py:239-240 | INTEGRATION→DELIVERY | Valid. State → DELIVERY. | `test_full_lifecycle_transitions` | `ValueError` |
| 9.2 | Create `delivery_task`, find, assign | orchestrator.py:242-251 | devops role | Task: "Create release notes and documentation". | Untested | Agent = `None` |
| 9.3 | `devops.execute(delivery_task, story)` | orchestrator.py:252; devops.py:29 | Task + Story | Title has "release": produces `RELEASE_NOTES`. Does NOT have "deploy"/"ci"/"pipeline". So only 1 artifact. | Untested | — |
| 9.4 | `add_artifact` + `complete_task` | orchestrator.py:253-255 | 1 artifact | Task → DONE. | Untested | — |

### Phase 10: DONE & Return (`orchestrator.py:257-263`)

| # | Step | File:Line | Inputs | Outputs / Side Effects | Test Coverage | Failure Mode |
|---|------|-----------|--------|------------------------|---------------|--------------|
| 10.1 | `transition_story(story.id, DONE, ...)` | orchestrator.py:258 | DELIVERY→DONE | Valid transition. State → DONE. Final event. | `test_full_lifecycle_transitions` | `ValueError` |
| 10.2 | Build return dict | orchestrator.py:260-263 | story + artifacts + engine | Calls `engine.story_summary(story.id)` (reads state, progress, history), `engine.get_artifacts_for_story(story.id)` (reads artifact summaries), `engine.status()` (agent utilization). | `test_run_full_pipeline` verifies structure | `KeyError` if story not in engine |

### Summary of All Executed Steps

| Phase | Tasks Created | Tasks Completed | Artifacts Produced | Approx. Step Count |
|-------|---------------|-----------------|-------------------|-------------------|
| INCEPTION | 1 | 1 | 2 (STORY_BRIEF, ACCEPTANCE_CRITERIA) | ~9 internal steps |
| PLANNING | 4 (1 planning + 3 planned) | 1 (planning) | 1 (TASK_BREAKDOWN) | ~11 internal steps |
| DESIGN | 3 | 3 | 4 (ARCH_DIAGRAM, TECH_DESIGN, API_SPEC, DATA_MODEL) | ~12 internal steps |
| IMPLEMENTATION | 0 (3 existing) | 3 | 9 (3 tasks × 3 TDD steps) | ~30 internal steps |
| REVIEW | 1 | 1 | 1 (REVIEW_FEEDBACK) | ~5 internal steps |
| ACCEPTANCE | 1 | 1 | 3 (TEST_PLAN, TEST_CODE, TEST_REPORT) | ~6 internal steps |
| INTEGRATION | 1 | 1 | 2 (CI_CONFIG, DEPLOYMENT_CONFIG) | ~6 internal steps |
| DELIVERY | 1 | 1 | 1 (RELEASE_NOTES) | ~6 internal steps |
| **TOTAL** | **12 tasks** | **12 tasks** | **~23 artifacts** | **~85+ calls** |

---

## 2. Object Lifecycle

### Story

```
CREATED (INCEPTION)
  │
  ├─ orchestrator.py:72  engine.create_story("User Auth", "")
  │   • engine.stories[id] = story
  │   • context.set("story:{id}:state", "inception")
  │   • emit("story_created")
  │
  ├─ orchestrator.py:73-74  if acceptance_criteria:
  │   • story.acceptance_criteria = ["Login", "Register"]
  │
  ├─ orchestrator.py:77  transition_story → PLANNING (before PO works!)
  │   • Story.transition("planning")
  │   • context.set("story:{id}:state", "planning")
  │   • emit("story_transition")
  │
  ├─ orchestrator.py:91  po_agent.execute()
  │   • story.description ← enriched
  │   • story.acceptance_criteria ← reconfirmed
  │
  ├─ orchestrator.py:110  planner.plan_story()
  │   • reads story.acceptance_criteria
  │
  ├─ orchestrator.py:124-125  transition_story → DESIGN
  ├─ orchestrator.py:159-160  transition_story → IMPLEMENTATION
  ├─ orchestrator.py:179-180  transition_story → REVIEW
  ├─ orchestrator.py:199-200  transition_story → ACCEPTANCE
  ├─ orchestrator.py:219-220  transition_story → INTEGRATION
  ├─ orchestrator.py:239-240  transition_story → DELIVERY
  ├─ orchestrator.py:258      transition_story → DONE
  │
  └─ orchestrator.py:261-262  story_summary() → reads story.state, progress, history, tasks
```

**State transitions count:** 8 (INCEPTION→PLANNING→DESIGN→IMPLEMENTATION→REVIEW→ACCEPTANCE→INTEGRATION→DELIVERY→DONE)

**Key observations:**
- The story transitions to PLANNING *before* the PO does inception work (line 77 fires before line 91). The story spends most of the INCEPTION phase in PLANNING state.
- Story accumulates task references via `story.tasks = [...]`, `.append()`, `.extend()`.
- Story accumulates artifact IDs via `engine.add_artifact()` → `story.artifacts.append(artifact.id)`.
- `story.history` grows by one entry per `transition()` call.
- Story's `progress` property is computed on demand from task step completion ratios.
- **No cleanup/deletion path exists** for stories.

### Task

```
CREATED (PENDING)
  │  • Task(title=..., required_role=..., priority=...)
  │
  ├─ scheduler.assign_task(task, agent)
  │   • task.assign(agent.id) → status = IN_PROGRESS
  │   • task.assigned_agent = agent.id
  │
  ├─ [If TDD task:] engine.execute_task_tdd()
  │   • For each step: step completed → potentially marks task done
  │
  ├─ engine.complete_task()
  │   • task.complete() → status = DONE
  │
  └─ agent.finish_task(task.id) → agent updates active_tasks list
```

**Task lifecycle table for this trace:**

| Task | Created | Assigned | Completed | Role |
|------|---------|----------|-----------|------|
| "Define acceptance criteria" | orch:81-86 | orch:90 | orch:94 | product_owner |
| "Break down into tasks" | orch:99-104 | orch:108 | orch:116 | scrum_master |
| "Login" (from criterion) | sm:103-108 | orch:174 | wf:191 | developer |
| "Register" (from criterion) | sm:103-108 | orch:174 | wf:191 | developer |
| "Integration verification" | sm:71-80 | orch:174 | wf:191 | developer |
| "Design system architecture" | orch:129-134 | orch:152 | orch:156 | architect |
| "Design API endpoints" | orch:135-140 | orch:152 | orch:156 | architect |
| "Design data model" | orch:141-146 | orch:152 | orch:156 | architect |
| "Code review" | orch:183-188 | orch:192 | orch:196 | reviewer |
| "Write and run end-user acceptance tests" | orch:203-208 | orch:212 | orch:216 | test_writer |
| "Set up CI pipeline and deploy to staging" | orch:223-228 | orch:232 | orch:236 | devops |
| "Create release notes and documentation" | orch:242-247 | orch:251 | orch:255 | devops |

**Key lifecycle details:**
- Tasks created by `ScrumMasterAgent.plan_story()` are generated from acceptance criteria. With 2 criteria, 3 tasks are created: one per criterion + integration.
- `Task.is_ready()` checks dependency completion. The planner wires linear dependencies (task N depends on task N-1).
- `Task.current_step` returns the first step with PENDING status — used for sequential step execution.
- Tasks with `required_role != "developer"` or without steps are **skipped** in the implementation loop but still counted.
- Tasks are never deleted once added. The `tasks` list only grows.

### TaskStep

```
CREATED (PENDING)
  │  • TaskStep(step_type=TaskStepType.RED|GREEN|REFACTOR, ...)
  │
  ├─ engine.execute_task_tdd() loop iteration
  │   • step.status = IN_PROGRESS (workflow.py:168)
  │   • emit("step_started")
  │
  ├─ developer.execute_step()
  │   • [RED]: _write_failing_test() → step.complete(artifact.id)
  │   • [GREEN]: _write_minimum_code() → step.complete(artifact.id)  
  │   • [REFACTOR]: _refactor() → step.complete(artifact.id)
  │
  └─ step.status = DONE (step.complete() at developer.py:113/135/158)
```

**Step lifecycle table (9 total steps in this trace):**

| Task | RED Step | GREEN Step | REFACTOR Step |
|------|----------|------------|---------------|
| "Login" | ✓ TEST_CODE | ✓ SOURCE_CODE | ✓ SOURCE_CODE |
| "Register" | ✓ TEST_CODE | ✓ SOURCE_CODE | ✓ SOURCE_CODE |
| "Integration verification" | ✓ TEST_CODE | ✓ SOURCE_CODE | ✓ SOURCE_CODE |

**Key observations:**
- Only developer tasks have steps. All other role tasks (PO, SM, architect, reviewer, test_writer, devops) have **zero steps**.
- Step completion is done by the agent (via `step.complete()`), not by the engine. The engine sets `IN_PROGRESS`; the agent sets `DONE`.
- `step.artifact_id` is set at completion time, linking to the produced artifact.
- Steps are never retried. If a step fails or produces an unexpected result, no rollback mechanism exists.
- `Task.next_step()` exists but is **never called** by the pipeline — `execute_task_tdd()` iterates `task.steps` directly.

### Artifact

```
CREATED
  │  • Artifact(artifact_type=..., name=..., content=..., 
  │    produced_by=agent.id, story_id=story.id, task_id=task.id)
  │
  ├─ [If engine available:] agent.produce_artifact() → engine.add_artifact()
  │   • engine.artifacts[artifact.id] = artifact
  │   • story.artifacts.append(artifact.id)
  │   • emit("artifact_produced")
  │
  └─ engine.story_summary() / engine.get_artifacts_for_story()
      • Reads artifact summary for reporting
```

**Artifact production summary (approximately 23 artifacts):**

| Phase | Agent | Artifact Types | Count |
|-------|-------|----------------|-------|
| INCEPTION | ProductOwnerAgent | STORY_BRIEF, ACCEPTANCE_CRITERIA | 2 |
| PLANNING | ScrumMasterAgent | TASK_BREAKDOWN | 1 |
| DESIGN | ArchitectAgent | ARCHITECTURE_DIAGRAM, TECH_DESIGN | 2 |
| DESIGN | ArchitectAgent | API_SPEC | 1 |
| DESIGN | ArchitectAgent | DATA_MODEL | 1 |
| IMPLEMENTATION | DeveloperAgent | TEST_CODE, SOURCE_CODE, SOURCE_CODE × 3 tasks | 9 |
| REVIEW | ReviewerAgent | REVIEW_FEEDBACK | 1 |
| ACCEPTANCE | TestWriterAgent | TEST_PLAN, TEST_CODE, TEST_REPORT | 3 |
| INTEGRATION | DevOpsAgent | CI_CONFIG, DEPLOYMENT_CONFIG | 2 |
| DELIVERY | DevOpsAgent | RELEASE_NOTES | 1 |

**Key observations:**
- Artifacts are produced via two paths: direct `add_artifact()` calls in `orchestrator.py`, or via `produce_artifact()` in agent subclasses (which also calls `add_artifact()` when `self.engine` is set).
- Architect may produce 1-2 artifacts per task depending on title keywords.
- TestWriter may produce 1-3 artifacts depending on title keywords.
- DevOps may produce 1-2 artifacts depending on title keywords.
- **No artifact deletion mechanism exists.**
- The `agent.produce_artifact()` helper method is used by all agents. The orchestrator also calls `add_artifact()` separately for return values from `agent.execute()`. This means all agents that use `produce_artifact()` internally have their artifacts added twice — once by `produce_artifact()` (via internal `add_artifact()`), and again when the orchestrator iterates the returned list. Let me verify...

Actually, looking at `base.py:61-62`:
```python
if self.engine:
    self.engine.add_artifact(artifact)
```

And at `orchestrator.py:91-93`:
```python
artifacts = po_agent.execute(inception_task, story)
for art in artifacts:
    engine.add_artifact(art)
```

**This is a bug!** The `produce_artifact()` method in `BaseAgent` already calls `engine.add_artifact()` when `self.engine` is set. Then the orchestrator iterates the return value and calls `add_artifact()` **again**. The same artifact object gets added twice — but since it's the same object reference, it overwrites in the dict. However, the `story.artifacts.append()` is called each time, so story artifact IDs will have duplicates.

Wait, let me re-read `add_artifact()`:
```python
def add_artifact(self, artifact: Artifact) -> None:
    self.artifacts[artifact.id] = artifact
    if artifact.story_id:
        story = self.stories.get(artifact.story_id)
        if story:
            story.artifacts.append(artifact.id)
```

The `self.artifacts` dict is keyed by `artifact.id`, so overwriting is harmless. But `story.artifacts.append(artifact.id)` is called both times, so the list would contain duplicate IDs. This is a real double-add bug.

### Agent

```
CREATED
  │  • Agent(name="Alice PO", role=PRODUCT_OWNER, ...)  (in models/agent.py)
  │  • Wrapped by BaseAgent subclass   (in agents/*.py)
  │
  ├─ agent.bind(engine)
  │   • engine.register_agent(agent) → engine.agents[agent.id] = agent
  │   • self.engine = engine (for BaseAgent internal use)
  │
  ├─ scheduler.find_best_agent()  (may be called multiple times)
  │   • Agent inspected for role match + availability
  │
  ├─ scheduler.assign_task(task, agent)
  │   • agent.pick_up_task(task.id) → active_tasks++  (may raise RuntimeError if at capacity)
  │
  ├─ [Per task:] agent.finish_task(task.id)  (via complete_task)
  │   • active_tasks--, completed_tasks++
  │
  └─ engine.status() → reads agent.utilization for reporting
```

**Agent workload progression (cumulative over the pipeline):**

| Agent | Tasks Assigned | Max Concurrent | Peak Active |
|-------|---------------|----------------|-------------|
| Alice PO | 1 | 1 | 1 |
| Grace Planner | 1 | 1 | 1 |
| Bob Architect | 3 (sequential) | 1 | 1 |
| Charlie Dev | 3 (sequential) | 1 | 1 |
| Diana Reviewer | 1 | 1 | 1 |
| Eve TestWriter | 1 | 1 | 1 |
| Frank DevOps | 2 (sequential) | 1 | 1 |

**Key observations:**
- All agents have `max_concurrent_tasks=1` (default). Each task is fully completed before the next assign.
- Agent `find_best_agent()` could select a different agent if multiple share the same role — but the default team has exactly one per role.
- Agent availability is checked but all tasks are sequential, so agents are always available when called.
- `agent.finish_task()` is called in `complete_task()` (workflow.py:203-205). If a task is never assigned (when `find_best_agent` returns None), `finish_task()` is not called and `assigned_agent` is None, so the `if task.assigned_agent` guard prevents errors.

---

## 3. State Transition Map (Concrete)

### Actual transitions for this trace

```
  INCEPTION ──[orch:77]──→ PLANNING ──[orch:124]──→ DESIGN
       │                       │                       │
       │  Reason: "Story      │  Reason: "Story       │  Reason: "Entering
       │  created, entering   │  created, entering     │  design stage"
       │  planning"           │  planning"             │
       │                       │                       │
       │                       ▼                       ▼
       │                   PLANNING                 IMPLEMENTATION
       │                       │                       │
       │                       │                       │  Reason: "Entering
       │                       │                       │  implementation stage"
       │                       │                       │
       │                       │                       ▼
       │                       │                   REVIEW ──[orch:179]──→ ACCEPTANCE
       │                       │                       │
       │                       │                       │  Reason: "Entering
       │                       │                       │  review stage"
       │                       │                       │
       │                       │                       ▼
       │                       │                   INTEGRATION ──[orch:219]──→ DELIVERY
       │                       │                       │
       │                       │                       │  Reason: "Entering
       │                       │                       │  integration stage"
       │                       │                       │
       │                       │                       ▼
       │                       │                    DONE ◄──[orch:258]──┘
       │                       │                       │
       │                       │              Reason: "All stages complete"
       │                       │                       │
       │                       ▼                       │
       └───────────────── All transitions validated by ─┘
                         Story.transition() against
                         VALID_TRANSITIONS dict
```

### Transition validation table

| From | To | Valid? | Trigger | Validated By |
|------|----|--------|---------|--------------|
| INCEPTION | PLANNING | ✓ | `orch:77` — unconditional call | `VALID_TRANSITIONS[INCEPTION] = [PLANNING, BLOCKED]` |
| PLANNING | DESIGN | ✓ | `orch:124` — `if story.state != DESIGN` (always true) | `VALID_TRANSITIONS[PLANNING] = [DESIGN, INCEPTION, BLOCKED]` |
| DESIGN | IMPLEMENTATION | ✓ | `orch:159` — `if story.state != IMPLEMENTATION` (always true) | `VALID_TRANSITIONS[DESIGN] = [IMPLEMENTATION, PLANNING, BLOCKED]` |
| IMPLEMENTATION | REVIEW | ✓ | `orch:179` — `if story.state != REVIEW` (always true) | `VALID_TRANSITIONS[IMPLEMENTATION] = [REVIEW, DESIGN, BLOCKED]` |
| REVIEW | ACCEPTANCE | ✓ | `orch:199` — `if story.state != ACCEPTANCE` (always true) | `VALID_TRANSITIONS[REVIEW] = [ACCEPTANCE, IMPLEMENTATION, BLOCKED]` |
| ACCEPTANCE | INTEGRATION | ✓ | `orch:219` — `if story.state != INTEGRATION` (always true) | `VALID_TRANSITIONS[ACCEPTANCE] = [INTEGRATION, IMPLEMENTATION, BLOCKED]` |
| INTEGRATION | DELIVERY | ✓ | `orch:239` — `if story.state != DELIVERY` (always true) | `VALID_TRANSITIONS[INTEGRATION] = [DELIVERY, ACCEPTANCE, BLOCKED]` |
| DELIVERY | DONE | ✓ | `orch:258` — unconditional call | `VALID_TRANSITIONS[DELIVERY] = [DONE, INTEGRATION, BLOCKED]` |

### Parallel mechanism: `TransitionGate` (defined in `transitions.py` but NEVER used by `run_full_pipeline()`)

The `transitions.py` module defines `TransitionGate` and `DEFAULT_STAGE_GATES` with pre-conditions like `ALL_TASKS_COMPLETE`, `HAS_ARTIFACTS`, `HAS_ACCEPTANCE_CRITERIA`, `MIN_PROGRESS`. These are **defined but never invoked** by `run_full_pipeline()` or by `WorkflowEngine.transition_story()`. The `validate_transition()` function exists but is only called in tests.

This means:
- **No gate checks occur** during `run_full_pipeline()`
- A story can transition to DONE even if no artifacts were produced
- A story can transition to DESIGN even if tasks are incomplete
- The `transition_story()` method only validates against `VALID_TRANSITIONS` (the state machine adjacency rules), not against business rules

### Alternative paths (shown but not taken)

The `VALID_TRANSITIONS` dict also supports:
- **BLOCKED** from any active state
- **Backtracking**: PLANNING→INCEPTION, DESIGN→PLANNING, IMPLEMENTATION→DESIGN, REVIEW→IMPLEMENTATION, ACCEPTANCE→IMPLEMENTATION, INTEGRATION→ACCEPTANCE, DELIVERY→INTEGRATION
- **Unblocking**: BLOCKED→any active state

These backtracking paths are **never exercised** by `run_full_pipeline()`.

---

## 4. Critical Path Analysis

### Absolute Minimum Path

If everything goes right and all agents are found, the pipeline always executes **all 9 states** and **all 8 phases**. There is no early-exit or short-circuit in `run_full_pipeline()`:

```
INCEPTION → PLANNING → DESIGN → IMPLEMENTATION → REVIEW → ACCEPTANCE → INTEGRATION → DELIVERY → DONE
```

The only way to skip an entire phase is if `find_best_agent()` returns `None` for that phase's task, which causes the `if agent:` block to be skipped but the `complete_task()` still runs and the transition still happens.

### Optional / Conditional Steps

| Step | Condition | Effect if False |
|------|-----------|-----------------|
| `story.acceptance_criteria = ...` | `if acceptance_criteria:` (orch:73) | Story keeps empty criteria list → planner generates a single default task |
| Agent task assignment + execution | `if agent:` (orch:89, 107, 151, 173, 191, 211, 231, 249) | Task is marked DONE without execution. No artifacts produced for that stage. |
| State transition guard | `if story.state != X` (orch:124, 159, 179, 199, 219, 239) | Always true on happy path. Would be false only if state somehow already advanced (e.g. if `advance_story()` was used) |
| Skip DONE tasks | `if task.status == TaskStatus.DONE: continue` (orch:165) | Skips already-completed tasks in implementation loop — **always skips** inception, planning, design tasks |
| Skip non-developer tasks | `if task.required_role != "developer": continue` (orch:167) | Skips review, acceptance, integration, delivery tasks in implementation loop |
| Skip step-less tasks | `if not task.steps: continue` (orch:169) | Skips any developer task that somehow has no TDD steps |
| Complete task only if all steps done | `if task.all_steps_done(): complete_task()` (wf:190) | If steps remain (shouldn't happen), task stays IN_PROGRESS |
| Reviewer refactoring suggestions | `if feedback["issues_found"] > 0` (reviewer.py:45) | Only produces REFACTOR_SUGGESTION if issues found (never happens — `issues_found` is hardcoded to 0) |
| PO acceptance criteria | `if story.acceptance_criteria` (product_owner.py:74) | If story already has criteria (from input), returns them. Otherwise generates defaults. |

### Chokepoints

| Chokepoint | Why | What Happens at Failure |
|------------|-----|------------------------|
| `next(a for a in agents if isinstance(...))` | 7 calls, each expects exactly one agent of that type. If the team has gaps, `StopIteration` crashes the pipeline. | **Unhandled crash** — `StopIteration` propagates to caller |
| `find_best_agent()` returning `None` | 8 calls. If no agent matches role or is available, the task is skipped but `complete_task()` still fires. | **Silent skip** — stage produces no artifacts, but no error is raised |
| `engine.get_story(story_id)` | Called 15+ times via various engine methods. Uses `self.stories[story_id]` — raises `KeyError` if ID is wrong. | **Unhandled crash** — `KeyError` propagates |
| `story.transition()` | Validates against `VALID_TRANSITIONS`. If somehow called with invalid transition (e.g., duplicate transition to same state). | **Unhandled crash** — `ValueError` propagates |
| Engine-agent duality | `BaseAgent.agent` (model) vs `BaseAgent` (handler). The engine stores `model.Agent` objects. `agent_handler` in `execute_task_tdd()` is a `BaseAgent` subclass. | Confusion between layers could cause type mismatches |
| Double-add artifact bug | `BaseAgent.produce_artifact()` calls `engine.add_artifact()` internally. Orchestrator also calls `engine.add_artifact()` on return values. | Artifact IDs duplicated in `story.artifacts` list (benign but wasteful) |

---

## 5. Failure Mode Analysis

### 5.1 What happens if an agent returns empty artifacts?

If any of these return `[]` (empty list):

- `po_agent.execute()` → no artifacts added for INCEPTION phase. `complete_task()` still runs. Pipeline continues. Story proceeds without STORY_BRIEF or ACCEPTANCE_CRITERIA artifacts.
- `planner.plan_story()` → generates tasks normally (that call is separate from `execute()`).
- `planner.execute()` → no TASK_BREAKDOWN artifact. Pipeline continues.
- `architect.execute()` → no design artifacts. Pipeline continues.
- `reviewer.execute()` → no REVIEW_FEEDBACK artifact. Pipeline continues.
- `test_writer.execute()` → no acceptance artifacts. Pipeline continues.
- `devops.execute()` (integration) → no CI/DEPLOY artifacts. Pipeline continues.
- `devops.execute()` (delivery) → no RELEASE_NOTES. Pipeline continues.

**Effect:** Silent degradation. The pipeline produces fewer artifacts but never complains.

**Test coverage:** Untested.

### 5.2 What happens if `find_best_agent()` returns None?

Each of the 8 calls is guarded:

```python
agent = engine.scheduler.find_best_agent(...)
if agent:
    engine.scheduler.assign_task(task, agent)
    artifacts = agent_cls.execute(task, story)
    for art in artifacts:
        engine.add_artifact(art)
engine.complete_task(story.id, task.id)  # <-- Still called!
```

If agent is `None`:
- No task assignment happens
- No artifacts are produced
- Task is marked DONE anyway
- Story transitions to next state regardless
- **No task was actually performed**

**Silent skip** — the pipeline continues merrily with no execution for that stage.

**Test coverage:** `test_no_available_agent` (scheduler.py:212-218) tests the scheduler level, but the orchestration-level handling is untested.

### 5.3 What happens if a task has no steps but `required_role="developer"`?

The implementation loop (orch:169) checks `if not task.steps: continue`. So tasks without steps are silently skipped.

However, if a developer task somehow has steps but they're all already DONE (unlikely), it's also skipped at workflow.py:165.

**Effect:** Silent skip. No TDD cycle runs.

### 5.4 What happens if `story.transition()` raises ValueError?

`ValueError` is raised when:
- Transitioning to a state not in `VALID_TRANSITIONS[from_state]`
- Transitioning to the same state (not allowed since no self-loop definitions)
- Transitioning from DONE (empty target list)

In `run_full_pipeline()`, all transitions follow the linear INCEPTION→PLANNING→DESIGN→IMPLEMENTATION→REVIEW→ACCEPTANCE→INTEGRATION→DELIVERY→DONE path. These are all valid.

But if the `if story.state != X` guards were somehow bypassed (e.g., if story was already at DESIGN when the PLANNING→DESIGN transition fires due to a double-call), the `transition()` method raises `ValueError`.

**No try/except exists** — `ValueError` propagates to `main()` and crashes the CLI.

### 5.5 What happens if a step fails?

There are several failure points within `execute_task_tdd()`:

1. **`get_story()` raises `KeyError`** if story_id not found → **crash**
2. **Task not found** in story.tasks → raises `KeyError` → **crash**
3. **`developer.execute_step()` raises `ValueError`** for unknown step_type (developer.py:50) → **crash**
4. **`add_artifact()`** could fail if artifact is invalid → **crash**
5. **`complete_task()` raises `KeyError`** if task was somehow removed → **crash**

There are **no try/except blocks** in `execute_task_tdd()` or anywhere in the pipeline.

### 5.6 What error handling exists?

| Error Type | Location | Handling |
|------------|----------|----------|
| Agent not found | 8 × `if agent:` in orchestrator.py | **Soft skip** — task completes without execution |
| Agent at capacity | `scheduler.assign_task()` → `agent.pick_up_task()` | **Raises `RuntimeError`** — unhandled, crashes |
| Invalid story transition | `Story.transition()` | **Raises `ValueError`** — unhandled, crashes |
| Missing story | `WorkflowEngine.get_story()` | **Raises `KeyError`** — unhandled, crashes |
| Missing task | `WorkflowEngine.complete_task()` | **Raises `KeyError`** — unhandled, crashes |
| Missing story in `get_story()` | `execute_task_tdd()`, `transition_story()` | **Raises `KeyError`** — unhandled, crashes |
| Unknown step type | `DeveloperAgent.execute_step()` | **Raises `ValueError`** — unhandled, crashes |
| Missing agent type in team | `next()` with `isinstance()` filter | **Raises `StopIteration`** — unhandled, crashes |

**Summary:** The pipeline has 8 soft-skip guards for missing agents, but zero error recovery for all other failure modes. Any unexpected error crashes the entire pipeline.

---

## 6. Test Coverage Trace

### Test mapping

| Test Name | What It Covers | What It Misses |
|-----------|---------------|----------------|
| `TestStory::test_create_story` | Story creation, default state, ID length | — |
| `TestStory::test_valid_transition` | Single transition, history tracking | — |
| `TestStory::test_invalid_transition_raises` | ValueError for invalid transitions | — |
| `TestStory::test_full_lifecycle_transitions` | All 8 happy-path transitions | — |
| `TestStory::test_progress_based_on_steps` | Progress based on step completion | — |
| `TestStory::test_ready_tasks` | Dependency-based readiness | — |
| `TestTask::test_task_dependencies` | Task is_ready() with dependency sets | — |
| `TestTask::test_task_tdd_steps` | Total/completed step counts | — |
| `TestTask::test_task_step_progression` | Sequential step completion, current_step | — |
| `TestTask::test_task_complete` | assign() + complete() flow | — |
| `TestTaskStep::test_step_complete` | Step completion with artifact_id | — |
| `TestAgent::test_agent_availability` | Agent capacity tracking | — |
| `TestAgent::test_agent_role_matching` | Role matching logic | — |
| `TestAgent::test_agent_utilization` | Utilization calculation | — |
| `TestAgent::test_test_writer_role` | TEST_WRITER role existence | — |
| `TestScheduler::test_find_agent_by_role` | Role-based agent selection | — |
| `TestScheduler::test_no_available_agent` | Returns None when no agent available | — |
| `TestScheduler::test_load_balancing` | Picks least-utilized agent | — |
| `TestContextManager::test_set_and_get` | Basic context ops | — |
| `TestContextManager::test_prefix_filtering` | Prefix-based key filtering | — |
| `TestContextManager::test_story_context` | Story-specific context retrieval | — |
| `TestContextManager::test_history` | Context change history | — |
| `TestTransitions::test_all_tasks_complete_gate` | ALL_TASKS_COMPLETE gate logic | Gate not used in pipeline |
| `TestTransitions::test_acceptance_criteria_gate` | HAS_ACCEPTANCE_CRITERIA gate logic | Gate not used in pipeline |
| `TestWorkflowEngine::test_create_and_transition` | Engine-level create + transition | — |
| `TestWorkflowEngine::test_register_agents` | Agent registration | — |
| `TestWorkflowEngine::test_event_emission` | Event handler system | — |
| `TestWorkflowEngine::test_status` | Engine status reporting | — |
| `TestWorkflowEngine::test_execute_task_tdd` | Full TDD cycle via engine | — |
| `TestAgentExecution::test_product_owner` | PO execute() produces STORY_BRIEF | Orchestration of PO in pipeline |
| `TestAgentExecution::test_architect` | Architect execute() produces artifacts | Orchestration of architect |
| `TestAgentExecution::test_developer_tdd_steps` | Developer step execution | Full orchestration of dev loop |
| `TestAgentExecution::test_test_writer` | TestWriter produces TEST_REPORT | Orchestration of test writer |
| `TestAgentExecution::test_devops` | DevOps execute() produces artifacts | Orchestration of devops |
| `TestAgentExecution::test_scrum_master_planner` | plan_story() output structure | Orchestration of planner |
| `TestFullPipeline::test_run_full_pipeline` | Full happy path end-to-end | All error/skip paths |
| `TestFullPipeline::test_pipeline_produces_tdd_artifacts` | RED/GREEN/REFACTOR artifacts exist | Content verification |
| `TestFullPipeline::test_pipeline_includes_acceptance_tests` | Acceptance test artifacts present | Edge cases |

### What is NOT tested

**Missing test coverage (critical gaps):**

1. **Empty acceptance_criteria** — calling `run_full_pipeline()` with `acceptance_criteria=None` (or empty list). The planner generates default criteria, but this path is untested.

2. **Missing agent scenario** — when `find_best_agent()` returns `None` for any phase. The `if agent:` skip logic is entirely untested at the pipeline level.

3. **Phase state guard conditions** — the `if story.state != X` checks (lines 124, 159, 179, 199, 219, 239) are always true on the happy path and never tested under conditions where they would be false.

4. **Implementation loop skip logic** — the three skip conditions (DONE tasks, non-developer role, missing steps) are implicitly part of the happy path but never explicitly tested with edge cases:
   - What if a developer task has no steps?
   - What if required_role is missing?
   - What if all tasks are somehow already DONE?

5. **`run_story()` method** — the engine's own pipeline driver (workflow.py:244-266) is completely untested. Only `run_full_pipeline()` (the orchestrator's procedural version) is tested.

6. **`advance_story()` method** — the automated state advancement logic is untested.

7. **`assign_tasks_for_stage()` method** — automated task assignment is untested.

8. **Error handling** — no tests verify behavior when:
   - `Story.transition()` raises `ValueError`
   - `engine.get_story()` raises `KeyError`
   - `engine.complete_task()` raises `KeyError`
   - `agent.pick_up_task()` raises `RuntimeError`

9. **CLI entry point** — `main()` and `_print_text()` are untested.

10. **Agent execute return values** — tests verify agents produce artifacts but not what happens when they return empty lists.

11. **Backtracking transitions** — no test exercises BLOCKED or reverse transitions through the pipeline.

12. **Multiple agents of same role** — the scheduler supports load-balancing, but the default team has exactly one per role. Multi-agent scenarios are untested at the pipeline level.

13. **Duplicate artifact IDs** — the double-add bug in `add_artifact()` via `produce_artifact()` + orchestrator iteration is untested.

14. **Step execution failure** — no test for `execute_step()` receiving an unknown `TaskStepType`.

15. **Task dependency ordering in implementation** — the planner sets dependencies, but the implementation loop just iterates `story.tasks` in insertion order and never checks task readiness. This is untested.

---

## 7. Code Path Counting

### Independent decision points in `run_full_pipeline()`

| # | Location | Branch | Type | Possible Values |
|---|----------|--------|------|-----------------|
| A | `orch:73` | `if acceptance_criteria:` | Binary | `None` (falsy) / non-empty list (truthy) |
| B | `orch:89,107,151,173,191,211,231,249` | `if agent:` | Binary × 8 | Found / Not found (independent per call) |
| C | `orch:124` | `if story.state != DESIGN` | Binary | True / False |
| D | `orch:159` | `if story.state != IMPLEMENTATION` | Binary | True / False |
| E | `orch:179` | `if story.state != REVIEW` | Binary | True / False |
| F | `orch:199` | `if story.state != ACCEPTANCE` | Binary | True / False |
| G | `orch:219` | `if story.state != INTEGRATION` | Binary | True / False |
| H | `orch:239` | `if story.state != DELIVERY` | Binary | True / False |
| I | `orch:165` | `if task.status == DONE: continue` | Multi-value | Depends on task count N (2^N per-task decisions) |
| J | `orch:167` | `if task.required_role != "developer": continue` | Multi-value | Depends on task count |
| K | `orch:169` | `if not task.steps: continue` | Multi-value | Depends on task count |
| L | `wf:165` | `if step.status == DONE: continue` | Multi-value | Depends on steps per task |
| M | `wf:190` | `if task.all_steps_done(): complete_task` | Binary | True / False (always true on happy path) |
| N | `rev:45` | `if feedback["issues_found"] > 0` | Binary | Hardcoded 0 → always False |
| O | `po:74` | `if story.acceptance_criteria` | Binary | Empty / non-empty |
| P | `tw:46` | Title matchers (multiple ifs) | 2^3 | 8 combinations of keyword matches |
| Q | `do:34,56,69` | Title matchers (multiple ifs) | 2^3+1 | 8+ combinations of keyword matches + default |

### Approximate path count formula

The number of distinct paths = combinations of independent decision outcomes.

**Conservative lower bound** (considering only binary decisions in `run_full_pipeline()`):

```
A × (B1 × B2 × ... × B8) × C × D × E × F × G × H

= 2 × (2^8) × 2^6
= 2 × 256 × 64
= 32,768
```

This does not include:
- The task-loop decisions (I, J, K) which depend on how many tasks exist
- The step-loop decisions (L) which depend on steps per task
- Agent-level decisions (N, O, P, Q)
- The number of acceptance criteria passed (affects task count)

**With task-loop factors included**, assuming 7 tasks in `story.tasks` (inception + planning + 3 design + 2 criteria tasks + integration):

```
32,768 × (2^7 × 4 × 4) × (2^3 × 2) × ...
```

The practical number is **at least 10⁶+ distinct paths**.

### Practical path categories

| Category | Approx. # Paths | Description |
|----------|-----------------|-------------|
| Full happy path (all agents found, 2 criteria) | 1 | The tested path |
| Happy path with 0 criteria | 1 | `acceptance_criteria=None`, planner generates 1 default task |
| Happy path with N criteria | 1 per N | Task count varies |
| One agent missing (7 variants) | 7 | Each of 8 agent-find calls returns None (but 2 use devops, 1 uses same PO) |
| Multiple agents missing | ~2^8 - 1 | Any combination of missing agents |
| State guard failures | ~2^6 | Various states already advanced |
| Agent-level content variations | ~2^6 | Per-agent title matching variations |
| **Total practical paths** | **500+** | Major behavioral differences |

### Practically important paths (untested)

| Path | Description | Risk |
|------|-------------|------|
| Missing developer agent | Developer tasks skipped; no TDD artifacts | **High** — the pipeline "succeeds" with no code |
| Missing architect agent | No design artifacts | **Medium** — design stage is a no-op |
| Missing reviewer agent | No review artifacts | **Medium** — review stage is a no-op |
| Empty acceptance_criteria | Planner generates a default task | **Medium** — different task structure |
| All agents missing | All stages are no-ops; story goes straight to DONE | **Low** (unrealistic) but demonstrates zero validation |
| Zero criteria pipeline | 1 default task from planner instead of N+1 | **Medium** — different task topology |

---

## Appendix A: Bug Report — Double Artifact Registration

**Location:** `agents/base.py:61-62` + `orchestrator.py:92-93` (and all similar patterns)

**Description:** `BaseAgent.produce_artifact()` calls `self.engine.add_artifact(artifact)` internally when `self.engine` is set. The orchestrator then iterates the return value of `agent.execute()` and calls `engine.add_artifact(art)` again for each artifact. Since all agents are bound to the engine (via `agent.bind(engine)` at orch:68-69), `self.engine` is always set.

**Impact:** `story.artifacts` list accumulates duplicate artifact IDs. For a pipeline with ~23 unique artifacts, the list may contain ~46 entries (2× each). The dict overwrite is harmless, but the list growth is technically a bug.

**Affected call sites:**
- `orch:92-93` — ProductOwnerAgent artifacts
- `orch:114-115` — ScrumMasterAgent artifacts  
- `orch:153-155` — ArchitectAgent artifacts
- `orch:194-195` — ReviewerAgent artifacts
- `orch:213-215` — TestWriterAgent artifacts
- `orch:234-235` — DevOpsAgent (integration) artifacts
- `orch:253-254` — DevOpsAgent (delivery) artifacts

**Exception:** DeveloperAgent artifacts are handled via `execute_task_tdd()` → `agent_handler.execute_step()` → `self.add_artifact()` (workflow.py:179), not via the orchestrator loop. Developer agent's `produce_artifact()` call happens inside `_write_failing_test()` etc. (developer.py:106-113), and then `add_artifact()` is called again at workflow.py:179. So DeveloperAgent has the same double-add bug.

## Appendix B: Unused Code

The following code exists but is **never called** by `run_full_pipeline()`:

| Code | Location | Why Unused |
|------|----------|------------|
| `TransitionGate`, `DEFAULT_STAGE_GATES`, `validate_transition()` | `engine/transitions.py` | Pipeline performs no gate validation |
| `WorkflowEngine.run_story()` | `workflow.py:244` | Orchestrator has its own procedural pipeline |
| `WorkflowEngine.assign_tasks_for_stage()` | `workflow.py:125` | Orchestrator calls scheduler directly |
| `WorkflowEngine.advance_story()` | `workflow.py:220` | Orchestrator transitions manually |
| `WorkflowEngine.check_stage_complete()` | `workflow.py:214` | Orchestrator doesn't check completeness |
| `Task.next_step()` | `story.py:152` | `execute_task_tdd()` iterates directly |

## Appendix C: Summary Statistics

- **Total lines of Python:** ~2,100 (all source files)
- **Functions called in trace:** ~85+
- **Objects created:** 1 Engine, 1 Scheduler, 1 ContextManager, 7 Agents, 1 Story, 12 Tasks, 9 TaskSteps, ~23 Artifacts
- **Events emitted:** ~50+ (story_created, story_transition ×8, artifact_produced ×~23, step_started ×9, step_completed ×9, task_completed ×12)
- **Test coverage of pipeline paths:** ~1 path out of ~500+ practical paths (<0.2%)
- **Error handling coverage:** 8 soft-skip guards, 0 try/except blocks
- **Valid transitions defined:** 24 (including BLOCKED and backtracking)
- **Valid transitions exercised:** 8 (the linear happy path only)
