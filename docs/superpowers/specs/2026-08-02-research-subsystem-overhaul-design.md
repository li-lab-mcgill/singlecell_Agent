# Research-subsystem overhaul — design

Date: 2026-08-02
Status: Design — awaiting user review
Supersedes standalone execution of: `2026-08-02-research-prompt-consolidation-design.md`
(that spec's prompt-module mapping is reused verbatim here as Track 3).

## Goal

One coordinated pass over the research/analysis subsystem that lands three tracks together,
organized by subsystem so each hot file is edited once:

- **Track 1 — correctness:** fix the confirmed bugs from the two code reviews.
- **Track 2 — efficiency:** apply the low-risk token/time optimizations.
- **Track 3 — prompts:** consolidate `updated_prompts/*.md` into `prompts/*.py` and refine.

Each concern is its own commit (bisectable), but files are visited by subsystem so we don't
re-open them three times.

## Sequencing principle

Phase 0 fixes the crashers first (two of them block running the pipeline end-to-end, so nothing
downstream can be validated until they're fixed). Then one phase per subsystem, each applying its
bug fixes + optimizations + prompt rewire. Cleanup + full verification last.

## Confirmed fix inventory

Confidence is from the review passes; only items that were verified against the code are included.
"Track" marks which concern each belongs to.

### Phase 0 — Crashers (Track 1, isolated)

| # | File / anchor | Bug | Fix |
|---|---|---|---|
| 0.1 | `frontend/server.py:547,555` | `scientist_panel.adversarial_panelist` doesn't exist → ResearchLoop dead at startup (caught, nulled) | Build a real `AdversarialPanelist(retriever=…, judge=…, paper_md_writer=…)` (pattern in `run_ad_monitor.py:171`); pass as `adversarial_panelist=`; drop the `alignment_reviewer=` arg |
| 0.2 | `agents/scientist_panel.py:405` (`_run_adversarial_loop`) | `formulate(mode="full")` (default) unconditionally raises `RuntimeError` | Remove the dead `formulate`/`_formulate_full`/`_run_adversarial_loop` path (ResearchLoop uses `run_initial_panelists`+`MediatorAgent`); or restore a working impl. Decision: **remove** the dead path |
| 0.3 | `backend/rna/_normalization.py:9,15-16,37` + `agents/tools.py:673,1840` | `sctransform` still selectable but its R script was deleted → `FileNotFoundError` | Drop `"sctransform"` from `KNOWN_METHODS`, both tool enums, and remove `_run_sctransform` (or raise a clear "removed" error) |
| 0.4 | `backend/tools/atac/topic/pycisTopic.py:168` | `models[n_topics_list[0]]` indexes a list by topic-count → `IndexError` (default 40) | `model = models[0]` |
| 0.5 | `backend/tools/atac/topic/pycisTopic.py:172-187` | `cell_topic` (topics×cells) assigned to `obsm` without `.T`; `topic_region` (regions×topics) given a wrong `.T` | Transpose `cell_topic` for `obsm`; drop `.T` on `topic_region` for `varm`/DataFrame. **Verify against pinned pycisTopic version first** |
| 0.6 | `backend/tools/multi/velocity/aggregate_peaks.py:93` | Wrong kwargs to `mv.aggregate_peaks_10x` + return discarded (stays peak-level) | Positional `peak_annot_file`/`linkage_file`, drop `use_gene_id`/`verbose`, capture return: `adata_atac = mv.aggregate_peaks_10x(...)`. **Verify against pinned MultiVelo version** |

### Phase 1 — Retrieval (`rag/agent.py`, `rag/literature_retriever.py`, `rag/store_backend.py`)

| # | File / anchor | Track | Change |
|---|---|---|---|
| 1.1 | `rag/store_backend.py` `deduplicate_documents` / `rag/agent.py:546` | 1+2 | Collapse cross-source duplicates by normalized DOI (else normalized title) **before** embedding/judging — same paper from PubMed/S2/OpenAlex currently survives 3× (quality bug + 3× token cost) |
| 1.2 | `rag/literature_retriever.py:494-501` (`_rrf_search`) | 1 | Aggregate chunk hits to one entry per `doc_id` before RRF (mirror `agent.py:_aggregate_hits_to_ranked_papers`); currently multi-chunk papers get multiple RRF increments |
| 1.3 | `rag/literature_retriever.py` (HyDE + search) | 2 | Per-phase cache of HyDE abstracts + search results keyed on normalized subquery, so the 3 panelists don't regenerate/re-search independently |
| 1.4 | `rag/literature_retriever.py:133-134`, `rag/agent.py:111` | 3 | Rewire to `prompts.literature_prompts` (new module) |
| 1.5 | `rag/literature_retriever.py:562-572` | 1 (minor) | Fallback summary dict omits `method_and_dataset`/`benchmark_methods` — add them |

### Phase 2 — Scientist panel + mediator (`agents/scientist_panel.py`, `agents/mediator_agent.py`)

| # | File / anchor | Track | Change |
|---|---|---|---|
| 2.1 | `agents/scientist_panel.py:172` (`run_panelist_callback`) | 1 | Normalize `callback_type` `"literature"→"ask_panelist_for_more_literature"` so mediator-driven literature callbacks actually retrieve (currently fall to the no-tools branch) |
| 2.2 | `agents/mediator_agent.py:271-277` (`_tag_done_handler`) | 1 | Accept the same alias tag set `_extract_tag_json` accepts, so an alias-wrapped output can't exhaust `max_iterations` |
| 2.3 | `agents/scientist_panel.py:443,562,724,752`, `agents/mediator_agent.py:190,228` | 2 | Route routine calls (mediator JSON-repair, callback synthesis) to `fast_engine`; keep primary panelist reasoning + main mediation on `engine` |
| 2.4 | `agents/scientist_panel.py:344,775`; `agents/mediator_agent.py:182` | 2 | Lower tool-loop `max_iterations` (12–20 → 6) |
| 2.5 | `agents/adversarial_panelist.py:77`; `agents/research_loop.py:675` | 2 | Lower adversarial `max_rounds` default 3→2 (early-exit on `survives`/`skipped` already exists) |
| 2.6 | `agents/scientist_panel.py:66-73`, `agents/mediator_agent.py:26-29` | 3 | Rewire to `prompts.panelist_prompts` + `prompts.mediator_prompts`; extract `PANEL_OUTPUT_SCHEMA`; refine (folds Track 2 "prompt bloat"); drop `indent=2` at `scientist_panel.py:702` |

### Phase 3 — Analyzer (`agents/analyzer_panel.py`, `agents/analyzer_tools.py`)

| # | File / anchor | Track | Change |
|---|---|---|---|
| 3.1 | `agents/analyzer_panel.py:363-368` | 1 | Include `best_path["metrics"]` and `objective_score` in the summary sent to panelists; remove the always-`None` `bp.get("status")` |
| 3.2 | `agents/analyzer_tools.py:115-132` (`interpret_figure`) | 1+2 | Fix the Responses-API content schema (`input_text`/`input_image`) so figure calls succeed instead of always 400-ing and being swallowed |
| 3.3 | `agents/analyzer_tools.py:351-359` (`omnipath_interactions`) | 1 (minor) | Read `references` and `source_genesymbol`/`target_genesymbol` (not `n_references`/UniProt IDs) |
| 3.4 | `agents/analyzer_panel.py:64` | 3 | Fold `analyzer.md` into `prompts/analyzer_prompts.py`; drop the `load_updated_prompt(..., fallback=)` |

### Phase 4 — Memory / paper / adversarial / critic

| # | File / anchor | Track | Change |
|---|---|---|---|
| 4.1 | `agents/short_term_memory.py:335-336` | 1 | Read `best_path["path_index"]`/`["stage_results"]` (not `path_id`/`stages`) |
| 4.2 | `agents/short_term_memory.py:295-305` | 1 | Direction-aware metric delta: lower-is-better metrics (`pct_mito`, `doublet_rate`) improve when they decrease |
| 4.3 | `agents/long_term_memory.py:185` | 1 | Overwrite `continues_from` when the arg is provided (not `setdefault`) |
| 4.4 | `agents/paper_judge.py:214` | 1 | Guard `float(confidence)` against `null`/non-numeric; don't let it drop the whole verdict |
| 4.5 | `agents/paper_judge.py:33-34`, `agents/paper_md_writer.py:33-35` | 3 | Rewire to `prompts.paper_prompts` (new module) |
| 4.6 | `agents/adversarial_panelist.py` | 3 | Refine `prompts/adversarial_prompts.py` in place; delete stale `adversary.md` |
| 4.7 | `agents/attributing_critic.py` | 3 | Refine `prompts/critic_prompts.py` in place |

### Phase 5 — Cleanup + verification

- Delete `updated_prompts/*.md`, `scientist_panel_schemas.json`, `agents/prompt_loader.py`; migrate the
  three loader-using tests (`test_mediator_prompt_modes`, `test_scientist_panel_callbacks`,
  `test_analyzer_phase_update`). Grep gate: no `load_updated_prompt`/`updated_prompts` references.
- Run the full affected suite.

## Track 3 module mapping

Reused verbatim from the prompt-consolidation spec: new `prompts/panelist_prompts.py`,
`mediator_prompts.py`, `paper_prompts.py`, `literature_prompts.py`; refine kept
`analyzer_prompts.py`, `adversarial_prompts.py`, `critic_prompts.py`. Placeholder contracts and
the `.format()` vs concat distinction are specified there and carried into the plan.

## Global constraints

- Every `.format()` placeholder set preserved exactly (paper/literature/critic prompts); braces
  `{{ }}`-escaped where `.format()`-ed, literal where concat-composed.
- Machine-readable contracts unchanged: panel output-schema keys, mediator tags + alias set,
  judge JSON keys, paper front-matter keys, post-analysis decision vocabulary.
- Two findings depend on external library versions and MUST be verified against the pinned
  package before editing: 0.5 (pycisTopic orientation) and 0.6 (MultiVelo `aggregate_peaks_10x`).
- Optimizations must not change scientific behavior: fast-engine routing only for
  formatting/repair/synthesis calls, never the primary reasoning; iteration caps rely on the
  existing done-handlers; adversarial early-exit path unchanged.
- No legacy-agent prompt changes (analyst, consultant, evaluator, generator, coder,
  session_router, tool_consultant).

## Deferred / optional (user's call, not in this plan unless requested)

- Lower-confidence robustness items: `state_graph` unguarded `continue_from_node_id` (wrap in
  try/except), `self_revise_plan` same-`steps` spin, `research_workspace` loose token match,
  bioRxiv "recent" actually-oldest ordering, `optimizing_coder` best-metrics (dead path today).
- Larger optimization ideas needing their own design: making the whole adversarial/callback
  machinery conditional on complexity; provider prompt-caching restructuring.

## Verification strategy

- Per bug fix: a unit test that reproduces the failure then passes (where unit-testable), else an
  existing integration test.
- Per prompt module: executable `.format(**all_keys)` contract test + import smoke check.
- Per phase: run that subsystem's tests; import-resolve the touched agents.
- Final: full affected suite + grep gate for removed loader/paths.
