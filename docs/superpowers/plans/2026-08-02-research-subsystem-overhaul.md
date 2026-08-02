# Research-Subsystem Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land three tracks — correctness bug fixes, low-risk token/time optimizations, and prompt consolidation — in one subsystem-organized pass over the research/analysis subsystem, each concern as its own commit.

**Architecture:** Phase 0 fixes crashers first (two block running the pipeline at all). Then one phase per subsystem (retrieval, panel+mediator, analyzer, memory/paper/adversarial/critic), each applying that subsystem's bug fixes + optimizations + prompt rewire. Cleanup + full verification last. Track-3 prompt-module creation is detailed in the companion plan `2026-08-02-research-prompt-consolidation.md`; this plan interleaves those tasks at the right phase by reference.

**Tech Stack:** Python, pytest, scanpy/anndata, OpenAI Responses API.

## Global Constraints

- Preserve every `.format()` placeholder set exactly; braces `{{ }}`-escaped where `.format()`-ed, literal where concat-composed.
- Preserve machine-readable contracts: panel output-schema keys, mediator tags + accepted alias set, judge JSON keys, paper front-matter keys, post-analysis decision vocabulary (`self_revise_plan`, `continue_from_node_id`).
- Tasks 0.5 (pycisTopic orientation) and 0.6 (MultiVelo `aggregate_peaks_10x`) MUST be verified against the installed package version before editing — inspect the installed signature/source; if it contradicts the finding, skip and note it.
- Optimizations must not change scientific behavior: fast-engine routing only for formatting/repair/synthesis calls; iteration caps rely on existing done-handlers; adversarial early-exit path unchanged.
- No legacy-agent prompt changes.
- One concern per commit even when a file is visited once for several concerns.

---

## Phase 0 — Crashers (unblock the pipeline)

### Task 0.1: ResearchLoop constructs at startup

**Files:** Modify `frontend/server.py:543-557`

- [ ] **Step 1:** In the `try` block that builds `ResearchLoop`, before the constructor, build the adversary explicitly (pattern from `run_ad_monitor.py:171`):

```python
from agents.adversarial_panelist import AdversarialPanelist
adversarial_panelist = AdversarialPanelist(
    retriever=scientist_panel.retriever,
    judge=scientist_panel.judge,
    paper_md_writer=scientist_panel.paper_md_writer,
)
```

- [ ] **Step 2:** In `ResearchLoop(...)`, replace both `scientist_panel.adversarial_panelist` references: pass `adversarial_panelist=adversarial_panelist`, and remove the `alignment_reviewer=` argument (run_ad_monitor omits it).
- [ ] **Step 3:** Verify: `python -c "import frontend.server"` resolves, and grep shows no `scientist_panel.adversarial_panelist` remains.

Run: `grep -n "scientist_panel.adversarial_panelist" frontend/server.py` → no output.

- [ ] **Step 4:** Commit: `git commit -am "fix: build AdversarialPanelist so ResearchLoop starts (was dead at startup)"`

### Task 0.2: Remove the dead `formulate` path

**Files:** Modify `agents/scientist_panel.py` (`formulate`, `_formulate_full`, `_run_adversarial_loop`)

- [ ] **Step 1:** Confirm no production caller: `grep -rn "\.formulate(" agents/ frontend/ | grep -v "def formulate"`. Expected callers are only `research_loop.py:576` (legacy dead branch) and tests.
- [ ] **Step 2:** Delete `_run_adversarial_loop` (the `raise RuntimeError` stub), `_formulate_full`, and `formulate`. If `research_loop.py:576`'s `legacy_mediator_flow` branch calls `formulate`, delete that branch too (guarded by a panel lacking `run_initial_panelists`, which never happens for the real panel).
- [ ] **Step 3:** Update/remove the tests that call `formulate` (`tests/test_scientist_panel_formulate.py`, `tests/test_research_loop_phase1.py`) to target `run_initial_panelists` instead, or delete if wholly obsolete.
- [ ] **Step 4:** Verify: `python -c "import agents.scientist_panel"` and the touched tests pass/are removed cleanly.
- [ ] **Step 5:** Commit: `git commit -am "refactor: remove dead formulate()/_run_adversarial_loop path"`

### Task 0.3: Remove `sctransform` normalization

**Files:** Modify `backend/rna/_normalization.py:9,15-16,33-38`, `agents/tools.py:673,1840`

- [ ] **Step 1: Write failing test**

```python
# tests/test_normalization_methods.py
import pytest
def test_sctransform_not_offered():
    from backend.rna import _normalization as n
    assert "sctransform" not in n.KNOWN_METHODS
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Remove `"sctransform"` from `KNOWN_METHODS`, delete the `if method == "sctransform"` branch and `_run_sctransform`; remove `"sctransform"` from both enums in `agents/tools.py`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: drop sctransform normalization (R script removed)"`

### Task 0.4: pycisTopic model index

**Files:** Modify `backend/tools/atac/topic/pycisTopic.py:168`

- [ ] **Step 1:** Change `model = models[n_topics_list[0]]` to `model = models[0]`.
- [ ] **Step 2:** Verify by reading `run_cgs_models`' return (list of models) — confirm single-element indexing is `[0]`.
- [ ] **Step 3:** Commit: `git commit -am "fix: pycisTopic index single model with [0] not [n_topics]"`

### Task 0.5: pycisTopic orientation (version-gated)

**Files:** Modify `backend/tools/atac/topic/pycisTopic.py:172-187`

- [ ] **Step 1:** Inspect the installed `pycisTopic` `CistopicLDAModel.cell_topic`/`topic_region` orientation (source or a shape probe). If `cell_topic` is topics×cells and `topic_region` is regions×topics, proceed; else skip and note.
- [ ] **Step 2:** Set `adata.obsm["X_topic"] = cell_topic.T...`; use `topic_region` directly (drop `.T`) for `varm["topic_peak_weights"]` and the DataFrame `index=adata.var_names`.
- [ ] **Step 3:** Verify shapes: `obsm["X_topic"].shape[0] == adata.n_obs`, `varm["topic_peak_weights"].shape[0] == adata.n_vars`.
- [ ] **Step 4:** Commit: `git commit -am "fix: correct pycisTopic cell_topic/topic_region orientation"`

### Task 0.6: MultiVelo peak aggregation (version-gated)

**Files:** Modify `backend/tools/multi/velocity/aggregate_peaks.py:93`

- [ ] **Step 1:** Inspect installed `multivelo.aggregate_peaks_10x` signature. Confirm positional `peak_annot_file`/`linkage_file`, no `use_gene_id`/`verbose`, and that it returns a new AnnData.
- [ ] **Step 2:** Rewrite the call: `adata_atac = mv.aggregate_peaks_10x(adata_atac, str(peaks_annot_path), str(linkage_path))` (map remaining supported kwargs by name).
- [ ] **Step 3:** Verify the downstream `adata_atac` is gene-level (n_vars changed) before the shared-gene check.
- [ ] **Step 4:** Commit: `git commit -am "fix: correct aggregate_peaks_10x call and capture gene-level return"`

---

## Phase 1 — Retrieval

### Task 1.1: Cross-source dedup by DOI/title

**Files:** Modify `rag/store_backend.py` (`deduplicate_documents` or add `deduplicate_cross_source`), `rag/agent.py:546`
**Test:** `tests/test_retrieval_dedup.py`

- [ ] **Step 1: Write failing test**

```python
def test_cross_source_dedup_collapses_same_doi():
    from rag.store_backend import RAGStore  # or the dedup helper's module
    docs = [
        _doc(doc_id="pubmed:1", doi="10.1/x", title="A Paper"),
        _doc(doc_id="semantic_scholar:2", doi="10.1/x", title="A Paper"),
        _doc(doc_id="openalex:3", doi="10.1/X", title="a paper"),
    ]
    out = dedup_cross_source(docs)
    assert len(out) == 1
```

(Provide a minimal `_doc` factory matching `RAGDocument`.)

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: collapse when normalized DOI matches (case-insensitive, stripped); fall back to normalized title when DOI is absent. Keep the richest copy (prefer full-text/PMC). Call it in `agent.py` where `deduplicate_documents` is used at :546.
- [ ] **Step 4:** Run → PASS; update the print to reflect true unique count.
- [ ] **Step 5:** Commit: `git commit -am "fix: dedup papers across sources by DOI/title (quality + 3x token cost)"`

### Task 1.2: RRF per-document aggregation

**Files:** Modify `rag/literature_retriever.py:490-501`
**Test:** `tests/test_retrieval_dedup.py`

- [ ] **Step 1: Write failing test** — build two ranked lists of chunk hits where one `doc_id` appears in 3 consecutive ranks; assert the fused top rank is not dominated purely by chunk count.

```python
def test_rrf_aggregates_chunks_per_document():
    # doc "full" has chunks at ranks 1,2,3; doc "abs" one chunk at rank 4
    ranked = [[("full",0.9),("full",0.8),("full",0.7),("abs",0.6)]]
    scores = rrf_fuse(ranked)  # extracted pure helper
    # "full" must not get 3x the increments of "abs"
    assert scores["full"] <= 1.0/ (60+1) + 1e-9
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Before fusion, collapse each ranked list to first occurrence per `doc_id` (keep best rank), then apply RRF. Extract a pure `rrf_fuse` helper for testability.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: aggregate chunk hits per document before RRF"`

### Task 1.3: Per-phase HyDE/search cache

**Files:** Modify `rag/literature_retriever.py`

- [ ] **Step 1:** Add an instance-level cache dict keyed on normalized subquery for (a) generated HyDE abstract and (b) `search_runtime` results, scoped to a retrieval phase. Guard with the existing lock if panelists share the retriever.
- [ ] **Step 2:** Verify by test or log that a repeated subquery within a phase does not re-issue the HyDE LLM call.
- [ ] **Step 3:** Commit: `git commit -am "perf: cache HyDE abstracts and searches per phase across panelists"`

### Task 1.4: Rewire retrieval prompts (Track 3)

- [ ] Execute companion plan **Tasks 8 and 10** (`prompts/literature_prompts.py` + rewire `literature_retriever.py`/`rag/agent.py`). Commit as specified there.

### Task 1.5: Fallback summary keys

**Files:** Modify `rag/literature_retriever.py:562-572`

- [ ] **Step 1:** Add `"method_and_dataset": ""` and `"benchmark_methods": ""` to the abstract-only fallback dict so it matches the success-path shape.
- [ ] **Step 2:** Commit: `git commit -am "fix: fallback summary includes method_and_dataset/benchmark_methods keys"`

---

## Phase 2 — Scientist panel + mediator

### Task 2.1: Normalize literature callback type

**Files:** Modify `agents/scientist_panel.py:172` (`run_panelist_callback`)
**Test:** `tests/test_panelist_literature_tools.py` (extend)

- [ ] **Step 1: Write failing test** — call `run_panelist_callback` with `callback_type="literature"` and assert the retrieval-tool branch is taken (e.g. registry built / retriever invoked), not the plain-LLM branch.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** In `run_panelist_callback`, normalize: if `callback.get("callback_type")` is `"literature"`, set it to `"ask_panelist_for_more_literature"` before dispatch (reuse the mapping used by `_extract_callback_requests`).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: mediator literature callbacks actually retrieve (normalize callback_type)"`

### Task 2.2: Mediator done-handler accepts aliases

**Files:** Modify `agents/mediator_agent.py:271-277` (`_tag_done_handler`)
**Test:** `tests/test_mediator_prompt_modes.py` (extend) or `tests/test_prompt_contracts.py`

- [ ] **Step 1: Write failing test** — feed `_tag_done_handler` text wrapped in an alias tag (`<MEDIATOR>…</MEDIATOR>`) and assert it returns done.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Make `_tag_done_handler` check the same alias set `_extract_tag_json` accepts (`MEDIATOR`, `MEDIATOR_POST_ANALYSIS`, `POST_ANALYSIS_DECISION`, canonical).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: mediator done-handler recognizes alias tags (avoid max_iterations hang)"`

### Task 2.3: Route routine calls to fast_engine

**Files:** Modify `agents/scientist_panel.py:443,562,724,752`; `agents/mediator_agent.py:190,228`

- [ ] **Step 1:** Change the mediator JSON-repair call (`mediator_agent.py:228`) and callback-synthesis / mechanical `single_llm_call`s to use `self.fast_engine_name`. Leave the primary panelist runner (`scientist_panel.py:337`) and main mediation (`:443`) on `self.engine_name` unless clearly formatting-only — decide per call, documented in the commit.
- [ ] **Step 2:** Verify imports/attrs (`fast_engine_name` exists on both classes) and touched tests still pass.
- [ ] **Step 3:** Commit: `git commit -am "perf: route mediator repair/synthesis calls to fast engine"`

### Task 2.4: Lower tool-loop iteration caps

**Files:** Modify `agents/scientist_panel.py:344,775`; `agents/mediator_agent.py:182`

- [ ] **Step 1:** Lower `max_iterations` from 12–20 to 6 at these call sites.
- [ ] **Step 2:** Verify the done-handlers terminate normally (existing tests / a smoke run).
- [ ] **Step 3:** Commit: `git commit -am "perf: cap panel/mediator tool loops at 6 iterations"`

### Task 2.5: Lower adversarial max_rounds

**Files:** Modify `agents/adversarial_panelist.py:77`

- [ ] **Step 1:** Change default `max_rounds` 3→2. (Early-exit on `survives`/`skipped` already exists in `research_loop.py:691`.)
- [ ] **Step 2:** Commit: `git commit -am "perf: lower adversarial max_rounds default to 2"`

### Task 2.6: Consolidate + refine panel/mediator prompts (Track 3)

- [ ] Execute companion plan **Tasks 1–5** (create `panelist_prompts.py` + `mediator_prompts.py`, rewire `scientist_panel.py`/`mediator_agent.py`, migrate the two tests). Additionally drop `indent=2` at `scientist_panel.py:702` and pass compact summaries where full dicts are serialized. Commit per companion steps + a `perf: trim callback context serialization` commit.
- [ ] **STOP for user style review** (companion Task 6) before continuing to Phase 3.

---

## Phase 3 — Analyzer

### Task 3.1: Analyzer receives eval metrics

**Files:** Modify `agents/analyzer_panel.py:363-368`
**Test:** `tests/test_analyzer_phase_update.py` (extend) or a new focused test

- [ ] **Step 1: Write failing test** — build a `dag_result` with `best_path["metrics"]={"ARI":0.8}` and `objective_score=0.8`; assert the summary passed to panelists contains them.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Add `"metrics": bp.get("metrics", {})` and `"objective_score": bp.get("objective_score")` to the `summary["best_path"]`; remove the always-`None` `"status": bp.get("status")`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: analyzer summary includes best_path metrics/objective_score"`

### Task 3.2: interpret_figure Responses-API schema

**Files:** Modify `agents/analyzer_tools.py:115-132`

- [ ] **Step 1:** Change content parts to Responses format: `{"type":"input_text","text":prompt}` and `{"type":"input_image","image_url":f"data:{mime};base64,{image_data}"}` (or the SDK's documented image field). Verify against the installed `openai` SDK's `responses.create` image schema.
- [ ] **Step 2:** Verify a real (or mocked) call no longer returns the `VLM call failed` error path.
- [ ] **Step 3:** Commit: `git commit -am "fix: interpret_figure uses Responses API image schema (was always 400)"`

### Task 3.3: omnipath fields

**Files:** Modify `agents/analyzer_tools.py:328,351-359`

- [ ] **Step 1:** Request/read `source_genesymbol`/`target_genesymbol` and parse `references` (count via split) instead of `n_references` and UniProt `source`/`target`.
- [ ] **Step 2:** Commit: `git commit -am "fix: omnipath reads gene symbols and references field"`

### Task 3.4: Analyzer prompt (Track 3)

- [ ] Execute companion plan **Task 11** (fold `analyzer.md` into `analyzer_prompts.py`, drop the loader fallback, migrate `test_analyzer_phase_update`).

---

## Phase 4 — Memory / paper / adversarial / critic

### Task 4.1: short_term_memory DAG keys

**Files:** Modify `agents/short_term_memory.py:335-336`
**Test:** `tests/test_session_storage.py` (extend) or new

- [ ] **Step 1: Write failing test** — pass a `dag_result` with `best_path={"path_index":2,"stage_results":[{},{}]}`; assert summary `best_path_id==2` and `n_stages==2`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Read `.get("path_index")` and `.get("stage_results", [])`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: short_term_memory reads path_index/stage_results"`

### Task 4.2: Direction-aware metric delta

**Files:** Modify `agents/short_term_memory.py:295-305`
**Test:** same test module

- [ ] **Step 1: Write failing test** — `pct_mito` 0.10→0.05 must be classified "improved"; `ARI` 0.5→0.7 "improved"; `doublet_rate` up must be "problematic".
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Introduce a lower-is-better set (`{"pct_mito","doublet_rate"}`); flip the improved/problematic branch for those.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: metric delta direction-aware for lower-is-better metrics"`

### Task 4.3: long_term_memory continues_from

**Files:** Modify `agents/long_term_memory.py:185`
**Test:** new

- [ ] **Step 1: Write failing test** — `compress_and_save(..., continues_from="S02")` where the parsed record has `continues_from=None`; assert result `continues_from=="S02"`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Replace `setdefault` with explicit overwrite when the arg is not None: `if continues_from is not None: record["continues_from"] = continues_from` else `record.setdefault("continues_from", None)`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: long_term_memory records provided continues_from"`

### Task 4.4: paper_judge null confidence

**Files:** Modify `agents/paper_judge.py:214`
**Test:** new

- [ ] **Step 1: Write failing test** — parse a payload `{"relevant":true,"confidence":null,...}`; assert it does not drop the verdict and yields a numeric confidence (0.0) with fields intact.
- [ ] **Step 2:** Run → FAIL (TypeError path swallows verdict).
- [ ] **Step 3:** Coerce safely: `conf = payload.get("confidence"); confidence = float(conf) if isinstance(conf,(int,float)) else 0.0`. Also make `relevant` robust to string `"false"`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit: `git commit -am "fix: paper_judge tolerates null/non-numeric confidence"`

### Task 4.5: Paper prompts (Track 3)

- [ ] Execute companion plan **Tasks 7 and 9** (`prompts/paper_prompts.py` + rewire `paper_judge.py`/`paper_md_writer.py`).

### Task 4.6: Adversarial prompt (Track 3)

- [ ] Execute companion plan **Task 12** (refine `adversarial_prompts.py`; `adversary.md` deleted in Phase 5).

### Task 4.7: Critic prompt (Track 3)

- [ ] Execute companion plan **Task 13** (refine `critic_prompts.py`).

---

## Phase 5 — Cleanup + verification

### Task 5.1: Delete the `.md` system + loader

- [ ] Execute companion plan **Task 14** (grep gate → `git rm -r updated_prompts/ agents/prompt_loader.py` → import smoke check → commit).

### Task 5.2: Full affected-suite run

- [ ] **Step 1:** Run:

```bash
pytest tests/test_prompt_contracts.py tests/test_mediator_prompt_modes.py \
  tests/test_scientist_panel_callbacks.py tests/test_paper_md_writer.py \
  tests/test_panelist_literature_tools.py tests/test_analyzer_phase_update.py \
  tests/test_todo2_rag_contract.py tests/test_session_storage.py \
  tests/test_retrieval_dedup.py tests/test_normalization_methods.py \
  tests/test_research_loop_phase1.py tests/test_research_loop_tool_alignment.py -v
```

Expected: PASS (network/model-dependent tests may skip; all must import cleanly).

- [ ] **Step 2: Final grep gate**

```bash
grep -rn "load_updated_prompt\|updated_prompts\|scientist_panel_schemas\|scientist_panel.adversarial_panelist" --include='*.py' .
```

Expected: no output.

---

## Self-review notes

- **Spec coverage:** every inventory row maps to a task — Phase 0: 0.1–0.6; Phase 1: 1.1–1.5; Phase 2: 2.1–2.6; Phase 3: 3.1–3.4; Phase 4: 4.1–4.7; Phase 5: 5.1–5.2. Track-3 rows delegate to the companion plan's concrete tasks by number.
- **Ordering:** 0.1 (server) and 0.2 (formulate) precede everything so the pipeline can run; retrieval before panel (panel consumes retrieval); prompt rewire within each phase follows that phase's code fixes so the file is touched once.
- **Version-gated tasks** (0.5, 0.6, 3.2) each begin with an inspect-installed-package step and a skip-and-note escape hatch.
- **Placeholder/contract preservation** enforced by the companion plan's `.format(**keys)` tests and the extend-existing-test steps here.
