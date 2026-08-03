# Plan Review: TODO2 — RAG and Paper Retrieval Redesign (v3)

Reviewed: 2026-05-11

---

## Previous Issues — Status

| Issue | Status |
|---|---|
| `broad_discovery` not in `retrieval_goal` enum | Fixed: removed, only `prior_findings` listed as exception in Fix 7 |
| WikiCoverageScorer vs RetrievalCoverageJudge ambiguity | Fixed: Fix 5 explicitly delegates wiki sufficiency judgment to the panelist, no separate scorer component |
| RoleBoundaryChecker LLM cost | Addressed: component removed entirely; role boundaries enforced via prompt rules only |
| Prescriptive evidence conversion not attributed to a component | Fixed: Fix 13 explicitly assigns to Mediator |
| Deduplication location unspecified | Fixed: Fix 9 specifies deduplication inside `retrieve_literature` with merge priority rules |
| `judge_mode` ambiguity | Fixed: Fix 7 says not to include it unless multiple modes are actually implemented |

---

## Structural Improvements In This Version

The redesign is substantially cleaner:

- Evidence-pattern extraction (Fix 12) and plan-requirement conversion (Fix 13) are now two separate, clearly scoped fixes with their own field schemas.
- Owner responsibilities (Fix 14) provides an explicit component ownership table — this alone eliminates most attribution ambiguity from prior versions.
- Fix 5 simplifies the wiki-first flow by trusting panelist reasoning rather than adding a scoring component.
- The `panelist_assessment` block in Fix 11 correctly captures the panelist's own judgment alongside the retrieved evidence.
- Fix 15 illustrates the full evidence-pattern → plan-requirements → adversary-response chain with a concrete example.

---

## Remaining Issues

### Issue 1 — Wiki query scoping is unspecified (Fix 5)

Fix 5 says the panelist calls:

```text
traverse_paper_wiki(task_id)
get_related_papers(paper_id)
```

But neither the derivation of `task_id` nor the scope of what these calls return is defined here. Practical questions an implementer must answer:

- How is `task_id` determined from the user's question? Is it a stable key per biological question type, a session ID, or something else?
- Do these calls return full structured wiki entries (with evidence patterns, methods, findings) or only titles and summaries?
- On a large wiki with hundreds of papers, the panelist would receive a very large context. Is there a result limit? Is there role-based filtering (e.g., biologist only sees biologically-tagged entries)?

Without this, the wiki-first flow works well on a small wiki but degrades on a larger one. The fix should specify either: (a) what arguments gate the traversal query (task + role + retrieval_goal), or (b) a deliberate deferral: "wiki query scoping is out of scope for this redesign."

---

### Issue 2 — Retrieval evidence log trigger is unspecified (Fix 11)

Fix 11 says:

> After the panelist decides that a retrieval intent is satisfied, automatically log the retrieval result into short-term memory.

But "automatically" does not name a mechanism. Two viable options:

- **Option A**: The panelist explicitly calls a `log_retrieval_evidence(...)` tool after setting `enough_information: true`. The tool writes the structured JSON to short-term memory.
- **Option B**: The orchestrator detects `panelist_assessment.enough_information == true` in the panelist's structured output and triggers the write automatically.

Option A is simpler to implement and debug; Option B requires the orchestrator to inspect panelist outputs. The plan should pick one and state it.

---

### Issue 3 — `covered_evidence_patterns` values are not cross-referenced (Fix 7)

Fix 7 (PaperJudge output) includes:

```json
"covered_evidence_patterns": ["entity_definition", "comparison_design"]
```

The valid values for this list are never stated. Fix 12 defines the full evidence pattern schema with fields:

```text
claim_supported, entity_definition, comparison_design, statistical_unit,
effect_metric, controls_covariates, validation, boundary_conditions, analysis_used
```

Fix 7 should state explicitly:

```text
covered_evidence_patterns:
  A subset of the evidence pattern field names defined in Fix 12.
  Valid values: entity_definition, comparison_design, statistical_unit,
  effect_metric, controls_covariates, validation, boundary_conditions.
  (Excludes claim_supported and analysis_used, which are paper-level, not field-level assessments.)
```

Without this, implementers must infer the connection.

---

### Issue 4 — Mediator/Adversary ordering is not stated in Fix 13, and conflicts with TODO.md

Fix 13 says:

> Mediator owns the conversion from evidence patterns into plan requirements.
> AdversarialPanelist checks whether the proposed plan satisfies those requirements.

But the ordering is not specified. The adversary must receive the plan requirements before it can check the plan against them. And the Mediator can only convert evidence patterns after panelists have extracted them. The required order is:

```text
Panelists extract evidence patterns (Fix 12)
  -> Mediator converts to plan requirements (Fix 13)
  -> Mediator produces a draft plan
  -> AdversarialPanelist challenges the plan against requirements (Fix 13)
  -> Multi-round debate (defined in TODO.md Fix 10)
```

This ordering is not stated in Fix 13. Since TODO.md defines the adversary loop separately, Fix 13 should at minimum include a note pointing to that ordering:

```text
This conversion must complete before AdversarialPanelist runs.
See TODO.md Fix 10 for the multi-round adversary debate protocol.
```

---

### Issue 5 — Role boundary enforcement is now prompt-only (watchpoint, not blocker)

The previous version introduced a `RoleBoundaryChecker` component with structured input/output. This version deliberately removes it in favor of strong prompt rules ("A panelist cannot change hats"). The rationale is coherent — a full LLM call per retrieval intent added significant overhead.

However, role drift during multi-step LLM reasoning is a known failure mode. With no lightweight enforcement mechanism, the plan depends entirely on prompt compliance. This is not a design flaw at this stage, but it is a testing priority: when integrating panelists, role-crossing should be tested explicitly with adversarial prompts to confirm the strong-rule instructions hold.

If violations are observed during testing, a **rules-based compatibility matrix** (not an LLM call) is the recommended corrective:

```text
BiologistPanelist allowed goals:
  prior_findings, evidence_pattern, extension_opportunity, contradiction

StatisticianPanelist allowed goals:
  evidence_pattern, validation, contradiction

BioinformaticianPanelist allowed goals:
  method_selection, evidence_pattern, validation
```

This would add near-zero latency compared to an LLM-based checker.

---

### Issue 6 — Fix 15 example is incomplete on the retrieval side

Fix 15 shows the evidence-pattern → plan-requirements → adversary flow well. However, it does not show the retrieval calls that produced the evidence pattern. The previous version of this document had a detailed multi-intent retrieval example (Biologist 3 retrievals, Statistician 2, Bioinformatician 2). That example was removed.

The current Fix 15 starts from a pre-existing evidence pattern with no indication of how it was retrieved. This leaves the end-to-end flow incomplete as documentation. A complete example should show:

```text
1. Panelist reads wiki -> what was found / what was missing
2. Role-specific retrieval calls with retrieval_intent + retrieval_goal + base_query
3. PaperJudge output for a key paper (covered_evidence_patterns, missing_evidence)
4. Panelist assessment (enough_information, what_was_learned)
5. Evidence pattern extracted from the paper
6. Mediator conversion to plan requirements
7. Adversary response
```

Fix 15 currently shows steps 5–7 only. Steps 1–4 could be added as a brief sketch without needing full detail — even pseudocode would close the gap.

---

## Summary

| Dimension | Status |
|---|---|
| Logical coherence | Solid — no logical conflicts found |
| Component attribution | Good — Fix 14 ownership table resolves prior ambiguity |
| Implementation clarity | 3 gaps remain (wiki query scoping, log trigger mechanism, covered_evidence_patterns cross-reference) |
| Cross-document consistency | Fix 13 ordering should reference TODO.md adversary loop |
| Role enforcement | Deliberate prompt-only approach; flag for testing, not a blocker |
| Documentation completeness | Fix 15 example missing retrieval-side steps |

The plan is in good shape. All structural issues from prior rounds are resolved. The remaining issues are implementation-level details — none require rethinking the architecture.
