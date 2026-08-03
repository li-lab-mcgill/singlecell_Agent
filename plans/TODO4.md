# TODO4 — MediatorAgent and Research-Loop Architecture Cleanup

## Rationale

The current implementation keeps Mediator behavior inside `ScientistPanel`.
That was acceptable when the Mediator was only a synthesis step, but it no
longer matches the intended design. The Mediator is the research lead / PI
across the full trajectory:

- before execution, it decides whether panelist evidence is sufficient to form
  a selected research plan;
- during formulation, it requests targeted panelist callbacks when evidence is
  incomplete;
- after execution, it reads Analyzer evidence, may call targeted panelist
  callback tools internally, and decides whether to conclude, revise, ask the
  user, or continue with the same research direction.

The outer `ResearchLoop` remains the true orchestrator. It owns the global
state graph, session storage, execution phases, ToolConsultant, DagExecutor /
Coder, AnalyzerPanel, and phase transitions. The formulation loop is only a
smaller pre-execution / revision sub-loop inside the outer orchestration.

At the top level, routing has two distinct stages:

```text
New user message
-> SessionRouter
-> ResearchWorkspace
-> active or new ResearchState
-> ResearchLoop
```

`SessionRouter` decides high-level intent: direct response, operational
execution, discovery/research, or ambiguity that requires user clarification.
`ResearchWorkspace` decides which task-scoped `ResearchState` should receive
the request.

## Target Ownership Model

### ResearchLoop / Orchestrator

Owns global lifecycle and state:

- `ScientistPanel`
- `MediatorAgent`
- `AdversarialPanelist` directly or through formulation loop wiring
- `ToolConsultantAgent`
- `ToolPlanAlignmentReviewer`
- `DagExecutor` / `CoderAgent`
- `AnalyzerPanel`
- `ResearchWorkspace`
- active task-scoped `ResearchState`
- `SessionRecorder`
- phase transitions and persistence

It owns the formulation loop before execution and calls
`MediatorAgent.post_analysis(...)` after Analyzer output.

### ScientistPanel

Becomes a specialist-panel runner only. It should own:

- initial panelist runs;
- targeted panelist callback runs;

It should not own Mediator logic, adversarial review wiring, or trajectory
commit decisions. It owns the same three panelist roles for both broad initial
formulation and narrow callback mode:

```text
BiologistPanelist
StatisticianPanelist
BioinformaticianPanelist
```

Only the initial formulation runs all three panelists broadly. Later targeted
callbacks run only the requested role and answer only the assigned gap.

### MediatorAgent

Owns research-lead reasoning across timelines:

- formulation readiness;
- targeted callback requests;
- final selected research plan synthesis;
- callback synthesis;
- post-analysis trajectory decision;
- targeted post-analysis panelist tool use;
- evidence-state update logic.

The Mediator uses `updated_prompts/mediator_shared_system.md` as its stable
system prompt and mode-specific prompts for formulation and post-analysis.

### AnalyzerPanel

Stays outside the formulation loop. It interprets produced execution evidence
and emits claim updates, missing outputs, artifact evidence, and result
verdicts. Its output can trigger a revision loop, but Analyzer is not part of
that loop.

## ResearchState and Context Views

### Single Source of Truth

Introduce `ResearchState` as the single authoritative research memory for one
coherent research task. `ResearchState` is task-scoped, not conversation-scoped.
A single conversation can contain multiple `ResearchState` objects.

Do not maintain independent state objects named `research_context`,
`mediator_formulation_context`, `mediator_adversary_revision_context`,
`mediator_post_analysis_context`, `panelist_context`, `adversary_context`,
`tool_context`, and `analyzer_context` as separate mutable sources of truth.
Those names should become filtered read-only views derived from `ResearchState`.

Recommended shape:

```yaml
ResearchState:
  task:
    research_state_id:
    conversation_id:
    parent_research_state_id:
    user_task:
    data_summary:
    mode:
    created_at:
    updated_at:
    storage_root:

  active_node_id:

  active_research_state:
    node_id:
    selected_research_plan:
    alternative_research_plans:
    evidence_state:
      analysis_claims:
      open_questions:
      literature_evidence:
      execution_evidence:
      current_belief:
    assumptions:
    limitations:
    formulation_status:
    evidence_completeness:
    callback_budget_exhausted:
    adversary_review:
    research_gap_resolution:

  trajectory:
    nodes:
    edges:
    recommended_continue_from:

  working_memory:
    panelist_outputs:
    callback_history:
    mediator_outputs:
    adversary_outputs:
    analyzer_reports:
    tool_decisions:

  artifact_index:
    artifacts:
```

`selected_research_plan` is the canonical research-plan body used everywhere
after Mediator synthesis. Keep the existing detailed plan schema; do not
replace it with a simplified competing shape. The orchestration fields
(`formulation_status`, `callback_requests`, `trajectory_decision`, etc.) wrap
this plan, but are not part of the plan body itself.

Canonical `selected_research_plan` shape:

```yaml
selected_research_plan:
  hypothesis:
  background:
  plan:
    main_method:
    downstream_analyses:
  supplemental_data:
  validation_metrics:
  novel_analysis_design:
  success_criteria:
  limitations:
  future_research_directions:
  alternative_plans:
  open_questions:
  literature_evidence:
  current_belief:
  overall_confidence:
```

`evidence_state` remains the scientific evidence ledger inside
`ResearchState`; it should not absorb plans, callbacks, adversary critiques, or
execution bookkeeping.

### ResearchWorkspace

`ResearchWorkspace` is the conversation-level container that owns the registry
of task-scoped research states and tracks which one is active. It prevents
unrelated tasks in the same conversation from being merged into one long,
ambiguous state.

```yaml
ResearchWorkspace:
  conversation_id:
  active_research_state_id:
  research_state_registry:
    - research_state_id:
      user_task:
      status:
      created_at:
      updated_at:
      data_fingerprint:
      short_summary:
      storage_root:
      related_research_state_ids:
```

`data_fingerprint` is a stable, lightweight dataset identity summary used for
task-state routing. It should not require hashing full h5ad files. It should be
computed when a `ResearchState` is created or when input data changes.

Recommended fields:

```yaml
data_fingerprint:
  input_paths:
  file_sizes:
  modified_times:
  modality_summary:
  n_obs:
  n_vars:
  obs_columns:
  var_name_hash:
```

For each new user message, `ResearchWorkspace` decides whether to:

```text
continue active ResearchState
create new ResearchState
switch to previous ResearchState
ask user which research task they mean
```

Examples:

```text
"Validate that with another metric"
  -> continue active ResearchState S001

"Now annotate cell types"
  -> create new ResearchState S002

"Go back to the MultiVelo result"
  -> switch active ResearchState back to S001
```

Only the active `ResearchState` is loaded into agent contexts by default.
Related prior states may be summarized or linked when the user explicitly asks
to resume, compare, or build on a prior task.

### StateGraph Semantics

The StateGraph is a research trajectory graph, not the executable DAG.

```text
StateGraph node = research state / plan logic
StateGraph iteration = one execution + Analyzer attempt under that research state
DagExecutor DAG = concrete computational steps inside an iteration
Artifact index = reusable files/results produced by iterations
```

A research-state node represents the logic of the research direction:

- what claim or objective is being tested;
- what evidence pattern is required;
- what analysis plan is intended;
- what assumptions and limitations apply;
- what alternatives were considered or rejected.

Each node can have multiple iterations:

```yaml
nodes:
  plan_001:
    node_type: research_state
    status: active | candidate | superseded | concluded | unanswerable | awaiting_user | invalid
    selected_research_plan_ref:
    evidence_state_ref:
    branch_from_node_id:
    branch_reason:
    iterations:
      - iteration_id:
        status:
        tool_plan_ref:
        execution_ref:
        analyzer_report_ref:
        decision_ref:
        produced_artifacts:
        reusable_artifacts:
        failed_steps:
        missing_outputs:
        parameters_used:
```

Transition rules:

```text
self_revise_plan:
  research logic changed
  create a new/revised research-state node
  branch from the closest prior node in research logic
  may reuse artifacts from prior nodes if logically valid

continue_with_same_research_plan:
  research logic unchanged
  keep the same active research-state node
  append a new iteration under that node
  reuse prior artifacts when compatible
```

This is the mechanism that prevents the system from starting from scratch after
every failed or partial run.

### Persistence Boundary

The target state path is:

```text
ResearchLoop -> ResearchWorkspace -> active ResearchState -> internal graph persistence
```

`ResearchLoop` should not maintain a separate `StateGraphManager` handle beside
`ResearchState`. `ResearchState` owns the runtime trajectory view and delegates
durable graph reads/writes to an internal persistence helper. The existing
`StateGraphManager` can be reused during migration, but only behind
`ResearchState`; it should not be called directly by `ResearchLoop` in the
target design.

Protocol:

```text
ResearchState is the runtime source of truth for one task.
ResearchState persists/loads its trajectory through internal graph persistence.
ResearchWorkspace persists the registry of task-scoped ResearchStates.
SessionRecorder persists traces, prompts, raw agent outputs, reports, and files.
```

On task start:

```text
ResearchWorkspace creates or loads the active ResearchState.
ResearchState initializes task metadata, empty working memory, artifact index,
and an empty or hydrated trajectory.
```

On trajectory mutation:

```text
ResearchLoop calls ResearchState.create_node(...)
ResearchLoop calls ResearchState.append_iteration(...)
ResearchLoop calls ResearchState.mark_concluded(...)
ResearchState updates its in-memory trajectory and persists the graph
internally.
```

This avoids two writable copies of the trajectory.

### Context Views

Agent contexts are filtered prompt packets built from `ResearchState`. They can
be saved as trace/debug snapshots, but they are not authoritative state. The
context builders should live on `ResearchState` or a dedicated
`ResearchStateContextBuilder`, not on `StateGraphManager`.

```python
formulation_context = research_state.context_for_mediator_formulation()
adversary_revision_context = research_state.context_for_mediator_adversary_revision(
    adversary_critique=adversary_critique,
    adversary_revision_round=adversary_revision_round,
    max_adversary_revision_rounds=max_adversary_revision_rounds,
)
post_analysis_context = research_state.context_for_mediator_post_analysis(
    analyzer_report=analyzer_report,
    dag_result_summary=dag_result_summary,
    tool_decision=tool_decision,
    artifact_registry_summary=artifact_registry_summary,
)
panelist_context = research_state.context_for_panelist(role, callback)
adversary_context = research_state.context_for_adversary(
    candidate_plan=mediator_output["selected_research_plan"],
    candidate_trajectory_decision=mediator_output["trajectory_decision"],
)
tool_context = research_state.context_for_tool_consultant()
analyzer_context = research_state.context_for_analyzer(execution_event)
```

Minimum view meanings:

- `research_context`: legacy name for accepted research-plan state. Do not
  preserve it as a new interface. Replace current call sites with
  `ResearchState.active_research_state` or a role-specific context view.
- Mediator contexts are mode-specific decision-ready views derived from
  `ResearchState`. The Mediator should not receive a generic `current_event`
  packet because formulation, adversary revision, and post-analysis have
  different prompts and different required inputs.
- `mediator_formulation_context`: pre-execution view containing user question,
  data summary, panelist outputs, callback history, prior Mediator outputs, and
  current evidence state.
- `mediator_adversary_revision_context`: plan-critique view containing the
  active selected research plan, evidence state, panelist evidence summaries,
  cited papers, adversary critique, adversary revision budget state, prior
  Mediator outputs, callback history, trajectory summary, and alternatives
  considered. The revision-round counters are runtime orchestration state
  supplied by `ResearchLoop`; they are not committed fields in `ResearchState`.
- `mediator_post_analysis_context`: post-execution view containing user
  question, data summary, active selected research plan, evidence state,
  Analyzer report, DAG/execution result summary, ToolConsultant decision,
  artifact registry summary, trajectory summary, prior Mediator outputs, and
  callback history.
- `panelist_context`: role-scoped view for one panelist and one assigned gap.
  It includes the assigned question, that role's prior reasoning, compact
  cross-panel state, mediated state, literature evidence, and relevant critique.
- `adversary_context`: review packet built from committed `ResearchState`
  context plus explicit uncommitted candidate fields. It contains the candidate
  plan under review, committed evidence_state, panelist evidence summaries,
  cited papers, limitations, research_gap_resolution, inherited candidate
  `trajectory_decision`, and prior critiques. The candidate plan is not read
  from committed ResearchState because it has not passed adversarial review yet.
  The AdversarialPanelist critiques the research decision and evidence pattern;
  it receives trajectory as context but does not judge or choose the trajectory
  action.
- `tool_context`: executable-planning view containing the selected plan,
  current iteration target, reusable artifacts, missing outputs, failed steps,
  recommended continue-from checkpoint, and any `rerun_intent` for the current
  iteration.
- `analyzer_context`: interpretation view containing the active plan, execution
  result, expected outputs, claim IDs, artifacts, and evidence requirements.

Trajectory mutations should be methods on `ResearchState` in the target
interface:

```python
research_state.create_node(...)
research_state.append_iteration(...)
research_state.branch(...)
research_state.mark_concluded(...)
```

If the existing `StateGraphManager` remains during migration, it should be an
internal implementation detail of `ResearchState`. It should not own
prompt-context construction in the target design.

### Artifact Path Access

Paths in context are references, not instructions for every agent to read all
files.

- Mediator, Panelists, and Adversary should usually receive summaries,
  artifact IDs, semantic types, limitations, and evidence links. They should
  not read arbitrary execution files by default.
- Panelists can fetch literature content, not arbitrary local artifacts.
- ToolConsultant can receive artifact IDs, semantic types, and paths to plan
  which DAG/code step should consume them, but it does not need to read all
  file contents.
- DagExecutor and CoderAgent must receive concrete paths because they execute
  code and need to load/reuse artifacts.
- AnalyzerPanel may inspect artifact contents through controlled artifact
  readers/previews, because its role is to interpret produced outputs.

Prefer controlled artifact tools over generic unrestricted file reads:

```text
fetch_artifact_summary(artifact_id)
fetch_artifact_table_head(artifact_id, n=20)
fetch_artifact_metadata(artifact_id)
fetch_artifact_figure_preview(artifact_id)
```

Example artifact record:

```yaml
artifact_id:
path:
semantic_type:
produced_by:
  node_id:
  iteration_id:
  step_id:
summary:
preview:
reusable:
limitations:
```

## Structured LLM Output Parsing

Every structured LLM output that controls program behavior must have a simple,
strict parser/validator. This applies to:

- SessionRouter output;
- Panelist formulation output;
- Panelist callback output;
- Mediator formulation output;
- Mediator post-analysis output;
- Adversary review output;
- ToolConsultant decision output;
- ToolPlanAlignmentReviewer output;
- Analyzer output;
- PaperJudge output;
- paper digest / summary output.

The parser should be mechanical, not semantically clever:

```text
1. Extract JSON from the expected XML-style tag.
2. Parse JSON.
3. Validate against the required schema.
4. Validate enum values.
5. Fill safe defaults only for optional fields.
6. Normalize only explicitly allowed aliases.
7. If invalid, retry the same LLM once with:
   - invalid output
   - validation error
   - required schema
   - repair instruction
8. If still invalid, return schema_error and let the caller/orchestrator decide.
```

The parser must not silently change the meaning of critical decisions. In
particular, an unknown post-analysis decision must never default to
`accept_and_conclude`.

Bad behavior to remove:

```text
unknown decision -> accept_and_conclude
```

Correct behavior:

```text
unknown decision -> schema_error -> repair prompt -> valid decision or explicit failure
```

The repair prompt fixes schema, not reasoning:

```text
Your previous output did not match the required schema.
Validation error:
...
Required schema:
...
Previous output:
...
Return only corrected JSON wrapped in <TAG>...</TAG>.
Do not add prose.
Preserve the substantive decision as closely as possible while satisfying the schema.
```

Recommended shared result shape:

```python
ParsedLLMOutput:
  ok: bool
  data: dict
  schema_error: str | None
  raw_text: str | None
```

The current functions named `_normalize_*` should be refactored into explicit
parsers/validators owned by the agent whose output they parse. Shared tag /
JSON / schema helpers may live in a small common module, but each agent owns the
schema for its own output.

Recommended parser ownership:

```text
Mediator parsers -> agents/mediator_agent.py
Panelist parsers -> agents/scientist_panel.py or a future panelist_agent.py
Adversary parser -> agents/adversarial_panelist.py
Analyzer parser -> agents/analyzer_panel.py
ToolConsultant parser -> agents/tool_consultant.py
PaperJudge / paper digest parsers -> literature retrieval module
Shared mechanical helpers -> agents/structured_output.py
```

## Target Flow

### Initial Formulation Mode

Input:

- user question;
- data summary;
- initial panelist outputs.

Loop:

1. Panelists run once in parallel.
2. Mediator reads all panelist outputs.
3. If evidence is insufficient, Mediator asks targeted panelist callbacks.
4. Only requested panelists answer only the assigned gaps.
5. Mediator reads callback history and checks readiness again.
6. Repeat up to callback budget.
7. When clear, Mediator emits a selected research plan ready for adversarial
   review.
8. If callback budget exhausts, Mediator emits the strongest defensible plan
   with explicit limitations, `evidence_completeness: partial`, and
   `callback_budget_exhausted: true`.

Output:

- `selected_research_plan` ready for adversarial review;
- candidate `trajectory_decision` with `action: initialize_plan`.

No user-question branch is allowed inside this loop. If the user's request is
ambiguous, `SessionRouter` / outer orchestrator should have asked the user
before entering the research loop.

### Post-Analysis Revision Mode

Input:

- active plan;
- Analyzer report;
- evidence_state;
- specific gaps, failed requirements, contradictions, or missing outputs.

Loop:

1. Mediator reads Analyzer output and current evidence_state.
2. If targeted specialist input is needed, Mediator calls internal panelist
   callback tools. Tool results return to the same `post_analysis(...)` run.
3. Mediator decides whether the current plan answered the user, needs direct
   revision, can continue with the same research plan, should ask the user, or
   is unanswerable.
4. Revised plans go to adversarial review before re-execution.

Output:

- revised or confirmed `selected_research_plan` ready for adversarial review,
  or a conclusion / unanswerable decision.

`call_panelists` is not a final post-analysis decision. Targeted panelist
callbacks are internal Mediator tool calls inside `post_analysis(...)`.

Post-analysis may ask the user only through the explicit `ask_user` decision.
This should be rare: user ambiguity should usually be handled by `SessionRouter`
/ outer orchestration before the research loop begins. Keep `ask_user` for
cases where execution or result inspection reveals that the next scientific
step depends on information only the user can provide.

### Adversary-Driven Revision Loop

The adversary-driven revision loop is separate from the pre-adversary callback
loop. It critiques an already-synthesized plan.

Budget:

```text
max_adversary_revision_rounds = 2
max_callback_rounds_after_analysis = 2
```

`max_callback_rounds_after_analysis` limits targeted panelist callback fallback
rounds after Analyzer output or post-analysis adversary revision. It is
separate from the adversary revision budget.

When the Adversary returns `needs_revision`, `ResearchLoop` should call
`MediatorAgent.revise_from_adversary(...)` with
`ResearchState.context_for_mediator_adversary_revision(...)`. The Mediator
returns a revised candidate plan plus a proposed `trajectory_decision`.

The AdversarialPanelist critiques the research decision: whether the plan
answers the user question, whether the evidence pattern is strong enough, what
assumptions are hidden, and what revisions are needed. It inherits the
Mediator's proposed `trajectory_decision` as context so critiques remain
traceable, but it does not decide, approve, or reject the trajectory action.
The Mediator owns the proposed trajectory decision; `ResearchLoop` commits it
deterministically after the research plan survives review.

Adversary verdict handling:

```text
survives:
  accept the candidate research plan
  commit the inherited trajectory_decision through ResearchState

needs_revision:
  send the critique to MediatorAgent.revise_from_adversary(...)
  continue the adversary-driven revision loop until survives or budget exhausts

unsalvageable:
  do not commit trajectory_decision
  during pre-execution formulation, Mediator must either:
    - receive the critique through MediatorAgent.revise_from_adversary(...)
    - reformulate a fundamentally different selected_research_plan
    - declare_unanswerable if no defensible plan exists
  during post-analysis revision, Mediator must either:
    - receive the critique through MediatorAgent.post_analysis(...)
    - reformulate a fundamentally different selected_research_plan
    - ask_user if the issue depends on missing user intent/data
    - declare_unanswerable if no defensible plan exists
```

```text
initial accepted plan:
  trajectory_decision.action = initialize_plan
  create the first research-state node after adversarial acceptance

research logic changed:
  trajectory_decision.action = create_revised_node
  create a revised research-state node after adversarial acceptance

research logic unchanged:
  trajectory_decision.action = continue_same_node
  append a new iteration after adversarial acceptance

fatal unfixable flaw:
  trajectory_decision.action = declare_unanswerable
  mark unanswerable after adversarial acceptance or final rejection
```

If the adversary revision budget is exhausted after repeated `needs_revision`
verdicts, the Mediator makes one final revision using the latest critique. That
final revised plan is committed and sent to ToolConsultant. The final plan must
explicitly record unresolved critiques as limitations in
`research_gap_resolution`; the system must not call
`revise_from_adversary(...)` again for the same plan.

Budget exhaustion on `unsalvageable` follows the `unsalvageable` rule, not the
`needs_revision` rule. If the last allowed adversary round returns
`unsalvageable`, do not commit `trajectory_decision`; the Mediator must
reformulate, ask the user only if this is post-analysis, or declare
unanswerable.

Post-analysis `unsalvageable` is routed through `MediatorAgent.post_analysis(...)`,
not `MediatorAgent.revise_from_adversary(...)`, because post-analysis is the
only Mediator mode allowed to emit `ask_user`. `revise_from_adversary(...)`
remains the narrow no-user candidate-repair loop for `needs_revision` critiques
and pre-execution unsalvageable reformulation.

No graph mutation is committed during adversary review itself. Candidate plans
are reviewed first; `ResearchLoop` commits the inherited trajectory action
through `ResearchState` only after the plan survives the adversary loop.

If `revise_from_adversary(...)` needs targeted panelist input, it should use
the same internal Mediator tools as `post_analysis(...)` whenever possible. If
the implementation cannot support tool calls in this mode yet,
`needs_panelist_callback` is an allowed fallback: `ResearchLoop` /
`ScientistPanel` runs only the requested targeted callbacks and then calls
`MediatorAgent.revise_from_adversary(...)` again with updated context. This
does not increment the adversary revision round counter. It counts against the
callback budget for the current stage:

```text
before first execution -> formulation callback budget
after Analyzer output -> max_callback_rounds_after_analysis
```

In post-analysis and adversary-revision modes, targeted panelist callbacks
should normally happen as internal Mediator tool calls. The outer fallback path
exists only to support staged migration if `revise_from_adversary(...)` is not
yet implemented with tools.

Boundary note: `AdversarialPanelist` primarily critiques the research plan and
evidence pattern. Tool/execution coverage should normally be handled by
`ToolPlanAlignmentReviewer`, Analyzer feedback, and ToolConsultant. If an
adversary critique is really about an already-required output not being
produced, or a parameter/rerun detail within the same plan, the Mediator should
route it as `continue_with_same_research_plan` rather than creating a new
research-state node.

## Implementation Tasks

### 1. Add `ResearchWorkspace`

Create:

```text
agents/research_workspace.py
```

`ResearchWorkspace` owns the registry of task-scoped `ResearchState` objects
for one conversation and tracks `active_research_state_id`.

For each routed task from `SessionRouter`, it should:

```text
load the ResearchStateRegistry from storage
if SessionRouter intent_mode == ambiguous:
  do not start ResearchWorkspace routing; return the router clarification
if the message clearly continues the active ResearchState:
  return that ResearchState
if the message clearly starts a new task:
  create a new ResearchState
if the message references a prior task:
  switch active_research_state_id to that ResearchState
if task-state routing is ambiguous:
  ask user which research task they mean, with candidate states as options
```

`ResearchWorkspace` matching can use:

- active state status;
- `user_task` summary;
- `data_fingerprint`;
- recency;
- explicit references in the user message;
- optional LLM-assisted matching for references such as "go back to the
  MultiVelo result".

Wire `ResearchWorkspace` into `SessionDispatcher` between `SessionRouter` and
`ResearchLoop`:

```text
SessionRouter
-> direct_response: respond directly
-> task + ambiguous: ask user at router layer
-> task + operational/discovery: ResearchWorkspace selects active/new/previous ResearchState
-> ResearchLoop runs on selected ResearchState
```

### 2. Add `MediatorAgent`

Create:

```text
agents/mediator_agent.py
```

Public methods:

```python
class MediatorAgent:
    def formulate(
        self,
        *,
        formulation_context,
    ) -> dict:
        ...

    def revise_from_adversary(
        self,
        *,
        adversary_revision_context,
    ) -> dict:
        ...

    def synthesize_callbacks(
        self,
        *,
        formulation_context,
        callback_outputs,
        round_number=1,
    ) -> dict:
        ...

    def post_analysis(
        self,
        *,
        post_analysis_context,
    ) -> dict:
        ...
```

`post_analysis(...)` should run through a tool-calling runner with two internal
tools for targeted panelist callbacks:

```text
ask_panelist_for_more_reasoning
ask_panelist_for_more_literature
```

The tools call the same three panelist roles owned by `ScientistPanel`, but in
callback mode rather than broad initial formulation mode.

`MediatorAgent` should receive the panelist callback executor by dependency
injection rather than owning `ScientistPanel` directly:

```python
MediatorAgent(
    ...,
    panelist_callback_executor: Callable[[str, dict], dict],
)
```

`ResearchLoop` wires this executor when constructing or configuring the
Mediator:

```python
mediator = MediatorAgent(
    ...,
    panelist_callback_executor=scientist_panel.run_panelist_callback,
)
```

The executor contract is:

```python
panelist_callback_executor(role: str, callback_input: dict) -> dict
```

The `role` is one of `biologist`, `statistician`, or `bioinformatician`. The
callback input follows the tool input shapes below.

Tool input shapes:

```yaml
ask_panelist_for_more_reasoning:
  role: biologist | statistician | bioinformatician
  assigned_gap:
  context:
  expected_output:

ask_panelist_for_more_literature:
  role: biologist | statistician | bioinformatician
  retrieval_intent:
  retrieval_goal:
  requirements:
  background:
  assigned_gap:
```

The tool results return to the same `post_analysis(...)` run. The final
`post_analysis(...)` output must be one of the terminal post-analysis decisions
listed in Task 10; it must not be `call_panelists`.

`MediatorAgent` should load:

```text
updated_prompts/mediator_shared_system.md
updated_prompts/mediator_formulation.md
updated_prompts/mediator_adversary_revision.md
updated_prompts/mediator_post_analysis.md
```

Use `mediator_shared_system.md` as the actual system prompt.

### AdversarialPanelist API Update

Update `AdversarialPanelist.run(...)` to use a single context object:

```python
adversary.run(
    *,
    adversary_context: dict,
) -> dict
```

Both the initial formulation path and the post-analysis `self_revise_plan` path
should call this same API. Do not keep separate adversary signatures for the
two timelines.

Minimum `adversary_context` shape:

```yaml
user_question:
candidate_plan:
evidence_state:
panelist_evidence_summary:
cited_papers:
research_gap_resolution:
limitations:
candidate_trajectory_decision:  # inherited context only; adversary does not approve/reject it
prior_critiques:
```

Build this review packet with:

```python
adversary_context = research_state.context_for_adversary(
    candidate_plan=mediator_output["selected_research_plan"],
    candidate_trajectory_decision=mediator_output["trajectory_decision"],
)
```

The adversary prompt must explain that `candidate_trajectory_decision` is
inherited context. The adversary critiques the research decision, evidence
pattern, assumptions, and plan validity; it must not approve, reject, or choose
the trajectory action.

The AdversarialPanelist must not consume or emit `formulation_status`.
`formulation_status` belongs only to Mediator formulation/revision methods. The
adversary returns its own verdict schema:

```yaml
adversary_verdict: survives | needs_revision | unsalvageable
critique_summary:
failure_modes:
required_revisions:
nonfatal_limitations:
fatal_flaws:
```

`formulation_context`, `adversary_revision_context`, and
`post_analysis_context` are filtered decision contexts generated from
`ResearchState`. They are different context schemas because the Mediator is
acting at different points in the research timeline.

Minimum `formulation_context` shape:

```yaml
user_task:
data_summary:
panelist_outputs:
callback_history:
previous_mediator_outputs:
evidence_state:
trajectory_summary:
```

Minimum `adversary_revision_context` shape:

```yaml
user_task:
data_summary:
candidate_plan:
candidate_trajectory_decision:
active_plan:
  node_id:
  selected_research_plan:
  assumptions:
  limitations:
  evidence_requirements:
evidence_state:
panelist_evidence_summary:
cited_papers:
adversary_critique:
  verdict:
  critique_summary:
  failure_modes:
  required_revisions:
  nonfatal_limitations:
  fatal_flaws:
prior_mediator_outputs:
callback_history:
adversary_revision_round:
max_adversary_revision_rounds:
trajectory_summary:
alternative_research_plans:
```

`mediator_adversary_revision.md` must be a separate mode-specific prompt. It
should begin by stating:

```text
You will be provided with:
- the user's original question
- the dataset summary
- the current committed research state
- the uncommitted candidate research plan under adversarial review
- the candidate trajectory decision proposed by the Mediator
- the adversary critique
- the adversary verdict: needs_revision or unsalvageable
- prior panelist evidence summaries
- cited literature evidence
- current evidence_state
- prior Mediator outputs
- prior adversary critiques
- callback history
- adversary_revision_round
- max_adversary_revision_rounds
```

The prompt must instruct the Mediator to revise the uncommitted candidate plan
in response to the adversary critique, not to restart from scratch unless the
critique makes the candidate unsalvageable. It must not ask the user in this
mode. If specialist reasoning is needed, return
`formulation_status: needs_panelist_callback`. If the plan is ready for another
adversarial review, return `formulation_status: ready_for_adversary`. If the
critique makes the plan impossible to defend, return
`formulation_status: ready_for_adversary` with
`trajectory_decision.action: declare_unanswerable`.

Minimum `post_analysis_context` shape:

```yaml
user_task:
data_summary:
phase_number:
active_plan:
evidence_state:
analyzer_report:
dag_result_summary:
tool_decision:
artifact_registry_summary:
trajectory_summary:
previous_mediator_outputs:
callback_history:
unresolved_gaps:
research_gap_resolution:
adversary_critique:  # present when a post-analysis candidate was unsalvageable
```

Minimum `post_analysis(...)` output shape:

```yaml
decision: accept_and_conclude | self_revise_plan | continue_with_same_research_plan | ask_user | declare_unanswerable
rationale:
evidence_state:
research_gap_resolution: []
panelist_callback_findings: []  # optional trace if internal callback tools were used

updated_selected_research_plan:  # required only when decision == self_revise_plan
trajectory_decision:             # required when decision == self_revise_plan
  action: initialize_plan | create_revised_node | continue_same_node | declare_unanswerable
  branch_from_node_id:
  reason:
rerun_intent:                    # required when decision == continue_with_same_research_plan
  reason:
  changed_parameters:
  required_outputs:
  reuse_artifacts:
clarifying_questions: []         # required when decision == ask_user
unanswerable_reason:             # required when decision == declare_unanswerable
what_would_be_needed:            # required when decision == declare_unanswerable
final_answer_summary:            # required when decision == accept_and_conclude
overall_confidence:
```

These contexts prevent repeated callbacks, preserve what the Mediator already
tried, and keep plan revision grounded in the current research trajectory.

`formulate(...)`, `synthesize_callbacks(...)`, and
`revise_from_adversary(...)` share the same formulation output envelope. The
`selected_research_plan` field inside that envelope must use the existing
canonical `selected_research_plan` schema from
`updated_prompts/scientist_panel_schemas.json`; do not introduce a competing
research-plan body schema. The envelope is:

```yaml
formulation_status: needs_panelist_callback | ready_for_adversary
selected_research_plan:  # canonical selected_research_plan schema; required when formulation_status == ready_for_adversary
callback_requests: []    # required when formulation_status == needs_panelist_callback
evidence_completeness: complete | partial
callback_budget_exhausted: true | false
limitations: []
research_gap_resolution: []
trajectory_decision:  # required when formulation_status == ready_for_adversary
  action: initialize_plan | create_revised_node | continue_same_node | declare_unanswerable
  branch_from_node_id:
  reason:
overall_confidence:
```

`needs_panelist_callback` is used by `formulate(...)` and
`synthesize_callbacks(...)` during the pre-execution formulation loop. After
initial formulation, targeted panelist callbacks should normally be internal
Mediator tool calls rather than final orchestration decisions.

It may additionally include adversary-specific trace fields:

```yaml
adversary_revision_summary:
  critique_addressed:
  classification_reason:
  remaining_limitations:
```

The Mediator proposes `trajectory_decision` because deciding whether the
trajectory should initialize, branch, continue the same node, or stop is a
research-lead judgment. The AdversarialPanelist receives this trajectory
decision as inherited context but critiques only the research decision and
evidence pattern. `ResearchLoop` commits the inherited action only after
adversarial review accepts the candidate plan. `ResearchState` then performs
the deterministic graph mutation.

Examples:

```yaml
initial formulation:
  trajectory_decision:
    action: initialize_plan
    branch_from_node_id: null
    reason: first accepted research plan for this task

parameter rerun:
  trajectory_decision:
    action: continue_same_node
    branch_from_node_id: active_node_id
    reason: research plan unchanged; only execution parameters need rerun

new downstream analysis:
  trajectory_decision:
    action: create_revised_node
    branch_from_node_id: plan_001
    reason: current outputs are insufficient, so the accepted plan adds downstream validation
```

Remove `research_context` and `state_graph_context` from new
`MediatorAgent.post_analysis(...)` calls. Those are legacy context fragments.
The Mediator should receive one mode-specific filtered context built from
`ResearchState`.

### 3. Move Mediator Logic Out of `ScientistPanel`

Move or delegate these behaviors:

- `_run_mediator_formulation(...)`
- `_run_mediator_callback_synthesis(...)`
- `decide_after_analysis(...)`

Do not add compatibility wrappers for the old Mediator helper methods. Replace
call sites directly so `ResearchLoop` and `ScientistPanel` call
`MediatorAgent`.

### 4. Tighten Formulation Status Contract

Mediator formulation/revision methods must return one of:

```text
needs_panelist_callback
ready_for_adversary
```

Meaning:

- `needs_panelist_callback`: no final research plan should be treated as ready
  yet; callbacks are required.
- `ready_for_adversary`: the selected research plan is ready for adversarial
  review.

This status is not an adversary verdict. The adversary has a separate
`adversary_verdict` schema:

```text
survives | needs_revision | unsalvageable
```

Do not mix these fields. `formulation_status` answers whether the Mediator has
formed a candidate plan; `adversary_verdict` answers whether the adversary
accepts, critiques, or rejects that candidate.

Additional fields:

```yaml
evidence_completeness: complete | partial
callback_budget_exhausted: true | false
limitations: []
```

When callback budget exhausts, the Mediator should still emit
`ready_for_adversary` if it can produce a defensible plan, but mark
`evidence_completeness: partial`, set `callback_budget_exhausted: true`, and
state the limitations explicitly. The AdversarialPanelist then decides whether
the partial-evidence plan survives or must be revised/rejected.

There must be no `ask_user` outcome in formulation mode.

`synthesize_callbacks(...)` and `revise_from_adversary(...)` follow the same
formulation status contract. They must return either
`needs_panelist_callback` or `ready_for_adversary` with the same additional
fields. This keeps initial formulation, callback synthesis, and
adversary-driven plan revision on one plan-readiness protocol.

When any formulation-mode Mediator method returns `ready_for_adversary`, it
must include a candidate `trajectory_decision`. For initial formulation this is
normally `action: initialize_plan`. For post-analysis revision this may be
`create_revised_node`, `continue_same_node`, or `declare_unanswerable`,
depending on whether the research logic changed.

### 5. Change Callback Timing

Current behavior:

```text
Mediator writes draft plan
-> callbacks patch the draft
-> adversary
```

Target behavior:

```text
Mediator reads panelist outputs
-> if evidence is insufficient, asks callbacks
-> repeats until clear or budget exhausted
-> only then emits selected_research_plan ready for adversary
```

This means callbacks are part of plan formation, not repair of a premature
plan.

After the pre-adversary callback loop ends:

```text
Mediator emits ready_for_adversary
-> AdversarialPanelist reviews
-> if survives, return accepted selected_research_plan to ResearchLoop and ToolConsultant
-> if needs_revision, run the adversary-driven revision loop
-> if unsalvageable, return critique to Mediator for fundamentally different reformulation or declare_unanswerable
```

The pre-adversary callback loop and the adversary-driven revision loop are
separate. The first resolves missing evidence before plan synthesis is treated
as ready. The second critiques an already-synthesized plan.

### 6. Refactor `ScientistPanel` Into a Specialist Runner

Keep `ScientistPanel` responsible for:

- running the three initial panelists;
- running targeted panelist callbacks;
- returning structured panelist outputs to `ResearchLoop`.

Do not let `ScientistPanel` own Mediator synthesis, adversarial review,
callback-loop orchestration, or global state graph decisions. Those belong to
`ResearchLoop`.

Suggested methods:

```python
run_initial_panelists(...)
run_panelist_callback(...)
```

`run_panelist_callback(role: str, callback_input: dict) -> dict` should be the
public narrow-callback entrypoint used by Mediator internal tools. It wraps the
existing private callback runner and calls the same three panelist roles in
callback mode. Do not keep a plural public callback API that implies the outer
loop owns post-analysis callback orchestration.

Remove or retire `ScientistPanel.formulate_research_plan(...)` as an owner of
the full formulation loop. If a helper with that name remains temporarily, it
must delegate orchestration back to `ResearchLoop` and must not call
`MediatorAgent`, `AdversarialPanelist`, or mutate `ResearchState`.

### 7. Keep `ResearchLoop` as the Outer Orchestrator

`ResearchLoop` should own or receive `MediatorAgent`, `ScientistPanel`, and
`AdversarialPanelist` directly. It owns the full formulation-stage
orchestration:

```text
ResearchLoop
-> ScientistPanel.run_initial_panelists(...)
-> MediatorAgent.formulate(...)
-> targeted ScientistPanel.run_panelist_callback(...) if requested
-> MediatorAgent.synthesize_callbacks(...) until ready_for_adversary or budget exhausted
-> ResearchState.context_for_adversary(candidate_plan, candidate_trajectory_decision)
-> AdversarialPanelist.run(adversary_context=...)
-> MediatorAgent.revise_from_adversary(...) if adversary needs revision
-> commit accepted trajectory_decision through ResearchState
```

This keeps uncommitted candidate plans outside `ResearchState` until the
adversary path accepts them or the repeated-`needs_revision` budget-exhaustion
rule commits the Mediator's final revised plan.

Before the first formulation call, `ResearchWorkspace` must create or load a
minimal task-scoped `ResearchState`:

```yaml
task:
  research_state_id:
  conversation_id:
  user_task:
  data_summary:
working_memory:
  panelist_outputs: []
  callback_history: []
  mediator_outputs: []
trajectory:
  nodes: []
active_research_state: null
```

Panelist outputs and Mediator outputs are merged into this `ResearchState` as
formulation proceeds. The selected plan becomes
`ResearchState.active_research_state` only after formulation returns a plan
ready for adversarial review and the plan is accepted.

The formulation stage should be implemented as a `ResearchLoop` helper, for
example:

```python
formulation_result = self._run_formulation_stage(
    research_state=research_state,
    user_question=user_question,
    data_summary=data_summary,
)
```

Minimum return shape:

```yaml
status: accepted | unanswerable
selected_research_plan:
trajectory_decision:
mediator_output:
adversary_result:
panelist_outputs:
callback_history:
research_gap_resolution:
limitations:
```

`status: accepted` means `ResearchLoop` can dispatch
`trajectory_decision.action` to `ResearchState`. `status: unanswerable` means
`ResearchLoop` marks the active task unanswerable and does not call
ToolConsultant.

After adversarial review accepts a candidate plan, `ResearchLoop` dispatches
the candidate `trajectory_decision.action` to `ResearchState`:

```text
initialize_plan:
  research_state.create_node(selected_research_plan, ...)

create_revised_node:
  research_state.branch(
    selected_research_plan,
    branch_from_node_id=trajectory_decision.branch_from_node_id,
    ...
  )

continue_same_node:
  research_state.append_iteration(...)

declare_unanswerable:
  research_state.mark_unanswerable(reason=trajectory_decision.reason)
```

`ResearchLoop` must not commit any trajectory mutation before adversarial
acceptance while revision budget remains. If repeated `needs_revision` verdicts
exhaust `max_adversary_revision_rounds`, the Mediator performs one final
revision using the latest critique. `ResearchLoop` then commits that final
revised plan and sends it to ToolConsultant. The committed plan must preserve
remaining critiques as explicit limitations or gap-resolution notes rather than
silently dropping them.

Before execution, `ResearchLoop` runs `_run_formulation_stage(...)` and commits
only the returned accepted candidate through `ResearchState`.

After execution:

```python
post_decision = mediator.post_analysis(
    post_analysis_context=research_state.context_for_mediator_post_analysis(
        analyzer_report=analyzer_report,
        dag_result_summary=dag_result_summary,
        tool_decision=tool_decision,
        artifact_registry_summary=artifact_registry_summary,
    )
)
```

Post-analysis decision dispatch:

```text
accept_and_conclude:
  research_state.mark_concluded(...)
  return final answer

declare_unanswerable:
  research_state.mark_unanswerable(...)
  return

ask_user:
  pause loop and surface clarifying_questions

continue_with_same_research_plan:
  no adversary review required
  research_state.append_iteration(..., rerun_intent=post_decision["rerun_intent"])
  include rerun_intent in ResearchState.context_for_tool_consultant()
  continue to ToolConsultant / execution

self_revise_plan:
  build adversary_context with candidate_plan=updated_selected_research_plan
  and candidate_trajectory_decision=trajectory_decision
  send adversary_context to AdversarialPanelist
  if adversary survives:
    commit trajectory_decision through ResearchState
  if adversary needs_revision:
    enter revise_from_adversary(...) loop
    if max_adversary_revision_rounds is exhausted:
      commit the Mediator's final revised plan and send it to ToolConsultant
  if adversary unsalvageable:
    do not commit trajectory_decision
    call MediatorAgent.post_analysis(...) again with the adversary critique added to post_analysis_context
    Mediator must return self_revise_plan with a fundamentally different candidate, ask_user, or declare_unanswerable
    if max_adversary_revision_rounds is exhausted on unsalvageable:
      do not commit trajectory_decision; follow the same unsalvageable terminal options
```

`ResearchLoop` remains responsible for:

- creating / updating research trajectory nodes through `ResearchState`;
- saving plan, tool, execution, analyzer, and decision files;
- deciding whether a user-facing clarification is needed at the orchestration
  layer;
- routing to ToolConsultant, execution, Analyzer, or final answer.
- maintaining `ResearchState` as the single source of truth and producing
  filtered context views for each agent.

### 8. Keep `ask_user` Only in Post-Analysis, Not Formulation

Formulation mode must not ask the user.

If user ambiguity exists before research planning, the outer router /
orchestrator should ask before entering the loop.

Post-analysis mode may emit `ask_user` when execution or result inspection
reveals that the next scientifically valid step depends on information only the
user can provide. The Mediator should provide concrete clarifying questions and
options. ResearchLoop owns the actual pause / user-interaction behavior.

### 9. Strengthen PI Gap-Solving Behavior

Add this rule to `mediator_shared_system.md`:

```text
When you encounter a gap, do not merely report that the system is blocked.
Act like a human research lead. Identify the missing evidence, explain why it
matters, choose the most reasonable first attempt to resolve it, specify the
fallback if that attempt fails, and define the stop condition where the claim
should be treated as unsupported, inconclusive, or unanswerable.
```

Mediator gap reasoning should include a trace record:

```yaml
research_gap_resolution:
  gap:
  why_it_matters:
  first_try:
  fallback_if_first_try_fails:
  stop_condition:
  target_owner: mediator | panelist | tool_consultant | analyzer | orchestrator
```

`research_gap_resolution` is not a parallel plan. It is an audit trail of how
the PI reasoned about the gap: what was missing, why it mattered, what was
worth trying first, what fallback was considered, and when to stop. If the
resolution changes the analysis, the executable/research content must also be
written into `updated_selected_research_plan`.

Location and consumption:

```text
research_gap_resolution is emitted as a top-level list on Mediator outputs.
ResearchLoop persists it on the active ResearchState node as gap_resolution_log.
The decision field drives control flow and graph mutation.
target_owner is advisory context for routing the next attempt; it does not
override the decision field.
```

### 10. Update Post-Analysis Decision Contract

Current decision set includes:

```text
accept_and_conclude
self_revise_plan
ask_user
declare_unanswerable
```

Target decision set:

```text
accept_and_conclude
self_revise_plan
continue_with_same_research_plan
ask_user
declare_unanswerable
```

Notes:

- `self_revise_plan`: Mediator can revise the research plan directly.
- `continue_with_same_research_plan`: the research plan remains valid and no
  new research logic is added. Only execution parameters or implementation
  details need to change.
- `ask_user`: execution or result inspection revealed that the next valid step
  depends on information only the user can provide. ResearchLoop handles the
  actual user interaction.
- `declare_unanswerable`: the available data / feasible evidence cannot support
  the required claim.

`call_panelists` is removed as a final decision. If the Mediator needs targeted
panelist reasoning or literature-backed interpretation during post-analysis, it
uses internal tools and receives those results before emitting the final
decision.

Decision boundary:

```text
research logic changes -> self_revise_plan
execution details change -> continue_with_same_research_plan
user-only information needed -> ask_user
```

`self_revise_plan` should be used when the next action adds an analysis, changes
the evidence pattern, changes the comparison, changes the statistical unit,
changes the method class, or changes what claim is being tested. This creates a
new/updated plan node.

`continue_with_same_research_plan` should be used only when the existing plan
already required the needed output and the next action is a rerun, dependency
repair, missing-file regeneration, or parameter adjustment within the same plan.
This records a new iteration under the same active node, with no new branch
node.

### 11. Rename Misleading Methods

Rename:

```python
_run_round1_formulate
```

to:

```python
_run_initial_panelist_formulation
```

because there is no `_run_round2_formulate` in the current design.

Consider renaming:

```python
_run_mediator_callback_loop
```

to:

```python
_run_formulation_callback_loop
```

or move it fully into the new formulation-loop coordinator.

### 12. Legacy Migration Strategy

Current implementation incompatibilities to account for:

- `research_context` is currently built by `_extract_research_context(...)` as
  an ad hoc dict and passed to ToolConsultant, alignment review, Analyzer, and
  Mediator post-analysis.
- post-analysis panelist callbacks are currently orchestrated by
  `ResearchLoop` via `decision == call_panelists`; TODO4 replaces this with
  internal Mediator tools inside `MediatorAgent.post_analysis(...)`.
- `state_graph_context` currently comes from `StateGraphManager` context
  builders, but `reusable_artifacts` and `unresolved_gaps` are placeholders.
- `working_model` is a legacy cross-component parameter used by ResearchLoop,
  ScientistPanel, AnalyzerPanel, and ContextManager. TODO4 replaces it with
  `ResearchState` and `evidence_state`.
- `_normalize_*` functions currently parse and mutate LLM outputs with loose
  defaults. TODO4 replaces them with strict parser/validator functions plus one
  schema-repair retry.
- Mediator logic currently lives inside `ScientistPanel` private methods and
  `ScientistPanel.decide_after_analysis(...)`.
- `StateGraphManager` currently treats nodes mostly as plan records with
  attached refs; TODO4 requires nodes to own iterations.
- `StateGraphManager` currently owns `context_for_*` methods. TODO4 moves
  prompt-context construction to `ResearchState`.
- deployed node statuses include `active`, `candidate`, `concluded`,
  `unanswerable`, `awaiting_user`, and `inactive`; TODO4 requires an explicit
  status migration.

Migration rules:

1. Introduce `ResearchWorkspace` and task-scoped `ResearchState` as the new
   state architecture.
   - `ResearchWorkspace` is conversation-scoped and tracks the active
     `ResearchState`.
   - `ResearchState` is task-scoped and owns the runtime trajectory,
     evidence_state, working memory, and artifact index for one research task.
   - The existing `StateGraphManager` may remain only as internal graph
     persistence behind `ResearchState`.
2. Replace `research_context`, `state_graph_context`, and `working_model` call
   sites with `ResearchState` fields or `ResearchState.context_for_*` views in
   the same implementation phase. Do not add new compatibility wrappers for
   these legacy names.
3. Remove or stop calling `StateGraphManager.context_for_*`; context builders
   should be `ResearchState.context_for_*`.
4. Replace loose `_normalize_*` functions for new/changed LLM outputs with
   strict parser/validator functions:

```python
parse_mediator_formulation_output(...)
parse_mediator_adversary_revision_output(...)
parse_mediator_post_analysis_output(...)
parse_panelist_formulation_output(...)
parse_panelist_callback_output(...)
parse_adversary_output(...)
parse_analyzer_output(...)
parse_tool_consultant_output(...)
```

5. Remove `call_panelists` from the final post-analysis decision parser and add
   `continue_with_same_research_plan`. Unknown decisions must produce
   `schema_error` and a repair retry, not default to `accept_and_conclude`.
6. Remove the legacy external `call_panelists` orchestration path:
   - delete the post-analysis `decision == call_panelists` while-loop in
     `ResearchLoop`;
   - delete or retire `ScientistPanel.run_post_analysis_callbacks()`;
   - remove `call_panelists` and its aliases from post-analysis decision
     normalization;
   - delete `_after_analysis_callback_limit()` if it is only used by that loop.
   Targeted post-analysis panelist callbacks should happen through
   `MediatorAgent` internal tools.
7. Replace `working_model` directly:
   - `ResearchLoop` should maintain `ResearchState`, not a `working_model`
     variable.
   - `MediatorAgent.post_analysis(...)` receives `post_analysis_context`, not
     `working_model`.
   - `AnalyzerPanel.analyze(...)` should receive `analyzer_context` or
     `evidence_state`, not `working_model`.
   - `ContextManager` should be removed from this path or refactored into
     `ResearchState` update helpers.
8. Migrate StateGraph nodes from `repeat_iterations` to full `iterations`:
   - add `iterations: []` to each node;
   - migrate existing `repeat_iterations` entries into legacy iteration records
     with null/empty refs for fields not previously tracked;
   - record every execution/analyzer cycle as an iteration;
   - implement `continue_with_same_research_plan` by appending a new iteration
     to the active node.
9. Apply node status migration:

```text
inactive -> superseded
candidate -> candidate  (keep for alternative plans)
awaiting_user -> awaiting_user  (keep because post-analysis ask_user remains)
invalid -> add as new status
```

Final allowed node statuses:

```text
active | candidate | superseded | concluded | unanswerable | awaiting_user | invalid
```

10. Delete or stop using old context paths as the implementation moves. The goal
   is migration away from the legacy design, not maintaining dual contracts.
11. Move direct `ResearchLoop -> StateGraphManager` calls to
    `ResearchLoop -> ResearchState`. If `StateGraphManager` is still used, it
    must be hidden behind `ResearchState` as graph persistence.

### 13. Update Schemas and Prompts

Update:

```text
updated_prompts/mediator_formulation.md
updated_prompts/mediator_adversary_revision.md
updated_prompts/mediator_post_analysis.md
updated_prompts/mediator_shared_system.md
updated_prompts/scientist_panel_schemas.json
updated_prompts/workflow.md
plans/update_system.md
agents/adversarial_panelist.py
agents/state_graph.py
```

The schema migration must use `selected_research_plan` as the single canonical
plan body. `updated_prompts/scientist_panel_schemas.json` should define the
canonical seven-section plan body and the Mediator envelopes should reference
that body instead of redefining a different plan schema.

Required Mediator formulation envelope:

```yaml
formulation_status: needs_panelist_callback | ready_for_adversary
selected_research_plan:  # canonical selected_research_plan schema
callback_requests: []
evidence_completeness: complete | partial
callback_budget_exhausted: true | false
limitations: []
research_gap_resolution: []
trajectory_decision:
  action: initialize_plan | create_revised_node | continue_same_node | declare_unanswerable
  branch_from_node_id:
  reason:
overall_confidence:
```

Required Mediator post-analysis envelope:

```yaml
decision: accept_and_conclude | self_revise_plan | continue_with_same_research_plan | ask_user | declare_unanswerable
rationale:
evidence_state:
research_gap_resolution: []
panelist_callback_findings: []
updated_selected_research_plan:  # canonical selected_research_plan schema; required only for self_revise_plan
trajectory_decision:             # required only for self_revise_plan
  action: initialize_plan | create_revised_node | continue_same_node | declare_unanswerable
  branch_from_node_id:
  reason:
rerun_intent:                    # required only for continue_with_same_research_plan
  reason:
  changed_parameters:
  required_outputs:
  reuse_artifacts:
clarifying_questions: []         # required only for ask_user
unanswerable_reason:             # required only for declare_unanswerable
what_would_be_needed:            # required only for declare_unanswerable
final_answer_summary:            # required only for accept_and_conclude
overall_confidence:
```

For post-analysis, `updated_selected_research_plan` is returned only when the
research plan actually changes (`decision == self_revise_plan`). For all other
decisions, the active plan remains the one already stored in `ResearchState`.
`continue_with_same_research_plan` carries execution changes through
`rerun_intent`, not by echoing a full unchanged plan.

Prompt/schema cleanup required in the same phase:

- replace `AdversarialPanelist.run(user_question, mediator_plan)` with
  `AdversarialPanelist.run(adversary_context=...)`; both initial formulation
  and post-analysis `self_revise_plan` use this same API;
- ensure adversary prompts and parsers use `adversary_verdict`, not
  `formulation_status`;
- remove legacy `mediator_decision` / `callbacks` fields from formulation
  schemas and prompts;
- remove legacy `panelist_callbacks` from post-analysis schemas and prompts;
- remove `call_panelists` as a final post-analysis decision;
- keep `panelist_callback_findings` only as a trace of internal Mediator tool
  use;
- ensure `trajectory_decision` has no `research_logic_changed` field.

Needed schema additions:

- `ResearchWorkspace` schema;
- `ResearchStateRegistry` schema;
- `ResearchState` schema;
- context view builders:
  - `context_for_mediator_formulation`;
  - `context_for_mediator_adversary_revision(adversary_critique, adversary_revision_round, max_adversary_revision_rounds)`;
  - `context_for_mediator_post_analysis`;
  - `context_for_panelist`;
  - `context_for_adversary(candidate_plan, candidate_trajectory_decision)`;
  - `context_for_tool_consultant`;
  - `context_for_analyzer`;
- `formulation_status`;
- `callback_requests`;
- canonical `selected_research_plan`;
- Mediator internal post-analysis tools:
  - `ask_panelist_for_more_reasoning`;
  - `ask_panelist_for_more_literature`;
- `evidence_completeness`;
- `callback_budget_exhausted`;
- `research_gap_resolution`;
- `gap_resolution_log` on StateGraph nodes;
- `trajectory_decision`;
- `continue_with_same_research_plan`;
- keep `ask_user` for post-analysis only.
- strict parser/validator schema for each structured LLM output;
- `parse_mediator_adversary_revision_output`;
- schema-repair retry prompt for invalid structured outputs;
- removal of silent terminal defaults for unknown decisions.

Also update `update_system.md` Phase 10 and the internal graph persistence path
behind `ResearchState` so `continue_with_same_research_plan` is handled
explicitly:

```text
continue_with_same_research_plan:
  keep active node status unchanged
  create a new iteration under the active node
  attach new execution/analyzer/decision refs to that iteration
  do not create a new branch node
```

Replace `StateGraphManager.context_for_tool_consultant()` with
`ResearchState.context_for_tool_consultant()` exposing enough continuation
information for incremental execution:

```yaml
previous_iterations:
reusable_artifacts:
failed_steps:
missing_outputs:
parameters_used:
recommended_continue_from:
rerun_intent:
```

### 14. Update Tests

Add or update tests for:

- `SessionRouter` handles high-level intent and `ResearchWorkspace` handles
  task-state routing.
- `ResearchWorkspace` can continue the active `ResearchState`, create a new
  `ResearchState`, and switch to a previous `ResearchState`.
- `ResearchState` is the single runtime source of truth for the active task and
  persists trajectory through its internal graph persistence path.
- `ResearchLoop` calls trajectory mutation methods through `ResearchState`, not
  directly through `StateGraphManager`.
- context view builders return filtered read-only projections rather than
  independent mutable state.
- `ResearchState.context_for_tool_consultant()` includes previous iterations, reusable
  artifacts, missing outputs, failed steps, parameters, and recommended
  continue-from checkpoint.
- `StateGraphManager.context_for_*` is no longer used by `ResearchLoop`.
- `working_model` is removed from ResearchLoop, MediatorAgent, AnalyzerPanel,
  and ContextManager call paths touched by TODO4.
- structured LLM parsers validate tag/schema/enum strictly and retry once with
  a repair prompt on invalid schema.
- unknown post-analysis decisions do not default to `accept_and_conclude`.
- reasoning agents receive artifact summaries/IDs rather than automatically
  reading raw file paths.
- `MediatorAgent` can be initialized independently.
- `mediator.formulate(...)` can return `needs_panelist_callback` without a
  ready plan.
- `mediator.revise_from_adversary(...)` follows the same formulation status
  contract as `formulate(...)` and `synthesize_callbacks(...)`.
- any Mediator formulation-mode output with `ready_for_adversary` includes a
  candidate `trajectory_decision`.
- formulation callbacks repeat until `ready_for_adversary`.
- callback budget exhaustion emits `ready_for_adversary` with
  `evidence_completeness: partial` and `callback_budget_exhausted: true`.
- formulation never emits `ask_user`.
- post-analysis may emit `ask_user`, and ResearchLoop pauses for user
  interaction.
- post-analysis cannot emit `call_panelists`; targeted panelist callbacks happen
  through internal Mediator tools and return inside the same
  `MediatorAgent.post_analysis(...)` run.
- `ask_panelist_for_more_reasoning` and `ask_panelist_for_more_literature` call
  the same three panelist roles in callback mode.
- `continue_with_same_research_plan` keeps the active StateGraph node active and
  records a new iteration without creating a new branch node.
- `self_revise_plan` creates or updates a plan node when research logic changes.
- `ResearchLoop` commits `trajectory_decision` only after adversarial
  acceptance and dispatches actions to the correct `ResearchState` method.
- adversary-driven revision loop stops at `max_adversary_revision_rounds` and
  classifies unresolved critiques as nonfatal limitations or fatal flaws.
- `ScientistPanel` delegates Mediator work to `MediatorAgent`.
- `ResearchLoop` calls `MediatorAgent.post_analysis(...)` directly after
  Analyzer output.
- Analyzer remains outside the formulation/revision loop.
- `_run_round1_formulate` rename does not break existing flow.

## Non-Goals

Do not split the three panelists into separate classes in this task unless it
falls out naturally. That can be a later refactor:

```python
PanelistAgent(role="biologist")
PanelistAgent(role="statistician")
PanelistAgent(role="bioinformatician")
```

The immediate priority is extracting `MediatorAgent` and correcting the
formulation / post-analysis loop contracts.
