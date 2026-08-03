# ScientistPanel Workflow Summary

How the system flows end to end, from a user research question to a delivered answer (or a clean declaration that the question cannot be answered with the available data).

---

## Overview

The system is a multi-agent scientific research panel for single-cell genomics. Three domain experts (Biologist, Statistician, Bioinformatician) work in parallel to survey the relevant literature and propose contributions. A Mediator (the panel's principal investigator) integrates their work into a coherent research plan, an Adversary stress-tests the plan, an executor runs it, and an Analyzer interprets the results. The Mediator then decides what happens next.

Two phases repeat in a loop: **plan formulation** (producing an accepted plan) and **execution + post-analysis** (running the plan and deciding the next move). The loop ends when the Mediator accepts the result, asks the user a clarifying question, or declares the question unanswerable.

---

## Phase 1: Plan Formulation

### Step 1: Three panelists run in parallel

Each panelist runs independently and does not see the other panelists' outputs.

Prompts: `biologist_formulation.md`, `statistician_formulation.md`, `bioinformatician_formulation.md`. Each inherits `panelist_shared_system.md`.

Each panelist does the following:

1. Paraphrases the user's research question into clearer wording (carried in the top-level `question` field).
2. Organizes literature reasoning into up to 3 intent-like iterations inside the role prompt. For each iteration:
   - States a `purpose` (what this iteration is trying to learn from the literature).
   - Composes a `search_query` (natural language, topic description, or keywords).
   - Calls `search_paper_wiki` first; falls back to `retrieve_literature` only when wiki is insufficient.
   - PaperJudge filters retrieved papers for relevance against the intent before they reach the panelist.
3. Applies the literature review methodology to the returned papers: deep reading (extract evidence_pattern fields), adversarial questioning, cross-paper synthesis (convergence, divergence, absence), quality weighting.
4. Builds a lane-specific synthesis (background, rationale, evaluation in prose with inline citations).
5. Issues a method_adequacy verdict from their lane (sufficient, sufficient_with_extension, partial, insufficient) with rationale and constraints on the method.
6. Generates novelty candidates from their lane using the six moves (failure_mode_root_cause, underexploited_signal, assumption_inversion, cross_field_transfer, output_reframing, modality_composition).
7. Contributes downstream_analysis and benchmark entries to the plan.
8. Surfaces open_questions where the iteration's purpose was not fully resolved.

Output: `panelist_formulation_output` JSON.

### Step 2: Mediator integrates and composes the plan

Prompts: `mediator_shared_system.md` + `mediator_formulation.md`.

The Mediator (the panel's PI) does the work that requires bridging across lanes:

1. Reads all three panelist outputs. Identifies convergence (what multiple lanes agree on), divergence (where they disagree), absence (what no lane addresses).
2. Reconciles the three method_adequacy verdicts.
3. **Forms the scientific hypothesis** (panelists do not formulate hypotheses). The hypothesis must draw from all three lanes; the falsification_criterion states what would refute it.
4. Applies the four gates to every novelty candidate (extends baseline, dataset affordance, falsifiable, cost-justified). Picks the single strongest candidate as `novel_analysis_design`. Failed-gate candidates go to `future_research_directions` or `limitations`.
5. Composes `selected_research_plan`, the seven-section plan body: hypothesis, background, plan (main_method + downstream_analyses), supplemental_data, validation_metrics, novel_analysis_design, limitations, future_research_directions. Plus success_criteria and alternative_plans.
6. Emits the formulation envelope: `formulation_status`, `selected_research_plan`, callback requests if needed, evidence completeness, research_gap_resolution, and candidate `trajectory_decision`.

Output: `mediator_formulation_output` JSON.

### Step 3: Adversary stress-tests the plan

Prompt: `adversary.md`.

The Adversary is a critical peer reviewer. It does not collect new literature, does not rewrite the plan, and does not assign challenges to specific panelists.

1. Checks the plan against the user's question, the method choice, the downstream analyses, the validation independence, the novelty falsifiability, the honesty of limitations, and the standard evidence patterns prior literature implies.
2. Issues a verdict: `survives`, `needs_revision`, or `unsalvageable`.
3. Lists `challenges` (in prose, naturally describing what part of the plan they target), `missing_analyses` (what prior work implies should be present), `open_questions_for_panelists` (recommendations to the Mediator about which panelist could resolve which gap), and `agreements` (what has been affirmed and should not be re-litigated in later rounds).

Output: `adversary_output` JSON.

### Step 4: Round loop until plan stabilizes

- If verdict = `survives` → plan accepted, proceed to Phase 2.
- If verdict = `needs_revision` → back to the Mediator. The Mediator decides:
  - **Call targeted panelist tools if needed**: each assigned panelist answers the gap in callback mode, returning `panelist_callback_output`. The Mediator re-synthesizes with the responses and emits a revised candidate plan. Back to the Adversary.
  - **Self-revise the plan**: Mediator writes the revision without calling panelists, emits a revised plan. Back to the Adversary.
- If verdict = `unsalvageable` → Mediator declares the question unanswerable or restarts the panel with a re-scoped question.
- Repeat up to the round budget.

When the Adversary returns `survives`, the formulation phase ends with an accepted plan.

---

## Phase 2: Execution

### Step 5: ToolConsultant translates the plan to an executable DAG

Not part of the panel itself; receives the accepted research plan and produces a DAG of tool calls (method-specific implementations of the abstract approach in the plan).

### Step 6: DagExecutor runs the DAG

Produces per-step outputs, metrics, figures, and any partial-failure flags.

---

## Phase 3: Post-Execution and Decision

### Step 7: Analyzer interprets the results

Prompt: `analyzer.md`. The Analyzer is panel-agnostic; it does not route questions to specific panelists.

1. Walks the plan piece by piece (`interpretation_loop`). For each iteration:
   - Names what was interpreted in descriptive text (e.g., "cell type prediction AUROC", "regulon-marker enrichment for myeloid lineage").
   - Writes prose interpreting what the result shows, tied to the specific metric or figure, and whether it supports, contradicts, or is inconclusive against the plan's expectation.
   - Surfaces `formulated_questions` — open questions the result raises, stated as plain questions (no role assignment).
2. Produces an `overall_interpretation` paragraph integrating the iterations and stating where the hypothesis stands.

Output: `analyzer_output` JSON.

### Step 8: Mediator makes the post-analysis decision

Prompts: `mediator_shared_system.md` + `mediator_post_analysis.md`.

1. Reads the Analyzer report and the active plan.
2. Updates `evidence_state.analysis_claims[*].status` using Analyzer
   `claim_updates`, while preserving unresolved questions and evidence records.
3. If the Analyzer raised questions that need lane-specific reasoning or
   literature-backed interpretation, calls internal targeted panelist tools.
   Tool results return inside the same Mediator post-analysis run.
4. Picks one of five mutually exclusive final decisions:
   - **accept_and_conclude** → emits `final_answer_summary`; loop ends.
   - **self_revise_plan** → Mediator emits `plan_revision` (`incorrect_from_step` + `what_was_wrong`) and the revised plan in `updated_selected_research_plan`. The revised plan goes back to the Adversary.
   - **continue_with_same_research_plan** → Mediator emits `rerun_intent`; ResearchLoop appends a new iteration under the same research-state node.
   - **ask_user** → emits `clarifying_questions` with concrete options; session pauses for user response.
   - **declare_unanswerable** → emits `unanswerable_reason` + `what_would_be_needed`; session ends.
5. Always fills `updated_selected_research_plan` with the plan that propagates to the next phase (the revised plan if `self_revise_plan`, otherwise the unchanged active plan).

Output: `mediator_post_analysis_output` JSON.

---

## Iteration and Termination

After the post-analysis decision:

- `self_revise_plan` → revised plan goes back to the Adversary → if `survives`, a new execution phase begins from Step 5.
- `continue_with_same_research_plan` → ResearchLoop appends a same-node iteration and returns to Step 5.
- `accept_and_conclude` → loop ends with the final answer.
- `ask_user` → session pauses; user response triggers re-entry.
- `declare_unanswerable` → loop ends with the unanswerable reason.

Across iterations, `updated_selected_research_plan` carries the active plan forward, and `evidence_state` tracks where the claim stands.

---

## Agent and Prompt Map

| Agent | Prompt file | Output schema |
|---|---|---|
| Biologist (formulation) | `biologist_formulation.md` | `panelist_formulation_output` |
| Statistician (formulation) | `statistician_formulation.md` | `panelist_formulation_output` |
| Bioinformatician (formulation) | `bioinformatician_formulation.md` | `panelist_formulation_output` |
| Panelist callback (any role) | `panelist_callback.md` | `panelist_callback_output` |
| Mediator (shared role) | `mediator_shared_system.md` | system prompt |
| Mediator (formulation) | `mediator_formulation.md` | `mediator_formulation_output` |
| Mediator (post-analysis) | `mediator_post_analysis.md` | `mediator_post_analysis_output` |
| Analyzer | `analyzer.md` | `analyzer_output` |
| Adversary | `adversary.md` | `adversary_output` |

All schemas are defined in `scientist_panel_schemas.json`. Panelist prompts inherit `panelist_shared_system.md`; Mediator mode prompts inherit `mediator_shared_system.md`.

---

## Key Design Principles

1. **Panelists describe; Mediator decides.** Panelists collect evidence and propose contributions. The Mediator forms hypotheses, composes plans, and owns all plan-shaped decisions.
2. **Parallel perspectives, not sequential stages.** The three panelists are three independent angles on the same question, not three stages of a pipeline. Their disagreements are real signals.
3. **Bounded intent loop with literature review methodology.** Each panelist forms intents, retrieves with PaperJudge filtering, then synthesizes across multiple papers (not paper-by-paper notes).
4. **Hypothesis formation is the Mediator's unique job.** It is the integrative move that requires bridging all three lanes.
5. **Six novelty moves with four gates.** Novelty is generated deliberately from explicit thinking operations and filtered through extends-baseline, dataset-affordance, falsifiability, and cost-justified gates.
6. **Analyzer is panel-agnostic.** It interprets results and surfaces open questions in plain language; the Mediator decides whether to call targeted panelist tools internally.
7. **Five mutually exclusive post-analysis decisions.** Tight orchestration: accept_and_conclude, self_revise_plan, continue_with_same_research_plan, ask_user, declare_unanswerable.
8. **Working plan propagates, not working model.** The active plan (with any revisions) is what carries forward across iterations, plus the current `evidence_state`.
