# Update System Implementation Plan

This plan updates the current system toward the workflow defined in
`/Users/vickydong/Documents/singlecell_Agent/updated_prompts`. The goal is not
only to change prompt text, but to align orchestration, schemas, literature
retrieval, state graph context, executable planning, and analyzer evidence flow.

## Target Architecture

The system should separate four responsibilities cleanly:

1. **ScientistPanel formulation**
   - Three panelists gather lane-specific evidence in parallel.
   - The Mediator directly synthesizes a unified research plan.
   - The Adversary stress-tests the research plan using panelist evidence, cited
     papers, and the plan.

2. **Executable planning**
   - ToolConsultant translates `selected_research_plan` into executable work.
   - Existing tools should be used where they correctly solve part of the plan.
   - Missing or custom analysis should be handed to CoderAgent.
   - CoderAgent saves machine-readable outputs, figures, and artifacts; it does
     not write the scientific final answer.

3. **Tool-plan alignment review**
   - A separate LLM reviewer checks whether the executable plan actually
     satisfies `selected_research_plan`.
   - If the research plan is valid but the executable plan is wrong, route back
     to ToolConsultant.
   - The reviewer does not rewrite or invalidate the research plan. If the
     plan's requirements are unclear, it reports an executable-planning blocker
     for ToolConsultant/Mediator handling rather than changing the research plan.
   - If it survives, execution proceeds.

4. **Post-analysis evolution**
   - Analyzer interprets actual artifacts and metrics, attaching exact evidence.
   - Mediator decides whether to conclude, call panelists, revise the plan, ask
     the user, or declare unanswerable.
   - StateGraph stores records and provides role-specific context for the next
     agent call.

## Terminology

Use these terms consistently:

- `selected_research_plan`: the current plan to execute next. This remains the
  canonical name from TODO3; do not rename it to `goal_satisfying_plan`.
- `evidence_state`: compact accumulated knowledge from literature and results.
- `analysis_claims`: the claim set that the selected plan is trying to support,
  weaken, or refute.
- `state_graph`: persisted trajectory of plans, executions, analyses, artifacts,
  decisions, and branches.

Avoid using `working_model` in new prompts and schemas where it would be
ambiguous. If existing code still uses `working_model`, treat it as a backwards
compatibility alias for `evidence_state`.

## Evidence State Contract

The user question can require multiple claims. The Mediator should create
`analysis_claims`. The ResearchLoop / Orchestrator owns the canonical
`evidence_state`: it initializes it after formulation and merges updates after
literature, execution, Analyzer output, Mediator decisions, and panelist
callbacks.

Use a compact `evidence_state`:

```text
evidence_state:
  analysis_claims:
    - claim_id
    - claim_text
    - status: pending | supported | refuted | inconclusive | partially_supported
    - support_summary
    - contradicting_evidence
    - unresolved_requirements

  open_questions:
    - question
    - why_it_matters
    - would_resolve
    - assigned_to: mediator | panelist | tool_consultant | user | analyzer

  literature_evidence:
    - paper_id
    - title
    - supports_claims
    - evidence_patterns
    - limitations

  execution_evidence:
    - artifact_id
    - path
    - metric_or_result
    - supports_claims
    - limitations

  current_belief:
    short prose summary
```

Do not duplicate this with separate `established_findings`, `refuted_claims`, or
`evidence_gaps` fields unless needed for backwards compatibility. Those concepts
are derivable from claim statuses, open questions, and evidence entries.

Plan steps should explicitly connect to claims for interpretation:

```text
selected_research_plan.steps[*].addresses_claims = ["C1", "C2"]
```

This field is primarily for Analyzer and Mediator interpretation, not for
ToolConsultant execution. ToolConsultant should carry out the selected plan
regardless of this mapping. Analyzer uses the mapping to decide which artifacts,
metrics, and figures bear on which claim.

If `addresses_claims` is missing on a step during transition, Analyzer should
treat that step as potentially relevant to all pending claims and mark the
interpretation linkage as:

```text
claim_linkage: best_effort_unmapped
```

After the new Mediator formulation prompt is active, every step should include
`addresses_claims`.

When a StateGraph node is created, the Orchestrator initializes each claim status
to `pending`. Analyzer and Mediator outputs provide evidence updates; the
Orchestrator merges those updates into the node's `evidence_state`.

The Mediator formulation output should produce enough structured content to
initialize evidence state:

```text
analysis_claims
open_questions
literature_evidence
current_belief
```

The Orchestrator constructs:

```text
evidence_state.analysis_claims = analysis_claims with status initialized to pending
evidence_state.open_questions = open_questions
evidence_state.literature_evidence = literature_evidence
evidence_state.execution_evidence = []
evidence_state.current_belief = current_belief
```

The new `mediator_formulation.md` prompt and schema must be active before this
construction is activated. If the Orchestrator receives only old TODO3 fields
such as `concrete_analysis_claim`, `open_risks`, or `verdict_rationale`, schema
validation should fail loudly with a prompt/schema mismatch error rather than
silently constructing ambiguous evidence state.

After each loop, the Orchestrator merges new evidence rather than asking any one
agent to own the entire accumulated state.

## Phase 1: Prompt and Schema Source of Truth

### Goal

Make `updated_prompts/` the source of truth for the new ScientistPanel workflow.

### Files

- `updated_prompts/panelist_shared_system.md`
- `updated_prompts/biologist_formulation.md`
- `updated_prompts/statistician_formulation.md`
- `updated_prompts/bioinformatician_formulation.md`
- `updated_prompts/mediator_formulation.md`
- `updated_prompts/panelist_callback.md`
- `updated_prompts/adversary.md`
- `updated_prompts/analyzer.md`
- `updated_prompts/mediator_post_analysis.md`
- `updated_prompts/scientist_panel_schemas.json`

### Changes

1. Add a prompt loader that can load `.md` prompt files by name.
2. Keep the existing Python prompt imports temporarily as compatibility wrappers.
3. Update prompt modules to read from `updated_prompts/` rather than duplicating
   large strings in Python.
4. Add schema loading and validation helpers for `scientist_panel_schemas.json`.
5. Normalize outputs against schemas after each LLM call.
6. Treat prompt/schema migration as an atomic cutover for fields that drive
   orchestration. Do not silently alias old field names into new contracts.

### Expected Result

The prompt text and schema contracts are no longer scattered across Python
strings. The new workflow can be edited in `updated_prompts/` and loaded by the
runtime.

## Phase 2: ScientistPanel Formulation Refactor

### Goal

Remove the separate Reconciler role and make the Mediator directly synthesize a
unified plan from the three panelist outputs.

### Current State

The current full formulation flow is roughly:

```text
panelists -> reconciler -> confidence adjustment -> mediator -> adversary
```

### Target Flow

```text
Biologist + Statistician + Bioinformatician in parallel
  -> Mediator formulation
  -> Adversary review
  -> Mediator revision or panelist callback loop if needed
  -> selected_research_plan
```

### Changes

1. Replace Reconciler-dependent mediator input with direct panelist outputs.
2. Remove the confidence-adjustment round as a required orchestration step.
3. Let the Mediator internally decide how to reconcile the panelist evidence.
   The Mediator does not need to expose `convergence`, `divergence`, or
   `absence` unless the schema asks for it.
4. Panelist formulation outputs should focus on:
   - clarified user question
   - literature intents and retrieved evidence
   - lane-specific synthesis
   - method adequacy
   - novelty candidates
   - downstream analyses
   - validation analyses
   - supplemental data
   - open questions
5. Mediator formulation output should produce:
   - analysis claims
   - falsification criterion
   - `selected_research_plan`
   - `novel_analysis_design`
   - `future_research_directions`
   - success criteria
   - limitations
   - alternative plans

### Selected Research Plan Definition

Use this wording:

```text
selected_research_plan:
  The strongest credible plan the research team believes can answer the user's
  request with the available data, literature, tools, and feasible custom
  implementation. It may use established methods, adapted methods, or a strong
  custom analysis if justified.
```

Novelty should be separated:

```text
novel_analysis_design:
  Extension that could add value beyond the requested answer. It executes only
  after the selected_research_plan succeeds or produces the necessary outputs.

future_research_directions:
  Promising ideas that are not executed now because they are not cost-justified,
  not feasible, require extra data, or are outside the user's immediate goal.
```

### Novel Analysis Execution

`novel_analysis_design` must not be included in the same ToolConsultant DAG as
the `selected_research_plan`.

Execution rule:

```text
selected_research_plan executes first.
If the active StateGraph node concludes successfully and novel_analysis_design
is defined, the orchestrator may create a child branch from the concluded node.
The child branch uses novel_analysis_design as the new selected_research_plan.
```

Interactive default:

```text
Ask the user before launching the novel_analysis_design branch.
```

StateGraph example:

```text
plan_001: selected_research_plan
  status: concluded

plan_002: novel_analysis_design
  parent_node_id: plan_001
  graph_action: create_child_node
  transition_reason: downstream_extension
  transition_note: novel_analysis_design_after_selected_plan_concluded
```

`transition_reason` is descriptive graph metadata, not an enum and not a control
surface. It should not decide behavior. The behavior is determined by the
orchestrator rule: when the selected plan concludes and the user accepts the
novel analysis, create a child node. `transition_note` carries the more specific
human-readable explanation.

## Phase 3: Literature Tool Contract

### Goal

Make literature calls explicit enough that PaperJudge can judge against the
actual reason the panelist needs the paper.

### Current Issue

The current tool contract distinguishes `retrieval_intent` and `retrieval_goal`,
but does not cleanly expose a separate search query in every prompt/schema path.

### Target Signature

```text
search_paper_wiki(
  retrieval_intent,
  retrieval_goal,
  search_query,
  requirements,
  background,
  top_k
)

retrieve_literature(
  retrieval_intent,
  retrieval_goal,
  search_query,
  requirements,
  background,
  retrieval_context_id,
  exclude_ids,
  top_k
)

fetch_paper_content(
  paper_id,
  content_need,
  section_type
)
```

### Semantics

- `retrieval_intent` means purpose: the specific question the panelist needs
  literature to answer.
- `retrieval_goal` means why the paper is needed in the reasoning loop:
  `method_selection`, `evidence_pattern`, `prior_findings`, `contradiction`,
  `validation`, `extension_opportunity`, or `broad_background`.
- `search_query` is the concrete query used to fetch candidate papers.
- `requirements` are constraints used for judging/reranking, not just search.
- `background` includes the user question, data summary, and why this intent
  matters.

### PaperJudge Output

PaperJudge should judge each paper against the `retrieval_intent`:

```text
intent_fit: direct | partial | weak | off_target
confidence: 0.0-1.0
useful_evidence_patterns: []
missing_information: []
reason: what is useful and what is not useful
```

Filtering rule:

```text
Return direct and partial papers to the panelist.
Filter away weak and off_target papers.
```

This replaces the TODO3 return threshold of `confidence >= 0.60`. Confidence is
still useful as a diagnostic, but return-to-panelist is now based on
`intent_fit`.

Persistence rule:

```text
persist_to_wiki:
  intent_fit in {direct, partial}
  confidence >= 0.75
  useful_evidence_patterns is not empty
```

Enforce this at the PaperJudge / panelist literature tool boundary, before papers
are returned to the panelist.

## Phase 4: Adversary Refactor

### Goal

Make the Adversary a research-plan reviewer, not a literature retriever or plan
rewriter.

### Inputs

Adversary receives:

- panelist evidence summaries
- cited paper summaries
- `evidence_state`
- Mediator research plan
- Mediator rationale

Do not use a separate `accepted_agreements` input. Anything already established
should be represented in `evidence_state.analysis_claims`,
`evidence_state.literature_evidence`, or `evidence_state.execution_evidence`.

### Outputs

Adversary emits:

```text
verdict: survives | needs_revision | unsalvageable
challenges: []
missing_analyses: []
open_questions_for_panelists: []
agreements: []
```

### Routing

- `survives`: accept research plan and move to ToolConsultant.
- `needs_revision`: back to Mediator. Mediator either self-revises or calls
  panelists narrowly.
- `unsalvageable`: Mediator declares unanswerable or restarts with a re-scoped
  question.

The Adversary should not retrieve new literature and should not rewrite the plan.

## Phase 5: StateGraph as Record and Context Source

### Goal

Upgrade StateGraph from mostly record storage plus generic `trajectory_context()`
to a record-and-context source with role-specific context builders.

### Current State

`StateGraphManager` currently stores:

- plan nodes
- alternative plan nodes
- tool plan refs
- implementation plan refs
- execution refs
- analyzer refs
- next decision refs
- active node and branches

It exposes:

```python
trajectory_context()
```

This is a useful MVP, but too generic.

### Target Methods

Add:

```python
context_for_mediator()
context_for_tool_consultant()
context_for_panelist_callback()
context_for_analyzer()
```

### Context for Mediator

Should include:

- active `selected_research_plan`
- evidence_state
- tried plans and outcomes
- untried alternatives
- latest Analyzer summaries
- Adversary critiques
- ToolPlanAlignment critiques
- reusable artifact summaries
- unresolved gaps

### Context for ToolConsultant

Should include:

- `selected_research_plan`
- success criteria
- required outputs
- constraints and limitations
- current input artifact paths
- previous failed tool plan summary if any
- ToolPlanAlignment critique if any
- reusable artifacts
- blocked dependencies or missing inputs

Must exclude:

- `novel_analysis_design` while the active node is still executing
  `selected_research_plan`

`novel_analysis_design` enters ToolConsultant context only after the selected
plan has concluded and the Orchestrator creates a child node where the novel
analysis becomes that node's `selected_research_plan`.

### Context for Panelist Callback

Should include:

- callback question
- role
- active `selected_research_plan`
- evidence_state
- relevant prior papers and evidence patterns
- what other panelists already established
- current unresolved gap
- instructions not to re-litigate resolved questions unless new evidence
  contradicts them

### Context for Analyzer

Should include:

- active `selected_research_plan`
- expected outputs
- artifact paths
- execution result summary
- success criteria
- evidence_state before execution

### StateGraph Node Shape

The graph is a compact data structure. Store small decision-relevant fields
directly on the node and store large records on disk with path references.

Example node:

```json
{
  "node_id": "plan_001",
  "status": "active",
  "selected_research_plan": {
    "plan_id": "plan_a",
    "steps": []
  },
  "evidence_state": {
    "analysis_claims": [],
    "open_questions": [],
    "literature_evidence": [],
    "execution_evidence": [],
    "current_belief": ""
  },
  "plan_path": "nodes/plan_001/research_plan.md",
  "plan_json_path": "nodes/plan_001/research_plan.json",
  "analyzer_report_path": "nodes/plan_001/analyzer_report.json",
  "execution_refs": ["executions/exec_001/dag_result.json"],
  "artifact_manifest_path": "executions/exec_001/artifact_manifest.json"
}
```

Large reports, execution outputs, figures, tables, and manifests should be saved
on disk and referenced by path. The StateGraph should stay readable and compact.

### Record vs Carry Forward

Persist everything important:

- prompt inputs
- LLM outputs
- papers
- plans
- tool plans
- code plans
- execution outputs
- analyzer reports
- mediator decisions
- critiques
- artifacts

Carry forward only compact decision-relevant state into the next agent call.
StateGraph should provide that compact state.

## Phase 6: ToolConsultant Coverage Reasoning

### Goal

Fix the core ToolConsultant issue: it must not produce a DAG just because some
tools are relevant. It must assign every research-plan requirement to tools,
custom code, or a blocking issue.

### Prompt Rule

ToolConsultant should internally reason through coverage before producing the
plan:

```text
For each research-plan requirement:
- Can existing tools correctly solve this requirement?
- Can existing tools partially solve it and produce reusable artifacts?
- Does the missing part require custom code?
- Is the requirement blocked by missing inputs, missing dependencies, or
  unavailable data?

Use tools for parts they truly solve.
Assign all missing/custom parts to CoderAgent.
Do not omit any research-plan requirement.
```

This coverage matrix can remain internal reasoning. It does not need to be a
formal output field.

### Output Contract

Keep existing output shape, but tighten semantics:

```text
dag_plan:
  only the tool-executable parts of selected_research_plan

implementation_plan:
  custom code responsibilities and exact machine-readable artifacts to save

blocking_questions:
  only if neither tools nor custom code can proceed without user/dependency/data
  clarification

preflight_checks:
  checks that must happen before expensive execution
```

Routing rule:

```text
If ToolConsultant returns non-empty blocking_questions, route to the user
immediately. Do not run ToolPlanAlignmentReviewer. ToolPlanAlignmentReviewer
runs only when ToolConsultant claims it has an executable plan.
```

No `execution_mode` enum is needed. The combination of `dag_plan` and
`implementation_plan` already implies tool-only, coder-only, or hybrid.

### CoderAgent Role

CoderAgent writes and runs code that saves outputs. It does not write the final
scientific interpretation.

The implementation plan should require saved artifacts such as:

- metrics tables
- diagnostic tables
- figures
- selected method manifests
- final h5ad paths
- artifact manifests
- logs

Analyzer reads these outputs and interprets them.

### Example Internal Assignment

For joint RNA+ATAC embedding:

Tools may handle:

- RNA QC
- ATAC QC
- barcode intersection
- RNA PCA
- ATAC LSI
- WNN embedding
- MultiVI only if prerequisites pass

Coder must handle if not tool-supported:

- paired audit before and after filtering
- leakage-safe CV macro-F1
- per-class F1
- method leaderboard
- WNN diagnostics
- FOSCTTM / recall@k
- deterministic selection rule
- final clustering on the selected representation if the tool chain cannot
  guarantee it
- saving all analyzer-readable outputs

## Phase 7: ToolPlanAlignmentReviewer

### Goal

Add a dedicated LLM reviewer for executable-plan alignment. This is separate
from the research Adversary.

### Why

The research plan can be valid while the ToolConsultant/DAG plan is wrong. This
should not be treated as a research-plan failure.

### Inputs

ToolPlanAlignmentReviewer receives:

- `selected_research_plan`
- ToolConsultant decision
- DAG plan
- implementation plan
- available tool metadata if needed
- data summary
- StateGraph `context_for_tool_consultant()`

### Review Questions

The reviewer checks:

- Does the executable plan satisfy every required analysis in the research plan?
- Are any research-plan requirements omitted?
- Are tools used for tasks they cannot actually solve?
- Are custom code responsibilities assigned for missing analyses?
- Are preflight checks sufficient?
- Are required outputs saved for Analyzer?
- Are final artifacts clearly named and machine-readable?
- Are dependencies and input prerequisites checked before expensive execution?
- Does the DAG risk producing misleading artifacts, such as clustering on the
  wrong embedding?

### Output

```text
verdict: survives | needs_tool_revision | blocked
target: tool_plan | implementation_plan | inputs_dependencies
core_critique: ""
required_revision: ""
missing_requirements: []
misused_tools: []
missing_custom_code: []
required_artifacts: []
questions_for_toolconsultant: []
```

### Routing

```text
survives:
  execute

needs_tool_revision:
  route back to ToolConsultant with critique

blocked:
  route by blocker_type
```

The ToolPlanAlignmentReviewer does not change the research plan. It only checks
whether the executable plan satisfies `selected_research_plan`. If a
plan requirement is unclear, it should report `blocked` or
`needs_tool_revision` with a concrete clarification request; the orchestrator may
then ask the user or send the issue to the Mediator, but the reviewer itself does
not own research-plan revision.

Use explicit blocker types:

```text
blocked:
  blocker_type:
    user_input_missing
    dependency_missing
    required_data_missing
    ambiguous_plan_requirement
  blocker_summary: ""
  required_resolution: ""
```

Routing:

```text
user_input_missing -> ask user
dependency_missing -> ask user / install flow
required_data_missing -> send blocker context to Mediator
ambiguous_plan_requirement -> send blocker context to Mediator
```

Sending blocker context to the Mediator does not mean the reviewer rewrites the
research plan. It means the Orchestrator gives the Mediator the blocker so the
Mediator can decide whether to revise the selected plan, ask panelists, ask the
user, or declare the question unanswerable with the current data.

### Budget

Use a small bounded loop:

```text
max_tool_plan_revision_rounds = 2
max_full_alignment_loops = 2
```

If still not `survives` after the budget:

- if target is tool/implementation: stop before execution and present the
  unresolved executable-plan mismatch
- if target is input/dependency: ask user

`max_full_alignment_loops` caps the full research-plan -> ToolConsultant ->
ToolPlanAlignmentReviewer cycle. If exhausted, do not execute; present the
unresolved issue.

## Phase 8: ResearchLoop Information Flow

### Goal

Wire the new contexts and reviewers into the main loop.

### Formulation Flow

```text
ScientistPanel.formulate()
  -> panelists
  -> Mediator formulation
  -> Adversary review/revision loop
  -> selected_research_plan
  -> StateGraph node
```

### Execution Planning Flow

```text
StateGraph.context_for_tool_consultant()
  -> ToolConsultant
      if blocking_questions -> ask user / stop before reviewer
  -> ToolPlanAlignmentReviewer
      survives -> execute
      needs_tool_revision -> ToolConsultant retry
      blocked -> route by blocker_type
```

### Execution and Analysis Flow

```text
DagExecutor / CoderAgent
  -> saved artifacts
  -> StateGraph records execution/artifact paths on the active node
  -> StateGraph.context_for_analyzer()
  -> Analyzer
  -> StateGraph records analyzer report path on the active node
```

### Post-Analysis Flow

```text
StateGraph.context_for_mediator()
  -> Mediator post-analysis decision
      accept_and_conclude
      call_panelists
      self_revise_plan
      ask_user
      declare_unanswerable
```

### Novel Analysis Branch Flow

```text
selected_research_plan node concludes successfully
  -> if novel_analysis_design exists, ask user whether to run it
  -> if accepted, create child StateGraph node from concluded node
  -> child node uses novel_analysis_design as selected_research_plan
  -> ToolConsultant planning starts from child node
```

### Panelist Callback Flow

```text
StateGraph.context_for_panelist_callback()
  -> panelist callback
  -> Mediator re-runs post-analysis decision
```

## Phase 9: Analyzer Evidence Contract

### Goal

Analyzer must attach exact evidence to every interpretation.

### Output Shape

```text
interpretation_loop:
  - interpreted_item
  - plan_step_id
  - source_artifact
  - metric_or_figure
  - observed_value
  - expectation
  - interpretation
  - supports_expectation: supported | contradicted | inconclusive | partially_supported
  - formulated_questions

overall_interpretation: ""
result_verdict: supported | contradicted | inconclusive | invalid | missing_outputs
claim_updates:
  - claim_id
  - status: supported | refuted | inconclusive | partially_supported
  - support_summary
  - contradicting_evidence
  - unresolved_requirements
missing_outputs: []
artifact_evidence_index: []
```

`claim_updates` replaces the old `hypothesis_status` field. Keep
`result_verdict` as the overall execution-level verdict; it is not replaced by
per-claim updates. ResearchLoop, StateGraph recording, and Mediator
post-analysis prompts should read `claim_updates`.

### Requirement

Analyzer should not make claims without pointing to an artifact, metric, or
figure. If no computational outputs exist, Analyzer should not run normal
literature grounding; the loop should route back through the Mediator or
ToolPlanAlignmentReviewer as appropriate.

## Phase 10: Post-Analysis Decision Schema

### Goal

Replace the current large post-analysis decision enum with the five-decision
workflow from `updated_prompts`.

### Decisions

```text
accept_and_conclude
call_panelists
self_revise_plan
ask_user
declare_unanswerable
```

### Important Distinction

`self_revise_plan` is for the Mediator to revise the research plan. It should
not be used for ordinary executable-plan mistakes. Those should be handled by
ToolPlanAlignmentReviewer before execution.

### Output

```text
decision
final_answer_summary
panelist_callbacks
plan_revision
updated_selected_research_plan
evidence_state
clarifying_questions
unanswerable_reason
what_would_be_needed
```

Use `updated_selected_research_plan` as the only field name for a revised plan in
the new schema. Do not introduce `next_research_plan` as a second name in the new
contract.

The cutover should be strict: update the post-analysis Mediator prompt and the
ResearchLoop/StateGraph readers together. If `decision == self_revise_plan` and
`updated_selected_research_plan` is missing, schema validation should fail before
any branch is created. Do not normalize `next_research_plan` into the new field.

### StateGraph Mapping

```text
accept_and_conclude:
  active node -> concluded
  no new node

call_panelists:
  no graph mutation until callback completes and Mediator re-issues a decision
  bounded by max_callback_rounds_after_analysis = 2

self_revise_plan:
  active node -> superseded
  create new branch node from active node
  new node becomes active

ask_user:
  active node -> awaiting_user
  no new node

declare_unanswerable:
  active node -> unanswerable
  no new node
```

## Phase 11: Tests

Add tests for each behavior before or during implementation.

### ScientistPanel

- Formulation no longer requires a Reconciler output.
- Mediator receives all three panelist outputs directly.
- Adversary receives panelist evidence summaries, cited papers, and research
  plan.
- `needs_revision` routes back to Mediator.
- Adversary `needs_revision` can trigger a Mediator panelist callback decision
  for the assigned gap.

### Literature

- `retrieve_literature` accepts `search_query`.
- PaperJudge filters away `weak` and `off_target`.
- Direct and partial papers are returned.
- Duplicate papers are not returned to the same panelist loop.

### StateGraph

- `context_for_mediator()` includes the active `selected_research_plan`,
  evidence state, tried plans, and critiques.
- `context_for_tool_consultant()` includes `selected_research_plan`, previous
  tool failures, artifact summaries, and missing requirements.
- `context_for_tool_consultant()` excludes deferred `novel_analysis_design`
  unless it has become the active node's `selected_research_plan`.
- `context_for_panelist_callback()` includes only the assigned gap and relevant
  prior state.
- `context_for_analyzer()` includes expected outputs and artifact paths.
- new node initializes `evidence_state.analysis_claims[*].status` to `pending`.
- Orchestrator constructs initial `evidence_state` from Mediator formulation
  outputs and merges later evidence updates.
- every plan step has `addresses_claims` as a list, used for Analyzer/Mediator
  interpretation.
- missing `addresses_claims` is interpreted as `claim_linkage:
  best_effort_unmapped`.
- novel analysis creates a child branch from the concluded selected-plan node.
- five post-analysis decisions map to deterministic node status/branch changes.
- post-analysis `call_panelists` is bounded by
  `max_callback_rounds_after_analysis = 2`.

### ToolConsultant

- If a research-plan requirement lacks tool support, the implementation plan
  must assign it to CoderAgent.
- A DAG-only plan is invalid when custom analyses are required.
- CoderAgent outputs must be machine-readable artifacts, not final scientific
  prose.

### ToolPlanAlignmentReviewer

- Surviving plan proceeds to execution.
- Tool mismatch routes back to ToolConsultant.
- Reviewer does not revise or invalidate the research plan.
- `blocked` routes by blocker type: user/dependency blockers go to the user or
  install flow; required-data and ambiguous-plan blockers go to Mediator with
  blocker context.
- Revision loop is bounded.

### Analyzer

- Every interpretation references a source artifact, metric, or figure.
- `result_verdict` is retained as the overall execution verdict.
- `claim_updates` replaces `hypothesis_status` for per-claim interpretation.
- Missing outputs are explicitly listed.
- Blocked execution does not trigger normal result interpretation.

## Implementation Order

Recommended order:

1. Add prompt/schema loader for `updated_prompts`.
2. Add literature tool `search_query` and PaperJudge filtering changes.
3. Refactor ScientistPanel formulation to use new panelist/Mediator/Adversary
   schemas.
4. Add StateGraph role-specific context builders.
5. Update ToolConsultant prompt to require internal coverage reasoning and
   coder assignment for missing parts.
6. Add ToolPlanAlignmentReviewer and wire it into ResearchLoop before execution.
7. Update Analyzer output schema and artifact evidence indexing.
8. Update post-analysis Mediator decision schema.
9. Add/adjust tests throughout.
10. Run a full frontend test on the paired PBMC RNA/ATAC workflow using:
    - RNA: `/Users/vickydong/Documents/singlecell_Agent/data/pbmc_RNA_count.h5ad`
    - ATAC: `/Users/vickydong/Documents/singlecell_Agent/data/pbmc_ATAC_count.h5ad`
    Verify that
    tool-plan mismatch routes back to ToolConsultant instead of producing an
    empty Analyzer result.

## Non-Goals for This Update

- Do not make CoderAgent write the final scientific answer.
- Do not force novelty into the first execution when the selected research plan
  is enough.
- Do not expose internal coverage matrices unless useful for debugging.
- Do not let Adversary retrieve new literature.
- Do not let ToolConsultant silently omit research-plan requirements.
