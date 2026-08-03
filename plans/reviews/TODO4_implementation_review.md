# TODO4 Implementation Review — MediatorAgent and Research-Loop Architecture

**Reviewed**: 2026-05-26 (ninth pass — post-update re-review)
**Plan**: `plans/TODO4.md`
**Scope**: Full pipeline flow + correctness review

---

## Top-Level Routing

```
User message
  └─ SessionDispatcher.handle()
       └─ SessionRouter.route()
            ├─ direct_response  → respond immediately
            ├─ task + ambiguous → surface clarifying question
            └─ task + operational/discovery
                  └─ ResearchLoop.run()
```

---

## ResearchLoop — Full Lifecycle

```
ResearchLoop.run(user_question, anchor_papers)
  │
  ├── [Phase 0] _run_formulation_stage(research_state)
  │     ├── ScientistPanel.run_initial_panelists() → record_panelist_outputs()
  │     ├── MediatorAgent.formulate()
  │     │         _record_mediator_output(..., source="formulation", phase_number=None)
  │     ├── _complete_mediator_callbacks()
  │     │       [while needs_panelist_callback AND budget]:
  │     │         ScientistPanel.run_panelist_callback()
  │     │         extend local callback_history
  │     │         MediatorAgent.synthesize_callbacks()    ← context has prior history ✓
  │     │         _record_mediator_output(..., source="callback_synthesis")
  │     │         record_callback_history()               ← committed after synthesis ✓
  │     └── _run_adversary_until_accepted()
  │           for round in 1..max_rounds:
  │             AdversarialPanelist.run() → record_adversary_output()
  │             ├── {survives, skipped}
  │             │     → _candidate_resolution_to_formulation_result(
  │             │           {status:"accepted", adversarial_review_status:verdict, ...})  ✓
  │             └── {needs_revision, unsalvageable}
  │                   MediatorAgent.revise_from_adversary()
  │                   _record_mediator_output(..., source="adversary_revision")
  │                   _complete_mediator_callbacks(callback_history=callback_history)
  │                   _resolve_candidate_revision(force_terminal=round >= max_rounds)
  │                   → if status in {accepted, unanswerable}:  ⚠ K1 (redundant guard)
  │                       _candidate_resolution_to_formulation_result(resolution, ...)
  │                   → else: update candidate; continue
  │           fallthrough → raise RuntimeError(...)
  │
  └── [Phases 1–N] execution loop
        ├── A. ToolConsultant.decide()
        │         _record_tool_decision(source="tool_consultant_initial")
        │         [alignment review]
        │         _record_tool_decision(source="tool_consultant_aligned")
        ├── B. [Optional] ToolPlanAlignmentReviewer
        ├── C. _execute()
        ├── D. AnalyzerPanel.analyze() | _blocked_execution_report()
        │         _record_analyzer_report(source="analyzer")
        ├── E. [Optional] AttributingCritic / ShortTermMemory / ContextManager
        ├── F. MediatorAgent.post_analysis()
        │         ← context_for_mediator_post_analysis()
        │              evidence_state = research_state.evidence_state  ⚠ stale after Phase 1
        │         _record_mediator_output(source="post_analysis")
        │         → decision:
        │           ┌─ accept_and_conclude → return
        │           ├─ continue_with_same_research_plan → next phase
        │           ├─ self_revise_plan
        │           │     _review_post_analysis_candidate_if_needed():
        │           │       for round in 1..max_rounds:
        │           │         AdversarialPanelist.run() → record_adversary_output()
        │           │         ├─ {survives, skipped}
        │           │         │     _candidate_resolution_to_post_decision(
        │           │         │       {status:"accepted", adversarial_review_status:verdict,...})  ✓
        │           │         ├─ unsalvageable
        │           │         │     MediatorAgent.post_analysis() + _record_mediator_output()
        │           │         │     → if not self_revise_plan: return; else continue
        │           │         └─ needs_revision
        │           │               MediatorAgent.revise_from_adversary() + _record_mediator_output()
        │           │               _complete_mediator_callbacks(
        │           │                 callback_history=research_state.current_callback_history())  ✓
        │           │               _resolve_candidate_revision()
        │           │               → unanswerable/force_terminal: _candidate_resolution_to_post_decision()
        │           │               → else: update candidate; continue
        │           │       budget exhausted → _post_analysis_budget_exhausted_decision()  ✓
        │           ├─ ask_user → node "awaiting_user"
        │           └─ declare_unanswerable → return
        ├── post_decision.evidence_state → working_model (not → research_state.evidence_state)  ⚠
        └── G. StateGraphManager.apply_post_analysis_decision()
```

---

## State Architecture

```
ResearchState  (task-scoped, one per research task)
  │
  │  All 6 setters — defined and wired at all correct call sites:
  │    record_panelist_outputs()     ← _run_formulation_stage()
  │    record_callback_history()     ← _complete_mediator_callbacks(), after synthesize
  │    record_adversary_output()     ← both adversary loops
  │    record_mediator_output()      ← via _record_mediator_output() wrapper (7 call sites)
  │    record_tool_decision()        ← via _record_tool_decision() wrapper (×2/phase)
  │    record_analyzer_report()      ← via _record_analyzer_report() wrapper (×1/phase)
  │
  │  Accessor:
  │    current_callback_history() → list copy; safe for sub-loop seeding
  │
  │  Compact transformers:
  │    _compact_mediator_event(), _compact_tool_event(), _compact_analyzer_event()
  │
  │  Context builders (read-only):
  │    context_for_mediator_formulation()
  │    context_for_mediator_adversary_revision()   → previous_mediator_outputs,
  │    context_for_mediator_post_analysis()           previous_tool_decisions,
  │    context_for_adversary()                        previous_analyzer_reports  (all populated)
  │    context_for_tool_consultant()
  │
  └── working_memory:
        panelist_outputs, callback_history, adversary_outputs,
        mediator_outputs (compact), tool_decisions (compact), analyzer_reports (compact)
```

---

## Module-level helpers

| Function | Purpose |
|----------|---------|
| `_resolve_candidate_revision()` | Pure; maps (revised_output, verdict, force_terminal) → {status, plan, trajectory, reason} |
| `_candidate_resolution_to_formulation_result()` | Phase-0 return dict builder; includes adversarial_review_status/interpretation |
| `_candidate_resolution_to_post_decision()` | Post-analysis return dict builder; propagates adversarial_review_status/interpretation |
| `_post_analysis_budget_exhausted_decision()` | Budget-exhausted fallthrough; forces declare_unanswerable with full enrichment |
| `_materially_different_research_plan()` | JSON-equality check over plan signal fields |
| `_blocked_execution_report()` | Analyzer-shaped report for pre-execution alignment blocks |
| `_next_action_from_post_analysis_decision()` | Maps decision type → done/abstain/awaiting_user/continue |
| `_canonical_post_decision()` | Normalizes legacy decision aliases |

---

## TODO4 Status: Implemented vs. Transitional

### Implemented

All N1–N5, F1–F4, G1–G2, H1–H2, I1–I3, J1 resolved. Core invariants hold:

- Every adversary loop exit routes through a shared helper that stamps `resolution_reason`, `adversarial_review_status`, `adversarial_review_interpretation`
- All 6 `ResearchState` setters wired; compact transformers prevent token bloat
- `_complete_mediator_callbacks` ordering: extend local list → synthesize → record to state
- `current_callback_history()` provides a safe copy for sub-loop callback seeding
- `_post_analysis_budget_exhausted_decision()` covers the budget-exhausted path
- `pre_execution` dead parameter removed (J1 fixed)

### Still Transitional

| Item | Current State | Impact |
|------|--------------|--------|
| `ResearchWorkspace` | Not instantiated; `ResearchState` created in `ResearchLoop.run()` | Architectural only |
| `ScientistPanel.formulate()` + `decide_after_analysis()` + `run_post_analysis_callbacks()` | Present; unreachable (legacy flag always False) | Dead code; no functional impact |
| `research_state.evidence_state` not updated post-Phase 0 | `commit_initial_plan()` sets it from formulation; post-analysis `evidence_state` only updates `working_model` and `research_context`, not `research_state.evidence_state` | **Functional**: Mediator's `context_for_mediator_post_analysis()["evidence_state"]` always returns Phase-0 evidence; phase-over-phase evidence accumulation visible to AnalyzerPanel (via `working_model`) is invisible to the Mediator |
| `working_model` | Updated from `post_decision["evidence_state"]` each phase; passed to `analyzer_panel.analyze()` | Should be superseded by `research_state.evidence_state` |
| `StateGraphManager` direct mutation from `ResearchLoop` | Called directly in loop body | Architectural only |

---

## New Findings (eighth-pass review)

### [K1] TRIVIAL — Redundant guard clause in `_run_adversary_until_accepted()` exit condition

```python
# line 706
if resolution["status"] in {"accepted", "unanswerable"} and (round_number >= max_rounds or resolution["status"] == "unanswerable"):
```

`_resolve_candidate_revision` returns `"accepted"` only when `force_terminal=True` (`round_number >= max_rounds`), and `"unanswerable"` always warrants an exit. Therefore the right-hand clause `(round_number >= max_rounds or resolution["status"] == "unanswerable")` is always True when the left-hand set membership check is True. The condition is equivalent to:

```python
if resolution["status"] in {"accepted", "unanswerable"}:
```

No behavioral change; purely a readability simplification.

---

## New Findings (ninth-pass review)

### [L1] LOW-MEDIUM — `research_state.evidence_state` never updated post-Phase 0

**Location**: `research_loop.py` lines 492–493

```python
# Current code — working_model is updated but ResearchState is not:
if post_decision.get("evidence_state"):
    working_model = {"evidence_state": post_decision.get("evidence_state")}
    # ← missing: research_state.evidence_state = post_decision["evidence_state"]
```

`research_state.evidence_state` is set exactly once — by `commit_initial_plan()` in Phase 0. All subsequent post-analysis decisions that carry an updated `evidence_state` field update only the local `working_model` dict (passed to `analyzer_panel.analyze()`) and `research_context` (only when `self_revise_plan` fires — see L2 below). The `ResearchState` object's `evidence_state` attribute stays frozen at the Phase-0 value for the entire run.

**Consequence**: every call to a `ResearchState` context builder that reads `self.evidence_state` — including `context_for_mediator_post_analysis()`, `context_for_mediator_adversary_revision()`, `context_for_adversary()`, and `context_for_tool_consultant()` — delivers Phase-0 evidence to the Mediator, the adversary, and the ToolConsultant for all phases after Phase 1. The Mediator must rely entirely on `previous_analyzer_reports` (compact summaries) to infer what evidence has accumulated, rather than receiving the structured `evidence_state` that its prompt is designed to interpret.

**Fix**: one line after the `working_model` update:

```python
if post_decision.get("evidence_state"):
    working_model = {"evidence_state": post_decision["evidence_state"]}
    research_state.evidence_state = post_decision["evidence_state"]   # ← add
```

This also removes the need to thread `evidence_state` through `research_context` for the purpose of giving the Mediator current evidence — the context builders will automatically read the updated value.

---

### [L2] LOW — `research_context["evidence_state"]` not updated on `continue_with_same_research_plan`

**Location**: `research_loop.py` lines 495–515

The `research_context` dict (which feeds `_build_session_state()` → ToolConsultant) is only rebuilt when `post_decision` carries an `updated_selected_research_plan` with steps — i.e., only on `self_revise_plan` decisions:

```python
next_plan = post_decision.get("updated_selected_research_plan")
if isinstance(next_plan, dict) and next_plan.get("steps"):       # ← only on self_revise_plan
    ...
    research_context = _extract_research_context(
        {
            ...
            "evidence_state": post_decision.get("evidence_state", ...),
        },
        user_question,
    )
```

For `continue_with_same_research_plan` decisions (the most common multi-phase path), this block is skipped. The `research_context["evidence_state"]` that `_build_session_state()` reads at line 1078 is the Phase-0 value from the initial formulation. The ToolConsultant's session state therefore carries stale evidence on all continue-path phases.

**Fix**: move the `evidence_state` update outside the `self_revise_plan` guard:

```python
# After the working_model / research_state.evidence_state update:
if post_decision.get("evidence_state"):
    research_context["evidence_state"] = post_decision["evidence_state"]

# Then the existing plan-update block unchanged:
next_plan = post_decision.get("updated_selected_research_plan")
if isinstance(next_plan, dict) and next_plan.get("steps"):
    ...
    research_context = _extract_research_context(
        {
            ...
            "evidence_state": post_decision.get("evidence_state", research_context.get("evidence_state", {})),
        },
        user_question,
    )
```

This is independent of L1 — L1 fixes `ResearchState`; L2 fixes the ToolConsultant's session state. Both should be applied together.

---

## Summary Table — All Open Findings

| ID | Severity | Location | Description | Status |
|----|----------|----------|-------------|--------|
| K1 | Trivial | `research_loop.py` line 706 | Redundant right-hand clause in `_run_adversary_until_accepted()` exit condition | Open |
| L1 | Low-Medium | `research_loop.py` lines 492–493 | `research_state.evidence_state` never updated post-Phase 0; Mediator/adversary/tool-consultant always see Phase-0 evidence | **New** |
| L2 | Low | `research_loop.py` lines 495–515 | `research_context["evidence_state"]` not updated on `continue_with_same_research_plan`; ToolConsultant gets stale evidence on continue phases | **New** |

### Previous findings — resolution status

| Previous ID | Description | Resolution |
|-------------|-------------|------------|
| N1 | `call_panelists` ghost | **Fixed** |
| N2 | `unsalvageable` not caught in formulation loop | **Fixed** |
| N3 | Unsalvageable re-run not persisted | **Fixed** |
| N4 | `context_for_mediator_formulation()` mutation side effect | **Fixed** |
| N5 | Last-round force-"accepted" ignores `declare_unanswerable` | **Fixed** |
| F1 | Dead-code fallthrough in `_run_adversary_until_accepted()` | **Fixed** — `raise RuntimeError` |
| F2 | Duplicated exit-dict construction | **Fixed** — all exits use helpers |
| F3 | `adversary_outputs` via direct dict access | **Fixed** |
| F4 | Callback context naming ambiguity | **Fixed** (H1 resolved root cause) |
| G1 | Three setters defined but never called | **Fixed** — wrapper methods at all call sites |
| G2 | Budget-exhausted fallthrough returned unenriched dict | **Fixed** — `_post_analysis_budget_exhausted_decision()` |
| H1 | `record_callback_history()` before `synthesize_callbacks()` | **Fixed** — committed after synthesis |
| H2 | `survives/skipped` used inline dict in `_run_adversary_until_accepted()` | **Fixed** — routes through helper |
| I1 | `survives` path in `_review_post_analysis_candidate_if_needed()` mutated in-place | **Fixed** — `_candidate_resolution_to_post_decision()` |
| I2 | `skipped` missing from `_review_post_analysis_candidate_if_needed()` check | **Fixed** — `{"survives", "skipped"}` |
| I3 | `callback_history=[]` overwrote prior history in state | **Fixed** — `current_callback_history()` seeder |
| J1 | `pre_execution` parameter declared and passed but never read | **Fixed** — removed from signature and call site |
| K1 | Redundant guard clause in `_run_adversary_until_accepted()` | Open (trivial) |
