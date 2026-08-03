# Plan Review: update_system.md — Update System Implementation Plan (v4)

Reviewed: 2026-05-19

---

## Previous Issues — Status

| Issue | Status |
|---|---|
| `updated_selected_research_plan` had no transition alias for deployed `next_research_plan` | Fixed: Phase 10 states strict cutover — prompt and readers updated together; validation fails if field is missing |
| Mediator formulation field transition (old TODO3 fields → new `evidence_state` fields) | Fixed: Evidence State Contract states schema validation should fail loudly if old fields arrive; cutover is atomic |
| `addresses_claims` default for deployed steps | Fixed: Evidence State Contract adds `claim_linkage: best_effort_unmapped` fallback |
| Phase 11 `needs_panelist_callback` test attribution wrong component | Fixed: Phase 11 now correctly states "Adversary `needs_revision` can trigger a Mediator panelist callback decision" |

---

## Overall Assessment

All previous issues are resolved. The plan is now complete, internally consistent, and safe against the risks of partial deployment. The atomic-cutover strategy (fail loudly on old fields rather than silently alias) is the right call given that TODO3 is live and the new schema is a structural change, not a rename.

No architectural conflicts remain. The remaining items are two minor implementation-level gaps.

---

## Remaining Issues

### Minor 1 — `call_panelists` StateGraph mapping has no stated termination condition if the Mediator loops indefinitely

Phase 10 StateGraph mapping for `call_panelists`:

```text
call_panelists:
  no graph mutation until callback completes and Mediator re-issues a decision
```

Phase 8 Panelist Callback Flow shows:

```text
StateGraph.context_for_panelist_callback()
  -> panelist callback
  -> Mediator re-runs post-analysis decision
```

If the Mediator repeatedly chooses `call_panelists` (e.g., each callback round surfaces a new gap), the callback loop has no stated budget in the post-analysis context. The formulation-phase callback budget (`max_mediator_callback_rounds = 3`, `max_callback_rounds_after_analysis = 2`) is defined in TODO3 Phase 3, which is deployed. But this plan introduces a new post-analysis flow with `call_panelists` as a first-class decision, and does not confirm whether the deployed budget applies or restate it here.

Add one line to Phase 8 or Phase 10:

```text
call_panelists is subject to the deployed max_callback_rounds_after_analysis = 2
budget. If exhausted without resolving the gap, Mediator must choose one of the
remaining four decisions.
```

---

### Minor 2 — `context_for_tool_consultant()` description does not mention `novel_analysis_design`

Phase 5 `context_for_tool_consultant()` lists what the context should include. Phase 2 establishes that `novel_analysis_design` must not be passed to ToolConsultant. But neither Phase 5 nor Phase 6 explicitly states that `novel_analysis_design` should be excluded from the ToolConsultant context.

Without an explicit exclusion, a ToolConsultant context builder that naively copies all fields from the active StateGraph node will include `novel_analysis_design` alongside `selected_research_plan`, potentially confusing ToolConsultant into treating it as part of the current executable plan.

Add to Phase 5 `context_for_tool_consultant()`:

```text
Do not include novel_analysis_design or future_research_directions in this
context. ToolConsultant receives only selected_research_plan for the current
execution.
```

---

## Summary

| Dimension | Status |
|---|---|
| Logical coherence | Clean — no conflicts |
| Terminology consistency | Consistent throughout |
| Evidence state construction and ownership | Fully specified |
| PaperJudge return rule migration | Explicitly stated |
| Post-analysis decision → graph outcome | Fully specified |
| `novel_analysis_design` sequencing | Fully specified |
| Blocker routing | Fully specified |
| Atomic cutover strategy | Correctly stated in Phase 1 and Phase 10 |
| `call_panelists` loop budget in post-analysis context | Not restated — minor gap |
| `novel_analysis_design` exclusion from ToolConsultant context | Not stated — minor gap |

The plan is ready to implement. Both remaining items are one-line additions and do not require rethinking any design.
