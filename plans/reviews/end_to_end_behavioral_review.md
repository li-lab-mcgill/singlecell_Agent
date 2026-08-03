# End-to-End Behavioral Review — AD Multiomics Query

**Reviewed**: 2026-05-26
**Query type**: Discovery — snRNA-seq + snATAC-seq, AD DLPFC, cell-type-specific regulatory architecture

---

## The Query

> Alzheimer's disease (AD) is a progressive neurodegenerative disorder... [full CellBench-style context including GWAS gap, CRE motivation, bulk limitation, modality pairing rationale, and DLPFC snRNA-seq + snATAC-seq study goal]

Key signals in the query:
- Clear biological mechanism framing (GWAS non-coding variants → CRE → TF → cell-type gene expression)
- Explicit modality pair (snRNA-seq + snATAC-seq) with a stated rationale for why both are needed
- Named data type (snMultiomics, DLPFC, AD vs. control)
- Discovery goals: characterize regulatory landscapes, identify AD-associated CREs, link CREs to TF programs, infer peak-to-gene regulatory interactions

---

## Stage 1 — SessionRouter

**File**: `agents/session_router.py`
**Prompt**: `prompts/session_router_prompts.py` → `SESSION_ROUTER_PROMPT`

### What happens

The router receives the full query text plus any `session_state` from the frontend. It runs one LLM call (no tools) via `ToolCallingAgentRunner` with `max_iterations=4, max_tool_calls=0`. The response handler extracts a `<SESSION_ROUTE>` JSON block and validates it:

```python
route ∈ {"direct_response", "task"}
intent_mode ∈ {"operational", "discovery", "ambiguous"}
```

### Expected behavior for this query

**Route: `task`** — the query asks for multi-step analysis (integration, clustering, differential accessibility, TF inference). Not answerable from general knowledge alone.

**Intent mode: `discovery`** — the session router prompt defines discovery as "requires hypothesis formation, literature, and iterative analysis" and lists signals: "mechanism", "interpret", "explain". This query uses all three: *why* non-coding GWAS variants function, *what* regulatory programs drive AD cell states, *how* chromatin and transcription interact. The query does **not** name a specific tool or pipeline; it frames an open biological question.

Operationally the router would resolve the intent as something like: *"Perform integrative single-nucleus multiomics analysis on AD vs. control DLPFC data to characterize cell-type-specific regulatory architecture, identify AD-associated CREs, and link chromatin accessibility changes to transcriptional programs and transcription factor activity."*

### Potential routing failure

**Risk**: the query is extremely long and contains a lot of methodological description ("snRNA-seq + snATAC-seq", "jointly profiling"). The router could misclassify as `operational` because the phrasing resembles a procedural task. The session router prompt says: *"Do not classify a routine analysis request as discovery merely because it is biological."*

**But**: the query also explicitly says "characterize", "identify", "infer", "investigate" — all open-ended discovery verbs. The four stated study aims are not a concrete pipeline; they are research goals. The router should route correctly to `discovery`.

**If misrouted to `operational`**: the query goes to `_handle_task()` → `execute_task()` → `ToolConsultantAgent.decide()` **directly**, bypassing the entire ScientistPanel + ResearchLoop. The system would produce a tool plan for multiomics QC + integration without any literature grounding, hypothesis formation, or adversarial review. The final output would be purely computational, not scientific.

---

## Stage 2 — SessionDispatcher

**File**: `agents/session_dispatcher.py` → `_handle_research_task()`

### What happens

```python
pipeline_mode_map = {"discovery": "full", "ambiguous": "brief"}
pipeline_mode = "full"   # for our query
loop_result = self.research_loop.run(user_question=resolved_message, pipeline_mode="full")
```

`resolved_message` is `route["resolved_intent"]` — the router's restatement of the user's goal. For this query the router's restatement should be close to the original; no ambiguous references to resolve.

### Critical conditional

If `self.research_loop is None` (ResearchLoop not configured), the dispatcher returns:

```
"status": "failed"
"message": "This request was classified as exploratory/discovery, but ResearchLoop is not configured..."
```

The user would receive a failure with no scientific output. This is a **deployment configuration issue**, not a code bug, but it is the most likely failure mode in practice: if the ResearchLoop is not wired at startup, all discovery queries silently fail.

---

## Stage 3 — ResearchLoop.run() Phase 0: Formulation

**File**: `agents/research_loop.py` → `_run_formulation_stage()`

Since `ScientistPanel` has `run_initial_panelists`, the new code path is taken (not legacy `formulate()`). The formulation stage is: panelists → record outputs → mediator formulate → callback loop → adversary until accepted.

### 3A: ScientistPanel.run_initial_panelists()

Three `ToolCallingAgentRunner` instances run in parallel. Each runs its role-specific prompt against the same user question and data summary. Tool access: `retrieve_literature`, `search_paper_wiki`, `fetch_paper_content`.

**Biologist** (`biologist_formulation.md`):

The biologist reframes the query through the lens of *what biology the data could actually address*. For this query, expected biological reasoning purposes:

1. How does the field define disease-associated cell states in AD brain (microglia, astrocytes, oligodendrocytes, inhibitory neurons)? What markers and signatures prior single-cell AD studies established?
2. What is the biological relationship between chromatin accessibility and transcriptional programs in neurodegenerative disease? What cell-type-specific regulatory programs have prior work linked to AD pathology?
3. What is the biological validation pattern for claims about cell-type-specific CREs driving disease gene expression (peak-to-gene linkage, TF footprinting, GWAS variant enrichment in accessible regions)?

The biologist does **not** decide statistical units or computational methods. Output: `method_adequacy` verdict (likely `sufficient_with_extension` — existing snMultiomics methods exist but linking CREs to GWAS variants requires added validation), novelty candidates from the biological angle, evidence patterns from retrieved papers.

**Statistician** (`statistician_formulation.md`):

Expected reasoning purposes:
1. What is the correct statistical unit for differential accessibility in snATAC-seq with disease state as the variable? (Cell vs. pseudobulk vs. mixed-model — prior work on pseudoreplication in single-cell)
2. How is disease-state confounding controlled in paired RNA+ATAC analysis? What covariates (donor, batch, cell-type composition) are needed?
3. What statistical tests are valid for peak-to-gene association given the zero-inflated, sparse nature of snATAC-seq counts?

Output: verdict on whether differential accessibility analysis as framed is statistically valid, constraints on what the plan must control for, novelty candidates from the statistical angle (e.g., cell-type-composition-aware differential testing).

**Bioinformatician** (`bioinformatician_formulation.md`):

Expected reasoning purposes:
1. What integration methods exist for joint snRNA-seq + snATAC-seq? (MultiVI, Seurat WNN, ArchR, scGLUE) — what do papers report about their performance on DLPFC-scale data?
2. What tools exist for TF motif enrichment and differential TF activity in snATAC-seq (ChromVAR, SCENIC+, pySCENIC)? What are the parameter regimes, and how do they scale to full multiomics?
3. What methods link accessible peaks to target genes (peak-to-gene correlation, ABC model, GRN inference)? What are the limitations of each and what data requirements do they have?

Output: canonical implementation recommendation, method adequacy verdict, computational feasibility assessment.

### 3B: MediatorAgent.formulate()

**Prompt**: `updated_prompts/mediator_formulation.md`

The Mediator receives:
- `user_task`: the full query text
- `data_summary`: profiled workspace (cell counts, modalities, batch structure from `profile_workspace()`)
- `panelist_outputs`: three text blocks from 3A
- `previous_mediator_outputs`: `[]` (Phase 0, no prior mediator history)
- `previous_tool_decisions`: `[]`
- `previous_analyzer_reports`: `[]`
- `callback_history`: `[]`
- `evidence_state`: `{}`
- `trajectory_summary`: graph state (empty at Phase 0)

**Synthesis process** (from prompt):

1. **Convergence/divergence/absence** across three panelist syntheses. For this query: convergence likely on the importance of pseudobulk differential accessibility; possible divergence on which integration method is preferred (Bioinformatician may prefer MultiVI while Statistician flags donor-level pseudoreplication concerns).

2. **Method adequacy integration**: Bioinformatician drives main method. Likely `sufficient_with_extension` — joint embedding exists (MultiVI) but peak-to-gene linkage and GWAS variant enrichment are extensions.

3. **Scientific hypothesis formation** (Mediator's exclusive job). Expected hypothesis for this query:
   > "AD-associated changes in chromatin accessibility are cell-type-specific and enriched at cis-regulatory elements that drive transcriptional programs in microglia, astrocytes, and oligodendrocytes; accessible chromatin regions containing GWAS risk variant enrichment are linked to disease-relevant target genes through peak-to-gene co-accessibility."

   This is specific, testable with snMultiomics DLPFC data, and falsifiable (if no enrichment of AD GWAS variants in cell-type-specific accessible regions, or if peak-to-gene correlations show no disease-state specificity, the hypothesis is refuted).

4. **Novelty candidate selection** (four-gate filter). For this query, strong novelty candidates might include:
   - Cell-type-specific TF network inference linking AD-accessible CREs to downstream gene expression (needs TF footprinting + GRN)
   - GWAS variant enrichment analysis in cell-type-specific accessible regions (requires GWAS summary stats in metadata or user-provided)
   - Intercellular signaling inference from co-accessibility across cell types

   Gate 2 (dataset affordance) may block GWAS enrichment if the data summary does not confirm GWAS summary stats are available. The Mediator would correctly move this to `future_research_directions`.

5. **Seven-section plan**. Each step carries `biological_goal`, `statistical_requirement`, `computational_approach`, `decision_criterion`. Expected steps:
   - QC: RNA + ATAC dual-modality quality filtering, cell-level intersect
   - Integration: Joint embedding (MultiVI or Seurat WNN), dimensionality selection, UMAP
   - Cell type annotation: Marker-based annotation of RNA clusters, cross-modality validation
   - Differential accessibility: Pseudobulk DAR by cell type × disease state
   - TF motif enrichment: ChromVAR or SCENIC+ on cell-type-specific peaks
   - Peak-to-gene linkage: Co-accessibility correlation within cell types
   - Downstream interpretation: Gene ontology enrichment, disease-gene overlap

6. **Output**: either `formulation_status: "ready_for_adversary"` (plan ready) or `"needs_panelist_callback"` (gap identified). For this well-framed query, likely `ready_for_adversary` after the first call.

**What the Mediator actually receives vs. what it should receive**:

The context builder `context_for_mediator_formulation()` now includes `previous_mediator_outputs`, `previous_tool_decisions`, `previous_analyzer_reports` — all empty at Phase 0. This is correct: no prior history exists. The panelist outputs are read from `working_memory["panelist_outputs"]` after `record_panelist_outputs()` is called. ✓

### 3C: _complete_mediator_callbacks()

If the Mediator returns `formulation_status: "needs_panelist_callback"`, targeted callbacks run. For this query, a likely callback: the Mediator identifies a gap in how peak-to-gene linkage should be validated statistically (Statistician should address). The Statistician callback returns reasoning on distance-based vs. correlation-based linkage and what significance thresholds are appropriate.

After `synthesize_callbacks()`, `record_callback_history()` is committed. ✓ (H1 fix: callback history is committed *after* synthesis, so the Mediator's context for synthesis only contains prior rounds, not the current round being synthesized.)

### 3D: _run_adversary_until_accepted()

**File**: `agents/adversarial_panelist.py` → `run(adversary_context=...)`

The Adversary receives `context_for_adversary(candidate_plan=..., candidate_trajectory_decision=...)` which includes:
- `user_question`, `candidate_plan`, `candidate_trajectory_decision`
- `evidence_state: {}` (Phase 0)
- `panelist_evidence_summary`: the panelist outputs from working_memory
- `cited_papers`: collected from panelist outputs
- `prior_critiques: []` (first round)

**Adversary review process** (from `updated_prompts/adversary.md`):

The Adversary works through seven checks:
1. Can the plan answer the research question? For our query: yes, snMultiomics + pseudobulk DAR + peak-to-gene linkage are appropriate.
2. Is the main method valid? MultiVI or WNN is appropriate for snRNA+ATAC joint embedding.
3. Do downstream analyses overclaim? Risk: peak-to-gene correlation does not establish causality; the Adversary should flag if the plan claims causal linkage.
4. Are validation metrics independent? Risk: if validation uses the same cells as inference.
5. Is the novel design falsifiable?
6. Are limitations honest? Risk: the plan may understate pseudoreplication concerns (multiple cells per donor as observations).
7. Missing analyses? Prior AD single-cell multiomics work (e.g., Sun et al. 2023, Morabito et al. 2021) establishes evidence patterns — if the plan deviates from these, the Adversary should flag.

**Expected verdict**: `needs_revision` — the pseudoreplication/pseudobulk statistical unit issue is likely flagged (if the initial plan used cell-level DAR rather than pseudobulk). If the Mediator's plan already uses pseudobulk, verdict could be `survives`.

**On `needs_revision`**: MediatorAgent.revise_from_adversary() is called. The revised plan should address the critique (switch to pseudobulk DAR, strengthen statistical unit wording). `_resolve_candidate_revision()` checks if the revision is materially different from the prior plan. If yes, `status: "needs_revision"` continues to next round; if `force_terminal` (last round), `status: "accepted"`.

**What the Mediator sees during revision**: `context_for_mediator_adversary_revision()` now includes `prior_mediator_outputs` (populated: the formulation output was recorded via `_record_mediator_output`), `prior_tool_decisions: []`, `prior_analyzer_reports: []`. The adversary critique is the direct argument. ✓

**Formulation result**: `_candidate_resolution_to_formulation_result()` produces a uniform dict with `status`, `selected_research_plan`, `trajectory_decision`, `adversarial_review_status`, `adversarial_review_interpretation`, `resolution_reason`. ✓

---

## Stage 4 — ResearchLoop.run() Phase 0: Plan Commit

After formulation completes with `status: "accepted"`, the main loop:

```python
research_state.commit_initial_plan(
    selected_plan=research_plan,
    evidence_state=research_context.get("evidence_state", {}),
    trajectory_decision=formulation_result.get("trajectory_decision", {}),
    ...
)
```

`research_state.evidence_state` is set once here. **This is the last time it is updated via `commit_initial_plan`**. Post-analysis `evidence_state` from Mediator outputs only updates `working_model` and `research_context`, not `research_state.evidence_state`. See **Behavioral Gap 1** below.

---

## Stage 5 — ResearchLoop Phases 1–N: Execution Loop

### 5A: ToolConsultantAgent.decide()

**File**: `agents/tool_consultant.py`

The consultant receives `user_message` (the session-formatted research plan + user question), `session_state` including `research_plan`, `data_summary`, `state_graph_context`. It queries `wiki_query_tasks` and `wiki_graph_query` to ground the plan in available tools.

**For this query, expected DAG**:

```
Layer 1: rna_qc_basic         (single variant: min_genes, max_pct_mito)
Layer 2: atac_qc_basic        (single variant: min_tsse, min_frags)
Layer 3: multi_qc_intersect   (single variant: intersect shared cells)
Layer 4: multi_embed_multivi  (possibly 2 variants: latent_dim 20 vs. 30 → multi-path)
Layer 5: rna_cluster_leiden   (possibly 2 variants: resolution 0.5 vs. 0.8)
Layer 6: rna_annotate         (single variant)
Layer 7: atac_diff_chromvar   (single variant: disease state group)
Layer 8: rna_de_wilcoxon      (single variant: pseudobulk by cell type × disease)
```

If multi-path: an `objective_name` (e.g., `silhouette_score`) is required for ranking. Decision schema validation enforces this.

`_record_tool_decision(research_state, decision, source="tool_consultant_initial", phase_number=1)` is called immediately after. ✓

After alignment review (if `alignment_reviewer` is configured), a second `_record_tool_decision(..., source="tool_consultant_aligned")` is called. `working_memory["tool_decisions"]` will have 2 compact entries for Phase 1. ✓

**Critical note**: the tool consultant receives `user_message` (the formatted research plan + question) but NOT `research_state.context_for_tool_consultant()` directly. The session_state injected into `_build_session_state()` includes `state_graph_context=research_state.context_for_tool_consultant(...)`. So the consultant does receive the research plan and evidence state — but they arrive via `session_state`, not as a direct context dict. This is by design: the consultant is a standalone agent that predates the research_state architecture.

### 5B: _execute()

DagExecutor runs the DAG layers. For multiomics:
- `rna_qc_basic` + `atac_qc_basic` can run in parallel
- `multi_qc_intersect` waits for both
- `multi_embed_multivi` runs joint embedding on intersected cells
- All downstream layers run in sequence

Each tool writes output metadata to `adata.uns`, which DagExecutor auto-injects into downstream layers.

### 5C: AnalyzerPanel.analyze()

**File**: `agents/analyzer_panel.py`

Receives: `user_question`, `research_plan`, `dag_result`, `figure_paths`, `working_model` (contains `evidence_state` from the last commit + mediator output), `phase_number`.

**Round 1a — ResultsInterpreter**: reads execution outputs and interprets figures (UMAP plots, cluster structure, accessibility tracks). For our AD query: does the UMAP show disease-state separation? Are microglia clusters present and separable? Do chromVAR scores show cell-type-specific TF enrichment differences?

**Round 1b — LiteratureGrounder + DatabaseValidator in parallel**:
- LiteratureGrounder: compares results to published AD single-cell studies. Are the cell types recovered consistent with prior DLPFC work? Do differential accessibility patterns overlap with known AD-associated regulatory regions?
- DatabaseValidator: validates against external databases (CellMarker for cell-type markers, JASPAR for TF motifs, etc.)

Both receive ResultsInterpreter output before starting. ✓

**Round 2 — AnalyzerMediator**: synthesizes into `analyzer_report` with `results_summary`, per-claim `hypothesis_status`, `claim_updates`, `open_questions`, `evidence_quality`.

`_record_analyzer_report(research_state, analyzer_report, source="analyzer", phase_number=1)` is called. ✓

### 5D: MediatorAgent.post_analysis()

**Context**: `research_state.context_for_mediator_post_analysis()` includes:
- `evidence_state`: **always the Phase-0 value** (see Behavioral Gap 1)
- `previous_mediator_outputs`: compact records of all prior mediator calls (formulation, revisions, callback syntheses) ✓
- `previous_tool_decisions`: compact records of tool consultant decisions ✓
- `previous_analyzer_reports`: compact records of prior phase analyzer reports ✓
- `analyzer_report`: current phase's full report (passed as argument, not from working_memory)
- `dag_result_summary`, `tool_decision`

**Decision process** (from `updated_prompts/mediator_post_analysis.md`):

1. Read analyzer's `overall_interpretation` and `interpretation_loop`.
2. Update `evidence_state` based on `claim_updates` → but this update only lives in the **output dict**, not in `research_state.evidence_state`. (Behavioral Gap 1)
3. Decide if internal panelist callbacks are needed (tools: `ask_panelist_for_more_reasoning`, `ask_panelist_for_more_literature`).
4. Choose one of five decisions.

For Phase 1 of the AD query, likely outcome:
- If all DAG steps succeeded and results are interpretable → `accept_and_conclude` or `self_revise_plan` (if additional validation is needed)
- If accessibility analysis shows strong disease-state signal in microglia and astrocytes, consistent with literature → `accept_and_conclude`
- If cell annotation is incomplete or the TF activity patterns are uninformative → `self_revise_plan` (e.g., switch to a different TF inference method, add a peak-to-gene step that wasn't in Phase 1)

`_record_mediator_output(research_state, post_decision, source="post_analysis", phase_number=1)` is called. ✓

If `self_revise_plan` → `_review_post_analysis_candidate_if_needed()` runs the adversary again on the revised plan before committing it. All findings I1, I2, I3 are fixed. ✓

---

## Behavioral Gaps and Correctness Assessment

### Gap 1 — `research_state.evidence_state` is never updated after Phase 0 (ongoing transitional issue)

**What happens**: `commit_initial_plan()` sets `research_state.evidence_state` from the formulation output. After each phase, `post_decision["evidence_state"]` (the Mediator's updated claim statuses) is written to `working_model` and `research_context`, but **not** back to `research_state.evidence_state`.

**Effect on the AD query**: `context_for_mediator_post_analysis()["evidence_state"]` always returns the Phase-0 evidence state regardless of how many phases have run. By Phase 3 of a multi-phase AD analysis, the Mediator receives an `evidence_state` that says every claim is `"pending"` even though Phase 1 and 2 already established microglia DAR and TF enrichment.

**What should happen**: After each phase's post-analysis decision, the Mediator's returned `evidence_state` should be written back to `research_state.evidence_state`. Likely location: in `ResearchLoop.run()` after `post_decision` is finalized, before moving to the next phase.

**Severity**: Medium. In single-phase runs (which `accept_and_conclude` on Phase 1) there is no effect. In multi-phase runs the Mediator loses evidence continuity.

### Gap 2 — `working_model` is not integrated into ResearchState; its update path bypasses the evidence state architecture

**What happens**: `working_model` is a local loop variable initialized at Phase 0 as `{"evidence_state": research_state.evidence_state, "mediator_output": brief}`. It is updated when `post_decision["evidence_state"]` is truthy. It is passed to `analyzer_panel.analyze()` as the `working_model` argument. But it is never accessible through `ResearchState` and is not part of any context builder.

**Effect on the AD query**: AnalyzerPanel receives current evidence state via `working_model`, but the Mediator's post-analysis context builder constructs `evidence_state` from `research_state.evidence_state` (stale). The two agents are working from different evidence pictures.

**What should happen**: Evidence state updates should flow through `ResearchState`, not through a local dict variable. The transitional plan already names this (`working_model` → `research_state.evidence_state`).

### Gap 3 — Adversary receives stale `evidence_state` during post-analysis plan revision

**What happens**: `context_for_adversary()` builds from `research_state.evidence_state` (stale Phase-0 value). When `_review_post_analysis_candidate_if_needed()` calls the adversary to review a revised plan proposed at Phase 3, the adversary does not know that Phases 1 and 2 already established or refuted key claims.

**Effect on the AD query**: If Phase 1 established that microglia show AD-specific accessibility changes (claim C1 = supported), but `evidence_state` still says C1 = pending, the adversary may challenge a Phase 3 revised plan that conservatively keeps microglia analysis — when in fact that analysis is already validated. The adversary works with less information than it should.

**Severity**: Low-Medium. Adversary challenges tend to be conservative; it will not falsely approve bad plans due to stale evidence. But it may generate unnecessary revision requests.

### Gap 4 — SessionRouter faces a genuine ambiguity risk for CellBench-style queries

**What happens**: The CellBench-style query is very long and describes the study design in detailed technical language ("snRNA-seq and snATAC-seq on dorsolateral prefrontal cortex tissues"). This phrasing sounds procedural. The router must infer from the *goals* ("characterize", "identify", "infer", "investigate") that this is discovery, not operational.

**Risk**: A router calibrated on shorter, simpler queries may over-weight the methodological description and under-weight the open-ended research goals. The session router prompt explicitly warns against this: "Do not classify a routine analysis request as discovery merely because it is biological." The converse failure mode — classifying a discovery request as operational because it is technically worded — is not explicitly guarded against.

**Mitigation**: The four study aims at the end of the query ("characterize cell-type-specific regulatory landscapes", "identify AD-associated cis-regulatory elements", "infer regulatory interactions", "investigate transcription factor programs") are all discovery-framed. A capable LLM router should catch these.

### Gap 5 — Mediator post-analysis prompt expects `call_panelists` as a potential decision but it is no longer a valid decision type

**What happens**: The `mediator_post_analysis.md` prompt lists five decisions: `accept_and_conclude`, `self_revise_plan`, `continue_with_same_research_plan`, `ask_user`, `declare_unanswerable`. It also says "Do not emit call_panelists as a final decision" — consistent with the code. However, the internal panelist callback mechanism is now handled by MediatorAgent itself (via `panelist_callback_executor`), not by the prompt's decision output. The prompt explicitly says to call `ask_panelist_for_more_reasoning` and `ask_panelist_for_more_literature` as internal tools during the post-analysis run.

**Status**: consistent — prompt and code agree. The `_extract_panelist_callback_requests()` mechanism only fires on the post-analysis output if `decision == "needs_panelist_callback"`. Since that is no longer a valid decision type (N1 fix), this dead path is unreachable. ✓

### Gap 6 — `_formulate_full()` in ScientistPanel is now dead code in the ResearchLoop path

**What happens**: `ScientistPanel.formulate()` and `_formulate_full()` still exist but are never called by `ResearchLoop`. ResearchLoop calls `run_initial_panelists()` directly, then delegates to `MediatorAgent.formulate()`. The `_formulate_full()` path (panelists → mediator → callback loop → adversarial loop, all inside ScientistPanel) is only reached if `run_initial_panelists` is absent (legacy path, `legacy_mediator_flow = True`).

**Effect**: No functional effect. Legacy code is dead. Confusing to read if `ScientistPanel.formulate()` is encountered in isolation.

---

## System Behavior vs. Expected Behavior: Summary Table

| Stage | Expected Behavior | Actual Behavior | Match? |
|-------|-------------------|-----------------|--------|
| **SessionRouter** | Route: task, intent: discovery | LLM call, likely correct; risk of operational misclassification on long technical query | Likely ✓ |
| **SessionDispatcher** | Hand off to ResearchLoop with pipeline_mode="full" | Correctly mapped; fails silently if research_loop is None | ✓ with deployment caveat |
| **run_initial_panelists** | Three panelists parallel, RAG tools, independent outputs | Runs via ScientistPanel._run_round1_formulate(); outputs recorded via record_panelist_outputs() | ✓ |
| **MediatorAgent.formulate** | Synthesize panelists → hypothesis → 7-section plan; no direct retrieval | single_llm_call with correct context including prior mediator/tool/analyzer outputs | ✓ |
| **Callback loop** | Prior history in context when synthesizing; state updated after synthesis | record_callback_history() called after synthesize_callbacks() | ✓ (H1) |
| **Adversary critique** | One critique per run; returns verdict + structured challenges | AdversarialPanelist.run() → single _run_challenge(); verdict + plan dict | ✓ |
| **Adversary loop exit** | Uniform helper with resolution_reason, adversarial_review_status | _candidate_resolution_to_formulation_result() used for all exits including survives/skipped | ✓ (H2) |
| **evidence_state after formulation** | Written to research_state.evidence_state via commit_initial_plan | ✓ written once | ✓ |
| **Tool consultant** | Ground plan in wiki, produce valid DAG; record to working_memory | _record_tool_decision() called twice (initial + aligned); compact events stored | ✓ (G1) |
| **Analyzer** | 3-round: ResultsInterpreter → LitGrounder+DBValidator parallel → AnalyzerMediator | Confirmed in analyzer_panel.py | ✓ |
| **Analyzer recording** | Record to working_memory for Mediator context | _record_analyzer_report() called; compact events stored | ✓ (G1) |
| **Mediator post-analysis context** | Receives previous_mediator_outputs, previous_tool_decisions, previous_analyzer_reports | All populated; but evidence_state is stale after Phase 1 | Partial ✗ (Gap 1) |
| **evidence_state continuity** | Updated per phase from post_decision["evidence_state"] | Only working_model updated; research_state.evidence_state frozen at Phase 0 | ✗ (Gap 1, 2, 3) |
| **post-analysis adversary** | survives/skipped → helper; needs_revision → _resolve_candidate_revision; budget exhausted → declare_unanswerable | All paths correct; I1/I2/I3 fixed | ✓ |
| **legacy flow** | Should be unreachable for current ScientistPanel | legacy_mediator_flow=False for all current configurations | ✓ (dead code, not a bug) |

---

## The Key Structural Problem: Evidence State is Single-Session Read-Only

The most significant behavioral gap for a multi-phase AD analysis is **evidence state staleness**. The system's architecture has three separate evidence representations in flight simultaneously:

```
research_state.evidence_state         ← set once at commit_initial_plan(); never updated
working_model["evidence_state"]       ← updated from post_decision each phase; passed to Analyzer
research_context["evidence_state"]    ← updated in _extract_research_context() on plan revision
```

The Mediator's context builder reads from `research_state.evidence_state` (stale). The Adversary's context also reads from `research_state.evidence_state` (stale). Only the Analyzer receives current evidence via `working_model`.

For the AD query in a single-phase run (Phase 1 → `accept_and_conclude`), this does not matter. For a multi-phase run (which is the common case for complex multiomics questions), the Mediator at Phase 2 does not know what Phase 1 established. It must re-read the Phase 1 analyzer report (which is now in `previous_analyzer_reports` via working_memory) to reconstruct what was established.

**The mitigation that partially compensates**: `previous_analyzer_reports` in the context builders now carries compact versions of all prior analyzer reports. The Mediator can infer from these what was established, even without a formal updated `evidence_state`. But this is implicit inference from report summaries rather than explicit structured evidence state. The Mediator is doing more reasoning work than it should.

---

## Recommendation for the AD Query

For the specific AD multiomics query, the system will:
1. Correctly route to discovery → ResearchLoop → full pipeline
2. Correctly run three panelists in parallel retrieving AD + multiomics literature
3. Correctly form a hypothesis about cell-type-specific regulatory architecture
4. Likely receive a `needs_revision` adversary verdict on statistical unit (pseudobulk vs. cell-level) and produce a defensible revised plan
5. Produce a valid multi-layer DAG (QC → intersect → joint embed → cluster → annotate → differential accessibility → TF enrichment)
6. Analyze results through ResultsInterpreter + LiteratureGrounder + DatabaseValidator
7. Make a post-analysis decision (likely `self_revise_plan` to add peak-to-gene linkage if not in Phase 1, or `accept_and_conclude` if Phase 1 covered all stated goals)

**The system will work correctly for Phase 1**. For multi-phase runs, evidence state staleness will silently degrade Mediator context quality from Phase 2 onward. This is the primary correctness gap for long-running AD analysis sessions.
