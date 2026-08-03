# Architecture Debug Report — Phases 1–3 Code Review

**Reviewed**: 2026-05-12  
**Scope**: TODO3.md Phases 1, 2, and 3 implementation in `prompts/panelist_prompts.py`, `agents/scientist_panel.py`, `agents/panelist_tools.py`  
**Test coverage**: `tests/test_scientist_panel_callbacks.py`, `tests/test_panelist_literature_tools.py`

---

# SCENIC+ Wiki Code Review

**Reviewed**: 2026-05-14  
**Scope**: Wiki nodes for SCENIC+ pipeline implementation  
**Implementation plan**: `plans/scenicplus_implementation.md`

Files reviewed:
- New: `wiki/packages/pycisTopic.md`, `pycistarget.md`, `scenicplus.md`
- New: `wiki/stages/topic_modeling.md`, `wiki/methods/enhancer_grn.md`
- New: `wiki/tools/atac_topic_pycisTopic.md`, `multi_grn_pycistarget.md`, `multi_grn_peak_to_gene.md`, `multi_grn_scenicplus.md`, `multi_grn_scenicplus_aucell.md`, `rna_grn_pyscenic_aucell.md`
- Updated: `wiki/stages/grn_inference.md`, `wiki/methods/coexpression_grn.md`, `wiki/packages/pyscenic.md`, `wiki/resources/pyscenic_databases.md`

---

## Package files

### `wiki/packages/pycisTopic.md`

Correct: `create_cistopic_object` requires regions × cells (transposed from AnnData), `model.topic_region` is topic × peak (must transpose for `varm`), model selection warnings.

**[PKG-1] Missing: `n_topics` wrapping requirement**  
The plan explicitly flags that `run_cgs_models()` requires `n_topics: list[int]` and will fail or produce wrong results if passed a bare int. Not mentioned. Users will hit a confusing error if they pass a single int directly to the internal call.

**[PKG-2] Missing: temp file path guidance**  
The plan notes Gibbs sampling writes large temp files and recommends using `save_path` for per-model saving. Not documented — users running large datasets may fill `/tmp` unexpectedly.

---

### `wiki/packages/pycistarget.md`

Correct: wrapper import path from `scenicplus.wrappers`, PyRanges conversion requirement, annotation_version mismatch warning, menr dict structure.

No issues.

---

### `wiki/packages/scenicplus.md`

Correct: all key function → module mappings, dill serialization requirement, Ray parallelism note, AUCell called twice.

No issues.

---

## Stage files

### `wiki/stages/topic_modeling.md`

**[STAGE-1] Missing output key: `pycisTopic_model_path`**  
The Outputs section lists 4 keys. The plan specifies 5:
```
adata.uns["pycisTopic_model_path"]   # Path to pickled best LDA model
```
The tool wiki (`atac_topic_pycisTopic.md`) lists all 5 correctly. The stage wiki is inconsistent.

---

### `wiki/stages/grn_inference.md` (updated)

The `enhancer_grn` edge is correctly added.

**[STAGE-2] Body text doesn't reference SCENIC+**  
The prose says "For ATAC or multi-omic: pySCENIC with ATAC peaks as cis-regulatory evidence, or SnapATAC2's integrated motif–gene linking." SCENIC+ is the primary multi-omic GRN method added in this implementation and should be mentioned here alongside pySCENIC.

**[STAGE-3] Pre-existing error: pycisTopic listed under footprinting**  
The body text lists "pycisTopic, HINT-ATAC" under the "Footprinting" evidence source. pycisTopic performs LDA topic modeling, not TF footprinting. HINT-ATAC is footprinting. pycisTopic belongs under a separate entry (topic modeling / chromatin accessibility decomposition) or should be removed from that list. This predates this implementation but is surfaced by this review.

---

## Method files

### `wiki/methods/enhancer_grn.md`

Correct: three evidence layers, eGRN vs pySCENIC table, pseudoreplication warning, output DataFrame spec.

**[METHOD-1] Missing column: `importance_x_abs_rho`**  
The plan's eRegulon metadata DataFrame spec lists:
```
importance_x_rho      float
importance_x_abs_rho  float   ← missing from wiki
importance            float
rho                   float
```
The wiki omits `importance_x_abs_rho`. This column is produced by `format_egrns()` and is important for ranking eRegulons by absolute strength regardless of direction.

---

### `wiki/methods/coexpression_grn.md` (updated)

The `rna_grn_pyscenic_aucell` edge is correctly added.

No issues.

---

## Tool files

### `wiki/tools/atac_topic_pycisTopic.md`

Frontmatter correct. All 5 output keys documented. Model selection behavior, memory guard, and prerequisite chain all correct.

No issues.

---

### `wiki/tools/multi_grn_pycistarget.md`

**[TOOL-1] `annotation_version: v9` default inconsistent with recommended usage**  
The frontmatter default is `v9` (matching the plan's implementation default) but the documentation immediately warns that `v10nr_clust` should be used with the standard preset. Most users will use the standard preset and will need to override this. Consider whether the default should be `v10nr_clust` or whether the param description should be even more prominent. As-is, users who copy the frontmatter defaults will run with the wrong annotation_version.

**[TOOL-2] Missing params: `dem_max_bg_regions`, `dem_motif_hit_thr` descriptions**  
Both params appear in the plan's signature and in the frontmatter but are not described in the params list section. `dem_motif_hit_thr` in particular (default 3.0) affects DEM sensitivity.

---

### `wiki/tools/multi_grn_peak_to_gene.md`

**[TOOL-3] `chromsizes_path` not listed as a param**  
The plan specifies `chromsizes_path: str | Path | None = None` as an explicit offline fallback parameter. The wiki mentions "provide `chromsizes_path` pointing to a UCSC .chrom.sizes file" under the Gene annotation section but does not list it in the params description. Users won't know the parameter name.

**[TOOL-4] `n_cpu` not listed in params description**  
`n_cpu: 4` appears in the frontmatter but is missing from the params description section.

---

### `wiki/tools/multi_grn_scenicplus.md`

**[TOOL-5] `rho_dichotomize_*` booleans not documented**  
The plan specifies three booleans that individually control the activating/repressing split for each link type:
```python
rho_dichotomize_tf2g: bool = True
rho_dichotomize_r2g: bool = True
rho_dichotomize_eregulon: bool = True
```
None appear in the frontmatter params or the params description. Users who want co-expression-only GRNs (no direction split) have no way to know these exist.

**[TOOL-6] `gsea_n_perm`, `quantiles`, `top_n_regionTogenes_per_gene` not described**  
All three are in the frontmatter params but absent from the params description section. `quantiles` and `top_n_regionTogenes_per_gene` are lists (non-scalar defaults) and need explanation — the plan describes their role in `build_grn()`.

**[TOOL-7] `"recompute"` sentinel not explained**  
Step 3 of the workflow says `coexpression_adj_path="recompute"` triggers internal recomputation using `calculate_TFs_to_genes_relationships()`. This sentinel value is not documented in the params section. Users reading only the params description will not know this string value triggers an alternate code path.

---

### `wiki/tools/multi_grn_scenicplus_aucell.md`

**[TOOL-8] `seed` param missing**  
The plan's frontmatter for this tool specifies:
```yaml
params:
  auc_threshold: 0.05
  seed: 42
  n_cpu: 4
```
The actual wiki has `n_cpu: 1` (changed from 4) and no `seed`. AUCell uses random ranking ties; `seed` is needed for reproducibility. Both the missing `seed` and the changed `n_cpu` default differ from the plan spec.

**[TOOL-9] `scplus_obj_key` and `eregulons_key` not documented**  
Both appear in the plan's tool signature but are not in the params description. Users can't change which uns keys the tool reads from.

---

## Updated files

### `wiki/packages/pyscenic.md` (updated)

AUCell section correctly added. Three-stage description and output key (`X_pyscenic_auc`, `pyscenic_auc_tf_names`) correctly described.

**[PKG-3] Filename inconsistency with `pyscenic_databases.md`**  
`pyscenic.md` describes a database file as `hg38_500bp_up_100bp_down_full_tx_v10_clust.genes_vs_motifs.rankings.feather` (v10 naming). `pyscenic_databases.md` lists the `hg38_refseq_500bp` alias as `hg38__refseq-r80__500bp_up_and_100bp_down_tss.mc9nr.feather` (v9/mc9nr naming). These are different files from different database versions. The two nodes disagree on what "the standard database" is. This predates this implementation.

---

### `wiki/resources/pyscenic_databases.md` (updated)

SCENIC+ compatibility note added. `annotation_version` warning added.

**[RES-1] `annotation_version='v10nr_clust'` advice conflicts with listed files**  
This is the most critical finding. The note says:
> "set `annotation_version='v10nr_clust'` to match the database version"

But the database files listed in this same resource all use `mc9nr` naming (e.g. `hg38__refseq-r80__10kb_up_and_down_tss.mc9nr.feather`). These are v9-era files, not v10nr_clust. If a user has only the files listed in this resource, setting `annotation_version='v10nr_clust'` would make `run_pycistarget()` use the wrong annotation lookup — the exact silent failure the warning is trying to prevent.

The note should be:
> "The `annotation_version` must match your actual database files. If you are using the files listed in this resource (`mc9nr` filenames), use `annotation_version='v9'`. If you have downloaded `v10nr_clust` files separately, use `annotation_version='v10nr_clust'`."

This may also reveal that the underlying resource needs to be updated to list v10nr_clust filenames if the system intends to use those for SCENIC+.

---

## Summary Table

| ID | File | Severity | Description |
|----|------|----------|-------------|
| RES-1 | pyscenic_databases.md | **Critical** | `annotation_version='v10nr_clust'` advice conflicts with `mc9nr` files actually listed |
| PKG-3 | pyscenic.md | Medium | Database filename inconsistency with pyscenic_databases.md (v10 vs mc9nr) |
| TOOL-8 | multi_grn_scenicplus_aucell.md | Medium | `seed` param missing; `n_cpu` default changed from plan spec |
| TOOL-5 | multi_grn_scenicplus.md | Medium | `rho_dichotomize_*` booleans not documented |
| TOOL-7 | multi_grn_scenicplus.md | Medium | `"recompute"` sentinel not explained |
| METHOD-1 | enhancer_grn.md | Medium | `importance_x_abs_rho` column missing from eRegulon metadata spec |
| STAGE-1 | topic_modeling.md | Low | Missing `pycisTopic_model_path` output key |
| STAGE-2 | grn_inference.md | Low | Body text doesn't mention SCENIC+ despite edge being added |
| STAGE-3 | grn_inference.md | Low | Pre-existing: pycisTopic incorrectly listed under footprinting |
| TOOL-1 | multi_grn_pycistarget.md | Low | `annotation_version: v9` default misleading; most users need v10nr_clust |
| TOOL-2 | multi_grn_pycistarget.md | Low | `dem_max_bg_regions`, `dem_motif_hit_thr` not described |
| TOOL-3 | multi_grn_peak_to_gene.md | Low | `chromsizes_path` not listed as a param |
| TOOL-4 | multi_grn_peak_to_gene.md | Low | `n_cpu` missing from params description |
| TOOL-6 | multi_grn_scenicplus.md | Low | `gsea_n_perm`, `quantiles`, `top_n_regionTogenes_per_gene` not described |
| TOOL-9 | multi_grn_scenicplus_aucell.md | Low | `scplus_obj_key`, `eregulons_key` not documented |
| PKG-1 | pycisTopic.md | Low | `n_topics` must be list — wrapping requirement not mentioned |
| PKG-2 | pycisTopic.md | Low | Temp file path guidance absent |

### Priority fixes

1. **RES-1** — Fix annotation_version advice: either clarify that mc9nr = v9 files → `annotation_version='v9'`, or update the resource to list v10nr_clust filenames if those are what the system actually uses. The current note gives incorrect guidance.
2. **TOOL-8** — Add `seed: 42` to `multi_grn_scenicplus_aucell.md` frontmatter.
3. **TOOL-5** — Document `rho_dichotomize_*` booleans in `multi_grn_scenicplus.md`.
4. **METHOD-1** — Add `importance_x_abs_rho` to `enhancer_grn.md` output spec.
5. **STAGE-1** — Add `pycisTopic_model_path` to `topic_modeling.md` outputs.

---

## Phase 1 — Prompt and Schema Contracts

### What was implemented

- `PANELIST_SHARED_SYSTEM`: "First establish the strongest existing solution path." instruction added. Three literature tool descriptions added (`search_paper_wiki`, `retrieve_literature`, `fetch_paper_content`). Evidence pattern framework and 5 negative instructions present.
- Round 1 panelist prompts (`BIOLOGIST_ROUND1_PROMPT`, `STATISTICIAN_ROUND1_PROMPT`, `BIOINFORMATICIAN_ROUND1_PROMPT`): all output `concrete_analysis_claim`, `existing_solution_path`, `extension_opportunities`, `evidence_patterns`, `retrieval_evidence`.
- `RECONCILER_PROMPT`: 4 conflict types (`biology_vs_statistics`, `biology_vs_computation`, `statistics_vs_computation`, `novelty`).
- `MEDIATOR_FORMULATION_PROMPT`: outputs `selected_research_plan`, `alternative_research_plans`, `mediator_decision` (`"accept" | "needs_panelist_callback"`), `callbacks` array, `plan_switch_policy`, `best_effort_claim`, `clarification_needed`, `literature_verdict`, `research_case`.
- `_normalize_research_plan_schema()` in `scientist_panel.py`: enforces all enum values, creates `research_plan` alias for `selected_research_plan`, enforces `clarification_needed` boolean, clamps `novelty_level` 0–5, derives `mediator_decision` from `callbacks` list presence.

### Issues

**[P1-1] `MEDIATOR_UPDATE_PROMPT` uses old action format**  
The update path mediator prompt still outputs `continue | pivot | done | abstain` rather than the new `mediator_decision` + `callbacks` schema. This is consistent with TODO3 deferring the update path to Phase 5, but it means `_normalize_research_plan_schema()` is called on update outputs that lack `selected_research_plan` and `alternative_research_plans`. The normalizer handles this gracefully by copying whatever `research_plan` exists, but the mismatch should be tracked explicitly.

Similarly `BIOLOGIST_UPDATE_PROMPT`, `STATISTICIAN_UPDATE_PROMPT`, `BIOINFORMATICIAN_UPDATE_PROMPT` do not include `evidence_patterns` or `retrieval_evidence` fields — consistent with Phase 5 deferral, but the update path panelists have no structured literature output.

**[P1-2] `_formulate_brief()` silently skips the callback loop**  
`_formulate_brief()` calls `_run_mediator_formulation()` and returns immediately. The Mediator prompt now includes a `callbacks` field, so the returned plan may contain `mediator_decision: "needs_panelist_callback"`. The brief path ignores this silently — no log line, no budget exhausted flag. If the Mediator requests callbacks, they are silently dropped.

Fix: either strip `callbacks` from the Mediator prompt variant used by `_formulate_brief()`, or add a guard that logs and sets `_callback_budget_exhausted = True` if callbacks are present but skipped.

**[P1-3] `_normalize_research_plan_schema()` does not validate `callbacks` entries**  
The normalizer enforces top-level fields but does not validate individual callback objects in the `callbacks` list. A callback missing `role`, `callback_type`, or `assigned_gap` reaches `_extract_callback_requests()` unguarded. `_extract_callback_requests()` calls `callback.get("role")` and filters unknown roles, so the immediate crash risk is low, but invalid entries are silently dropped without logging.

---

## Phase 2 — Panelist Literature Tools and Constrained PaperJudge

### What was implemented

- `build_panelist_tool_registry()` registers exactly `search_paper_wiki`, `retrieve_literature`, `fetch_paper_content`. Old tools (`query_paper_wiki`, `traverse_paper_wiki`, `get_related_papers`) are not registered (classes exist but unused).
- `_RETURN_TO_PANELIST_THRESHOLD = 0.60`, `_PERSIST_TO_WIKI_THRESHOLD = 0.75` constants defined.
- `RetrieveLiteratureTool.run()`: per-context seen-ID tracking via `self._contexts`; exclude list support; background wiki write for papers above persist threshold; `return_to_panelist` / `persist_to_wiki` flags on each paper.
- `SearchPaperWikiTool.run()`: queries `PaperIndex`, formats canonical summaries with `summary`, `objective`, `key_findings`, `analysis`, `limitations` fields.
- `FetchPaperContentTool.run()`: calls `retriever.fetch_paper_section()`, returns raw section text.

### Bugs

**[P2-1] Duplicate `"limitations"` key in `_compact_paper()`**  
`_compact_paper()` defines `"limitations"` twice in the same dict literal. Python silently uses the second definition. The first occurrence (around line 566) extracts `paper.get("limitations", [])` which is the correct field from the judged paper; the second occurrence (around line 578) appears to be a copy-paste remnant. The result is that the limitations field from the judged paper output is always discarded in favor of whatever the second assignment contains.

```python
# Current (broken) — two "limitations" keys:
return {
    ...
    "limitations": paper.get("limitations", []),   # line ~566 — DISCARDED
    ...
    "limitations": paper.get("study_limitations", []),  # line ~578 — wins
}

# Fix: remove the first occurrence and keep only the semantically correct one.
```

**[P2-2] Abstract-only confidence cap is absent**  
TODO3 specifies: papers with `full_text_status == "abstract_only"` should have their confidence capped at 0.70 before the return/persist thresholds are applied. This cap is not implemented in `_canonicalize_judged_paper()`. As a result, an abstract-only paper judged at 0.85 confidence would be both returned to the panelist and persisted to the wiki, contrary to the spec.

Fix:
```python
def _canonicalize_judged_paper(paper: dict) -> dict:
    confidence = paper.get("confidence", 0.0)
    if paper.get("full_text_status") == "abstract_only":
        confidence = min(confidence, 0.70)
    return_flag = confidence >= _RETURN_TO_PANELIST_THRESHOLD
    persist_flag = confidence >= _PERSIST_TO_WIKI_THRESHOLD
    ...
```

**[P2-3] `search_paper_wiki` `top_k` not enforced**  
The tool description states "maximum 10 results", but `SearchPaperWikiTool.run()` passes `top_k` directly to `paper_index.query_papers()` without capping it. If the LLM passes `top_k=50` the index will return up to 50 results.

Fix: `top_k = min(kwargs.get("top_k", 10), 10)` before calling `query_papers()`.

### Design gaps

**[P2-4] `PaperStore` abstraction not implemented**  
TODO3 specifies a `PaperStore` abstraction to unify wiki-read (`SearchPaperWikiTool`) and wiki-write (`paper_md_writer`) behind a single interface. The implementation uses the raw `PaperIndex` and `paper_md_writer` objects directly in the tool classes. This is functional but means tool classes are coupled to two separate storage interfaces. Deferrable to a later phase, but should be tracked.

**[P2-5] Session retrieval cache is in-memory only**  
`RetrieveLiteratureTool._contexts` is an instance variable dict. It is not persisted between ScientistPanel instantiations, so a second `formulate()` call on a new panel instance will re-fetch papers already seen in a prior session. TODO3 does not explicitly require disk persistence here, but the lack of durability means retrieval deduplication only works within a single Python process.

**[P2-6] Rejected papers not audited**  
Papers that fail the `_RETURN_TO_PANELIST_THRESHOLD` are silently dropped. They are not stored in the context cache (`self._contexts[retrieval_context_id]["seen_ids"]`), so the same rejected papers may be retrieved and rejected again on the next call with the same context ID.

Fix: add rejected paper IDs to `seen_ids` after judge filtering.

---

## Phase 3 — Mediator Callback Loop

### What was implemented

- `ScientistPanel.__init__()` accepts `max_mediator_callback_rounds=3`, `max_callbacks_per_round=3`, `max_callbacks_per_panelist_per_round=1`.
- `_run_mediator_callback_loop()`: iterates up to budget, calls `_extract_callback_requests()` → `_build_panelist_callback_context()` → `_run_panelist_callback()` → `_run_mediator_callback_synthesis()`. Sets `_callback_rounds`, `_callback_history`, `_callback_budget_exhausted` on result dict.
- `_extract_callback_requests()`: filters invalid roles, enforces `max_per_role`, enforces `max_callbacks` total.
- `_build_panelist_callback_context()`: six context keys — `original_task`, `panelist_state`, `cross_panel_state`, `mediated_state`, `adversarial_state`, `literature_state`. Explicitly excludes tool plans, implementation plans, artifact paths.
- Callback prompts: `PANELIST_REASONING_CALLBACK_PROMPT`, `PANELIST_LITERATURE_CALLBACK_PROMPT`, `MEDIATOR_CALLBACK_SYNTHESIS_PROMPT` all added. All contain required tags (`<CALLBACK>`, `<MEDIATOR>`).
- 5 tests in `test_scientist_panel_callbacks.py` cover: prompt tag presence, extraction limits, single-panelist dispatch, context exclusion of execution state, and round-limit enforcement.

### Issues

**[P3-1] `adversarial_state` in callback context is always empty**  
`_build_panelist_callback_context()` includes an `adversarial_state` key but populates it with empty fields (`critique: ""`, `adversarial_verdict: ""`). The adversarial panelist runs before the callback loop in `_formulate_full()`, so its output exists in the panel at callback time — but it is not threaded into the callback context builder. Panelists asked to do more reasoning during a callback have no visibility into what the adversarial panelist already challenged.

Fix: pass `adversarial_output` into `_build_panelist_callback_context()` and populate `adversarial_state` from it.

**[P3-2] `update()` path has no callback loop**  
`update()` calls `_run_mediator_update()` and returns its output directly. The Mediator update prompt still uses the old schema, so this is consistent for now. However, when Phase 5 upgrades the update Mediator schema to include `callbacks`, the `update()` path will silently drop them unless a callback loop is wired in. This should be a tracked TODO for Phase 5.

**[P3-3] `max_callback_rounds_after_analysis` not yet wired**  
TODO3 specifies a second callback budget (`max_callback_rounds_after_analysis=2`) that applies when the callback loop is triggered after the AnalyzerPanel in the ResearchLoop. `ScientistPanel.__init__()` does not accept this parameter; `ResearchLoop` does not pass a distinct budget when invoking the panel post-analysis. Deferred to Phase 5, but currently undocumented.

**[P3-4] `_callback_history` not exposed to Mediator synthesis prompt**  
`_run_mediator_callback_synthesis()` receives `callback_outputs` (the results of the current round's panelist callbacks) but not `callback_history` (the accumulated outputs from prior rounds). The Mediator synthesis prompt does not reference prior-round reasoning. If the loop runs 2 rounds, the round-2 Mediator synthesis cannot see what the round-1 panelist said.

Fix: include `callback_history` as a parameter to `_run_mediator_callback_synthesis()` and thread it into the prompt.

**[P3-5] Test coverage gap: `_formulate_brief()` callback bypass not tested**  
`test_scientist_panel_callbacks.py` tests the full callback loop via `_run_mediator_callback_loop()` directly. No test covers the scenario where the Mediator returns `mediator_decision: "needs_panelist_callback"` but `_formulate_brief()` silently ignores it (issue P1-2). This path is not tested and the silent drop is not flagged.

---

## Summary Table

| ID | Phase | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| P1-1 | 1 | Low | Deferred (Phase 5) | Update prompts use old action schema |
| P1-2 | 1 | Medium | Bug | `_formulate_brief()` silently drops callbacks |
| P1-3 | 1 | Low | Bug | `_normalize_research_plan_schema()` doesn't validate callback entries |
| P2-1 | 2 | High | Bug | Duplicate `"limitations"` key in `_compact_paper()` |
| P2-2 | 2 | High | Bug | Abstract-only confidence cap absent from `_canonicalize_judged_paper()` |
| P2-3 | 2 | Medium | Bug | `search_paper_wiki` top_k not capped at 10 |
| P2-4 | 2 | Low | Deferred | `PaperStore` abstraction not implemented |
| P2-5 | 2 | Low | Design gap | Session retrieval cache in-memory only |
| P2-6 | 2 | Medium | Bug | Rejected papers not added to seen_ids; may be re-fetched |
| P3-1 | 3 | Medium | Bug | `adversarial_state` in callback context always empty |
| P3-2 | 3 | Low | Deferred (Phase 5) | `update()` path has no callback loop |
| P3-3 | 3 | Low | Deferred (Phase 5) | `max_callback_rounds_after_analysis` not wired |
| P3-4 | 3 | Medium | Bug | `_callback_history` not passed to Mediator synthesis prompt |
| P3-5 | 3 | Medium | Test gap | No test for `_formulate_brief()` silent callback drop |

### Priority fixes before Phase 4

1. **P2-1** — Remove duplicate `"limitations"` key in `_compact_paper()`. One-line fix; silent data loss.
2. **P2-2** — Add abstract-only confidence cap in `_canonicalize_judged_paper()`. Affects wiki quality.
3. **P3-4** — Thread `callback_history` into `_run_mediator_callback_synthesis()`. Multi-round loops are broken without it.
4. **P2-6** — Add rejected paper IDs to `seen_ids` after judge filtering. Prevents redundant retrievals.
5. **P1-2** — Add guard in `_formulate_brief()` to log/flag silently dropped callbacks.

---

# Phases 4–6 Code Review

**Reviewed**: 2026-05-14  
**Scope**: TODO3.md Phases 4, 5, and 6 implementation  
**Files reviewed**:
- `agents/adversarial_panelist.py`, `prompts/adversarial_prompts.py` (Phase 4)
- `prompts/tool_consultant_prompts.py` (Phase 4)
- `prompts/analyzer_prompts.py` (Phase 5)
- `agents/research_loop.py` (Phases 4, 5, 6 integration)
- `agents/session_dispatcher.py` (Phase 4, 6 partial)
- `agents/session_recorder.py`, `agents/state_graph.py` (Phase 6, new files)
- `tests/test_research_loop_tool_alignment.py`, `tests/test_analyzer_phase_update.py`
- `tests/test_state_graph.py`, `tests/test_session_storage.py`

---

## Phase 4 — ToolConsultant + Adversarial Alignment Review

### What was implemented

- `AdversarialPanelist.review_alignment()`: calls `ADVERSARIAL_ALIGNMENT_PROMPT`, extracts `<ALIGNMENT_REVIEW>` block, normalizes via `_normalize_alignment_review()`.
- `_normalize_alignment_review()`: enforces `verdict` ∈ `{"survives", "needs_revision", "unsalvageable"}`, `failure_mode` ∈ 10-value set, `target` ∈ 5-value set.
- `ADVERSARIAL_ALIGNMENT_PROMPT`: structured prompt checking whether the executable plan satisfies the research plan's `evidence_requirements` and `steps`.
- `TOOL_CONSULTANT_OUTPUT_SCHEMA_PROMPT`: includes `output_retention_policy` array with `output_id`, `semantic_type`, `retention_intent`, `reason` fields.
- `ResearchLoop._review_and_maybe_revise_decision()`: runs alignment review after ToolConsultant; if `needs_revision` and tool-targeted, re-runs ToolConsultant with critique; runs second review; if `unsalvageable` on second pass → sets `execution_blocked=True`.
- `_alignment_targets_tool_revision()`: classifies whether critique should trigger ToolConsultant revision or research revision.
- 7 tests in `test_research_loop_tool_alignment.py`.

### Issues

**[P4-1] `ADVERSARIAL_REMEDIATOR_PROMPT` uses legacy Phase 1 schema**  
`prompts/adversarial_prompts.py` (lines ~291–341): `ADVERSARIAL_REMEDIATOR_PROMPT` asks the model to output `<MEDIATOR>` with fields `consensus_hypothesis` and `research_plan.steps`. The Phase 1 Mediator output schema uses `selected_research_plan` and `alternative_research_plans`, not `consensus_hypothesis`. The remediator prompt was never updated to match the final schema. Any response parsed through `_normalize_research_plan_schema()` will produce a plan with `selected_research_plan = None` because the key doesn't exist in the prompt's output block.

Fix: Update `ADVERSARIAL_REMEDIATOR_PROMPT` `<MEDIATOR>` block to use `selected_research_plan` / `alternative_research_plans` / `mediator_decision` / `callbacks` — matching `MEDIATOR_FORMULATION_PROMPT`'s output schema.

**[P4-2] Alignment review not wired into `SessionDispatcher.execute_task()`**  
`agents/session_dispatcher.py` (lines ~257–387): `execute_task()` and `_execute_composable_task()` build a `ToolConsultantDecision` and run the DAG executor with no alignment review step. Only `ResearchLoop` (via `_handle_research_task()`) runs Phase 4. Operational tasks — which also call ToolConsultant — bypass adversarial alignment entirely. If `SessionDispatcher` is intended to be the single entry point for operational execution, it should either call the alignment reviewer or delegate to `ResearchLoop` for all ToolConsultant-dependent execution.

**[P4-3] `_alignment_targets_tool_revision()` routes `missing_analysis` to ToolConsultant — wrong ownership**  
`agents/research_loop.py` (lines ~969–974): `_alignment_targets_tool_revision()` returns `True` when `failure_mode in {"missing_analysis", "tool_mismatch", "retention_gap"}`. But `missing_analysis` means the research plan itself is missing an analysis step — the ToolConsultant cannot add an analysis step that isn't in the research plan. Routing this to ToolConsultant revision gives ToolConsultant authority to expand the analysis scope beyond what the Mediator selected, violating the ownership boundary. `missing_analysis` should route to research-level revision (i.e., escalate back to the Mediator/ResearchLoop's outer loop), not ToolConsultant re-execution.

Fix: Remove `missing_analysis` from the tool-revision routing set. Treat it the same as `weak_evidence` or `overclaim` — research-level issues that require Mediator intervention, not ToolConsultant revision.

**[P4-4] Second alignment review does not hard-block on `needs_revision`**  
`agents/research_loop.py` (lines ~673–695): after the revised ToolConsultant plan, a second alignment review runs. The code hard-blocks (`execution_blocked=True`) only if the second verdict is `unsalvageable`. If the second verdict is still `needs_revision`, execution proceeds silently. This means a plan that fails alignment twice — but not catastrophically — continues to execution with known problems. The spec does not explicitly state what should happen on repeated `needs_revision`, but proceeding silently is inconsistent with the intent of the second review pass.

Consider: log a warning and record the unresolved critique in `session_state` rather than proceeding silently.

**[P4-5] Missing two tests from spec**  
`test_research_loop_tool_alignment.py` has 7 tests. TODO3 Phase 4 specifies at least 2 additional scenarios that are not covered:
- `test_alignment_review_detects_missing_downstream_analysis`: verifies `failure_mode == "missing_analysis"` when the DAG plan omits a step the research plan requires.
- `test_alignment_review_detects_cell_level_test_for_sample_level_claim`: verifies `failure_mode == "invalid_statistical_unit"` when the tool plan uses cell-level testing for a sample-level biological claim.

---

## Phase 5 — Analyzer-Driven Phase Update Schema

### What was implemented

- `ANALYZER_MEDIATOR_PROMPT`: outputs `evidence_requirement_status` (per-requirement with `status`, `evidence_summary`, all `linked_*` fields nullable), `result_verdict`, `problem_localization` (`problem_stage`, `problem_type`, `affected_steps`, `affected_outputs`, `nearest_valid_artifact_before_problem`, `reuse_upstream_possible`), `recommended_plan_changes`, `future_directions`, `improvements`.
- `ScientistPanel.decide_after_analysis()`: Mediator post-analysis prompt with 14 `decision_type` values.
- `ResearchLoop._decide_after_analysis()`: calls `scientist_panel.decide_after_analysis()` if present; fallback for old panels.
- Post-analysis callback handling (lines ~342–364): if `decision_type == "ask_panelist_callback"` → runs `run_post_analysis_callbacks()` → re-calls `_decide_after_analysis()` once.
- Panel update handling (lines ~376–398): if `decision_type == "start_panel_update_round"` → calls `scientist_panel.update()` once.
- 4 tests in `test_analyzer_phase_update.py`.

### Issues

**[P5-1] `_decide_after_analysis()` fallback unconditionally triggers full update for legacy panels**  
`agents/research_loop.py` (lines ~586–623): the fallback branch (when `scientist_panel` lacks `decide_after_analysis`) returns `{"decision_type": "start_panel_update_round"}`. This means any panel without Phase 5 support will unconditionally run a full panel update after every analysis, regardless of whether the result warrants it. This is the opposite of the Phase 5 intent, which makes the full update an explicit choice. Legacy panels in tests or earlier pipeline modes will silently over-run the update path.

Fix: change the fallback to `{"decision_type": "conclude"}` (or `"interpretation_only"`) as the conservative default. If a panel update is needed, require explicit opt-in via `decide_after_analysis()`.

**[P5-2] `max_callback_rounds_after_analysis=2` is not looped — only 1 callback round runs**  
`agents/research_loop.py` (lines ~342–364): the post-analysis callback block calls `run_post_analysis_callbacks()` once and then re-calls `_decide_after_analysis()` once. There is no loop. If the re-decision is again `ask_panelist_callback`, it is ignored. TODO3 specifies `max_callback_rounds_after_analysis=2` to allow a second round if the first callback does not resolve the question. The second round is silently dropped.

Fix: wrap the callback block in a loop capped at `max_callback_rounds_after_analysis`, breaking when `decision_type != "ask_panelist_callback"`.

**[P5-3] `trajectory_context()` returns `{}` when `state_graph_manager` is absent on first call**  
`agents/research_loop.py` (lines ~163–192 and the Mediator call sites): `trajectory_context()` is called on `self.state_graph_manager` to provide the Mediator with tried/untried plan context. When `state_graph_manager` is `None` (e.g., in tests or first-run conditions), the loop falls back to returning `{}`. A Mediator receiving an empty trajectory context treats every run as the first attempt, even if prior state exists in memory. The issue is not critical on a true first call, but the `None` guard is used as a general fallback rather than a narrowly guarded case for initialization.

**[P5-4] Missing 5 tests from spec**  
TODO3 Phase 5 specifies test scenarios not present in `test_analyzer_phase_update.py`:
- `test_post_analysis_decision_routes_parameter_change_correctly`: verifies `parameter_change` adds to `repeat_iterations` in StateGraph without creating a new node.
- `test_post_analysis_decision_routes_revise_plan_correctly`: verifies `revise_plan` creates a new StateGraph branch.
- `test_post_analysis_decision_routes_declare_unanswerable`: verifies terminal state.
- `test_max_callback_rounds_after_analysis_enforced`: verifies the loop stops at `max_callback_rounds_after_analysis`.
- `test_trajectory_context_injected_into_mediator_call`: verifies the Mediator post-analysis call receives `state_graph_context` with the correct `active_node`.

---

## Phase 6 — Session Storage and StateGraph

### What was implemented

- `SessionRecorder` (new file, 180 lines): owns directory layout creation, `session.json`, `conversation.json`, `progress.jsonl`, `start_turn()`, `save_json()`, `save_text()`, `append_progress()`.
- `StateGraphManager` (new file, 441 lines): `state_graph.json`, node creation, `initialize_research_plan()`, `create_branch_from_decision()`, `apply_post_analysis_decision()`, `trajectory_context()`, `_validate_one_active()`.
- `ResearchLoop.run()`: Phase 6 recorder/graph calls wired throughout — turn start, plan node creation, tool plan attachment, execution reference, analyzer attachment, decision reference, conclusion.
- 4 tests in `test_state_graph.py`, 1 integration test in `test_session_storage.py`.

### Issues

**[P6-1] `ConversationManager` class is absent**  
TODO3 Phase 6 specifies a two-class split: `ConversationManager` owns the `conversations/{conversation_id}/` root (one object per conversation, persists across sessions) and `SessionRecorder` owns the `sessions/{session_id}/` subtree. The implementation collapses both into `SessionRecorder`. A single `SessionRecorder` object creates both the conversation root and the session subtree, handling `conversation.json` and `session.json` in the same `__init__`. This makes it impossible to resume an existing conversation with a new session without re-creating the conversation directory from scratch.

**[P6-2] `SessionDispatcher` not integrated with `SessionRecorder`**  
`agents/session_dispatcher.py` (line ~41): `self.feedback_dir = self.result_dir / "feedback"` — the old layout is still used for operational tasks. Only `ResearchLoop` writes to the `SessionRecorder` directory structure. `execute_task()` / `_execute_composable_task()` write results directly to `self.result_dir` without going through `SessionRecorder`. The two layouts will coexist until `SessionDispatcher` is updated, making session directory contents inconsistent between discovery and operational runs.

**[P6-3] `_compact_active()` stores a file path in `latest_analyzer_verdict`**  
`agents/state_graph.py` (lines ~429–436): `_compact_active()` sets `latest_analyzer_verdict` to `node.get("analyzer_report_path")` — a string file path like `"nodes/plan_001/analyzer_report.json"`. The Mediator receives this path and has no way to read the file it points to (the Mediator is a language model, not a file system client). The field name implies a verdict value (e.g., `"supported"` or `"insufficient"`), not a path. The Mediator in `decide_after_analysis()` would misinterpret a path string as a verdict label.

Fix: populate `latest_analyzer_verdict` from the parsed analyzer report's `result_verdict` field, not the file path. Store the file path separately as `analyzer_report_path` (it is already on the node for reference).

**[P6-4] `reusable_artifacts` and `unresolved_gaps` always empty in `trajectory_context()`**  
`agents/state_graph.py` (lines ~319–325): `trajectory_context()` always returns `"reusable_artifacts": []` and `"unresolved_gaps": []`. The spec defers artifact linking to Phase 8, so the empty lists are expected. However, this is undocumented — a future developer reading the code has no indication these are intentional stubs vs. implementation oversights. Add a comment marking these as Phase 8 deferred stubs.

**[P6-5] `leaderboard.json` not written**  
TODO3 Phase 6 specifies a `leaderboard.json` file at the conversation level that tracks per-node quality metrics across sessions. `SessionRecorder` does not write or update this file. The spec lists it as part of the conversation-level layout (alongside `conversation.json`). This may be intentionally deferred, but it is not marked as deferred in code or comments.

**[P6-6] `initialize_research_plan()` idempotency guard swallows re-initialization silently**  
`agents/state_graph.py` (lines ~37–39): if `graph["active_node_id"]` is already set, `initialize_research_plan()` returns the existing node ID without writing anything. This is correct idempotency behavior, but it also means a second call with a different `selected_plan` or `alternatives` silently does nothing. If `ResearchLoop` calls `initialize_research_plan()` twice (e.g., due to a retry), the second plan is discarded without any log or error. Add a warning log when the early-return guard fires with a non-matching plan.

**[P6-7] Missing 11 tests from spec**  
TODO3 Phase 6 specifies test scenarios beyond the current 5 (4 unit + 1 integration):
- `test_session_recorder_append_progress_creates_jsonl`: verifies `progress.jsonl` format and event fields.
- `test_session_recorder_save_returns_relative_path`: verifies `save_json()` returns path relative to session root.
- `test_state_graph_attach_execution_deduplicates_refs`: verifies `attach_execution()` does not duplicate refs.
- `test_state_graph_trajectory_returns_tried_plans_in_order`: verifies `tried_solutions` ordering.
- `test_state_graph_branch_creates_edge_with_transition_reason`: verifies edge `transition_reason` field.
- `test_state_graph_apply_ask_user_clarification_sets_awaiting`: verifies `awaiting_user` status.
- `test_state_graph_apply_parameter_change_adds_iteration`: verifies `repeat_iterations` accumulation.
- `test_state_graph_materially_different_plan_same_steps_no_branch`: verifies no branch created when steps are identical.
- `test_research_loop_writes_execution_to_state_graph`: verifies `exec_001` appears in `execution_refs` on node.
- `test_research_loop_writes_plan_node_before_tool_consultant`: verifies StateGraph node exists before ToolConsultant is called (ordering guarantee).
- `test_research_loop_trajectory_context_passed_to_mediator`: verifies `state_graph_context` in post-analysis Mediator call contains correct `active_node`.

---

## Summary Table

| ID | Phase | File | Severity | Description |
|----|-------|------|----------|-------------|
| P4-1 | 4 | adversarial_prompts.py | **High** | `ADVERSARIAL_REMEDIATOR_PROMPT` uses legacy `consensus_hypothesis` schema; `selected_research_plan` always `None` after parse |
| P4-3 | 4 | research_loop.py | **High** | `missing_analysis` routed to ToolConsultant revision — wrong ownership; ToolConsultant cannot add research steps |
| P5-1 | 5 | research_loop.py | **High** | Legacy panel fallback unconditionally triggers full update; should default to `conclude` |
| P5-2 | 5 | research_loop.py | **High** | Post-analysis callback loop not looped — only 1 round runs despite `max=2` spec |
| P6-3 | 6 | state_graph.py | **High** | `_compact_active()` sets `latest_analyzer_verdict` to a file path string — Mediator receives path instead of verdict label |
| P4-2 | 4 | session_dispatcher.py | Medium | Alignment review not wired into `execute_task()` — operational tasks bypass Phase 4 |
| P4-4 | 4 | research_loop.py | Medium | Second alignment review does not hard-block on repeated `needs_revision` — proceeds silently |
| P4-5 | 4 | tests/ | Medium | 2 alignment review test scenarios missing from spec |
| P5-3 | 5 | research_loop.py | Medium | `trajectory_context()` returns `{}` when `state_graph_manager` is `None` — over-broad fallback |
| P5-4 | 5 | tests/ | Medium | 5 post-analysis decision test scenarios missing from spec |
| P6-1 | 6 | session_recorder.py | Medium | `ConversationManager` class absent — conversation/session split collapsed into `SessionRecorder` |
| P6-2 | 6 | session_dispatcher.py | Medium | `SessionDispatcher` still uses old `feedback_dir` layout — operational runs bypass `SessionRecorder` |
| P6-5 | 6 | session_recorder.py | Medium | `leaderboard.json` not written — no per-node quality tracking across sessions |
| P6-7 | 6 | tests/ | Medium | 11 StateGraph and session storage test scenarios missing from spec |
| P6-4 | 6 | state_graph.py | Low | `reusable_artifacts` and `unresolved_gaps` always `[]` — Phase 8 stubs undocumented |
| P6-6 | 6 | state_graph.py | Low | `initialize_research_plan()` idempotency guard silently discards re-initialization with different plan |

### Priority fixes before Phase 7

1. **P4-1** — Update `ADVERSARIAL_REMEDIATOR_PROMPT` to use `selected_research_plan` / `alternative_research_plans` schema. Current schema produces a `None` plan after normalization — any remediator call is silently broken.
2. **P4-3** — Remove `missing_analysis` from `_alignment_targets_tool_revision()`. Route it as a research-level escalation, not a ToolConsultant re-run.
3. **P5-1** — Change `_decide_after_analysis()` fallback from `start_panel_update_round` to `conclude`. Legacy panels should not unconditionally trigger a full update.
4. **P5-2** — Wrap the post-analysis callback block in a loop capped at `max_callback_rounds_after_analysis`. Currently only 1 of 2 permitted rounds runs.
5. **P6-3** — Fix `_compact_active()` to populate `latest_analyzer_verdict` from the parsed `result_verdict` string, not the `analyzer_report_path` file path.

---

# Phases 1–6 Re-Review (Post-Correction)

**Reviewed**: 2026-05-14  
**Scope**: Full re-read of all Phase 1–6 files after user corrections.

Files re-read:
- `agents/scientist_panel.py`, `agents/panelist_tools.py`, `prompts/panelist_prompts.py` (Phases 1–3)
- `agents/adversarial_panelist.py`, `prompts/adversarial_prompts.py`, `prompts/tool_consultant_prompts.py` (Phase 4)
- `prompts/analyzer_prompts.py` (Phase 5)
- `agents/research_loop.py`, `agents/session_dispatcher.py`, `agents/session_recorder.py`, `agents/state_graph.py` (Phases 4–6)
- `tests/test_research_loop_tool_alignment.py`, `tests/test_analyzer_phase_update.py`, `tests/test_state_graph.py`, `tests/test_session_storage.py`

---

## What Was Fixed

**Phase 1:**

- **P1-2 FIXED** — `_formulate_brief()` no longer silently drops callbacks. Now calls `_mark_callbacks_skipped()` which sets `_callbacks_skipped=True`, `_callback_budget_exhausted=True`, and `_callback_skip_reason` on the returned plan. Same for `_formulate_lightweight()`. Callbacks are recorded, not discarded.
- **P1-3 FIXED** — `_normalize_callbacks()` now validates each callback entry for `role ∈ _ROLES`, `callback_type ∈ {ask_panelist_for_more_reasoning, ask_panelist_for_more_literature}`, and non-empty `assigned_gap`. Invalid entries go into `_invalid_callbacks` instead of being silently dropped.

**Phase 2:**

- **P2-1 FIXED** — `_compact_paper()` (panelist_tools.py line ~575) now has exactly one `"limitations"` key: `sections.get("limitations", "")`. The duplicate is gone.
- **P2-2 FIXED** — `_canonicalize_judged_paper()` caps `confidence = min(confidence, 0.70)` for `full_text_status == "abstract_only"` papers. The cap is correctly exempted for `retrieval_goal == "broad_background"`.
- **P2-3 FIXED** — `SearchPaperWikiTool.run()` now uses `limit = _clamped_int(top_k, default=5, lower=1, upper=10)`. The 10-result cap is enforced.
- **P2-6 FIXED** — `_record_seen()` is called on all fresh papers (line ~197) before the `exclude_keys` filter is applied. Rejected papers are now added to `seen_ids` and will not be re-fetched in the same context.

**Phase 3:**

- **P3-3 FIXED** — `ScientistPanel.__init__()` now accepts `max_callback_rounds_after_analysis: int = 2`. `run_post_analysis_callbacks()` passes `max_rounds=self.max_callback_rounds_after_analysis` to `_run_mediator_callback_loop()`.
- **P3-4 FIXED** — `_run_mediator_callback_synthesis()` now takes a `callback_history` parameter (line ~844). The loop in `_run_mediator_callback_loop` passes `callback_history=callback_history` at each synthesis call. Round-N Mediator synthesis can now see round-1…N-1 outputs.

**Phase 4:**

- **P4-1 FIXED** — `ADVERSARIAL_REMEDIATOR_PROMPT` now uses `selected_research_plan` / `alternative_research_plans` / `mediator_decision` / `callbacks` schema. `consensus_hypothesis` removed. Test `test_adversarial_remediator_prompt_uses_phase1_research_plan_schema` added and passes.
- **P4-3 FIXED** — `_alignment_targets_tool_revision()` (research_loop.py line ~986–991): `missing_analysis` removed from the failure-mode routing set. Only `tool_mismatch` and `retention_gap` route to ToolConsultant revision. Test verifies `("research_plan", "missing_analysis")` returns `False`.
- **P4-4 FIXED** — `_review_and_maybe_revise_decision()` line ~697 now blocks execution on both `needs_revision` and `unsalvageable` for the second review pass: `if second_review.get("verdict") in {"needs_revision", "unsalvageable"}`. New test `test_second_alignment_review_needs_revision_blocks_execution` passes.

**Phase 5:**

- **P5-1 FIXED** — `_decide_after_analysis()` fallback (research_loop.py line ~622–631) now returns `{"decision_type": "conclude", "rationale": "ScientistPanel does not expose decide_after_analysis; conservatively concluding ..."}`. Legacy panels no longer trigger an unconditional full update. Test `test_legacy_panel_post_analysis_fallback_concludes_without_update` passes.
- **P5-2 FIXED** — Post-analysis callback handling is now a `while` loop bounded by `_after_analysis_callback_limit(self.scientist_panel)` (research_loop.py lines ~342–373). Two-round budget is enforced. Test `test_post_analysis_callbacks_can_run_two_bounded_rounds` verifies two callback rounds run and two redecisions fire.

---

## Remaining Issues

### Phase 1

**[P1-1] `MEDIATOR_UPDATE_PROMPT` still uses old action schema — deferred, acknowledged**  
`MEDIATOR_UPDATE_PROMPT` (panelist_prompts.py lines ~1198–1269) outputs `"next_action": "continue | pivot | done | abstain"` with a `research_plan` key — not the new `decision_type` / `selected_research_plan` schema. This is a documented Phase 5 deferral. However, when `start_panel_update_round` fires and calls `scientist_panel.update()`, the research_loop uses `update_result.get("research_plan")` (line ~396) — the key matches the old schema, so the update path works correctly end-to-end for now. No immediate breakage, but the schema mismatch will accumulate as a debt once the update prompts are migrated.

---

### Phase 2

**[P2-4] `PaperStore` abstraction not implemented — deferred**  
Still no unified abstraction. Tools use raw `PaperIndex` and `paper_md_writer` directly.

**[P2-5] Session retrieval cache in-memory only**  
`RetrieveLiteratureTool._contexts` remains an instance-level dict. Deduplication does not survive across ScientistPanel instantiations.

---

### Phase 3

**[P3-1] `adversarial_state` in callback context still populated from callback fields, not adversarial output**  
`_build_panelist_callback_context()` (scientist_panel.py lines ~793–796):
```python
"adversarial_state": {
    "critique_summary": callback.get("critique_summary", ""),
    "critique_target": callback.get("critique_target", ""),
    "failure_mode": callback.get("failure_mode", ""),
    "required_revision": callback.get("required_revision", ""),
},
```
Standard callback objects from `_extract_callback_requests()` carry `role`, `callback_type`, `callback_source`, `assigned_gap`, `why_needed`, `expected_output` — none of the adversarial fields. So `adversarial_state` will always be all-empty strings. The adversarial panelist result is not stored on the panel after `_run_adversarial_loop()` and therefore cannot be threaded in. Panelists doing post-analysis callbacks have no visibility into prior adversarial critique.

Fix: store `adv_result` on `self` after `_run_adversarial_loop()`, then pass it into `_build_panelist_callback_context()`.

**[P3-2] `update()` path has no callback loop — deferred**  
`update()` calls `_run_round1_update()` + `_run_mediator_update()` and returns directly. `MEDIATOR_UPDATE_PROMPT` uses the old `continue | pivot | done | abstain` schema. When Phase 5 migrates the update Mediator, any `callbacks` the updated Mediator requests will be dropped.

**[P3-5] No test for `_formulate_brief()` / `_formulate_lightweight()` explicit callback skip**  
`_mark_callbacks_skipped()` is now called and sets explicit flags, which is correct. But no test verifies that a Mediator returning `"mediator_decision": "needs_panelist_callback"` via the brief path results in `_callbacks_skipped=True` and `_skipped_callbacks` being populated. The behavioral change is correct; the test coverage is still absent.

---

### Phase 4

**[P4-2] Alignment review not wired into `SessionDispatcher.execute_task()`**  
`session_dispatcher.py` (lines ~257–387): `execute_task()` and `_execute_composable_task()` call ToolConsultant and run the DAG without any alignment review. Only `ResearchLoop` (via `_handle_research_task()`) applies Phase 4. Operational task paths receive no adversarial alignment check.

**[P4-5] Two spec-mandated test scenarios still missing**  
`test_research_loop_tool_alignment.py` now has 8 tests (3 new: schema validation, `needs_revision` block, normalizer default). The following two spec scenarios remain absent:
- `test_alignment_review_detects_missing_downstream_analysis`: `failure_mode == "missing_analysis"` when DAG plan omits a required research step.
- `test_alignment_review_detects_cell_level_test_for_sample_level_claim`: `failure_mode == "invalid_statistical_unit"` when cell-level testing is used for a sample-level claim.

---

### Phase 5

**[P5-4] Two spec-mandated test scenarios still missing**  
`test_analyzer_phase_update.py` now has 7 tests (3 new: two-round callbacks, legacy fallback concludes, trajectory context injected). Still missing:
- `test_post_analysis_decision_routes_parameter_change_correctly`: `parameter_change` adds to `repeat_iterations` in StateGraph without creating a new node.
- `test_post_analysis_decision_routes_revise_plan_correctly`: `revise_plan` / `produce_next_research_plan` creates a new StateGraph branch.

---

### Phase 6

**[P6-1] `ConversationManager` class still absent**  
`SessionRecorder` still handles both conversation root (`conversation.json`, `conversations/{id}/`) and session subtree (`sessions/{id}/`). The two-class split from the spec (`ConversationManager` + `SessionRecorder`) is not implemented. Resuming an existing conversation with a new session still requires re-creating the session dir from scratch.

**[P6-2] `SessionDispatcher` still uses old layout for operational tasks**  
`session_dispatcher.py` line ~41: `self.feedback_dir = self.result_dir / "feedback"`. `execute_task()` writes to `feedback_dir / f"{session_tag}_task_execution.json"` and `_handle_research_task()` writes to `feedback_dir / f"{session_tag}_research_task.json"`. Neither uses `SessionRecorder`. Operational and research task output directories diverge.

**[P6-3] `_compact_active()` still stores a file path in `latest_analyzer_verdict`**  
`agents/state_graph.py` (lines ~429–436):
```python
def _compact_active(node: dict[str, Any]) -> dict[str, Any]:
    return {
        ...
        "latest_analyzer_verdict": node.get("analyzer_report_path"),   # ← BUG: file path string
        ...
    }
```
`analyzer_report_path` is a relative file path like `"nodes/plan_001/analyzer_report.json"`. The Mediator's `decide_after_analysis()` receives this in `state_graph_context["active_node"]["latest_analyzer_verdict"]` and would interpret a path string as a verdict label. The Analyzer's `result_verdict` field (a value like `"supported"`) is what should go here.

Fix: read `node.get("analyzer_refs", {}).get("result_verdict")` (if stored) or derive from the attached report, not the path.

**[P6-4] `reusable_artifacts` and `unresolved_gaps` stubs undocumented**  
`trajectory_context()` still returns `"reusable_artifacts": []` and `"unresolved_gaps": []` with no code comment marking these as Phase 8 deferred stubs.

**[P6-5] `leaderboard.json` not written**  
Spec requires a `leaderboard.json` at the conversation level tracking per-node quality metrics. Neither `SessionRecorder._ensure_metadata()` nor any other path writes this file.

**[P6-6] `initialize_research_plan()` idempotency guard still silent**  
`state_graph.py` lines ~37–39: early return when `active_node_id` is already set is still silent. No log or warning emitted when a second call with different plan content is discarded.

**[P6-7] 11 spec-mandated StateGraph and session storage tests still missing**  
`test_state_graph.py` and `test_session_storage.py` are unchanged from the initial implementation. All 11 scenarios remain absent (see Phase 6 section above for the full list).

---

## New Findings

**[NEW-1] `_normalize_post_analysis_decision()` defaults invalid `decision_type` to `start_panel_update_round`**  
`scientist_panel.py` (line ~1254–1258):
```python
out["decision_type"] = _enum_or_default(
    out.get("decision_type"),
    allowed=_POST_ANALYSIS_DECISIONS,
    default="start_panel_update_round",
)
```
If the LLM returns a garbled or unrecognized `decision_type`, the normalizer silently defaults to `start_panel_update_round`, triggering a full panel update. This is the opposite of the conservative-default intent behind P5-1. The fallback in `_decide_after_analysis()` was correctly changed to `conclude`, but the normalizer default was not. A malformed LLM response will still trigger an expensive full update.

Fix: change the `_enum_or_default` default to `"conclude"` to match the conservative intent of P5-1.

**[NEW-2] Abstract-only confidence cap exempts `broad_background` — undocumented spec extension**  
`_canonicalize_judged_paper()` (panelist_tools.py lines ~631–633):
```python
if full_text_status == "abstract_only" and retrieval_goal != "broad_background":
    confidence = min(confidence, 0.70)
```
The `broad_background` exemption is defensible (background context is less sensitive to full-text status) but is not in the TODO3 spec. It means an abstract-only paper retrieved for background context can exceed the 0.70 cap and be persisted to the wiki at full confidence. This should be explicitly documented as an intentional design decision.

**[NEW-3] `_build_panelist_callback_context()` adversarial fields are always empty**  
Related to P3-1 but worth clarifying: the four adversarial fields (`critique_summary`, `critique_target`, `failure_mode`, `required_revision`) are read from the `callback` dict (line ~793–796). These keys do not exist on any callback produced by `_extract_callback_requests()` or `_normalize_callbacks()`. They will always be empty strings regardless of whether an adversarial review was run. The code silently provides an empty adversarial_state to all callbacks.

**[NEW-4] `run_post_analysis_callbacks()` builds `current_plan` without `user_question`**  
`run_post_analysis_callbacks()` (scientist_panel.py lines ~495–514): `current_plan` is built from `research_context` only and does not include `user_question`. The `_build_panelist_callback_context()` uses `user_question` as a top-level parameter (passed separately), so this does not cause a crash. However, `current_plan` passed to the callback loop lacks some fields that would allow the Mediator to assess plan completeness accurately (e.g., `concrete_analysis_claim`).

---

## Updated Summary Table

| ID | Phase | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| P1-1 | 1 | Low | Deferred | Update prompts use old `continue | pivot | done | abstain` schema |
| P1-2 | 1 | Medium | **FIXED** | `_formulate_brief()` / `_formulate_lightweight()` now use `_mark_callbacks_skipped()` |
| P1-3 | 1 | Low | **FIXED** | `_normalize_callbacks()` validates entries; invalid entries go to `_invalid_callbacks` |
| P2-1 | 2 | High | **FIXED** | Duplicate `"limitations"` key removed from `_compact_paper()` |
| P2-2 | 2 | High | **FIXED** | Abstract-only confidence cap implemented in `_canonicalize_judged_paper()` |
| P2-3 | 2 | Medium | **FIXED** | `SearchPaperWikiTool` top_k capped at 10 via `_clamped_int` |
| P2-4 | 2 | Low | Deferred | `PaperStore` abstraction not implemented |
| P2-5 | 2 | Low | Open | Session retrieval cache is in-memory only |
| P2-6 | 2 | Medium | **FIXED** | Rejected papers added to `seen_ids` via pre-filter `_record_seen()` call |
| P3-1 | 3 | Medium | Open | `adversarial_state` in callback context always empty — fields not stored on panel |
| P3-2 | 3 | Low | Deferred | `update()` path has no callback loop |
| P3-3 | 3 | Low | **FIXED** | `max_callback_rounds_after_analysis` wired into `__init__()` and `run_post_analysis_callbacks()` |
| P3-4 | 3 | Medium | **FIXED** | `callback_history` threaded into `_run_mediator_callback_synthesis()` |
| P3-5 | 3 | Medium | Open | No test for brief/lightweight explicit callback skip behavior |
| P4-1 | 4 | High | **FIXED** | `ADVERSARIAL_REMEDIATOR_PROMPT` uses Phase 1 schema; test added |
| P4-2 | 4 | Medium | Open | Alignment review not wired into `SessionDispatcher.execute_task()` |
| P4-3 | 4 | High | **FIXED** | `missing_analysis` removed from tool-revision routing; test updated |
| P4-4 | 4 | Medium | **FIXED** | Second alignment review blocks on `needs_revision` as well as `unsalvageable` |
| P4-5 | 4 | Medium | Partial | 3 of 5 missing tests added; 2 spec scenarios still absent |
| P5-1 | 5 | High | **FIXED** | `_decide_after_analysis()` fallback now returns `conclude`; test added |
| P5-2 | 5 | High | **FIXED** | Post-analysis callback loop is now a `while` loop with two-round budget; test added |
| P5-3 | 5 | Medium | Resolved | `_ensure_state_graph()` always creates manager in `run()`; `None` guard is a narrow edge |
| P5-4 | 5 | Medium | Partial | 3 of 5 missing tests added; parameter_change and revise_plan routing tests still absent |
| P6-1 | 6 | Medium | Open | `ConversationManager` class absent |
| P6-2 | 6 | Medium | Open | `SessionDispatcher` still uses old `feedback_dir` layout |
| P6-3 | 6 | High | Open | `_compact_active()` stores file path in `latest_analyzer_verdict` — Mediator sees path not verdict |
| P6-4 | 6 | Low | Open | `reusable_artifacts` / `unresolved_gaps` stubs undocumented |
| P6-5 | 6 | Medium | Open | `leaderboard.json` not written |
| P6-6 | 6 | Low | Open | `initialize_research_plan()` idempotency guard silently discards re-initialization |
| P6-7 | 6 | Medium | Open | 11 StateGraph and session storage tests still missing from spec |
| NEW-1 | 5 | High | Open | `_normalize_post_analysis_decision()` defaults to `start_panel_update_round` for unrecognized `decision_type` |
| NEW-2 | 2 | Low | Open | Abstract-only cap exempts `broad_background` — undocumented spec extension |
| NEW-3 | 3 | Low | Open | `adversarial_state` fields always empty — not populated by `_extract_callback_requests()` |
| NEW-4 | 5 | Low | Open | `run_post_analysis_callbacks()` `current_plan` omits `concrete_analysis_claim` |

### Priority fixes before Phase 7

1. **P6-3** — `_compact_active()`: change `latest_analyzer_verdict` to read from a parsed verdict string (e.g., from `node.get("analyzer_refs", {}).get("result_verdict")` or attached analyzer report), not from `analyzer_report_path`. The Mediator currently receives a file path where it expects a judgment value.
2. **NEW-1** — `_normalize_post_analysis_decision()`: change the `_enum_or_default` default from `"start_panel_update_round"` to `"conclude"`. A garbled LLM response currently triggers an expensive full panel update.
3. **P3-1 / NEW-3** — Store `adv_result` on `self.adversarial_panelist` or on the panel after `_run_adversarial_loop()`, then thread it into `_build_panelist_callback_context()` as the `adversarial_state`. Currently the four adversarial fields are always empty strings.
4. **P4-2** — Wire alignment review into `SessionDispatcher.execute_task()` or require operational tasks to pass through `ResearchLoop`. Currently all operational ToolConsultant calls bypass Phase 4.
5. **P4-5 + P5-4** — Add the 4 remaining spec test scenarios: `missing_downstream_analysis`, `cell_level_test`, `parameter_change_routing`, `revise_plan_routing`.
