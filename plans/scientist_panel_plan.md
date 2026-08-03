# Scientist Panel — Design Plan

## Overview

The Scientist Panel is the scientific reasoning layer that sits above the Planner
(ToolConsultant). It takes a user's biological question, debates across three expert
perspectives informed by literature, and produces a **research plan** in natural
language. The Planner translates the research plan into a DAG.

The panel runs in two contexts:
- **Formulate** (`formulate()`): before any execution — design the first research plan
- **Update** (`update()`): after each execution phase — review results, decide next
  research plan or stop

There is no separate synthesis phase. The loop ends when the Mediator signals
`"done"` in an `update()` call. The last Analyzer report is the final answer.

---

## The Research Plan

The research plan is an **ordered list of natural language steps** passed to the
Planner. It is question-aware from the first iteration:

- **Canonical steps** (Phase 1) address the research question through standard
  methodology — the choices of which cell type to focus on, which covariates to
  correct for, which comparisons to make are all driven by the question
- **Hypothesis-specific steps** layer on top as the loop progresses, targeting
  the specific biological claim more directly
- **Validation steps** are embedded within the plan — statistical tests, module
  scores, pseudobulk comparisons — not a separate artifact
- **Required visualizations** are specified explicitly so the Planner generates
  them and the Analyzer can interpret them

The plan evolves across loop iterations: Phase 1 is canonical + question-aware,
Phase 2 builds on Phase 1 findings with more targeted analyses, Phase 3+ becomes
increasingly innovative and mechanistic.

Example research plan output:
```
consensus_hypothesis: CD8+ T cells in COVID-19 show transcriptional exhaustion
  signatures driven by chronic antigen stimulation

research_plan:
  steps:
    1. QC, filter low-quality cells with disease-relevant thresholds (mito < 20%)
    2. Normalize, identify highly variable genes (exclude mito/ribo)
    3. Embed with batch-aware method correcting for donor_id
    4. Cluster at multiple resolutions; annotate using canonical T/B/myeloid markers
    5. Quantify cell type proportions across COVID-19 vs healthy donors
    6. Compute exhaustion module score (TIGIT, LAG3, HAVCR2, TOX, PDCD1) per CD8+ T cell
    7. Pseudobulk by donor; test exhaustion score difference disease vs control
       (Mann-Whitney, p < 0.05 threshold)
    8. Run pseudobulk DE within CD8+ T cells between conditions

  required_visualizations:
    - UMAP colored by cluster, by donor_id, by condition
    - Dot plot of canonical T/B/myeloid markers per cluster
    - Bar chart of cell type proportions per condition
    - Violin plot of exhaustion module score by condition
    - Pseudobulk comparison boxplot (exhaustion score, disease vs control)
    - Volcano plot of CD8+ T cell DE genes disease vs control

next_action: continue
```

---

## Panelists

### BiologistPanelist
- **Perspective**: known cell biology — cell types, marker programs, cell states,
  developmental trajectories, tissue-specific and disease biology
- **Reasons about**: what the data should show given known biology; what analyses
  are standard for this tissue/disease; what novel hypotheses the literature supports
- **Literature**: retrieves papers on cell types in this tissue, marker genes,
  cell states, relevant atlases, canonical analyses used in similar studies,
  disease-specific biology
- **Contribution to research plan**: biological rationale for each step;
  which cell populations to focus on; what biological comparisons to make;
  what module scores or signature scores are relevant
- **Designs validation steps**: computational tasks that would confirm or refute
  the biological hypothesis (e.g. "compute pyroptosis module score and compare
  disease vs control pseudobulked by donor")

---

### StatisticianPanelist
- **Perspective**: technical confounders, data quality, batch effects, normalization
  artifacts, statistical validity
- **Reasons about**: what the data can and cannot show given its technical properties;
  what statistical tests belong in the plan; what covariates must be accounted for
- **Literature**: retrieves methods papers, benchmarking papers, papers on confounders
  in this data type
- **Data summary**: actively reasons over n_obs, obs columns, batch composition,
  cell counts per condition — not just literature
- **Contribution to research plan**: which batch variables to correct; what
  statistical tests to use for each comparison; what sample sizes permit; what
  thresholds are appropriate; warns about underpowered comparisons
- **Designs validation steps**: statistical tests with explicit criteria
  (e.g. "pseudobulk by donor_id before testing — raw cell-level tests invalid
  given donor pseudoreplication")
- **Constraints are advisory**: never override explicit user instructions

---

### BioinformaticianPanelist
- **Perspective**: computational approach fit — which analytical strategy best suits
  the biological question given this data's characteristics
- **Reasons about**: method selection rationale, resolution choices, modality
  considerations, known failure modes of approaches
- **Does NOT** name specific tools or software. Reasons in the abstract:
  "a variational autoencoder with batch correction" not "scVI". Tool mapping
  is the Planner's job
- **Literature**: retrieves benchmarking papers, method comparison papers,
  computational approach papers for this data type and question
- **Contribution to research plan**: what computational strategy suits each step;
  what resolution parameters are appropriate; what failure modes to watch for;
  what modality-specific considerations apply

---

### Reconciler (Round 2 only — formulate() only, not a panelist)
- Reads all three Round 1 outputs
- Identifies specific conflicts between panelists
  (e.g. Biologist wants trajectory; Statistician flags too few cells per timepoint;
  Bioinformatician says pseudotime requires continuous manifold)
- Produces a conflict summary: list of disagreements with evidence each side has
- Does NOT resolve — only surfaces tensions for the Mediator

---

### Mediator (final round — both formulate() and update())
- Reads panelist outputs + (in formulate) Reconciler conflict summary
- Resolves conflicts via confidence-weighted reasoning
- Synthesizes into the final research plan:
  - Ordered natural language steps
  - Required visualizations
  - Consensus hypothesis
- In `update()`, additionally decides:
  - `"continue"` → produce next research plan
  - `"pivot"` → evidence changes direction, produce revised research plan
  - `"done"` → enough evidence, loop ends, last Analyzer report is the answer
  - `"abstain"` → evidence contradictory or data cannot answer the question

---

## Round Structure

### formulate() — full 4-round panel

```
Round 1 — independent, parallel
  BiologistPanelist       ──┐
  StatisticianPanelist    ──┤  each calls retrieve_literature() multiple times
  BioinformaticianPanelist ──┘  independently; reasons from literature + data summary

Round 2 — Reconciler (single LLM call, no tools)
  reads all 3 Round 1 outputs
  → conflict summary

Round 3 — confidence adjustment, parallel
  BiologistPanelist       ──┐
  StatisticianPanelist    ──┤  each receives: own Round 1 + conflict summary
  BioinformaticianPanelist ──┘  can only adjust confidence, not change position

Round 4 — Mediator (single LLM call, no tools)
  reads all 3 Round 3 outputs + conflict summary
  → consensus hypothesis + research plan (steps + required visualizations)
```

### update() — lighter 2-round panel

```
Round 1 — independent, parallel
  BiologistPanelist       ──┐
  StatisticianPanelist    ──┤  each optionally calls retrieve_literature()
  BioinformaticianPanelist ──┘  if results open new directions; reasons over
                                Analyzer report + prior working model

Round 2 — Mediator (single LLM call, no tools)
  reads all 3 Round 1 outputs + Analyzer report
  → next research plan (continue / pivot) OR done / abstain
```

No Reconciler and no confidence adjustment round in `update()`.

---

## Panelist Tool Set

Each panelist (Rounds 1 and 3) is a `ToolCallingAgentRunner` with two tools:

| Tool | Description |
|------|-------------|
| `retrieve_literature(base_query, background)` | Full retrieval pipeline: keyword gen → parallel fetch (PubMed + S2 + OpenAlex) → embed → HyDE rerank → PaperJudge → labeled top-K papers. Multiple calls allowed per round. `base_query` is free-form — the panelist's own statement of retrieval intent. |
| `fetch_paper_section(paper_id, section_type)` | Drill into abstract / methods / results / discussion of a retrieved paper. |

In `formulate()` Round 1: RAG is required (each panelist must retrieve literature).
In `update()` Round 1: RAG is optional (panelist calls it only if results raise new
questions that need literature support).

The Reconciler and Mediator are single LLM calls (no tools).

---

## Literature Pipeline (inside `retrieve_literature`)

```
panelist states base_query (free-form intent)
        ↓
generate_keyword_queries(base_query, background)
  → PubMed-style Boolean queries (for PubMed)
  → natural language queries (for S2 + OpenAlex)
        ↓
parallel fetch: PubMed + Semantic Scholar + OpenAlex
        ↓
deduplicate by DOI / normalized title
        ↓
generate_hyde_subqueries(base_query, background, n=4)
  → subqueries + hypothetical abstracts
        ↓
embed fetched papers → ChromaDB → HyDE rerank → RRF → top-K
        ↓
PaperJudge (automatic, not panelist-controlled)
  parallel LLM calls, role-specific relevance question
  threshold: relevant=true AND confidence >= 0.6
        ↓
returns labeled papers to panelist
  {title, abstract, key_methods, main_findings,
   relevant, confidence, reason, user_provided}
```

User-provided anchor papers bypass fetch but go through PaperJudge.
They carry `user_provided: true` so panelists treat them as anchors.

---

## Data Summary

All panelists receive a structured data summary derived from h5ad metadata
(no matrix load):

```json
{
  "n_obs": 8432,
  "n_vars": 3000,
  "obs_columns": ["donor_id", "condition", "pct_mito", "n_counts"],
  "obsm_keys": ["X_pca"],
  "layers": ["counts"],
  "batch_composition": {
    "donor_id": {"D1": 4100, "D2": 412, "D3": 3920}
  },
  "condition_composition": {
    "condition": {"IBD": 4200, "healthy": 4232}
  }
}
```

StatisticianPanelist actively derives flags from this (unequal batch sizes,
missing layers, confounded covariates). Biologist and Bioinformatician use it
for context.

---

## Output to Planner

The Mediator's output is passed to the Planner as a natural language brief:

```
Consensus hypothesis:
  CD8+ T cells in COVID-19 show transcriptional exhaustion signatures.

Research plan steps:
  1. QC and filter (mito < 20%, min_genes > 200)
  2. Normalize (scran pooling recommended given cell size variation)
  3. Embed correcting for donor_id (batch-condition partially confounded —
     use latent batch-aware model rather than post-hoc correction)
  4. Cluster at resolution 0.3, 0.5, 0.8; annotate with canonical markers
  5. Compute exhaustion module score per CD8+ T cell
  6. Pseudobulk by donor; Mann-Whitney test disease vs control
  7. Pseudobulk DE within CD8+ T cells
  Caveat: donor_id partially confounded with condition —
    interpret clustering cautiously.

Required visualizations:
  - UMAP colored by cluster, donor_id, condition
  - Dot plot of T/B/myeloid markers per cluster
  - Violin plot of exhaustion score by condition
  - Pseudobulk boxplot disease vs control
  - Volcano plot CD8+ DE
```

Constraints are advisory. The Planner respects explicit user instructions
over panelist warnings.

---

## Loop Structure

```
formulate()
    ↓
Planner → DAG → Execute
    ↓
Analyzer → report
    ↓
update()  ──→  "done" / "abstain"  →  last Analyzer report = answer
    ↓ "continue" / "pivot"
Planner → DAG → Execute
    ↓
Analyzer → report
    ↓
update() ...
```

The loop is driven by an Orchestrator that calls formulate() once,
then alternates execute → analyze → update() until Mediator signals done.

---

## Settled Decisions

- **No synthesize() method**: loop ends when Mediator says `"done"`. Last
  Analyzer report is the final answer. No NarratorPanelist.

- **BioinformaticianPanelist — no wiki access**: reasons purely in the abstract.
  Tool mapping is entirely the Planner's job.

- **Research plan format**: natural language ordered steps + required
  visualizations. Not structured JSON with separate validation_tasks field.

- **Validation steps are embedded in the plan**: statistical tests, module
  scores, pseudobulk comparisons are just steps in the research plan.

- **Working model persistence**: session-scoped. Resets when user exits frontend.

- **update() panelists**: all three panelists participate with optional RAG.
  No Reconciler or confidence adjustment round.

---

## Files

| File | Description |
|------|-------------|
| `agents/scientist_panel.py` | `ScientistPanel` class with `formulate()` and `update()`. Orchestrates round structure. Panelists run as `ToolCallingAgentRunner`. Rounds 1/3 parallel via `ThreadPoolExecutor`. Reconciler + Mediator are single LLM calls. |
| `agents/panelist_tools.py` | `RetrieveLiteratureTool`, `FetchPaperSectionTool`, `build_panelist_tool_registry()` |
| `agents/paper_judge.py` | `PaperJudge`: parallel LLM relevance filter, role-specific questions, threshold 0.6 |
| `prompts/panelist_prompts.py` | All round prompts: Round 1 × 3 roles, Reconciler, Round 3, Mediator formulation, Mediator update |
| `rag/literature_retriever.py` | `LiteratureRetriever`: keyword gen → parallel fetch → HyDE → RRF → summaries |
| `rag/sources.py` | PubMed + Semantic Scholar + OpenAlex fetchers |
