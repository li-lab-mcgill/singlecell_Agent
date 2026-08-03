# End-to-End Behavioral Review v2 — AD Multiomics Query (Full Stack Trace)

**Reviewed**: 2026-05-26
**Scope**: Full pipeline from HTTP request through frontend, routing, formulation, execution, analysis, and response
**Query type**: Discovery — snRNA-seq + snATAC-seq, AD DLPFC, cell-type-specific regulatory architecture

---

## The Query

> Alzheimer's disease (AD) is a progressive neurodegenerative disorder... [the full 500-word CellBench-style AD DLPFC multiomics query, including GWAS non-coding variant motivation, CRE-TF linkage goals, bulk epigenomics limitations, and four specific study aims: characterize cell-type-specific regulatory landscapes, identify AD-associated CREs, infer regulatory interactions between accessible chromatin regions and target genes, investigate TF programs]

---

## System Architecture: Full Stack

```
HTTP POST /chat
  └─ _FrontendState.chat()
       └─ SessionDispatcher.handle()
            ├─ SessionStateStore.snapshot() → persistent_session
            └─ SessionRouter.route()
                 └─ validate_session_route() → {route="task", intent_mode="discovery"}
                      └─ SessionDispatcher._handle_research_task()
                           └─ ResearchLoop.run(user_question=resolved_intent, pipeline_mode="full")
                                ├─ [Phase 0] _run_formulation_stage()
                                │     ├─ ScientistPanel.run_initial_panelists()
                                │     ├─ MediatorAgent.formulate()
                                │     ├─ _complete_mediator_callbacks()
                                │     └─ _run_adversary_until_accepted()
                                │           └─ AdversarialPanelist.run() [×N rounds]
                                │                └─ MediatorAgent.revise_from_adversary()
                                │
                                └─ [Phases 1–N] execution loop
                                      ├─ ToolConsultantAgent.decide()
                                      ├─ _review_and_maybe_revise_decision()
                                      ├─ _execute() → DagExecutor
                                      ├─ AnalyzerPanel.analyze()
                                      └─ MediatorAgent.post_analysis()
                                            └─ [if self_revise_plan] _review_post_analysis_candidate_if_needed()
```

---

## Stage 0: HTTP Frontend (server.py → `_FrontendState.chat()`)

### What happens

`do_POST()` receives a `/chat` POST request with the AD query as body. It calls `state.chat(clean_message)`.

`chat()` assembles a **per-turn `session_state`**:

```python
session_state = {
    "input_h5ad_path":  args.input_mod1,          # snRNA-seq h5ad path
    "input_mod2_path":  args.input_mod2,           # snATAC-seq h5ad path (may be None)
    "tool_artifact_dir": str(self.tool_artifact_dir),
    "initial_query":    persistent.get("initial_query"),
    "current_message":  clean_message,             # the full AD query text
    "history":          self.session_store.history(limit=8),
}
```

Then calls `session_dispatcher.handle(user_message=clean_message, session_state=session_state, session_tag=session_tag)`.

### Construction-time wiring (critical context)

`_FrontendState.__init__()` creates the ResearchLoop:

```python
self.research_loop = ResearchLoop(
    scientist_panel=scientist_panel,
    analyzer_panel=analyzer_panel,
    tool_consultant=self.tool_consultant,
    dag_executor=self.dag_executor,
    coder=self.coder,
    short_term_memory=short_term_memory,
    input_h5ad_path=args.input_mod1,
    data_paths=[args.input_mod2] if args.input_mod2 else None,   # ← ATAC modality
    result_dir=Path(self.config.result_dir) / "research_loop",
    max_phases=args.research_max_phases,
    # adversarial_panelist=  ← NOT PASSED
    # mediator_agent=        ← NOT PASSED
    # alignment_reviewer=    ← NOT PASSED
    # attributing_critic=    ← NOT PASSED
    # context_manager=       ← NOT PASSED
)
```

**What is correctly wired**:
- `input_mod2` is passed as `data_paths` → `profile_workspace([mod1, mod2], data_summary)` sees both modalities. ToolConsultant and panelists will know about the ATAC file.
- `ShortTermMemory` is wired → phase traces are recorded across phases.

**What is NOT wired (lazy construction via `_ensure_*`):**

| Component | Construction-time | Lazy fallback | Failure mode |
|-----------|------------------|---------------|--------------|
| `MediatorAgent` | Not passed | `_ensure_mediator_agent()` constructs one from `scientist_panel.client` + `scientist_panel.engine_name` | Silent construction; fails only if `scientist_panel` has no `client` or `engine_name` |
| `AdversarialPanelist` | Not passed | `_ensure_adversarial_panelist()` reads `scientist_panel.adversarial_panelist` | **RuntimeError** if `ScientistPanel` doesn't expose an `adversarial_panelist` attribute — ALL discovery queries fail |
| `alignment_reviewer` | Not passed | Falls back to `scientist_panel.adversarial_panelist.review_alignment` | If None: all tool plans get `verdict="survives"` silently — alignment review is silently disabled |
| `AttributingCritic` | Not passed | Skipped — `if self.attributing_critic is not None:` | No per-step attribution; not a correctness issue |
| `ContextManager` | Not passed | Skipped — `if self.context_manager is not None:` | No layered context; partially compensated by `ShortTermMemory` |

### [GAP M1] HIGH — AdversarialPanelist not passed at construction

`_ensure_adversarial_panelist()`:
```python
adversary = getattr(self, "adversarial_panelist", None)
if adversary is not None:
    return adversary
adversary = getattr(self.scientist_panel, "adversarial_panelist", None)
if adversary is None:
    raise RuntimeError("AdversarialPanelist is required for ResearchLoop formulation.")
```

If `ScientistPanel` does not expose `adversarial_panelist` as an attribute, every call to `_run_formulation_stage()` raises `RuntimeError`. The exception is caught at line 217 of `_handle_research_task()`:

```python
try:
    loop_result = self.research_loop.run(...)
except Exception as exc:
    loop_result = {"status": "failed", "error": str(exc), "phases_completed": 0}
```

The user receives a "failed" response with status "failed". The error message mentions `RuntimeError: AdversarialPanelist is required` — not user-friendly. All discovery queries fail silently as infrastructure errors.

**Expected behavior**: `AdversarialPanelist` should be instantiated and passed explicitly to `ResearchLoop` at startup in `_FrontendState.__init__()`, just as `ScientistPanel` and `AnalyzerPanel` are.

### [GAP M2] MEDIUM — alignment_reviewer not wired; all tool plans pass alignment silently

`_review_and_maybe_revise_decision()`:
```python
reviewer = self.alignment_reviewer or getattr(
    getattr(self.scientist_panel, "adversarial_panelist", None), "review_alignment", None
)
if reviewer is None:
    decision.setdefault("tool_plan_alignment_review", _default_alignment_review("No alignment reviewer configured."))
    decision.setdefault("adversarial_alignment_review", decision["tool_plan_alignment_review"])
    return decision
```

`_default_alignment_review()` returns `{"verdict": "survives", ...}` — so every tool plan passes alignment review without critique. For a complex multiomics pipeline, this means:
- A plan that clusters before QC would pass
- A plan missing batch correction would pass
- A plan claiming GWAS enrichment without matched peak calls would pass

---

## Stage 1: SessionDispatcher.handle()

### What happens

```python
session_state["persistent_session"] = _trim_persistent_session(self.state_store.snapshot())
route = self.router.route(user_message=user_message, session_state=session_state, ...)
```

`_trim_persistent_session()` strips `history`, trims `last_decision` to `{decision, task, objective_name}`, trims `last_result`, trims `last_route` to `{route, reason}`. This prevents the router from being flooded with prior raw results.

For a fresh session (first message), `persistent_session` is essentially empty — `last_decision`, `last_result`, `last_route` are all absent. This is correct: the router has no prior context to distract it.

`session_state` passed to the router includes `input_h5ad_path`, `input_mod2_path`, `tool_artifact_dir`, `initial_query`, `current_message`, `history` (last 8 turns), and `persistent_session`. The router sees the modality info (ATAC path present) and the full message text.

### [GAP M3] LOW — planning_state not forwarded to ResearchLoop.run()

```python
planning_state = self._build_task_session_state(session_state)
resolved_message = route.get("resolved_intent") or user_message
...
loop_result = self.research_loop.run(
    user_question=user_message,   # ← resolved_message, not planning_state
    pipeline_mode=pipeline_mode,
)
```

`planning_state` contains prior plan info, execution context, previous results summary — useful for multi-turn sessions. But `ResearchLoop.run()` only accepts `user_question` and `pipeline_mode`; it does not receive `planning_state`. For the first turn this is benign. For a follow-up discovery query ("now also check if these CREs are enriched in AD GWAS loci"), the ResearchLoop would not know what was done in the prior turn — it must re-run the full formulation stage from scratch instead of extending from prior evidence.

---

## Stage 2: SessionRouter.route()

### What happens

`ToolCallingAgentRunner` runs with `max_iterations=4, max_tool_calls=0` (pure LLM, no tool calls). Prompt is `SESSION_ROUTER_PROMPT.format(user_message=..., session_state=...)` + `SESSION_ROUTER_SCHEMA_PROMPT`.

The AD query text (500 words) plus session_state JSON are passed as the user message.

### Expected routing decision

**Route**: `task` — the query requires multi-step analysis. It cannot be answered from general knowledge alone.

**Intent mode**: `discovery` — the query uses open-ended research verbs throughout:
- "characterize cell-type-specific regulatory landscapes"
- "identify AD-associated cis-regulatory elements"
- "infer regulatory interactions"
- "investigate transcription factor programs"

None of these are concrete pipeline instructions. The query gives a scientific motivation (GWAS non-coding variants → CRE → TF → cell-type expression) rather than naming a specific tool or workflow. The session router's `discovery` definition covers exactly this pattern.

**Resolved intent**: should faithfully restate the four study aims without collapsing them.

### [GAP M4] MEDIUM — resolved_intent is the sole user_question for all downstream agents

`resolved_message = route.get("resolved_intent") or user_message`

This restatement is passed verbatim as `user_question` to:
- `scientist_panel.run_initial_panelists()` — determines what biology the panelists formulate about
- `mediator.formulate()` — determines the hypothesis and plan
- `tool_consultant.decide()` — determines what computational steps are planned
- `analyzer_panel.analyze()` — determines the interpretive frame
- `mediator.post_analysis()` — determines what counts as "done"

If the router compresses "characterize cell-type-specific regulatory landscapes, identify AD-associated CREs, infer regulatory interactions between accessible chromatin regions and target genes, and investigate TF programs" into "analyze AD multiomics data", the downstream agents lose:
- The specific four-aim framing
- The GWAS variant enrichment validation requirement
- The peak-to-gene linkage goal
- The TF footprinting goal

The biologist might not retrieve GWAS enrichment papers; the statistician might not add pseudobulk DA testing requirements; the ToolConsultant might not plan a GWAS enrichment step. The entire scientific scope narrows.

**Expected behavior**: the router should produce a `resolved_intent` that is a faithful 2-3 sentence restatement preserving all four goals. The router prompt should instruct this explicitly.

### [GAP M5] LOW — invalid intent_mode silently normalizes to "ambiguous"

```python
# validate_session_route():
if intent_mode not in VALID_INTENT_MODES:
    intent_mode = "ambiguous"
```

If the LLM produces `"exploratory"` or `"research"` as intent_mode (both plausible variations), the dispatcher routes to `_handle_ambiguous_task()` which returns a clarification request:

```python
"I need to clarify the goal before running analysis. Option 1: operational. Option 2: discovery. Please choose."
```

The user would receive a dead-end clarification prompt instead of any analysis. No error is raised; the normalization is silent. For a 500-word query with strong discovery signals, this is a user-experience failure.

**Expected behavior**: the router retry loop (up to 4 iterations) should catch this; the response handler returns `done=False` with a schema correction prompt if the route itself is invalid. But since `intent_mode` normalization does NOT raise `DecisionValidationError`, the retry loop is never triggered — the invalid value is silently accepted.

---

## Stage 3: SessionDispatcher._handle_research_task()

### What happens

```python
pipeline_mode = pipeline_mode_map.get(intent_mode)   # "full"
loop_result = self.research_loop.run(
    user_question=user_message,
    pipeline_mode="full",
)
```

The loop_result is unwrapped:
- `final_report` = `loop_result.get("final_report")` — the last AnalyzerPanel report
- `message` = `final_report.get("summary") or final_report.get("conclusion") or ...`
- If `loop_result["status"] in ("done", "abstain", "max_phases_reached", "awaiting_user")` → result status = "completed" (even "abstain" is shown as "completed")

**Note**: an `"abstain"` result (no defensible research plan found) is shown to the user as `status: "completed"` with `message: "No defensible research plan could be formed."`. This may confuse users who expect a "failed" status.

---

## Stage 4: ResearchLoop.run() — Phase 0 Formulation

### What happens

```python
research_state = ResearchState(
    user_question=user_question,     # resolved_intent text
    data_summary=self.data_summary,  # profiled from mod1 + mod2
    recorder=recorder,
    graph=state_graph,
)
formulation_result = self._run_formulation_stage(research_state=..., mode="full")
```

`data_summary` is the `profile_workspace([mod1_path, mod2_path], user_provided_data_summary)` result — includes cell counts, modality info, obs columns, var gene counts, etc. For the AD multiomics dataset, this gives the Mediator and panelists concrete information about the data structure.

---

### Stage 4A: ScientistPanel.run_initial_panelists()

Three `ToolCallingAgentRunner` instances run in parallel. Each uses its role-specific formulation prompt and has RAG access (`retrieve_literature`, `search_paper_wiki`, `fetch_paper_content`).

**Biologist** — retrieves AD snRNA-seq / snMultiomics papers:
- Expected papers: Mathys 2019 (cell-type AD transcriptomics), Morabito 2021 (snMultiomics AD), Leng 2021 (ROSMAP snATAC), Green 2023 (DLPFC cell atlas)
- Biological framing: disease-associated microglial (DAM) activation signature, ExN subtype vulnerability, oligodendrocyte stress response, endothelial activation in AD
- Method adequacy assessment: snMultiomics methods exist (MultiVI, ArchR) but cell-type-specific GWAS enrichment requires added validation against ENCODE/GTEx regulatory annotations

**Statistician** — frames statistical requirements:
- Pseudoreplication: nucleus ≠ independent observation; pseudobulk aggregation per donor per cell type required for DE / DA
- Multiple donors per group required for pseudo-replicated tests
- Peak-to-gene linkage: correlation threshold + distance constraint + permutation testing
- Batch correction: harmony/BBKNN for RNA, LSI/LDA for ATAC; must test if correction removes biology

**Bioinformatician** — frames computational pipeline:
- MultiVI or ArchR+Seurat WNN for joint embedding
- Leiden clustering; cell type annotation by marker gene + label transfer from ROSMAP atlas
- chromVAR for TF motif enrichment
- Cicero or ArchR's gene activity score for peak-to-gene linkage
- DeSeq2 pseudobulk for DA and DE

`research_state.record_panelist_outputs(panelist_outputs)` committed after all three complete.

**Expected vs. actual**: panelists should retrieve the full set of AD multiomics papers and frame all four stated aims. If the `resolved_intent` was compressed (Gap M4), panelists may not retrieve GWAS enrichment-specific literature, missing the peak-GWAS linkage validation requirement.

---

### Stage 4B: MediatorAgent.formulate()

Context from `context_for_mediator_formulation()`:
```python
{
    "user_task": resolved_intent,
    "data_summary": <profiled data>,
    "panelist_outputs": <three panelist reports>,
    "callback_history": [],              # empty on first call
    "previous_mediator_outputs": [],
    "previous_tool_decisions": [],
    "previous_analyzer_reports": [],
    "evidence_state": {},                # empty on first call
    "trajectory_summary": <graph state>,
}
```

Mediator prompt (`updated_prompts/mediator_formulation.md`) runs the four-gate filter:

1. **Convergence/divergence scan**: all three panelists agree on joint embedding and the need for pseudobulk DA testing. Divergence: statistician says pseudobulk is mandatory; bioinformatician proposes per-nucleus TF motif scoring. Mediator must adjudicate: pseudobulk for DA/DE, per-nucleus for TF motif (chromVAR operates on cells).

2. **Method adequacy**: `sufficient_with_extension` — standard snMultiomics methods exist; GWAS enrichment analysis requires explicit linkage to GWAS catalog (liftover, LD-pruning, Fisher's test on accessible regions).

3. **Hypothesis**: "Cell-type-specific chromatin accessibility dynamics in AD DLPFC are coordinated with transcriptional alterations in disease-associated cell populations (particularly microglia, excitatory neurons, and oligodendrocytes). Non-coding AD GWAS variants are preferentially located within accessible regulatory elements in cell types known to be pathologically activated."

4. **Novelty filter**: GWAS variant enrichment in cell-type-specific accessible chromatin at snMultiomics resolution — clear novelty relative to bulk ATAC studies.

Output: seven-section plan with steps referencing each panelist's contribution, `evidence_requirements`, `required_visualizations` (UMAP by cell type, DA peak volcano plots, TF enrichment heatmaps, peak-to-gene linkage network, GWAS enrichment bar chart), `alternative_research_plans`, `evidence_state`, `limitations`.

---

### Stage 4C: _complete_mediator_callbacks()

If `mediator_output["formulation_status"] == "needs_panelist_callback"`, the callback loop runs. For this query, likely callbacks:
- Statistician: "What minimum donor count per group is required for pseudobulk DA tests to be statistically valid?"
- Biologist: "What cell-type markers distinguish disease-associated microglia (DAM) from homeostatic microglia in snRNA-seq data?"

H1 is correctly implemented: `extend(callback_outputs)` → `synthesize_callbacks()` → `record_callback_history()`. The prior callback history is in context for each synthesis call.

If `formulation_status != "needs_panelist_callback"` after budget, the code checks:
```python
if not isinstance(mediator_output.get("selected_research_plan"), dict):
    return {"status": "unanswerable", ...}
mediator_output["formulation_status"] = "ready_for_adversary"
```

This is a graceful degradation for budget-exhausted formulation.

---

### Stage 4D: _run_adversary_until_accepted()

`_ensure_adversarial_panelist()` is called. If M1 (adversarial panelist not wired) is triggered, `RuntimeError` is raised here, caught in `_handle_research_task()`, and returned as `status="failed"`.

**Assuming M1 is not triggered** (i.e., `ScientistPanel` exposes `adversarial_panelist`):

Round 1:
- `adversary_context = research_state.context_for_adversary(candidate_plan=..., candidate_trajectory_decision=...)`
- Context includes `evidence_state={}` (Phase-0 empty — trivially correct here since no prior evidence exists)
- `adversary.run(adversary_context=adversary_context)` — one critique

Expected adversarial challenges for this plan:
1. "Peak-to-gene correlation thresholds are not standardized. Citing 0.4 as a threshold without permutation-based FDR control leads to inflated false positive regulatory links."
2. "chromVAR motif scores are aggregate over all motif instances in a peak; they do not distinguish which specific TF is active. Claiming specific TF programs is not supported by motif enrichment alone."
3. "Joint embedding with MultiVI assumes paired observations; if cells are drawn from separate tissue aliquots (not truly paired nuclei), the pairing assumption is violated."

Verdict: `needs_revision` (likely on first pass — all three critiques are methodological correctness issues)

Round 2 (if `needs_revision`):
- `MediatorAgent.revise_from_adversary()` called
- Plan revised to: add permutation-based FDR for peak-to-gene linkage; qualify TF claims as "TF family motif enrichment" not specific TF activation; add ATAC/RNA cell pairing validation step
- `_resolve_candidate_revision()` checks material difference → plan IS materially different → `status="needs_revision"` (not terminal yet if `round_number < max_rounds`)

On final round (force_terminal=True):
- K1 (trivial, unfixed): redundant guard clause at line 706 evaluates correctly despite verbosity
- `_candidate_resolution_to_formulation_result()` called → formulation_result returned with `adversarial_review_status`, `adversarial_review_interpretation`

---

### Stage 4E: commit_initial_plan()

```python
active_node_id = research_state.commit_initial_plan(
    selected_plan=research_plan,
    evidence_state=research_context.get("evidence_state", {}),  # ← frozen here
    ...
)
working_model = {"evidence_state": research_state.evidence_state, "mediator_output": brief}
```

`research_state.evidence_state` is now set from the formulation result's `evidence_state`. This is the **last time** `research_state.evidence_state` is updated for the entire run.

---

## Stage 5: Phase 1 — ToolConsultant

### Stage 5A: _build_session_state()

```python
state = {
    "input_h5ad_path": current_input_h5ad,
    "data_summary": self.data_summary,
    "selected_research_plan": research_context.get("selected_research_plan", {}),
    "evidence_state": research_context.get("evidence_state", {}),   # Phase-0 value
    "analysis_requirements": [...],
    "validation_requirements": [...],
    "success_criteria": {...},
    ...
    "state_graph_context": research_state.context_for_tool_consultant(...),
    "phase_trace": short_term_memory.format_for_scientists(),  # ShortTermMemory active
}
```

The ToolConsultant sees the full research plan with steps, evidence state (Phase-0), and graph context. For Phase 1 this is correct — evidence_state is empty as formulation just concluded.

### Stage 5B: tool_consultant.decide()

For the AD multiomics plan, expected DAG plan:

```
step_0: QC snRNA-seq (doublet detection, mito filter ≤20%, n_genes 200–5000)
step_1: QC snATAC-seq (TSS enrichment ≥4, fragment count 1000–50000)
step_2: Cell intersection (retain nuclei passing both modality QC)
step_3: MultiVI joint embedding (latent dim 20, epochs 400)
step_4: Leiden clustering (resolutions 0.3, 0.5, 0.8)
step_5: Cell type annotation (marker gene scoring + reference label transfer)
step_6: chromVAR TF motif enrichment
step_7: Peak-to-gene linkage (Cicero; distance 250kb, correlation ≥0.4 with FDR control)
step_8: Pseudobulk DA testing (DESeq2, diagnosis × cell type, n ≥ 6 donors per group)
step_9: GWAS variant enrichment (LD-pruned variants from GWAS catalog; Fisher test per cell type)
```

### Stage 5C: _review_and_maybe_revise_decision() — alignment gap

**Gap M2 active here**: `alignment_reviewer` is None. The review falls back to `_default_alignment_review("No alignment reviewer configured.")` which returns `verdict="survives"`. The 10-step pipeline is not adversarially reviewed for alignment with the research plan.

Consequence: if the ToolConsultant omitted the GWAS enrichment step (step_9), or added an extraneous step, or clustered before QC, the alignment check would still return `verdict="survives"` and the plan would proceed to execution unchallenged.

---

## Stage 6: _execute() — DagExecutor

```python
dag_result, figure_paths, execution_status = self._execute(decision=decision, ...)
```

For the 10-step multiomics DAG this is the most compute-intensive stage. Outputs:
- Processed h5ad with joint embedding, clusters, cell type labels
- chromVAR TF motif scores
- Peak-to-gene linkage table
- DA testing results table
- GWAS enrichment results table
- UMAP plots, volcano plots, heatmaps

`current_input_h5ad` is advanced if the DAG produces a new processed h5ad (`_extract_best_h5ad(dag_result)`).

---

## Stage 7: AnalyzerPanel.analyze()

Three-round structure:
- **Round 1a** (ResultsInterpreter): interprets DAG outputs vs. research plan claims
- **Round 1b** (LiteratureGrounder + DatabaseValidator, parallel): both receive 1a output
  - LiteratureGrounder: grounds claims in retrieved literature
  - DatabaseValidator: checks cell type marker consistency against reference databases
- **Round 2** (AnalyzerMediator): single LLM call synthesizing all three rounds

`working_model` passed = `{"evidence_state": research_state.evidence_state, "mediator_output": brief}` — for Phase 1, `evidence_state` is the Phase-0 value, which is correct here since Phase 1 is the first analysis phase.

For the AD multiomics results, the Analyzer would interpret:
- Clustering quality (silhouette, Leiden stability)
- Cell type identification confidence (marker enrichment scores)
- TF motif enrichment pattern (disease vs. control, per cell type)
- DA peak count and directionality
- GWAS enrichment significance per cell type

Expected `result_verdict`: `partially_supported` — cell types are identified, DA peaks found, but GWAS enrichment p-values may be borderline, and peak-to-gene linkage requires validation (no independent perturbation data available).

---

## Stage 8: MediatorAgent.post_analysis()

```python
post_analysis_context = research_state.context_for_mediator_post_analysis(
    phase_number=1,
    analyzer_report=analyzer_report,
    dag_result_summary=_summarize_execution_for_mediator(dag_result),
    tool_decision=decision,
    artifact_registry_summary=None,
)
```

`context_for_mediator_post_analysis()` includes:
```python
{
    ...
    "evidence_state": self.evidence_state,    # ← Phase-0 frozen (L1 GAP)
    "previous_mediator_outputs": [...],        # compact
    "previous_tool_decisions": [...],          # compact
    "previous_analyzer_reports": [],           # empty for Phase 1 (nothing prior)
    ...
}
```

For Phase 1, the `evidence_state` being Phase-0 is not yet wrong — Phase 1 hasn't produced evidence yet. The Mediator sees the full analyzer report and decides.

**Expected decision for this query at Phase 1**:
- Cell types identified ✓
- DA peaks found ✓
- TF motif enrichment patterns ✓
- Peak-to-gene linkage complete ✓
- GWAS enrichment: borderline or preliminary ✓

If all four aims are addressed, decision could be `accept_and_conclude`. If GWAS enrichment requires more donors or validation, decision could be `continue_with_same_research_plan` to run validation analyses.

**If decision = `accept_and_conclude`**: loop exits. `final_report = analyzer_report`. Return to frontend.

**If decision = `continue_with_same_research_plan`**: evidence state gap becomes active.

---

## Stage 9: Evidence State Update (Post-Phase 1, if continuing)

```python
# Lines 492-493:
if post_decision.get("evidence_state"):
    working_model = {"evidence_state": post_decision.get("evidence_state")}
    # ← research_state.evidence_state NOT updated  [GAP L1]
```

**[GAP L1 activated here]**: The Mediator's post-analysis decision carries updated `evidence_state` reflecting what Phase 1 established (cell types, DA peaks, TF patterns). This update goes only into `working_model`, not into `research_state.evidence_state`.

```python
# Lines 495-515 — research_context updated only on self_revise_plan:
next_plan = post_decision.get("updated_selected_research_plan")
if isinstance(next_plan, dict) and next_plan.get("steps"):    # ← only on self_revise_plan
    research_context = _extract_research_context({
        ...
        "evidence_state": post_decision.get("evidence_state", ...),
    }, user_question)
# else: research_context["evidence_state"] stays at Phase-0 value  [GAP L2]
```

**[GAP L2 activated here on continue]**: For `continue_with_same_research_plan`, `research_context["evidence_state"]` is NOT updated. `_build_session_state()` at Phase 2 reads `research_context.get("evidence_state", {})` → delivers Phase-0 evidence to the ToolConsultant.

---

## Stage 10: Phase 2 — ToolConsultant with Stale Evidence

`_build_session_state()` at Phase 2:

```python
state["evidence_state"] = research_context.get("evidence_state", {})  # ← Phase-0 (L2 gap)
```

The ToolConsultant for Phase 2 does not know what Phase 1 established. It cannot use "cell type labels from Phase 1 are stored in `leiden_0.5` column" or "DA peaks are in `atac_da.csv`" — this context is absent from its evidence_state.

**Partial mitigation**: `_build_session_state()` also includes `last_post_analysis_decision` (which contains the Mediator's narrative about what was established), and `state_graph_context` (which includes the node history). The ToolConsultant can infer some prior results from these. But it lacks the structured `evidence_state` its prompts are designed to interpret.

**Parallel gap for Mediator at Phase 2**:
`context_for_mediator_post_analysis()` at Phase 2:
```python
"evidence_state": self.evidence_state,   # ← Phase-0 frozen (L1 gap)
"previous_analyzer_reports": [compact_phase1_report],  # ← only compensating signal
```

The Mediator must infer what Phase 1 established from compact report summaries (`result_verdict`, `results_summary`, `claim_updates`) rather than from the structured `evidence_state`. For the AD query, this means the Mediator may not correctly track which claims are supported vs. pending vs. contradicted across phases.

---

## Stage 11: Final Response — Return to Frontend

When `next_action = "done"` (or `"abstain"`, `"awaiting_user"`):

```python
return {
    "status": next_action,             # "done" → "completed" in frontend
    "final_report": analyzer_report,   # last phase AnalyzerPanel report
    "post_analysis_decision": post_decision,
    "phases_completed": phase_number,
    "phase_log": phase_log,
    "pipeline_mode": pipeline_mode,
}
```

Back in `_handle_research_task()`:
```python
message = (
    final_report.get("summary")
    or final_report.get("conclusion")
    or final_report.get("message")
    or f"Research loop completed: {loop_status} after {loop_result.get('phases_completed', 0)} phase(s)."
)
status = "completed" if loop_status in ("done", "abstain", ...) else "failed"
```

In `chat()`:
```python
if not any(payload_result.get(key) for key in ("message", "search_summary", "recommendation")):
    payload_result["message"] = assistant_display_text(result)
```

The final message shown to the user is `final_report["summary"]` (the AnalyzerPanel's prose summary) or a fallback. For the AD multiomics query, the user sees the Analyzer's scientific narrative about cell-type-specific regulatory findings.

**Gap**: figure paths are resolved relative to `tool_artifact_dir` and `result_dir`. If the DAG produced figures to a non-standard path, `_artifact_url_for_path()` may not resolve them correctly, and figures would not display in the chat UI even if they exist on disk.

---

## Behavioral Gap Summary

| ID | Severity | Stage | Description | Impact |
|----|----------|-------|-------------|--------|
| M1 | **High** | Stage 0 / frontend construction | `AdversarialPanelist` not passed to ResearchLoop at startup; `_ensure_adversarial_panelist()` raises RuntimeError if ScientistPanel doesn't expose it | All discovery queries fail with "failed" status |
| M2 | Medium | Stage 5C / tool plan alignment | `alignment_reviewer` not wired; all tool plans silently pass alignment with `verdict="survives"` | Incorrect or misaligned plans (wrong statistical unit, wrong clustering order, missing steps) proceed to execution unchallenged |
| M3 | Low | Stage 1 / dispatcher | `planning_state` not forwarded to `ResearchLoop.run()`; ResearchLoop cannot leverage prior-turn context | Multi-turn research queries re-run full formulation instead of extending prior work |
| M4 | Medium | Stage 2 / router | Router's `resolved_intent` becomes sole `user_question` for all downstream agents; if compressed, panelists miss specific study aims (GWAS enrichment, peak-to-gene linkage) | Scientific scope narrows; key validation analyses may not be planned |
| M5 | Low | Stage 2 / router | Invalid `intent_mode` silently normalizes to `"ambiguous"` without triggering retry loop | Discovery query receives clarification prompt instead of analysis; user must re-phrase |
| L1 | Low-Medium | Stage 9 / execution loop | `research_state.evidence_state` never updated post-Phase 0; Mediator/adversary context for Phases 2+ always carries Phase-0 evidence | Mediator cannot use structured evidence_state to track claim progress; relies on compact report summaries |
| L2 | Low | Stage 9/10 / execution loop | `research_context["evidence_state"]` not updated on `continue_with_same_research_plan`; ToolConsultant gets Phase-0 evidence for all continue phases | ToolConsultant cannot ground Phase 2+ plans in prior-phase findings |
| K1 | Trivial | Stage 4D / adversary loop | Redundant right-hand guard clause at line 706 | No functional impact; readability only |

### Priority order for fixes

1. **M1** (High) — instantiate `AdversarialPanelist` explicitly in `_FrontendState.__init__()` and pass to `ResearchLoop`
2. **M2** (Medium) — instantiate `AdversarialPanelist.review_alignment` as `alignment_reviewer` in `_FrontendState.__init__()`
3. **M4** (Medium) — add explicit instruction to router prompt to preserve all study aims in `resolved_intent`; consider passing full `user_message` as fallback if `resolved_intent` is significantly shorter
4. **L1** (Low-Medium) — add `research_state.evidence_state = post_decision["evidence_state"]` after `working_model` update (line 493)
5. **L2** (Low) — update `research_context["evidence_state"]` outside the `self_revise_plan` guard (lines 495–515)
6. **M3** (Low) — consider adding `session_context: dict | None` parameter to `ResearchLoop.run()` for multi-turn continuity
7. **M5** (Low) — raise `DecisionValidationError` in `validate_session_route()` if `intent_mode` is invalid, triggering the retry loop
8. **K1** (Trivial) — simplify line 706 guard clause
