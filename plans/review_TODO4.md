# Plan Review: TODO4 — MediatorAgent and Research-Loop Architecture Cleanup (v20)

Reviewed: 2026-05-25

---

## Previous Issues — Status

| Issue | Status |
|---|---|
| `context_for_mediator_adversary_revision()` cannot supply `adversary_revision_round` or `max_adversary_revision_rounds` | **Fixed in v20**: Context Views call site (lines 382–386) now passes all three parameters; Task 13 schema list (line 1831) documents the full signature `context_for_mediator_adversary_revision(adversary_critique, adversary_revision_round, max_adversary_revision_rounds)`; view description note clarifies these are runtime orchestration state supplied by `ResearchLoop` |

---

## Overall Assessment

No open issues. The plan is coherent and fully specified across all tracked dimensions. All context builder signatures are complete, all output contracts are specified, all dispatch tables are fully enumerated, and the formulation-to-trajectory-commit boundary is unambiguous.

---

## Summary

| Dimension | Status |
|---|---|
| Logical coherence | Fully coherent |
| Ownership model | Fully specified |
| ResearchWorkspace + SessionDispatcher wiring | Fully specified |
| ResearchState persistence protocol | Fully specified |
| Three mode-specific Mediator context schemas | Fully specified — all builder signatures complete |
| Unified formulation output envelope | Fully specified |
| `post_analysis()` return schema and optionality | Fully specified |
| `trajectory_decision` dispatch tables | Fully specified for all paths |
| `unsalvageable` verdict dispatch (both paths) | Fully specified |
| Budget-exhaustion exit condition (both verdicts) | Fully specified |
| `call_panelists` orchestration removal | Fully specified |
| `MediatorAgent` panelist executor injection + `run_panelist_callback` | Fully specified |
| `rerun_intent` wired into ToolConsultant context | Fully specified |
| `AdversarialPanelist.run()` new signature | Fully specified |
| `context_for_adversary()` signature | Fully specified |
| `_run_formulation_stage()` return contract | Fully specified |
| Node schema `status` values | Fully specified |
| `context_for_mediator_adversary_revision()` loop counter parameters | Fully specified |

All tasks are ready for implementation.
