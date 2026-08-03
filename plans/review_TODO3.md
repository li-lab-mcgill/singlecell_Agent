# Plan Review: TODO3 — Evolving Research Logic Implementation Plan (v7)

Reviewed: 2026-05-13

---

## Previous Issues — Status

| Issue | Status |
|---|---|
| Issue 1: Phase 5 trajectory actions with no graph-mutation rule | Fixed: Phase 5 now explicitly states which decisions mutate the graph and which don't |
| Issue 2: `leaderboard.json` schema missing | Not fixed |
| Minor 1: `execution_refs` / `execution_result_path` duplication in node schema | Fixed: `execution_result_path` removed |
| Minor 2: `turn_id` defined but unused in file layout | Not fixed |
| Minor 3: `create_branch` edge type mapping per `branch_reason` implicit | Fixed by removal: edge-type taxonomy replaced with simple parent-child edges plus metadata |
| Minor 4: `reports/` directory absent from storage layout | Fixed: `reports/` added to layout |

---

## Overall Assessment

The architectural change in this version is significant and well-designed. The `update_state_graph` LLM-callable tool has been removed. The Mediator now produces a structured `decision_type` and the ResearchLoop / Orchestrator infers and applies the graph outcome deterministically. This is the right separation: the Mediator speaks research intent, not graph vocabulary. The trajectory context packet (tried solutions, untried alternatives, reusable artifacts) is a genuine improvement — the Mediator no longer reasons only from the latest result but from the full history of what has been tried.

The edge schema simplification (parent-child with metadata instead of a named edge-type taxonomy) removes an entire class of ambiguity.

Four issues remain. The most significant is new: the Mediator produces 13+ `decision_type` values, and the Orchestrator must infer the internal graph outcome from each — but the inference rules are not stated. This blocks Phase 6 implementation the same way the old Issue 1 did.

---

## Remaining Issues

### Issue 1 — Mediator `decision_type` → Orchestrator internal graph outcome mapping is not specified

Phase 6 StateGraph Update Helper states:

```text
Internal graph outcomes:
  initialize_plan
  carry_forward
  repeat_step
  create_branch
  declare_unanswerable
  conclude

These outcomes are inferred by ResearchLoop / Orchestrator; the Mediator does
not need to speak graph vocabulary.
```

For the five process-routing decisions, Phase 5 already specifies what the Orchestrator does:

```text
ask_user_clarification  -> set session status to awaiting_user, no new node
request_tool_plan_revision -> rerun ToolConsultant, no new node unless plan changes
ask_panelist_callback -> run callbacks, no mutation until follow-on decision
start_panel_update_round -> run ScientistPanel.update, no mutation until new plan
produce_next_research_plan -> formulate first, then create node if plan changed
```

But the research-direction decisions have no stated mapping:

```text
interpretation_only           -> carry_forward? No execution needed.
new_downstream_analysis       -> carry_forward or create_branch? Depends on whether
                                 the plan content changes.
parameter_change              -> repeat_step or create_branch? Unclear.
upstream_preprocessing_change -> create_branch.
method_replacement            -> create_branch.
data_change                   -> create_branch.
revise_plan                   -> create_branch.
conclude                      -> conclude.
declare_unanswerable          -> declare_unanswerable.
```

The ambiguous cases are `interpretation_only`, `new_downstream_analysis`, and `parameter_change`. For these, the Orchestrator has no contract. Add to Phase 5 or Phase 6:

```text
Orchestrator graph outcome inference rules:

  interpretation_only:
    No execution. carry_forward if no plan content changed.
    If the Mediator's next_research_plan differs from the active node plan,
    create_branch instead.

  new_downstream_analysis:
    carry_forward if the active node plan is extended without branching.
    create_branch if a new downstream-only plan node is required.

  parameter_change:
    repeat_step if only tool parameters change within the same plan node.
    create_branch if the plan content itself changes.

  upstream_preprocessing_change / method_replacement / data_change / revise_plan:
    create_branch unconditionally.

  conclude:
    conclude.

  declare_unanswerable:
    declare_unanswerable.
```

The key distinguishing rule is whether `next_research_plan` differs materially from the active node's plan. Without that rule, the Orchestrator cannot decide `carry_forward` vs `create_branch` for the ambiguous cases.

---

### Issue 2 — `produce_next_research_plan` missing from Phase 6 `decision_type` schema enum

Phase 5 "Allowed Mediator post-analysis decision types" lists `produce_next_research_plan` as a valid decision. Phase 5 also describes its graph behavior:

```text
produce_next_research_plan:
  formulate the next plan first
  Orchestrator compares it with the active plan and creates a new node only if
  the plan trajectory changed
```

But the Phase 6 Mediator post-analysis decision shape defines `decision_type` as:

```text
"decision_type": "conclude | ask_user_clarification | request_tool_plan_revision |
  ask_panelist_callback | start_panel_update_round | interpretation_only |
  new_downstream_analysis | parameter_change | upstream_preprocessing_change |
  method_replacement | data_change | revise_plan | declare_unanswerable"
```

`produce_next_research_plan` is absent. Either add it to the schema enum or clarify that it is subsumed by one of the existing values (e.g., `revise_plan` triggers a new formulation and is therefore equivalent).

---

### Issue 3 — `leaderboard.json` schema still missing

`leaderboard.json` appears in the storage layout under `executions/{execution_id}/` and Phase 9 references DagExecutor best-path scoring. No schema is defined. This is a blocker before Phase 8/9.

Minimum fields needed:

```json
{
  "execution_id": "...",
  "tool_plan_id": "...",
  "scored_paths": [
    {
      "path_index": 0,
      "path_id": "path_000",
      "score": 0.82,
      "objective_metrics": {},
      "artifact_handles": [],
      "selected": false
    }
  ],
  "selected_path_index": 1,
  "selection_reason": "..."
}
```

---

## Minor Issues

### Minor 1 — `turn_id` defined in Storage Concepts but not explicitly placed in any file or directory

Storage Concepts defines `turn_id` and ConversationManager creates it per user message. Save Timeline Step 0 updates `session.json.turns[]`. But the plan does not state whether `turn_id` is a key within `session.json.turns[]` entries or whether it deserves a `turns/` directory.

This is ambiguous for an implementer. Add one line to the ConversationManager section or the storage layout:

```text
turn_id is the key of an entry in session.json.turns[].
No separate turns/ directory is needed.
```

### Minor 2 — `clarification/` directory in Save Timeline Step 2B absent from storage layout

Save Timeline Step 2B saves:

```text
clarification/request.md
clarification/options.json
```

But the storage layout under `sessions/{session_id}/` lists only `route/`, `nodes/`, `traces/`, `executions/`, `artifacts/`, and `reports/`. There is no `clarification/` entry. Either add it to the layout or redirect clarification files to an existing path (e.g., `route/` or `traces/responder/`).

---

## Summary

| Dimension | Status |
|---|---|
| Logical coherence | Clean — no conflicts found |
| Phase ordering | Sound throughout |
| Session / iteration / turn scoping | Defined; `turn_id` placement still unspecified |
| Mediator / Orchestrator split | Well-designed; Mediator speaks decision intent, Orchestrator applies graph rules |
| Mediator `decision_type` → graph outcome mapping | Gap: ambiguous cases for `interpretation_only`, `new_downstream_analysis`, `parameter_change` |
| `produce_next_research_plan` in Phase 6 schema | Missing from `decision_type` enum |
| `leaderboard.json` schema | Still missing |
| Storage layout completeness | `clarification/` directory referenced but absent |

The plan is ready to implement Phases 1–5 now. Before Phase 6 begins, Issue 1 (graph outcome inference rules for the ambiguous research-direction decisions) must be resolved — it is the direct successor of the old Issue 1 and blocks the same Orchestrator implementation. Issue 2 (`produce_next_research_plan` schema gap) is a one-line fix that should be done at the same time.
