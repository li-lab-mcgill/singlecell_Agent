# Evolving Research Logic Implementation Plan

## Purpose

This document describes how to implement the research reasoning changes from
`evolving_research_logic.md`.

The goal is not to replace the current system. The current system already has:

```text
ScientistPanel
  -> BiologistPanelist / StatisticianPanelist / BioinformaticianPanelist
  -> Reconciler
  -> Mediator
  -> AdversarialPanelist
  -> ResearchLoop
  -> AnalyzerPanel
```

The implementation should preserve that structure and strengthen the reasoning
contracts, schemas, artifact handling, and phase evolution behavior.

### Runtime Ownership

Use these ownership boundaries throughout the implementation:

```text
ResearchLoop / Orchestrator:
  owns call order and state updates.

ScientistPanel:
  owns panelist reasoning.

Mediator:
  owns research-plan synthesis and trajectory decisions.

AdversarialPanelist:
  owns critique.

ToolConsultant:
  owns executable plan translation.

DagExecutor:
  owns execution.

DagExecutor path-ranking helper:
  owns leaderboard / best-path selection from DAG experiments.

ArtifactRegistry:
  owns useful artifact tracking and handle resolution.

AnalyzerPanel:
  owns result interpretation.
```

The Mediator decides where the research trajectory should go. The Orchestrator
records state changes that happen because tools executed or analysis completed.

## Current State Summary

### Already Present

The repo already has most of the orchestration pieces:

```text
agents/scientist_panel.py
  formulate()
  update()
  parallel panelist calls
  mediator formulation
  adversarial loop

agents/panelist_tools.py
  query_paper_wiki
  retrieve_literature
  fetch_paper_section
  traverse_paper_wiki
  get_related_papers
  PaperJudge integration in the current implementation
  wiki persistence for judged papers

agents/adversarial_panelist.py
  challenge / defense / re-mediator loop

agents/research_loop.py
  phase loop around ScientistPanel, execution, AnalyzerPanel

prompts/panelist_prompts.py
prompts/adversarial_prompts.py
prompts/analyzer_prompts.py
  existing prompt contracts

agents/dag_executor.py
  DAG execution
  per-run artifact directory
  dag_result.json
  artifact_manifest.json
  retention behavior
```

### Main Gaps

The missing pieces are:

```text
1. Panelist prompts do not yet strongly enforce existing-solution-first reasoning.
2. Mediator output does not yet expose selected active plan + alternative plan fields.
3. Literature tools are still five separate tools and PaperJudge is too broad /
   not cleanly separated from panelist scientific reasoning.
4. Mediator cannot yet perform gap-directed callback rounds.
5. Adversary mostly reviews a final mediator plan, not the full research decision chain.
6. There is no persistent StateGraph of how the system has tackled the problem.
7. AnalyzerPanel output does not yet localize evidence failures to graph nodes,
   research steps, tool steps, or artifact checkpoints.
8. ResearchLoop cannot yet apply Mediator post-analysis decisions to the
   StateGraph.
9. ResearchLoop does not yet request delta plans from a chosen graph node and
   resolved artifact handle.
10. Artifact handling uses raw paths, not logical artifact handles.
11. Retention keeps final outputs/metadata but not selective rollback checkpoints.
12. Dependency preflight is not yet enforced before DAG execution.
13. Frontend/session outputs are split across results_frontend, tool_artifacts,
    saved_code, feedback files, and research_loop folders instead of one
    session-centered storage layout.
14. Progress UI reconstructs state by scanning recent files instead of reading
    an explicit progress/event stream.
```

## Implementation Strategy

Implement in layers.

Do not start with artifact handles or delta execution. First make the reasoning
outputs structured enough that later execution changes have a stable contract.

Recommended order:

```text
Phase 1: Prompt and schema contracts
Phase 2: Panelist literature tools with constrained PaperJudge
Phase 3: Mediator callback loop
Phase 4: ToolConsultant + adversarial alignment review
Phase 5: Analyzer-driven phase update schema
Phase 6: Session storage and StateGraph
Phase 7: Conservative incremental planning MVP
Phase 8: Artifact registry and selective retention
Phase 9: Full delta planning from graph nodes and artifact handles
Phase 10: Dependency preflight
```

## Phase 1: Prompt And Schema Contracts

### Goal

Make the existing ScientistPanel produce the new research reasoning fields.

This phase should not change orchestration much. It mainly updates prompts and
parsing expectations.

### Files

```text
prompts/panelist_prompts.py
prompts/session_router_prompts.py
agents/scientist_panel.py
agents/session_router.py
agents/session_dispatcher.py
tests/test_scientist_panel_formulate.py
tests/test_research_loop_phase1.py
tests/test_mediator_prompt_modes.py
tests/test_session_routing.py
```

### Panelist Prompt Changes

Update `PANELIST_SHARED_SYSTEM` with the research guideline paragraphs from
`evolving_research_logic.md`:

```text
First establish the strongest existing solution path.
Then decide what additional contribution, if any, should be built on top of it.
```

Add explicit instructions:

```text
Do not jump directly from user query to tools.
Do not retrieve papers using only the raw user query.
Do not summarize papers without reconstructing how they made the claim credible.
Do not invent a method before identifying the closest existing baseline.
Do not stop at running a method when the user asks for interpretation.
```

If the user names a method and asks an interpretive question, the panel should
reason over both parts together. The named method is not the final answer; it is
the execution component that may produce raw outputs. The panel must still define
what downstream analysis or interpretation is required to support, weaken, or
reject the user's intended scientific claim.

Example:

```text
User: Run MultiVelo and determine whether chromatin primes RNA expression.

Panel reasoning:
  MultiVelo execution is required.
  The research plan must also define what "chromatin primes RNA expression"
  means operationally, what MultiVelo outputs are relevant, what downstream
  lead-lag / peak-gene / gene-set analyses are needed, and what evidence would
  count as supported, contradicted, or inconclusive.
```

Routing prerequisite:

```text
If the router marks a request as ambiguous, do not send it into a brief discovery
loop by default. Ask the user to choose between two concrete interpretations.
Only run the research loop after the intended interpretation is explicit.
```

### Panelist Output Changes

Each panelist should still return role-specific output, but add these fields:

```json
{
  "concrete_analysis_claim": "...",
  "existing_solution_path": {
    "what_prior_work_does": "...",
    "papers_or_workflows": [],
    "how_it_makes_the_claim_credible": "...",
    "what_it_directly_establishes": "...",
    "what_it_does_not_answer": "..."
  },
  "extension_opportunities": [
    {
      "extension": "...",
      "why_this_dataset_can_add_it": "...",
      "depends_on_existing_solution_output": true
    }
  ],
  "evidence_patterns": [],
  "analysis_requirements": [],
  "role_claims": [],
  "role_uncertainties": [],
  "evidence_gaps": [],
  "retrieval_evidence": []
}
```

Keep the role-specific lens:

```text
Biologist:
  biological entities, markers, states, prior findings, validation.

Statistician:
  comparison design, statistical unit, metrics, confounders, robustness.

Bioinformatician:
  workflow structure, data requirements, method assumptions, computational outputs.
```

Panelists should not explicitly route work to other panelists. Each panelist
states its own role claims, uncertainties, analysis requirements, and evidence
gaps. The Mediator decides whether another panelist needs a targeted callback.

### Mediator Prompt Changes

Update `MEDIATOR_FORMULATION_PROMPT` so the final `<MEDIATOR>` JSON includes:

```json
{
  "concrete_analysis_claim": "...",
  "best_effort_claim": "...",
  "clarification_needed": false,
  "uncertainty_reason": "",
  "clarifying_questions": [],
  "literature_verdict": "answered_well | partially_answered | not_answered",
  "verdict_rationale": "...",
  "research_case": "prior_answered | established_method_fits | no_adequate_existing_solution",
  "existing_solution_path": {},
  "existing_solution_plan": {},
  "extension_or_de_novo_plan": {},
  "novelty_level": 0,
  "why_extension_is_justified": "...",
  "baseline_requirement": "...",
  "analysis_requirements": [],
  "validation_requirements": [],
  "success_criteria": {
    "supports": "...",
    "weakens": "...",
    "contradicts": "...",
    "inconclusive": "..."
  },
  "selected_research_plan": {
    "plan_id": "plan_a",
    "summary": "...",
    "reason_selected": "...",
    "steps": [],
    "required_visualizations": [],
    "caveat": ""
  },
  "alternative_research_plans": [
    {
      "plan_id": "plan_b",
      "summary": "...",
      "when_to_use": "...",
      "why_not_selected_now": "...",
      "evidence_requirements": [],
      "expected_starting_artifact_type": "raw_h5ad | qc_h5ad | normalized_h5ad | clustered_h5ad | annotated_h5ad | multimodal_h5ad | table | none"
    }
  ],
  "selection_rationale": "...",
  "plan_switch_policy": {
    "revise_current_plan_when": [],
    "promote_alternative_plan_when": [],
    "ask_user_when": []
  },
  "open_risks": [],
  "confidence": 0.0
}
```

Maintain backward compatibility by still producing `consensus_hypothesis` and
`research_plan`, because downstream code may depend on those fields. Do not ask
the Mediator prompt to produce both `selected_research_plan` and `research_plan`;
the normalizer should create `research_plan` as a compatibility alias from
`selected_research_plan`.

The Mediator should keep exactly one selected active plan for execution. It may
record multiple alternatives, but alternatives are not sent to ToolConsultant for
execution unless later Analyzer feedback, panelist callbacks, or user input make
one of them the selected active plan.

Use one Mediator class/agent, but separate its prompt modes:

```text
ResearchMediator.formulate:
  input: panelist outputs, literature summaries, user question, data summary
  output: selected_research_plan, alternative_research_plans, evidence requirements

ResearchMediator.update_from_analysis:
  input: current StateGraph, Analyzer report, active plan, alternatives,
         ToolConsultant plan, ArtifactRegistry summary
  output: structured post-analysis research decision, including next plan and
          requested continuation point when needed
```

This keeps one reasoning owner while preventing one prompt from doing unrelated
jobs.

If the panel cannot form a concrete analysis claim, it should not silently invent
certainty. In interactive mode, ambiguous requests should ask the user to choose
between two concrete interpretations. In noninteractive or forced-run contexts,
the Mediator may populate `best_effort_claim`, set `clarification_needed=true`,
and record `uncertainty_reason`. A best-effort claim is a flagged fallback, not a
fully accepted scientific target.

Do not add a separate `claim_status` field. The Analyzer should assess the
evidence for the plan it receives. Ambiguity should be handled before execution
in interactive mode, or carried as an explicit caveat through `clarification_needed`
and `best_effort_claim` in noninteractive mode.

### ScientistPanel Parsing

`agents/scientist_panel.py` currently parses the mediator JSON generically with
`_extract_tag_json`. Minimal code changes are needed in Phase 1.

Add a normalizer after `_run_mediator_formulation()`:

```text
_normalize_research_plan_schema(plan)
```

Responsibilities:

```text
ensure required top-level keys exist
copy concrete_analysis_claim to consensus_hypothesis if consensus_hypothesis is missing
if selected_research_plan is present, copy it to research_plan for compatibility
ensure research_plan.steps exists
ensure alternative_research_plans is a list
ensure literature_verdict is one of the allowed values
ensure research_case is one of the allowed values
ensure novelty_level is integer 0-5
ensure clarification_needed is boolean
```

### Tests

Add prompt/schema tests:

```text
test_mediator_schema_contains_existing_solution_fields
test_mediator_schema_contains_selected_and_alternative_plans
test_panelist_prompt_contains_existing_solution_first_guideline
test_ambiguous_route_requests_user_choice_between_two_interpretations
test_normalize_research_plan_schema_backfills_legacy_fields
test_best_effort_claim_requires_clarification_flag
```

## Phase 2: Panelist Literature Tools With Constrained PaperJudge

### Goal

Replace the current five literature tools with three clearer panelist-facing tools.
The retrieval layer should retrieve, deduplicate, judge, summarize, persist, and
expose paper content. The panelist remains responsible for scientific reasoning
over the returned judged summaries.

PaperJudge should be kept, but with a constrained role. The prior design problem
was not that PaperJudge exists; it was that its role could blur into scientific
plan judgment. The cleaner split is:

```text
PaperJudge:
  judges whether one paper is useful for one retrieval intent.
  extracts what evidence pattern the paper contributes.
  decides whether the paper is worth returning to the panelist and/or persisting.

Panelist:
  decides what the useful papers mean scientifically.
  decides whether more retrieval is needed.
  decides how the evidence changes its role-specific reasoning.
```

PaperJudge must not decide the research plan, novelty claim, biological truth, or
final conclusion.

### Files

```text
agents/panelist_tools.py
agents/scientist_panel.py
agents/paper_md_writer.py
agents/paper_judge.py
rag/literature_retriever.py
prompts/paper_md_writer_prompts.py
prompts/paper_judge_prompts.py
wiki/paper_index.py
tests/test_panelist_literature_tools.py
```

### Target Tool Surface

Current legacy panelist literature tools:

```text
query_paper_wiki
retrieve_literature
fetch_paper_section
traverse_paper_wiki
get_related_papers
```

Target panelist literature tools:

```text
search_paper_wiki
retrieve_literature
fetch_paper_content
```

Only the target tools should remain visible to panelists after Phase 2. The old
tools should be internalized or removed from the panelist tool registry, not kept
as LLM-callable compatibility tools. Their functionality can be reused behind the
new tools.

These are panelist-facing tools. Internally, they may call lower-level retrieval,
wiki, vector store, and full-text functions. For example, `retrieve_literature`
may call external search, full-text parsers, PaperJudge, session cache, vector
indexing, and paper wiki persistence.

### PaperStore And Paper Wiki

Use `PaperStore` as the source of truth.

```text
PaperStore:
  owns paper IDs, deduplication, raw metadata, abstracts, full-text chunks,
  vector index entries, canonical summaries, retrieval cache records, and
  PaperJudge results.

Paper wiki:
  curated human-readable view/export over useful PaperStore papers.
  stores canonical structured summaries for papers worth preserving for future
  sessions.
  is not the source of truth and can be regenerated from PaperStore metadata.
```

When a paper passes persistence criteria:

```text
1. Store / update the paper and chunks in PaperStore.
2. Store the canonical structured summary in PaperStore metadata.
3. Export or update a paper wiki markdown file containing the summary.
```

Future sessions can call `search_paper_wiki` to retrieve the preserved summary
quickly. They should call `fetch_paper_content` only when the summary is
insufficient and a specific section or chunk is needed.

### search_paper_wiki

Purpose:

```text
Search accumulated paper memory and return canonical structured paper summaries.
```

Behavior:

```text
1. Search curated PaperStore summaries / paper wiki exports using retrieval_intent.
2. Deduplicate internally.
3. Rank by deterministic keyword/BM25 search over title, abstract, objective,
   analysis, main_findings, and tasks_supported.
4. Optionally apply embedding rerank if a vector index exists.
5. Optionally apply LLM rerank only for the top N ambiguous matches.
6. Return canonical paper summaries.
```

The wiki should not contain duplicate papers, but PaperStore and the tool should
still deduplicate defensively by DOI, PMID, PMCID, source IDs, and normalized
title hash before returning results.

### retrieve_literature

Purpose:

```text
Fresh external retrieval only.
```

Input:

```json
{
  "retrieval_context_id": "optional context id for this panelist retrieval loop",
  "retrieval_intent": "...",
  "retrieval_goal": "...",
  "requirements": "...",
  "background": "...",
  "exclude_ids": {
    "paper_ids": [],
    "dois": [],
    "pmids": [],
    "pmcids": [],
    "semantic_scholar_ids": [],
    "openalex_ids": [],
    "normalized_titles": []
  },
  "top_k": 8
}
```

Definitions:

```text
retrieval_intent:
  The specific question this retrieval call is trying to answer.
  It is scoped to this one call and drives search.

retrieval_goal:
  Why this paper is needed in the reasoning loop.
  Allowed values:
    method_selection
    evidence_pattern
    prior_findings
    contradiction
    validation
    extension_opportunity
    broad_background

requirements:
  The current research-plan constraints the paper must be interpreted against.
  Requirements should be used for PaperJudge and reranking, not as the default
  external search query.
```

`retrieval_context_id` lifecycle:

```text
If omitted, retrieve_literature creates a new context ID and returns it.
Scope is one panelist retrieval loop within one ScientistPanel call.
PaperStore stores the session retrieval cache keyed by context ID.
The context tracks seen paper IDs, DOIs, source IDs, and normalized titles.
Context expires at the end of the session unless persisted for debugging.
```

Internal flow:

```text
1. Search external sources.
2. Normalize identifiers.
3. Merge caller-provided exclude_ids with IDs already seen in retrieval_context_id.
4. Remove candidates matching exclude_ids.
5. Deduplicate candidates across sources.
6. Fetch/enrich full text when available.
7. Summarize each candidate into the canonical paper structure.
8. Run PaperJudge once per candidate against the retrieval intent.
9. Store all candidates and judge results in a session retrieval cache.
10. Return only useful judged summaries to the panelist.
11. Persist only high-confidence useful papers to the paper wiki.
```

### PaperJudge Contract

PaperJudge receives one paper at a time:

```json
{
  "retrieval_intent": "...",
  "retrieval_goal": "method_selection | evidence_pattern | prior_findings | contradiction | validation | extension_opportunity | broad_background",
  "requirements": "...",
  "background": "...",
  "paper": {
    "canonical_summary": {},
    "full_text_status": "pmc_xml | preprint_jats | open_pdf | abstract_only",
    "available_sections": []
  }
}
```

PaperJudge returns:

```json
{
  "paper_id": "...",
  "relevant": true,
  "confidence": 0.84,
  "retrieval_intent_fit": "direct | partial | weak | off_target",
  "usefulness": "method_selection | evidence_pattern | prior_findings | contradiction | validation | extension_opportunity | broad_background",
  "return_to_panelist": true,
  "reason_returned": "...",
  "useful_sections": ["methods", "results"],
  "canonical_summary": {},
  "evidence_pattern": {
    "entity_definition": "...",
    "comparison": "...",
    "statistical_unit": "...",
    "metric": "...",
    "covariates": "...",
    "validation": "..."
  },
  "missing_information": [],
  "persist_to_wiki": true,
  "persistence_reason": "...",
  "reason_not_persisted": ""
}
```

Return rule:

```text
Return to panelist when:
  relevant == true
  confidence >= 0.60
```

Persistence rule:

```text
Persist to long-term paper wiki only when:
  relevant == true
  confidence >= 0.75
  retrieval_intent_fit in ["direct", "partial"]
  canonical_summary.analysis is non-empty

If full_text_status == "abstract_only":
  cap confidence at 0.70 by default unless retrieval_goal == broad_background.
```

Session cache rule:

```text
Store all retrieved candidates, judged or rejected, in the session retrieval cache.
Use this cache for duplicate avoidance and audit.
Do not promote rejected or low-confidence papers to the paper wiki.
```

This keeps long-term paper memory clean while still letting the system explain
what was searched and rejected.

### fetch_paper_content

Purpose:

```text
Fetch section-level or targeted full-text content from the vector database or
parsed paper store.
```

It should work for both wiki papers and newly retrieved papers using `paper_id`,
`doc_id`, or `vector_doc_id`.

Input:

```json
{
  "paper_id": "...",
  "content_need": "...",
  "section_type": "abstract | introduction | methods | results | discussion | conclusion | any"
}
```

### Canonical Paper Summary Schema

All papers returned to panelists should have the same structure:

```json
{
  "paper_id": "...",
  "doc_id": "...",
  "title": "...",
  "url": "...",
  "doi": "...",
  "source_ids": {},
  "published": "...",
  "source": "...",
  "full_text_status": "pmc_xml | preprint_jats | open_pdf | abstract_only",
  "abstract": "...",
  "objective": "...",
  "background": "...",
  "analysis": "...",
  "main_findings": "...",
  "limitations": "...",
  "available_sections": [],
  "vector_doc_id": "..."
}
```

The paper wiki markdown should store this same canonical structure. Wiki papers
and freshly retrieved papers should therefore have the same shape when returned
to panelists.

Canonical summaries returned to panelists should include the PaperJudge fields
that explain why the paper was returned:

```json
{
  "judge_relevance": true,
  "judge_confidence": 0.84,
  "retrieval_intent_fit": "direct",
  "usefulness": "evidence_pattern",
  "return_to_panelist": true,
  "persist_to_wiki": true,
  "evidence_pattern": {},
  "missing_information": []
}
```

### Panelist Prompt Guidance

Panelists should be told:

```text
Use search_paper_wiki before fresh retrieval when accumulated memory may already
cover the intent.

Use retrieve_literature for fresh search when wiki results are missing,
insufficient, or stale. Pass retrieval_context_id or exclude_ids from wiki results
and previous retrievals to avoid duplicates.

Use fetch_paper_content when a summary is not enough and you need exact methods,
results, discussion, or targeted evidence from a specific paper.

Retrieved paper summaries are evidence inputs, not conclusions. Extract the parts
that help your role-specific reasoning. Ignore off-target summaries. Do not output
a separate paper-accept/reject judgment unless needed for traceability.
```

### Tests

```text
test_search_paper_wiki_returns_canonical_summaries
test_search_paper_wiki_uses_bm25_before_optional_rerank
test_retrieve_literature_accepts_exclude_ids
test_retrieve_literature_tracks_retrieval_context_seen_ids
test_retrieve_literature_deduplicates_across_sources
test_paper_judge_filters_off_target_papers
test_retrieve_literature_returns_only_useful_judged_summaries
test_retrieve_literature_persists_only_high_confidence_useful_papers
test_paper_judge_return_threshold_is_lower_than_persistence_threshold
test_abstract_only_confidence_is_capped_for_non_background_goals
test_fetch_paper_content_works_for_wiki_and_fresh_papers
test_panelist_registry_exposes_three_literature_tools
test_legacy_literature_tools_are_not_llm_callable
```

## Phase 3: Mediator Callback Loop

### Goal

Allow the Mediator to ask a specific panelist for more reasoning or more literature
without restarting the full panel.

### Files

```text
agents/scientist_panel.py
prompts/panelist_prompts.py
tests/test_scientist_panel_callbacks.py
```

### Add Callback Decision Schema

After the initial mediator draft, allow Mediator to request callbacks:

```json
{
  "mediator_decision": "accept | needs_panelist_callback",
  "callbacks": [
    {
      "callback_type": "ask_panelist_for_more_reasoning | ask_panelist_for_more_literature",
      "callback_source": "mediator_gap | adversary_critique | analyzer_feedback",
      "role": "biologist | statistician | bioinformatician",
      "assigned_gap": "...",
      "why_needed": "...",
      "expected_output": "..."
    }
  ]
}
```

Implementation approach:

```text
1. Keep current formulate() rounds.
2. After initial Mediator output, inspect `callbacks`.
3. If callbacks exist, run only those panelists with callback prompts.
4. Re-run Mediator with prior plan + callback outputs.
5. Limit to explicit budgets.
```

Budgets:

```text
max_mediator_callback_rounds = 3
max_callbacks_per_round = 3
max_callbacks_per_panelist_per_round = 1
max_callback_rounds_after_analysis = 2
```

`max_callbacks_per_round` means the Mediator can ask at most three targeted
panelist callbacks in one refinement cycle. Since there are three panelists, this
allows at most one focused callback per panelist per round. If one panelist has
multiple related gaps, the Mediator should combine them into one focused callback.

If the callback budget is exhausted, the Mediator should produce the best available
plan, record unresolved gaps explicitly, and either proceed to ToolConsultant,
ask the user for clarification, or declare the question unanswerable with current
evidence.
```

### Context Packet

Implement:

```python
_build_panelist_callback_context(...)
```

Context should include:

```text
Original task
Panelist state
Cross-panel state
Mediated state
Adversarial state if relevant
Literature state
```

Do not include:

```text
raw tool plan
implementation plan
expected artifact paths
package/dependency errors
low-level feasibility details
```

### Callback Prompt

Add prompts:

```text
PANELIST_REASONING_CALLBACK_PROMPT
PANELIST_LITERATURE_CALLBACK_PROMPT
MEDIATOR_CALLBACK_SYNTHESIS_PROMPT
```

Callback output:

```json
{
  "role": "...",
  "assigned_gap": "...",
  "role_claims": [],
  "role_uncertainties": [],
  "analysis_requirements": [],
  "evidence_gaps": [],
  "new_reasoning": "...",
  "changed_requirements": [],
  "new_evidence_patterns": [],
  "gap_resolved": true,
  "remaining_uncertainty": "..."
}
```

Callback context packet fields:

```text
Original task:
  user_question
  data_summary
  current_research_iteration
  reason_for_callback

Panelist state:
  role
  prior_role_reasoning
  prior_role_claims
  prior_role_uncertainties

Mediated state:
  selected_research_plan
  alternative_research_plans_summary
  accepted_analysis_requirements
  disputed_or_missing_requirements
  callback_question

Adversarial state:
  critique_summary
  critique_target
  failure_mode
  required_revision

Literature state:
  papers_already_used
  remaining_literature_gaps
```

Do not pass raw tool plans, implementation plans, dependency errors, package
logs, or artifact paths into panelist callbacks. The Mediator should translate
execution feedback into a scientific or reasoning question first.

### Tests

```text
test_mediator_callback_runs_only_assigned_panelist
test_callback_context_excludes_execution_state
test_callback_result_updates_mediator_plan
test_callback_round_limit_prevents_infinite_loop
```

## Phase 4: ToolConsultant And Adversarial Alignment Review

### Goal

Make the second loop explicit:

```text
research plan -> ToolConsultant -> tool/implementation plan -> adversarial review -> Mediator routes critique
```

The research plan and tool plan must stay conceptually separate:

```text
ResearchMediator:
  chooses one active research strategy and records alternatives.

ToolConsultant:
  receives the selected active research plan only.
  converts it into one executable tool pipeline.
  proposes a bounded parameter/method search space inside that pipeline.
```

Different strategies such as clustering-to-abundance, MultiVelo lead-lag
analysis, and trajectory/pseudotime DE are different research plans. They should
not be packed into one ToolConsultant DAG. A ToolConsultant DAG represents one
selected research plan with method/parameter variants over a fixed execution
structure.

### Files

```text
agents/session_dispatcher.py
agents/research_loop.py
agents/adversarial_panelist.py
prompts/adversarial_prompts.py
prompts/tool_consultant_prompts.py
tests/test_research_loop_tool_alignment.py
```

### Current Behavior

Currently, ScientistPanel runs adversarial review before ToolConsultant sees the
plan. That catches scientific plan problems but cannot catch mismatches between
research requirements and executable plan.

### Target Behavior

Keep the current pre-execution adversary, but add a second adversarial reasoning
review after ToolConsultant produces the executable plan.

This review should remain a reasoning critique, not a contract checker and not a
checklist. It should review whether the research plan and executable tool plan
together can answer the user's scientific question. It should ask whether the
planned evidence is strong enough for the intended interpretation, whether the
method output is being overread, whether necessary downstream analysis is missing,
and whether prior literature implies a stronger evidence pattern.

If the plan names a method, the adversary should distinguish running that method
from proving the biological claim the user cares about.

New object:

```json
{
  "research_plan": {},
  "tool_plan": {},
  "implementation_plan": {},
  "adversarial_alignment_review": {}
}
```

ToolConsultant output should also start declaring output semantics and retention
intent, even before ArtifactRegistry enforcement is complete:

```json
{
  "output_retention_policy": [
    {
      "output_id": "clustered_h5ad",
      "semantic_type": "clustered_h5ad",
      "retention_intent": "required_checkpoint | active_branch_output | candidate_until_evaluated | final_output | lightweight_summary | recomputable_intermediate | ephemeral",
      "reason": "Rollback point before annotation and abundance analysis."
    }
  ]
}
```

This is not just storage bookkeeping. It is how the executable plan tells the
StateGraph/ArtifactRegistry which outputs can become future rollback points.

Phases 4-7 behavior:

```text
DagExecutor records output_retention_policy in dag_result.json.
It does not enforce the policy beyond existing keep_intermediates / keep_top_k
behavior until ArtifactRegistry exists.
Full retention enforcement starts in Phase 8.
```

Adversarial prompt framing:

```text
You are reviewing whether the proposed research plan and executable tool plan are
capable of answering the user's scientific question. Do not merely check whether
tools are present. Ask whether the planned evidence would actually support the
intended interpretation, whether the method output is being overread, whether
necessary downstream analysis is missing, whether statistical units and controls
are sufficient, and whether prior literature implies a stronger evidence pattern.

Your critique should identify the weakest assumption in the research/tool plan
and state what must change before execution.
```

Structured output:

```json
{
  "verdict": "survives | needs_revision | unsalvageable",
  "core_critique": "...",
  "weakest_assumption": "...",
  "failure_mode": "none | weak_evidence | missing_analysis | invalid_statistical_unit | overclaim | missing_control | tool_mismatch | alternative_explanation | literature_mismatch | retention_gap",
  "target": "research_plan | tool_plan | implementation_plan | panelist_reasoning | mediator_synthesis",
  "required_revision": "...",
  "questions_for_panelists": [],
  "questions_for_toolconsultant": [],
  "reasoning_trace_summary": "brief human-readable summary of the adversarial reasoning"
}
```

The adversary should focus on the research and tool plan before execution. It
should not review the Analyzer interpretation in this phase.

### Mediator Routing

If alignment review fails, the Mediator routes critique:

```text
scientific requirement issue -> panelist callback or mediator revision
tool mapping issue -> ToolConsultant revision
implementation detail issue -> CoderAgent/ToolConsultant revision
user ambiguity -> clarification_required
```

Phase 4 can start with a simpler version:

```text
Adversary returns adversarial_alignment_review.
If failed due to tool issue, rerun ToolConsultant once with critique.
If failed due to scientific issue, mark for future Phase 3 callback support.
```

### Tests

```text
test_alignment_review_detects_missing_downstream_analysis
test_alignment_review_detects_cell_level_test_for_sample_level_claim
test_toolconsultant_revision_receives_adversarial_critique
test_toolconsultant_output_retention_policy_contains_semantic_types
test_adversarial_alignment_review_returns_reasoned_failure_mode
```

## Phase 5: Analyzer-Driven Phase Update Schema

### Goal

AnalyzerPanel should explicitly report what happened in the execution results.
It should not own the research-plan decision. The Mediator uses the Analyzer
report plus the current research state to decide what should happen next.

Phase 5 defines the Analyzer output schema and Mediator post-analysis decision
schema. It should not define storage layout or StateGraph mechanics. Phase 6 owns
session storage and deterministic StateGraph updates.

### Files

```text
prompts/analyzer_prompts.py
agents/analyzer_panel.py
agents/research_loop.py
agents/session_router.py
agents/session_dispatcher.py
prompts/panelist_prompts.py
prompts/session_router_prompts.py
tests/test_analyzer_phase_update.py
tests/test_session_routing.py
```

### Analyzer Output Additions

Update `ANALYZER_MEDIATOR_PROMPT` output:

```json
{
  "results_summary": "...",
  "hypothesis_status": [],
  "evidence_requirement_status": [
    {
      "requirement": "...",
      "status": "satisfied | partial | missing | invalid",
      "evidence": "...",
      "needed_next": "...",
      "linked_research_step_id": "nullable until StateGraph exists",
      "linked_tool_step_id": "nullable until ToolConsultant step IDs exist",
      "linked_artifact_handle": "nullable until ArtifactRegistry exists"
    }
  ],
  "result_verdict": "supported | contradicted | inconclusive | invalid | missing_outputs",
  "problem_localization": {
    "problem_stage": "none | qc | normalization | feature_selection | embedding | clustering | annotation | abundance | trajectory | velocity | differential_test | visualization | interpretation | unknown",
    "problem_type": "none | parameter_error | missing_covariate | invalid_output | weak_validation | wrong_method | unsupported_claim | missing_output | dependency_failure | data_limitation | unknown",
    "affected_research_step_ids": [],
    "affected_tool_step_ids": [],
    "affected_artifact_handles": [],
    "nearest_valid_artifact_before_problem": null,
    "reuse_upstream_possible": true
  },
  "recommended_plan_changes": [],
  "future_directions": [],
  "improvements": []
}
```

### ResearchLoop Behavior

ResearchLoop should pass AnalyzerPanel output to the Mediator for one
post-analysis decision point. In Phase 5, graph and artifact fields may be null
or absent because StateGraph and ArtifactRegistry are introduced later.

The Mediator eventually receives:

```text
current research state summary
StateGraph trajectory context when available
selected active research plan
alternative research plans
ToolConsultant plan
DagExecutor result
Analyzer report
ArtifactRegistry summary
```

Until those systems exist, the Mediator receives the best available current
session state and must not hallucinate artifact handles.

Post-analysis flow:

```text
Research iteration N
  -> AnalyzerPanel
      reports what happened
  -> Mediator
      outputs a structured research decision and next plan if needed
```

Allowed Mediator post-analysis decision types:

```text
conclude
ask_user_clarification
request_tool_plan_revision
ask_panelist_callback
start_panel_update_round
interpretation_only
new_downstream_analysis
parameter_change
upstream_preprocessing_change
method_replacement
data_change
revise_plan
declare_unanswerable
produce_next_research_plan
```

Ownership split:

```text
AnalyzerPanel:
  says what happened in the results:
    supported
    contradicted
    inconclusive
    invalid
    missing_outputs

Mediator:
  decides what the research plan should do next:
    interpretation_only
    new_downstream_analysis
    parameter_change
    upstream_preprocessing_change
    method_replacement
    data_change
    revise_plan
    conclude
    declare_unanswerable
```

ToolConsultant is responsible only for tool / implementation plan revisions. It
does not decide the research-plan action.

The Mediator should not mutate graph state by prose and should not be required
to speak internal StateGraph terminology. It should produce a structured
post-analysis research decision. The decision may include a next research plan,
`continue_from_node_id`, and `continue_from_artifact` when those concepts are
available, but it does not directly edit the StateGraph. Before Phase 6 exists,
the Mediator decision should be stored as a structured post-analysis decision
without graph mutation.

Not every Mediator decision mutates the graph:

```text
ask_user_clarification:
  set session status to awaiting_user
  no new node

request_tool_plan_revision:
  rerun ToolConsultant against the same active node
  no new research node unless the research plan changes

ask_panelist_callback:
  run targeted callbacks
  no graph mutation until callback outputs are integrated into a new Mediator
  decision

start_panel_update_round:
  run ScientistPanel.update once
  no graph mutation until the update produces a changed research plan

produce_next_research_plan:
  formulate the next plan first
  Orchestrator compares it with the active plan and creates a new node only if
  the plan trajectory changed
```

If the Mediator chooses `ask_panelist_callback`:

```text
Run up to max_callback_rounds_after_analysis = 2 targeted callback rounds.
Each callback round can ask at most one focused question per panelist.
Mediator integrates callback outputs.
Mediator must then choose:
  conclude
  ask_user_clarification
  request_tool_plan_revision
  produce_next_research_plan
  declare_unanswerable
```

If the Mediator chooses `start_panel_update_round`:

```text
Run ScientistPanel.update once for this research iteration.
The update round may internally use up to 3 reasoning rounds.
Panelists may retrieve literature if needed.
Mediator synthesizes next_research_plan.
No second start_panel_update_round is allowed for the same research iteration.
```

Rule:

```text
Full update is a research-iteration transition action, not a recursive reasoning
action.
```

### Tests

```text
test_analyzer_can_request_new_downstream_analysis
test_analyzer_can_mark_outputs_insufficient
test_analyzer_problem_localization_includes_stage_type_and_artifact
test_mediator_receives_analyzer_report_and_state_graph_before_update_action
test_targeted_callbacks_after_analysis_are_budget_limited
test_full_panel_update_runs_at_most_once_per_execution_phase
test_toolconsultant_revision_happens_only_after_mediator_research_plan_decision
test_orchestrator_applies_mediator_decision_to_state_graph
```

## Phase 6: Session Storage And StateGraph

### Goal

Add a persistent session-centered storage model and a StateGraph describing how
the system has tackled the problem so far.

The storage model must work for both:

```text
operational runs:
  router -> ToolConsultant -> execution -> ResultSummarizer

discovery runs:
  router -> ScientistPanel -> Mediator -> Adversary -> ToolConsultant
  -> execution -> AnalyzerPanel -> Mediator update
```

The StateGraph is a graph of solution / plan states, not a graph of every
execution or analysis event. A node represents one solution attempt, operational
plan, or research plan state. Execution outputs, Analyzer reports, LLM traces,
and artifacts are saved as files and attached to nodes by reference.

The Mediator sees the trajectory context and outputs a structured research
decision. ResearchLoop / Orchestrator validates that decision, records any
resulting StateGraph changes, and attaches execution / analysis references after
tools run.

### Files

```text
agents/session_recorder.py          # new
agents/conversation_manager.py      # new or fold into frontend/session layer
agents/state_graph.py              # new
agents/state_graph_manager.py      # new deterministic StateGraph helper
agents/scientist_panel.py
agents/research_loop.py
agents/session_dispatcher.py
agents/session_state.py
frontend/server.py
prompts/panelist_prompts.py
tests/test_state_graph.py
tests/test_session_storage.py
tests/test_mediator_state_graph_updates.py
```

### Storage Concepts

Use strict concepts:

```text
Conversation:
  one frontend/project conversation containing multiple task sessions

Session:
  one task or research episode

Iteration:
  one plan -> execute -> analyze cycle inside a session

Node:
  one plan state inside a session

Trace:
  raw and parsed LLM reasoning, transcripts, and tool calls

Execution:
  actual DAG or code run

Artifact:
  concrete produced file with a stable handle

Report:
  human-readable or structured interpretation / final answer
```

The current `results_frontend`, `tool_artifacts_frontend`, `saved_code_frontend`,
and `feedback` split should be replaced by one session-centered layout. Frontend
is a display client, not the storage root.

Recommended layout:

```text
runs/
  conversations/
    {conversation_id}/
      conversation.json
      sessions/
        {session_id}/
          session.json
          state_graph.json
          progress.jsonl

          route/
            route_decision.json
            dispatch.json

          clarification/
            request.md
            options.json

          nodes/
            {node_id}/
              node.json
              operational_plan.json
              research_plan.md
              research_plan.json
              literature_refs.json
              adversarial_review.md
              tool_plan.json
              implementation_plan.md
              execution_summary.json
              analyzer_report.md
              analyzer_report.json
              result_summary.md
              next_decision.json
              artifact_refs.json

          traces/
            router/
            panelists/
            mediator/
            adversary/
            tool_consultant/
            analyzer/
            summarizer/
            responder/

          executions/
            {execution_id}/
              dag_plan.json
              dag_result.json
              coder_report.json
              leaderboard.json
              stdout.log
              stderr.log
              path_*/

          artifacts/
            artifact_registry.json
            files/

          reports/
            final_answer.md
            final_answer.json
```

`conversation_id`, `session_id`, and `iteration_id` have different
lifetimes:

```text
conversation_id:
  broad frontend/project conversation. Generated server-side when a new
  conversation starts, returned to the frontend, and sent back on later turns.

session_id:
  one task or research episode inside a conversation. Follow-up questions,
  clarification answers, downstream plots, parameter changes, and analysis of
  previous outputs stay in the same session when they belong to the same task.
  A new session starts for an unrelated dataset, unrelated biological question,
  or unrelated tool workflow.

iteration_id:
  one plan -> execute -> analyze cycle inside a session. A single discovery
  session can have multiple iterations when Analyzer/Mediator feedback revises
  the plan.
```

Example:

```text
conversation C001

session S001: "Run MultiVelo and determine chromatin priming"
  original user request
  iteration_001: initial plan -> execute -> analyze
  user asks follow-up about the result
  iteration_002: revised downstream analysis if needed
  user asks for a plot from the same output
```

Later sessions may reference artifacts from earlier sessions through
ArtifactRegistry handles.

### Save Ownership

Use one `SessionRecorder` abstraction to own paths, common metadata writes, and
`progress.jsonl`. The component that creates information saves the detailed file
through `SessionRecorder`.

```text
ConversationManager:
  creates conversation_id
  creates or reuses session_id based on whether the user is continuing the same
  task episode
  owns conversation.json

SessionRecorder:
  owns session.json
  owns progress.jsonl
  owns directory layout
  provides save_* helpers

SessionRouter:
  saves route decision and router traces

ScientistPanel:
  saves panelist raw responses, parsed reasoning, and panelist tool calls

Mediator:
  saves mediator synthesis and post-analysis trajectory decisions

AdversarialPanelist:
  saves adversarial critique

ToolConsultant:
  saves tool plan / implementation plan and tool-call traces

DagExecutor / CoderAgent:
  saves execution outputs under executions/{execution_id}/

ArtifactRegistry:
  registers concrete output files and returns stable artifact handles

AnalyzerPanel:
  saves raw response, parsed report, and human report

ResultSummarizer:
  saves final user-facing answer for operational runs

StateGraph:
  stores compact node records and references to saved files
```

Important rule:

```text
StateGraph records references.
ArtifactRegistry records produced files and stable handles.
SessionRecorder records where everything is saved.
```

### Save Timeline

Step 0: user sends a message.

```text
Saver:
  ConversationManager / SessionRecorder

Save:
  conversations/{conversation_id}/conversation.json
  sessions/{session_id}/session.json
  sessions/{session_id}/progress.jsonl

Update:
  append user message to session.json.message_history[]
```

Step 1: route the request.

```text
Saver:
  SessionRouter via SessionRecorder

Save:
  route/route_decision.json
  traces/router/transcript.jsonl
  traces/router/tool_calls.jsonl if any

Update:
  session.json.route_ref
  progress.jsonl
```

Step 2A: direct response with no execution.

```text
Saver:
  DeterministicResponder / ResultSummarizer via SessionRecorder

Save:
  traces/responder/final_response.md

Update:
  session.json.status = completed

Graph:
  no node required unless the response changes reusable state
```

Step 2B: clarification needed.

```text
Saver:
  SessionDispatcher / SessionRecorder

Save:
  clarification/request.md
  clarification/options.json

Update:
  session.json.status = awaiting_user

Graph:
  no plan node yet because no plan was selected
```

Step 2C: operational task without discovery.

```text
Saver:
  SessionDispatcher / StateGraph

Create:
  nodes/op_001/node.json

Save:
  nodes/op_001/operational_plan.json

Update:
  state_graph.json
  session.json.active_node_id = op_001
```

Step 2D: discovery task.

```text
Saver:
  ScientistPanel + Mediator + AdversarialPanelist via SessionRecorder

Save:
  traces/panelists/{role}/round_001_raw_response.txt
  traces/panelists/{role}/round_001_parsed.json
  traces/panelists/{role}/round_001_tool_calls.jsonl
  traces/mediator/formulate_round_001_raw_response.txt
  traces/mediator/formulate_round_001_parsed.json
  traces/adversary/review_round_001_raw_response.txt
  traces/adversary/review_round_001_parsed.json

Create:
  nodes/plan_001/node.json
  nodes/plan_001/research_plan.md
  nodes/plan_001/research_plan.json
  nodes/plan_001/literature_refs.json
  nodes/plan_001/adversarial_review.md

Update:
  state_graph.json
  session.json.active_node_id = plan_001
```

Step 3: ToolConsultant converts the selected node into an executable plan.

```text
Saver:
  ToolConsultant via SessionRecorder

Save:
  traces/tool_consultant/transcript.jsonl
  traces/tool_consultant/tool_calls.jsonl
  traces/tool_consultant/decision.json
  nodes/{node_id}/tool_plan.json
  nodes/{node_id}/implementation_plan.md if present

Update:
  nodes/{node_id}/node.json.tool_plan_ref
  progress.jsonl
```

Step 4: execute DAG or code.

```text
Saver:
  DagExecutor or CoderAgent

Save for DAG:
  executions/{execution_id}/dag_plan.json
  executions/{execution_id}/dag_result.json
  executions/{execution_id}/leaderboard.json
  executions/{execution_id}/stdout.log
  executions/{execution_id}/stderr.log
  executions/{execution_id}/path_*/

Save for code:
  executions/{execution_id}/script.py
  executions/{execution_id}/coder_report.json
  executions/{execution_id}/attempts/

Update:
  nodes/{node_id}/execution_summary.json
  nodes/{node_id}/node.json.execution_refs
  progress.jsonl
```

`leaderboard.json` schema:

```json
{
  "execution_id": "exec_001",
  "tool_plan_id": "tool_plan_001",
  "objective_name": "...",
  "scored_paths": [
    {
      "path_index": 0,
      "path_id": "path_000",
      "status": "completed | failed | skipped",
      "score": 0.82,
      "objective_metrics": {},
      "artifact_handles": [],
      "selected": false,
      "rejection_reason": ""
    }
  ],
  "selected_path_index": 1,
  "selected_path_id": "path_001",
  "selection_reason": "...",
  "selected_artifact_handles": []
}
```

DagExecutor writes the leaderboard after scoring candidate DAG paths. The
ArtifactRegistry uses the selected path and selected artifact handles to promote
the winning candidate outputs and record rejected candidate metadata.

Step 5: register artifacts.

```text
Saver:
  ArtifactRegistry

Input:
  dag_result.json or coder_report.json

Save:
  artifacts/artifact_registry.json

Optionally move/copy retained files to:
  artifacts/files/{artifact_id}/...

Return:
  artifact://session/{session_id}/iteration/{iteration_id}/{semantic_type}/{label}

Update:
  nodes/{node_id}/artifact_refs.json
  nodes/{node_id}/node.json.artifact_handles
  session.json.active_artifacts
```

Step 6A: operational summarization.

```text
Saver:
  ResultSummarizer

Save:
  traces/summarizer/transcript.jsonl
  traces/summarizer/final_response.md
  nodes/{node_id}/result_summary.md

Update:
  session.json.final_response_ref
  session.json.status = completed
```

Step 6B: discovery analysis.

```text
Saver:
  AnalyzerPanel

Save:
  traces/analyzer/{node_id}_raw_response.txt
  traces/analyzer/{node_id}_parsed_report.json
  traces/analyzer/{node_id}_report.md
  nodes/{node_id}/analyzer_report.md
  nodes/{node_id}/analyzer_report.json

Update:
  nodes/{node_id}/node.json.analyzer_refs
  progress.jsonl
```

Step 7: Mediator decides next trajectory after Analyzer.

```text
Saver:
  Mediator + StateGraph

Save:
  traces/mediator/update_after_analysis_raw_response.txt
  traces/mediator/update_after_analysis_parsed.json
  nodes/{node_id}/next_decision.json

If plan changes:
  create nodes/plan_002/node.json
  create nodes/plan_002/research_plan.md
  update state_graph.json edge plan_001 -> plan_002

If no plan changes:
  update nodes/{node_id}/node.json.status

Update:
  session.json.active_node_id
  progress.jsonl
```

Step 8: final answer.

```text
Saver:
  ResultSummarizer or AnalyzerPanel/Mediator finalizer

Save:
  reports/final_answer.md
  reports/final_answer.json

Update:
  session.json.final_response_ref
  session.json.status = completed
  conversation.json.latest_session_id
```

### Core Separation

```text
StateGraph:
  graph of solution / plan states
  stores selected plan nodes, alternative plan nodes, revised branch nodes,
  unanswerable/concluded states, and parent/child trajectory edges
  plan nodes point to saved plan/report/result files and artifact handles

ArtifactRegistry:
  physical artifact inventory
  stores files, paths, hashes, provenance, parent artifact links, retention status

StateGraph helper:
  deterministic helper used by ResearchLoop / Orchestrator
  records the graph transition inferred from the Mediator research decision
  derives graph mutations from validated plans, node refs, and artifact refs
  marks the active branch
```

### StateGraph Node Types

`node_id` is the ID of one solution / plan state in the research trajectory. It
is not an execution ID and not an artifact ID.

Examples:

```text
op_001
op_002
plan_001
plan_002
plan_003
conclusion_001
```

For no-discovery runs, create an operational node. The node means "the selected
way this request was handled", not necessarily "a scientific research plan".

Minimum node types:

```json
{
  "node_id": "...",
  "node_type": "operational_plan | research_plan | conclusion",
  "mode": "operational | discovery",
  "status": "active | inactive | candidate | completed | completed_inconclusive | execution_failed | invalid | superseded | awaiting_user | unanswerable | concluded",
  "created_at": "...",
  "summary": "...",
  "metadata": {},
  "route_ref": "...",
  "plan_path": "...",
  "plan_json_path": "...",
  "tool_plan_ref": "...",
  "implementation_plan_ref": "...",
  "execution_refs": [],
  "analyzer_refs": {},
  "analyzer_report_path": "...",
  "result_summary_path": "...",
  "trace_refs": {},
  "artifact_refs_path": "...",
  "artifact_handles": []
}
```

Operational nodes:

```json
{
  "node_id": "op_001",
  "node_type": "operational_plan",
  "mode": "operational",
  "status": "completed",
  "user_question": "Run cell type annotation on this PBMC dataset.",
  "route_ref": "route/route_decision.json",
  "tool_plan_ref": "nodes/op_001/tool_plan.json",
  "execution_refs": ["executions/exec_001/dag_result.json"],
  "artifact_refs_path": "nodes/op_001/artifact_refs.json",
  "trace_refs": {
    "tool_consultant": "traces/tool_consultant/decision.json",
    "summarizer": "traces/summarizer/final_response.md"
  }
}
```

Research plan nodes:

```json
{
  "node_id": "plan_001",
  "node_type": "research_plan",
  "mode": "discovery",
  "plan_id": "plan_a_v1",
  "role": "selected | alternative",
  "parent_node_id": null,
  "continue_from_node_id": null,
  "continue_from_artifact": null,
  "transition_reason": "",
  "steps": [],
  "evidence_requirements": [],
  "selection_rationale": "...",
  "why_not_selected_now": null,
  "active": true,
  "trace_refs": {
    "panelist_reasoning": [
      "traces/panelists/biologist/round_001_parsed.json",
      "traces/panelists/statistician/round_001_parsed.json",
      "traces/panelists/bioinformatician/round_001_parsed.json"
    ],
    "mediator": "traces/mediator/formulate_round_001_parsed.json",
    "adversary": "traces/adversary/review_round_001_parsed.json",
    "tool_consultant": "traces/tool_consultant/decision.json",
    "analyzer": "traces/analyzer/plan_001_parsed_report.json"
  }
}
```

Nodes should remain compact and readable. Verbose raw LLM responses, transcripts,
tool calls, stdout/stderr, and full execution directories belong under `traces/`
or `executions/`, then nodes reference them.

### StateGraph Edges

Do not introduce an edge-type taxonomy. The graph only needs parent-child edges
with metadata explaining why the child exists.

Edge schema:

```json
{
  "from_node_id": "plan_001",
  "to_node_id": "plan_002",
  "reason": "Analyzer found the MultiVelo output insufficient for the chromatin priming claim.",
  "transition_reason": "revise_current_plan | promote_alternative | rollback_after_failure | new_hypothesis | user_followup | downstream_extension",
  "continue_from_node_id": "plan_001",
  "continue_from_artifact": "artifact://session/S001/iteration/iteration_001/velocity_output/best",
  "mediator_decision_ref": "nodes/plan_001/next_decision.json",
  "created_by": "ResearchLoop",
  "created_at": "..."
}
```

The meaning of a transition comes from node status plus edge metadata, not from
named edge types.

### StateGraph Update Helper

The Mediator should not send arbitrary `new_nodes`, `new_edges`, and
`status_updates` as free-form graph mutations. That would make the graph only as
reliable as one LLM response.

Do not make StateGraph updating a new LLM agent. It should be a deterministic
helper owned by ResearchLoop / Orchestrator.

The Mediator outputs a structured research decision. ResearchLoop / Orchestrator
compares that decision with the active node, prior tried solutions, next plan,
Analyzer report, and ArtifactRegistry state, then applies deterministic graph
rules.

The graph rule is intentionally simple:

```text
If the research plan materially changes:
  create a new node connected to the requested continuation node.

If only execution parameters change within the same research plan:
  record a repeat iteration on the same node.

If no execution is needed:
  update the current node only.

If the task is terminal:
  mark the current node concluded or unanswerable.
```

The important decision is where to continue from. The Mediator may provide
`continue_from_node_id` and `continue_from_artifact`; ResearchLoop / Orchestrator
validates them before recording anything.

Execution and analysis attachment are not graph actions. They are deterministic
Orchestrator bookkeeping. After execution or analysis completes, the Orchestrator
already knows the active `node_id`, `iteration_id`, `execution_id`, result paths,
Analyzer report paths, and artifact handles. It writes those references directly
to `node.json`, `execution_summary.json`, and `artifact_refs.json` through
SessionRecorder / ArtifactRegistry without asking the Mediator for a graph
action.

Mediator post-analysis decision shape:

```json
{
  "decision_type": "conclude | ask_user_clarification | request_tool_plan_revision | ask_panelist_callback | start_panel_update_round | produce_next_research_plan | interpretation_only | new_downstream_analysis | parameter_change | upstream_preprocessing_change | method_replacement | data_change | revise_plan | declare_unanswerable",
  "reason": "...",
  "continue_from_node_id": "plan_001",
  "continue_from_artifact": "artifact://session/S001/iteration/iteration_001/velocity_output/best",
  "next_research_plan": {},
  "requested_tool_plan_revision": {},
  "panelist_callback_requests": [],
  "clarifying_questions": [],
  "terminal_summary": {}
}
```

ResearchLoop / Orchestrator must validate `continue_from_node_id` and
`continue_from_artifact` before using them. The Mediator may choose where and why
to continue from, but deterministic code decides whether that requested start
point is legal and how to record it.

Creating a new node is the only structural graph operation for starting a new
solution state. The new node is created from a validated `continue_from_node_id`
and marked active when it is selected for execution or interpretation. Revised
plans, promoted alternatives, rollback-based fixes, new hypotheses, user
follow-ups, and downstream extensions all use this same structural operation.
`transition_reason` is metadata explaining why the new node exists.

The continuation node should be the closest preceding solution node in plan
logic, not necessarily the latest node in time.

Old node status is determined by evidence, not by `transition_reason` alone:

```text
if old plan was wrong:
  old node -> invalid

if old plan was replaced before completion:
  old node -> superseded

if old plan completed and the new branch extends it:
  old node -> completed

if old plan remains usable but is no longer active:
  old node -> inactive
```

The StateGraph helper should validate:

```text
referenced nodes exist
referenced artifact handles exist in ArtifactRegistry or are marked pending
only one solution_plan node is active at a time
continue_from_node_id exists
continue_from_artifact points to a valid or pending artifact handle when provided
continue_from_artifact belongs to, or descends from, continue_from_node_id
new node creation records parent/continuation metadata
old node status is updated only from explicit evidence/status fields, not from
transition_reason alone
```

StateGraph initialization timing:

```text
Operational task:
  SessionDispatcher creates an operational node after routing but before
  ToolConsultant execution planning.

Discovery task immediately after initial Mediator formulation:
  Orchestrator initializes the StateGraph deterministically
  creates selected solution node
  creates alternative solution nodes
  marks exactly one solution node active

Do this before ToolConsultant receives the selected plan. The ordering is
enforced by Orchestrator / SessionDispatcher call sequence, not by prompt
instruction.
```

### Mediator Responsibilities With StateGraph

Before `Mediator.update_from_analysis`, ResearchLoop builds a compact trajectory
context packet from StateGraph + ArtifactRegistry. The Mediator must see prior
tried solutions so it can decide where to continue from instead of only reacting
to the latest result.

Trajectory context packet:

```json
{
  "active_node": {
    "node_id": "plan_003",
    "summary": "...",
    "status": "completed_inconclusive",
    "latest_analyzer_verdict": "inconclusive",
    "artifact_handles": []
  },
  "tried_solutions": [
    {
      "node_id": "plan_001",
      "summary": "...",
      "outcome": "completed | invalid | superseded | inconclusive",
      "what_was_learned": "...",
      "why_insufficient": "...",
      "usable_artifacts": []
    }
  ],
  "untried_alternatives": [
    {
      "plan_id": "plan_b",
      "summary": "...",
      "why_not_selected_before": "...",
      "when_to_try": "..."
    }
  ],
  "reusable_artifacts": [
    {
      "handle": "artifact://session/S001/iteration/iteration_001/annotated_h5ad/best",
      "semantic_type": "annotated_h5ad",
      "producing_node_id": "plan_001",
      "producing_iteration_id": "iteration_001",
      "reusable": true
    }
  ],
  "unresolved_gaps": []
}
```

The Mediator decides the research trajectory semantically, but the graph
operation stays deterministic. Many scientific decisions map to the same
structural graph operation.

The Mediator may decide:

```text
carry forward:
  current plan worked; continue with downstream analysis

repeat step:
  same upstream artifact, same research plan, revised tool parameters

rollback to step/artifact:
  ask to continue from the closest valid parent artifact before the failed step

revise current plan:
  output a next plan with the same broad plan but changed evidence requirement or
  analysis step

promote alternative plan:
  select the alternative plan because it now better answers the
  question

create new branch:
  current results reveal a new hypothesis or path worth testing
```

ResearchLoop / Orchestrator compares the Mediator decision and next plan against
the active node and trajectory context. If the plan trajectory changed, it
creates a new node and a simple parent-child edge with metadata. If the plan did
not change, it updates the current node or records another iteration under the
current node.

### Tests

```text
test_session_recorder_creates_conversation_and_session_layout
test_operational_run_creates_operational_node_without_panelist_traces
test_discovery_run_creates_research_node_with_reasoning_refs
test_direct_response_saves_session_without_plan_node
test_clarification_saves_awaiting_user_without_plan_node
test_progress_panel_reads_progress_jsonl_not_recent_file_scan
test_state_graph_allows_one_active_selected_plan
test_state_graph_records_alternative_plans
test_state_graph_helper_creates_node_from_logical_predecessor
test_state_graph_helper_rejects_freeform_node_mutation
test_state_graph_edges_are_parent_child_with_metadata
test_mediator_receives_tried_solution_history
test_orchestrator_validates_continue_from_artifact
test_initialize_plan_runs_before_toolconsultant
test_new_node_can_promote_alternative_plan
test_declare_unanswerable_marks_active_node_terminal
```

## Phase 7: Conservative Incremental Planning MVP

### Goal

Before ArtifactRegistry exists, future phases should avoid unnecessary execution
only in the safe cases. This is a conservative bridge, not the final self-evolving
rollback system.

The goal is to support:

```text
interpretation_only:
  no execution

new_downstream_analysis:
  reuse active_h5ad_path only after validating the path exists

all upstream or uncertain changes:
  rerun full plan
```

Full delta planning from StateGraph nodes and ArtifactRegistry handles belongs
to Phase 9, after handles and retention are implemented.

### Files

```text
agents/research_loop.py
agents/session_dispatcher.py
prompts/tool_consultant_prompts.py
agents/dag_executor.py
tests/test_incremental_phase_planning.py
```

### Conservative Plan Contract

ToolConsultant should accept:

```text
active_research_plan
previous_tool_plan
analyzer_feedback
revised_analysis_requirements
active_h5ad_path
```

and return:

```json
{
  "plan_type": "full | interpretation_only | downstream_only",
  "start_from_path": "/validated/path/or/null",
  "reuse": [],
  "rerun": [],
  "add": [],
  "do_not_rerun": [],
  "reasoning": "..."
}
```

### Change Rules

Implement the policy:

```text
interpretation_only:
  no execution, update answer/model only

new_downstream_analysis:
  reuse active_h5ad_path only after existence validation

parameter_change:
  rerun full plan in the MVP

upstream_preprocessing_change:
  rerun full plan in the MVP

method_replacement:
  rerun full plan in the MVP

data_change:
  rerun full plan in the MVP
```

`active_h5ad_path` source before ArtifactRegistry:

```text
1. Prefer dag_result.best_path.resolved_outputs.output_h5ad_path.
2. Validate the path exists before passing it to ToolConsultant or CoderAgent.
3. If the path is missing or invalid, set active_h5ad_path = null.
4. If active_h5ad_path is null, ToolConsultant must return plan_type = "full"
   rather than attempting downstream-only reuse.
```

### Tests

```text
test_interpretation_only_skips_execution
test_new_downstream_analysis_uses_active_h5ad_when_valid
test_upstream_change_forces_full_rerun_before_artifact_registry
```

## Phase 8: ArtifactRegistry, Handles, And Selective Retention

### Goal

Stop passing stale raw paths between research phases. Use logical artifact handles
and resolve them immediately before execution.

ArtifactRegistry is not the same as StateGraph:

```text
StateGraph:
  why an artifact matters in the research process

ArtifactRegistry:
  where the artifact is, what produced it, whether it is valid, and whether it
  can be reused or recomputed
```

StateGraph nodes should reference artifact handles. They should not store raw file
paths as the primary contract.

### Files

```text
backend/artifacts/registry.py       # new
backend/artifacts/manifest.py       # extend or keep as low-level manifest
agents/dag_executor.py
agents/session_state.py
agents/session_dispatcher.py
prompts/tool_consultant_prompts.py
prompts/coder_agent_prompts.py
tests/test_artifact_registry.py
tests/test_artifact_resolution.py
```

### Artifact Registry Schema

Add registry entries:

```json
{
  "artifact_id": "artifact://session/{session_id}/iteration/{iteration_id}/{semantic_type}/{label}",
  "handle": "artifact://session/{session_id}/iteration/{iteration_id}/{semantic_type}/{label}",
  "path": ".../path_000/04_rna_cluster_leiden/output.h5ad",
  "status": "pending | candidate | promoted | rejected | superseded | valid | deleted_recomputable | stale | missing | invalid",
  "semantic_type": "raw_h5ad | qc_h5ad | normalized_h5ad | feature_selected_h5ad | embedded_h5ad | clustered_h5ad | annotated_h5ad | multimodal_h5ad | velocity_output | trajectory_output | abundance_table | de_table | figure | model | metadata",
  "stage": "raw | qc | normalize | feature_selection | embed | cluster | annotation | trajectory | velocity | abundance | differential_test | visualization | custom",
  "producer_step_id": "cluster_rna",
  "producer_tool": "rna_cluster_leiden",
  "producer_method": "leiden",
  "iteration_id": "iteration_001",
  "research_plan_id": "plan_a_v1",
  "tool_plan_id": "tool_plan_1_v1",
  "run_id": "...",
  "path_index": 3,
  "modality": "rna",
  "kind": "h5ad",
  "sha256": "...",
  "parents": ["artifact://session/{session_id}/iteration/{iteration_id}/embedded_h5ad/best"],
  "children": [],
  "inputs": ["artifact://session/{session_id}/iteration/{iteration_id}/embedded_h5ad/best"],
  "params": {},
  "param_hash": "...",
  "code_hash": "...",
  "dependencies": [],
  "metrics": {},
  "rejection_reason": "",
  "retention": "required_checkpoint | active_branch_output | candidate_until_evaluated | final_output | lightweight_summary | recomputable_intermediate | ephemeral",
  "reusable": true,
  "can_recompute": true
}
```

Canonical handle format:

```text
artifact://session/{session_id}/iteration/{iteration_id}/{semantic_type}/{label}
```

Examples:

```text
artifact://session/S03/iteration/iteration_001/clustered_h5ad/best
artifact://session/S03/iteration/iteration_001/clustered_h5ad/candidate_res_0_8
artifact://session/S03/iteration/iteration_002/annotation_table/v1
```

Use this format everywhere. Include `session_id` from the start so cross-session
reuse and lookup are unambiguous.

### Handle Resolution

Implement:

```python
resolve_artifact_handle(handle: str, expected: dict | None = None) -> ResolvedArtifact
```

Validation:

```text
handle exists
status is valid or deleted_recomputable
path exists when status is valid
sha256 matches when available
producer step completed
iteration/session matches or artifact marked reusable
modality/kind/stage match expected constraints
```

### Prompt Rules

ToolConsultant and CoderAgent should use handles in plans:

```json
{
  "inputs": {
    "rna_h5ad": "artifact://session/S03/iteration/iteration_001/clustered_h5ad/best"
  }
}
```

Dispatcher resolves handles to real paths before execution.

Coder prompt rule:

```text
Use only resolved paths from RESOLVED_INPUTS.
Do not invent, guess, glob, or hardcode artifact paths.
```

### Selective Retention

Extend retention policy in `DagExecutor`:

```text
required_checkpoint:
  keep h5ad

active_branch_output:
  keep artifact used by the active StateGraph branch

candidate_until_evaluated:
  keep temporarily until branch scoring/analyzer selection completes

final_output:
  keep h5ad

lightweight_summary:
  keep metadata/table/figure

recomputable_intermediate:
  may delete h5ad but keep provenance

ephemeral:
  delete
```

ToolConsultant should declare retention intent per output in the tool plan:

```json
{
  "output_id": "clustered_h5ad",
  "semantic_type": "clustered_h5ad",
  "retention_intent": "required_checkpoint",
  "reason": "Potential rollback point before annotation and abundance analysis."
}
```

Wiki/tool metadata should provide defaults, and ToolConsultant can override them
when the current research plan needs a stronger checkpoint. DagExecutor and
ArtifactRegistry enforce the policy after execution.

During parameter search, do not overwrite candidate outputs. Store candidates
separately, score them, then promote the winning path:

```text
artifact://session/S03/iteration/iteration_001/clustered_h5ad/candidate_res_0_4
artifact://session/S03/iteration/iteration_001/clustered_h5ad/candidate_res_0_8
artifact://session/S03/iteration/iteration_001/clustered_h5ad/candidate_res_1_2

promoted winner:
artifact://session/S03/iteration/iteration_001/clustered_h5ad/best
```

Rejected candidate records should keep metrics and rejection reasons even when
large files are deleted.

Research runs should mark likely branch points as checkpoints:

```text
filtered h5ad
normalized / feature-selected h5ad when expensive
integrated embedding or multimodal latent output
annotation output
trajectory / velocity output
final analysis h5ad
```

### Tests

```text
test_registry_records_valid_artifact_handle
test_resolver_rejects_missing_file
test_resolver_rejects_stale_sha
test_deleted_recomputable_artifact_keeps_provenance
test_coder_inputs_are_resolved_from_handles
test_candidate_outputs_are_not_overwritten
test_winning_candidate_is_promoted_to_stable_handle
test_rejected_candidate_keeps_metrics_after_file_cleanup
```

## Phase 9: Full Delta Planning From Graph Nodes And Artifact Handles

### Goal

After StateGraph and ArtifactRegistry exist, future phases should produce real
delta plans instead of full reruns by default. The plan should start from a
StateGraph node and a resolved artifact handle, not from an implicit latest path.

### Files

```text
agents/research_loop.py
agents/session_dispatcher.py
agents/state_graph.py
backend/artifacts/registry.py
prompts/tool_consultant_prompts.py
agents/dag_executor.py
tests/test_delta_planning_with_artifacts.py
```

### Full Delta Plan Contract

ToolConsultant should accept:

```text
current_state_graph
active_research_plan
selected_start_node
selected_start_artifact
previous_tool_plan
artifact_registry_summary
analyzer_feedback
revised_analysis_requirements
```

and return:

```json
{
  "plan_type": "delta",
  "start_from_artifact": "artifact://...",
  "start_from_stage": "...",
  "reuse": [],
  "rerun": [],
  "add": [],
  "do_not_rerun": [],
  "reasoning": "..."
}
```

### Full Delta Rules

```text
interpretation_only:
  no execution, update answer/model only

new_downstream_analysis:
  resolve selected_start_artifact
  verify it is valid and retained
  build downstream-only ToolConsultant plan from that handle

parameter_change:
  rollback to parent artifact before the affected step
  rerun affected step and downstream dependents

method_replacement:
  rollback to parent artifact before replaced method
  rerun replacement and downstream dependents

upstream_preprocessing_change:
  rollback to the artifact before preprocessing change
  rerun from that point

data_change:
  rerun all consumers of changed data
```

Every delta execution should record the new phase as a child of the selected
StateGraph node.

### Scoring Ownership

Do not introduce an `Evaluator` agent. The best-path selection is a deterministic
function over all DAG experiments run for the selected tool plan.

DagExecutor/objective scoring and Analyzer have different jobs:

```text
DagExecutor best-path scoring:
  ranks parameter branches using declared objective metrics.
  selects best computational path inside the selected tool plan.

Analyzer:
  evaluates whether the selected path satisfies research evidence requirements.

Mediator:
  may reject, revise, or roll back from the winning computational path if
  Analyzer says it fails the scientific requirement.
```

This prevents computational metric ranking from silently becoming scientific
truth.

### Tests

```text
test_delta_plan_uses_selected_state_graph_node
test_delta_plan_rejects_invalidated_start_artifact
test_parameter_change_rolls_back_to_parent_artifact
test_method_replacement_reruns_downstream_dependents
test_dag_executor_ranks_candidates_but_analyzer_checks_scientific_requirements
```

## Phase 10: Dependency Preflight

### Goal

Fail before execution when required packages are missing.

### Files

```text
backend/tools/**/*
backend/tools/dependencies.py       # new
agents/dag_executor.py
agents/session_dispatcher.py
frontend/server.py
tests/test_dependency_preflight.py
```

### Tool Declarations

Each tool module should declare:

```python
REQUIRED_IMPORTS = {
    "scanpy": "scanpy",
    "decoupler": "decoupler",
}

OPTIONAL_IMPORTS = {
    "skimage": "scikit-image",
}
```

or expose:

```python
def check_dependencies(params: dict) -> list[DependencyIssue]:
    ...
```

`check_dependencies` is better when dependency requirements depend on params.

Example:

```text
scrublet with automatic threshold:
  requires skimage

scrublet with manual threshold:
  may not require skimage
```

### Preflight Behavior

Before DAG execution:

```text
collect selected tool path
check dependencies for all selected tools
if missing required dependencies:
  return dependency_missing status
  ask user for install approval
  install into configured venv only after approval
  rerun preflight
  start execution only after preflight passes
```

Default declaration rule:

```text
Use REQUIRED_IMPORTS and OPTIONAL_IMPORTS for simple unconditional dependencies.
Use check_dependencies(params) when dependency requirements depend on selected
parameters or execution mode.
If both are present, check_dependencies(params) takes precedence.
```

### Tests

```text
test_preflight_reports_missing_decoupler
test_preflight_reports_missing_skimage_for_auto_scrublet
test_preflight_runs_before_first_dag_step
test_preflight_allows_execution_when_dependencies_present
```

## Integration Milestones

### Milestone 1: Reasoning Contract Only

Deliver:

```text
updated panelist prompts
updated mediator schema
normalizer for mediator plan
tests for schema presence
```

Risk:

```text
Low. Mostly prompt/schema changes.
```

### Milestone 2: Better Literature Flow

Deliver:

```text
search_paper_wiki tool
retrieve_literature tool with retrieval_context_id, exclude_ids, PaperJudge, and canonical summaries
fetch_paper_content tool backed by vector/full-text store
session retrieval cache for all candidates
canonical paper summary schema persisted to wiki only for high-confidence useful papers
old wiki traversal tools removed from default panelist registry
```

Risk:

```text
Medium. Tool-calling behavior changes. Update prompts and registry in the same
implementation step so only the three new literature tools are LLM-callable.
Old functions may remain as internal helpers behind the new tools.
```

### Milestone 3: Callback Refinement

Deliver:

```text
Mediator callback schema
gap-directed panelist callback prompts
max callback rounds
context packet builder
```

Risk:

```text
Medium. Needs careful loop limits and transcript logging.
```

### Milestone 4: Execution Alignment

Deliver:

```text
post-ToolConsultant adversarial alignment review
ToolConsultant revision with critique
simple mismatch detection tests
```

Risk:

```text
Medium. Requires ResearchLoop/SessionDispatcher changes.
```

### Milestone 5: Analyzer Phase Evolution

Deliver:

```text
Analyzer result_verdict / evidence_requirement_status schema
Mediator post-analysis decision schema
ScientistPanel.update used only when Mediator chooses start_panel_update_round
```

Risk:

```text
Medium-low. Mostly prompt/schema and ResearchLoop wiring.
```

### Milestone 6: Session Storage And StateGraph MVP

Deliver:

```text
ConversationManager / SessionRecorder
conversation_id + session_id layout
session.json and progress.jsonl
operational nodes for no-discovery tool runs
research nodes for discovery runs
trace directories for raw/parsed LLM reasoning and tool calls
StateGraph data model
StateGraph helper
selected active plan + alternatives recorded as graph nodes
solution plan nodes can reference saved plan files, Analyzer reports, execution
results, and artifact handles
frontend progress reads progress.jsonl instead of scanning recent files
tests for graph updates and active branch invariants
```

Risk:

```text
Medium-high. This changes the contract between research reasoning and execution,
but can be introduced without changing actual execution first.
```

### Milestone 7: Incremental Research MVP

Deliver:

```text
interpretation_only skips execution
new_downstream_analysis can reuse active_h5ad_path after validation
upstream changes still rerun full plan
```

Risk:

```text
Medium. Must validate active_h5ad_path before use.
```

### Milestone 8: Full Artifact Handles

Deliver:

```text
ArtifactRegistry
artifact:// handles
resolver
selective retention
candidate artifact promotion / rejection records
```

Risk:

```text
High. This affects planning, execution, session state, and generated code.
```

### Milestone 9: Full Delta Planning

Deliver:

```text
delta plans start from StateGraph nodes and resolved artifact handles
parameter/method changes roll back to parent artifacts
DagExecutor best-path scoring ranks computational candidates
Analyzer checks scientific evidence requirements
Mediator can reject or roll back from a computational winner
```

Risk:

```text
High. Requires StateGraph, ArtifactRegistry, ToolConsultant, DagExecutor, and
Analyzer contracts to line up.
```

### Milestone 10: Dependency Preflight

Deliver:

```text
dependency declarations
preflight before DAG execution
user approval install flow
```

Risk:

```text
Medium. Installation flow must be explicit and environment-specific.
```

## Key Design Decisions

### Do Not Remove Current Panelists

Keep the three distinct panelists.

They may reason over overlapping high-level research questions, but they must answer
from different lenses.

### Do Not Give Raw Execution State To Panelist Callbacks

Panelist callbacks should not receive raw tool plans, implementation plans, package
errors, or artifact paths.

Mediator should translate execution feedback into scientific or computational-strategy
questions before asking a panelist.

### Keep ToolConsultant As Implementation Translator

ToolConsultant should not decide scientific meaning.

It receives analysis requirements and returns executable plans.

ToolConsultant should optimize tool usage by proposing bounded method/parameter
branches inside one selected research plan. In this project, method is treated as
one kind of tool parameter. The DAG path search is therefore a parameter-combination
search over tools, not a set of unrelated scientific strategies.

Distinct strategies such as:

```text
clustering -> annotation -> abundance
MultiVelo -> lead-lag analysis
trajectory -> pseudotime DE
```

are different research plans and should be represented by ResearchMediator as a
selected plan plus alternatives, not as one ToolConsultant DAG.

### Existing Solution First, Not Existing Solution Only

The first plan component should establish the strongest known solution path.

The second component may extend it, combine methods, adapt a method, or propose a
new method if justified.

### PaperJudge Judges Paper Utility, Not Scientific Truth

PaperJudge should exist, but it should have a narrow role.

```text
PaperJudge decides:
  whether one paper is useful for one retrieval intent
  what evidence pattern it contributes
  whether it should be shown to the panelist
  whether it should be promoted from session cache to paper wiki

PaperJudge does not decide:
  the final research plan
  whether the biological claim is true
  whether the work is novel
  how the panelist should interpret the evidence
```

This keeps retrieval quality high without taking scientific reasoning away from
the panelists.

### Incremental Execution Requires Artifact Trust

Do not implement aggressive delta execution until artifact handles and validation
exist.

The safe MVP is:

```text
reuse active_h5ad_path only after existence validation
otherwise rerun
```

### StateGraph And ArtifactRegistry Are Different

StateGraph records how the system has reasoned and branched:

```text
which research plan was selected
which alternatives were considered
which research iteration executed
which Analyzer conclusion invalidated a step
which branch is active now
where the next iteration should start
```

ArtifactRegistry records concrete execution objects:

```text
where a file is on disk
what produced it
which parameters produced it
which parent artifact it came from
whether it is valid, retained, recomputable, or deleted
```

StateGraph nodes reference artifact handles. They do not own raw file paths.

### Session Storage Is The Backbone

Do not use frontend feedback directories as the canonical storage system.

Every user turn should be recorded inside a session. A new session is created
only when the user starts a new task or research episode. Operational,
discovery, clarification, direct-response, failed, and blocked turns all save
through the same session layout. They differ in which files exist, not in whether
they use the storage backbone.

```text
direct response:
  session + route + response, usually no graph node

clarification:
  session + route + clarification request, no graph node yet

operational:
  session + operational node + tool plan + execution + artifacts + summary

discovery:
  session + research node(s) + traces + tool plan + execution + artifacts +
  Analyzer report + Mediator trajectory decision
```

The frontend progress panel should read `progress.jsonl`. It should not infer
system state by scanning recent files in `results_frontend` or tool artifact
directories.

### Mediator Owns Research State Updates

Do not introduce a separate PhaseOrchestrator agent in this version. The Mediator
sees the StateGraph trajectory context, Analyzer report, plans, tried solutions,
and reusable artifacts. It decides the next scientific move and may identify
which previous node/artifact to continue from.

The graph update itself must be deterministic and structured. The Mediator
decides where and why to continue; ResearchLoop / Orchestrator validates the
requested continuation point and records the StateGraph transition.

The same Mediator should use separate prompt modes:

```text
formulate:
  synthesize panelist reasoning into selected plan + alternatives

update_from_analysis:
  read Analyzer report + StateGraph trajectory context and choose the next
  research decision / continuation point
```

This is a design compromise: one research owner, but two narrower prompts.

### Prompt Guidance Is Not Enough

Important behavior should be enforced by schema checks, graph validation, or
orchestration rules, not only by natural-language prompts.

```text
Bad behavior: panelist jumps directly to tools
Enforcement: panelist output must include concrete_analysis_claim,
existing_solution_path, and evidence_patterns before Mediator accepts it.

Bad behavior: Mediator executes multiple research plans at once
Enforcement: StateGraph permits only one active selected research_plan.

Bad behavior: ToolConsultant treats different research strategies as DAG variants
Enforcement: alignment review checks whether DAG variants are method/parameter
choices inside one selected plan.

Bad behavior: Analyzer says "bad result" without locating the issue
Enforcement: Analyzer schema requires problem_localization.

Bad behavior: system rolls forward from a bad artifact
Enforcement: StateGraph helper / ArtifactRegistry validation rejects invalidated
artifacts as active start points.

Bad behavior: code guesses a previous output path
Enforcement: CoderAgent receives resolved artifact handles only.
```

## Concrete First PR Scope

The first implementation PR should be deliberately small:

```text
1. Update PANELIST_SHARED_SYSTEM with existing-solution-first reasoning.
2. Update MEDIATOR_FORMULATION_PROMPT schema with selected_research_plan,
   alternative_research_plans, best_effort_claim, and clarification fields.
3. Remove `research_plan` from the prompt schema and add
   _normalize_research_plan_schema() in ScientistPanel to create it as a
   compatibility alias from selected_research_plan.
4. Add mediator prompt-mode tests for formulate vs update_from_analysis.
5. Update Analyzer prompt with result_verdict and evidence_requirement_status fields,
   with graph/artifact fields nullable until later phases.
6. Add tests for prompt/schema contracts.
```

Do not include artifact registry, dependency install flow, or callback loops in the
first PR.

Reason:

```text
The reasoning schema must stabilize before execution and artifact systems can rely
on it.
```
