# Evolving Research Logic: Research Reasoning Guidelines, Plan Refinement, and Evolving Phases

## Goal

This document captures the desired research reasoning behavior for discovery sessions.
It builds on the current ScientistPanel structure rather than replacing it.

The system should keep the current high-level architecture:

```text
SessionRouter
  -> operational task
      -> ToolConsultant
      -> execution

  -> discovery task
      -> ScientistPanel
          -> BiologistPanelist
          -> StatisticianPanelist
          -> BioinformaticianPanelist
      -> panelist literature tools as needed
      -> Mediator
      -> ToolConsultant
      -> AdversarialPanelist
      -> execution
      -> AnalyzerPanel
      -> ScientistPanel.update if another phase is needed

  -> ambiguous task
      -> ask user to choose between two concrete interpretations
```

The new requirement is not a new architecture. The requirement is a stronger research
discipline inside the existing architecture.

Core rule:

```text
First establish the strongest existing solution path.
Then decide what additional contribution, if any, should be built on top of it.
```

The system should not treat every discovery request as a request to invent a new
method. It should also not stop at a standard workflow when the user asks for an
interpretive or discovery answer. The existing solution is the foundation; extensions,
new analyses, method combinations, adaptations, or new models build on top of that
foundation.

## Why This Is Needed

The current panelist structure is useful, but without explicit research reasoning
guidelines it can drift into one of two bad behaviors:

```text
1. Generic planning:
   The panelists propose broad analyses without reconstructing what prior work did
   or what evidence is actually required.

2. Fake novelty:
   The panelists jump to new analyses or custom methods before identifying the best
   existing evidence path.
```

The desired behavior is closer to how a careful researcher works:

```text
1. Understand the question.
2. Translate it into a falsifiable research hypothesis or concrete analysis claim.
3. Review literature with a specific target.
4. Reconstruct the strongest existing evidence or analysis path.
5. Decide whether the user's question is already answered, partially answered, or
   not answered.
6. Plan the existing solution first.
7. Add extension or de novo components only when justified.
8. Execute.
9. Let results determine whether the next phase concludes, extends, pivots, or
   revises the plan.
```

## Fix 1: Add Existing-Solution-First Reasoning To Panelist Prompts

All three panelists should follow the same research arc, but from different
perspectives. The separation is by lens, not by a mutually exclusive checklist.

Shared prompt guideline:

```text
Before proposing a new analysis, first establish the strongest existing solution
path. Look for the papers, accepted workflows, or evidence patterns that most
directly answer this kind of question. Do not only ask what conclusion those papers
reached. Reconstruct how they made the conclusion credible: what data they used,
how they defined the relevant entities, what comparison they ran, what metric they
reported, what controls or validation they required, and what assumptions their
method depends on.

Treat the existing solution path as the foundation of the research plan. If the
literature already answers the same or a very similar question, the first plan
component should reproduce or apply that established evidence or analysis on the
user's data, following the relevant literature. The next component should ask what
this dataset can add beyond prior work: a new context, subtype, modality, covariate,
trajectory, regulatory layer, or more detailed analysis.

If the exact question has not been answered but a suitable established method or
evidence pattern exists, use that existing path as the starting point. The research
contribution may come from applying it to the user's specific context or from
analyzing its outputs in a new way. For example, running MultiVelo is not itself
the scientific answer. The research plan must specify what downstream evidence
from MultiVelo outputs would support chromatin priming, lagging, or lockstep
dynamics.

If no adequate existing solution exists, still identify the closest reasonable
baseline. A de novo analysis, method combination, method adaptation, or new model
is only justified when the panel can explain what the existing baseline cannot
answer. Even then, the baseline remains part of the plan, because the new
contribution must be compared against it.

Novelty can appear at several levels. It may be a new biological context, a new
analysis of existing method outputs, a new combination of established methods, an
adaptation of an existing method, or a genuinely new model. Do not equate novelty
only with inventing a new algorithm. Also do not invent a new method when the
user's question can be answered by applying the existing evidence path carefully.

When proposing an extension beyond the existing solution, explain what the existing
path directly establishes and what remains unanswered. The extension should be tied
to the user's dataset and hypothesis, not added as decorative novelty. After
execution, AnalyzerPanel results should decide whether the next phase concludes,
confirms more carefully, extends the analysis, pivots, or proposes a new method.
```

Role lens:

```text
BiologistPanelist:
  Applies the research arc through biological entities, cell types, cell states,
  marker genes, pathways, prior findings, mechanisms, tissue context, disease
  context, and biological validation.

StatisticianPanelist:
  Applies the research arc through comparison design, statistical unit, effect
  metric, controls, confounders, robustness, validity, and what would make the
  evidence credible or invalid.

BioinformaticianPanelist:
  Applies the research arc through workflow structure, data requirements, method
  assumptions, computational outputs, tool feasibility, intermediate artifacts,
  and whether existing tools can produce the evidence required.
```

Important:

```text
The panelists may reason about the same high-level research problem.
They should not produce the same kind of answer.
Their outputs should be complementary because each panelist applies a different lens.
```

## Fix 2: Require A Concrete Hypothesis Or Analysis Claim Before Literature Retrieval

The first job in discovery is not tool planning. The first job is to clarify what
the user is asking the system to establish.

Do not use the abstract `claim_type` field. Instead, require a concrete statement:

```text
What exactly would the analysis need to show for the user's question to be answered?
```

The hypothesis or analysis claim should name:

```text
entities
direction or expected relationship, if applicable
comparison or context
dataset constraints
what would count as support
what would count as contradiction or insufficiency
```

Example:

```text
User question:
  Do T cells expand in this disease dataset?

Concrete analysis claim:
  T cells, defined by reference annotation and CD3D/CD3E/TRAC marker support,
  have higher sample-level abundance in disease samples than controls after
  accounting for available batch or donor covariates.
```

Example:

```text
User question:
  Run MultiVelo and determine whether chromatin primes RNA expression.

Concrete analysis claim:
  Along the relevant cell-state trajectory, accessibility dynamics for a coherent
  set of regulatory elements or genes precede RNA expression dynamics more often
  than expected by lockstep or lagging alternatives, and the pattern is linked to
  interpretable TF or motif activity.
```

This concrete statement becomes the target for literature retrieval, panelist
reasoning, Mediator synthesis, ToolConsultant planning, and adversarial review.

## Fix 3: Literature Review Must Produce More Than Summaries

Panelists should use a small literature tool surface:

```text
search_paper_wiki
retrieve_literature
fetch_paper_content
```

The literature tools should not decide the scientific meaning of a paper for the
panelist. They retrieve, deduplicate, canonicalize, summarize, persist, and expose
paper content. The panelist reads the returned summaries, incorporates the useful
parts into role-specific reasoning, ignores off-target material, asks for deeper
paper content when needed, and retrieves again when gaps remain.

### Tool 1: search_paper_wiki

Purpose:

```text
Search accumulated paper memory and return canonical structured paper summaries.
```

Behavior:

```text
1. Search wiki entries by retrieval intent, retrieval goal, requirements, and background.
2. Deduplicate internally.
3. Return canonical paper summaries.
```

The paper wiki should not contain duplicate papers. The search tool should still
deduplicate defensively before returning results.

### Tool 2: retrieve_literature

Purpose:

```text
Fresh external retrieval only.
```

Inputs:

```text
retrieval_intent
retrieval_goal
requirements
background
exclude_ids
```

`exclude_ids` should include already known wiki papers and papers already returned
in the current panelist loop:

```text
paper_ids
dois
pmids
pmcids
semantic_scholar_ids
openalex_ids
normalized_titles
```

Behavior:

```text
1. Search external sources.
2. Normalize identifiers.
3. Remove candidates matching exclude_ids.
4. Deduplicate candidates across sources.
5. Fetch/enrich full text when available.
6. Summarize each paper into the canonical paper structure.
7. Persist returned fresh paper summaries to the paper wiki.
8. Return canonical paper summaries to the panelist.
```

There is no separate PaperJudge step in the panelist literature loop. The retrieval
layer should make a good-faith targeted search and return structured summaries.
The panelist owns the scientific use of those summaries.

### Tool 3: fetch_paper_content

Purpose:

```text
Fetch section-level or targeted full-text content from the vector database or
parsed paper store.
```

It should work for both wiki papers and newly retrieved papers, using `paper_id`,
`doc_id`, or `vector_doc_id`.

Use when:

```text
the summary is not enough
the panelist needs exact methods/results/discussion details
the panelist needs targeted evidence inside one paper
```

### Canonical Paper Summary

All papers returned to panelists should use the same canonical structure:

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

The wiki paper markdown should store this same canonical structure so wiki papers
and freshly retrieved papers have the same shape when returned to panelists.

Panelists should reconstruct how prior work made a conclusion credible.

For each useful paper, extract:

```text
question_answered:
  What question was the paper trying to answer? Is it the same as ours, adjacent,
  methodologically similar, or only vocabulary-overlapping?

concrete_hypothesis_or_claim:
  What specific statement did the paper try to support?

data_context:
  Assay, sample size, organism, tissue, condition, cohort, modality, and whether
  it transfers to the user's dataset.

analysis_or_method:
  Pipeline, model, statistical test, tool, or workflow used.

finding:
  Direction, magnitude if available, and the important result, not just whether
  it was significant.

limitations:
  What the authors acknowledged.

failure_or_correction:
  What the paper failed to control for, what later work corrected, or what a
  skeptical reviewer would challenge.

benchmark_or_gold_standard:
  Accepted datasets, metrics, baselines, or evaluation practices in the area.

method_failure_modes:
  Where the current best methods fail and why.

open_questions:
  Questions the authors left unresolved that may motivate the user's next phase.
```

The synthesis from literature review should be a verdict, not a summary.

Mediator should record:

```text
literature_verdict:
  answered_well
  partially_answered
  not_answered

verdict_rationale:
  Why this verdict follows from the papers and the user's data context.

existing_solution_path:
  The strongest evidence or analysis path established by literature.

remaining_gap:
  What the user's dataset or question can still contribute.
```

## Fix 4: Explicitly Handle The Three Research Cases

The Mediator should classify the discovery plan into one of three broad cases.
These cases are about research logic, not routing.

### Case 1: Prior Work Already Answered The Same Or Very Similar Question

Use when literature has a credible answer that transfers reasonably well to the
user's setting.

Plan shape:

```text
Existing solution plan:
  Reproduce or apply the established evidence / analysis on the user's data,
  following the relevant literature.

Extension plan:
  Identify what can be learned beyond prior work using this dataset.
```

Example:

```text
Prior work already showed T cell expansion in a similar disease context.

Existing solution:
  Define T cells using reference labels and marker support.
  Compute abundance at the sample or donor level when available.
  Compare disease versus control.
  Report effect size and uncertainty.
  Validate labels and compare direction with prior work.

Extension:
  Ask whether expansion is driven by CD8 cytotoxic, exhausted, memory, regulatory,
  or other T cell states.
  Ask whether the expansion is linked to a gene program, tissue compartment,
  treatment state, trajectory, or regulatory signature.
```

The plan should not be marked unsalvageable just because the biological conclusion
is known. Known literature should define what evidence is required and what useful
extension remains.

### Case 2: Exact Question Is Not Answered, But Established Methods Fit

Use when literature does not answer the exact user question, but there is a strong
existing method or evidence pattern for this kind of biological or analytical
problem.

Plan shape:

```text
Existing solution plan:
  Use the best established method or evidence pattern for this kind of question.

Extension plan:
  Apply it to the user's specific question, dataset, or context, then add analysis
  specific to the user's hypothesis.
```

Example:

```text
No paper answers this exact MultiVelo question in the user's dataset.

Existing solution:
  Run MultiVelo correctly on matched RNA/ATAC cells.
  Extract standard velocity, latent time, and gene/accessibility dynamics outputs.

Extension:
  Quantify chromatin-RNA lead-lag patterns.
  Stratify by cell state.
  Link primed genes to motif accessibility, TF activity, and target expression.
  Report genes or programs as priming, lagging, lockstep, or unsupported.
```

### Case 3: No Adequate Existing Solution Exists

Use only when no existing method or evidence path can adequately answer the user's
question.

Plan shape:

```text
Existing baseline plan:
  Run the closest reasonable existing method, even if imperfect.

De novo plan:
  Propose an adaptation, method combination, new analysis, or new method.
  Benchmark it against the baseline.
```

Rules:

```text
New method work is justified only if the existing baseline cannot answer the
question and the failure mode is explicitly stated.

Even in de novo work, the closest existing baseline remains part of the plan.

A new method without a head-to-head against the obvious existing method is not a
credible contribution.
```

## Fix 5: Define Novelty As A Ladder, Not Only A New Algorithm

Novelty should not mean only deep learning or new model development.

Use this ladder:

```text
Level 0: Known execution
  Run an established method for a routine operational request.

Level 1: New application or context
  Apply an established evidence path to a new dataset, tissue, condition, cohort,
  modality setting, or disease context.

Level 2: New analysis of existing method outputs
  Run an established method, then ask a new downstream question from its outputs.
  Example: use MultiVelo outputs to quantify cell-state-specific lead-lag evidence.

Level 3: New combination of existing methods
  Combine established methods in a way that answers a question neither method
  answers alone.
  Example: MultiVelo plus motif enrichment plus target expression plus trajectory
  state transitions.

Level 4: Method adaptation
  Modify an existing method because the canonical version has a known failure mode
  for this data or question.

Level 5: New method
  Design a genuinely new algorithm or model. Requires baselines, benchmarks,
  ablations, and evidence that existing methods are insufficient.
```

Mediator should record:

```text
novelty_level
why_this_level_is_justified
what_existing_solution_is_still_run
what_extension_is_built_on_top
```

## Fix 6: Keep ToolConsultant Separate From Scientific Reasoning

Panelists and Mediator produce research requirements.

ToolConsultant answers:

```text
Given these analysis requirements, what executable tools, DAG steps, or custom
code are needed?
```

ToolConsultant should not decide the scientific meaning of the user query.

ToolConsultant receives:

```text
research_plan
analysis_requirements
existing_solution_component
extension_or_de_novo_component
validation_requirements
success_criteria
```

ToolConsultant returns:

```text
tool_plan
implementation_plan
expected_outputs
required_dependencies
known_feasibility_risks
```

The tool plan must show how execution will produce the evidence required by the
research plan. Running a method is not sufficient if the user asked for an
interpretation.

Example:

```text
Bad:
  Run MultiVelo.

Good:
  Run MultiVelo, extract latent time and gene-wise accessibility/expression
  dynamics, quantify lead-lag relationships, stratify by cell state, and generate
  tables/figures that let AnalyzerPanel classify patterns as priming, lagging,
  lockstep, or unsupported.
```

## Fix 7: Two Refinement Loops

Discovery should use two refinement loops.

### Loop 1: Scientific Reasoning Loop

Goal:

```text
Make the research plan scientifically coherent.
```

Flow:

```text
Panelists reason from the user question and data summary.
Panelists call search_paper_wiki, retrieve_literature, and fetch_paper_content as needed.
Panelists extract evidence patterns and research requirements.
Mediator synthesizes a draft research plan.
Mediator decides whether more evidence is needed.
Mediator sends gap-directed callbacks to panelists if needed.
Mediator updates the research plan.
Repeat until the plan is coherent enough to send to ToolConsultant.
```

The output of Loop 1 is:

```text
research_plan
analysis_requirements
existing_solution_path
extension_or_de_novo_path, if any
validation_requirements
success_criteria
open_risks
```

### Loop 2: Execution-Feasibility Refinement Loop

Goal:

```text
Make the research plan executable without losing the science.
```

Flow:

```text
Mediator sends research plan to ToolConsultant.
ToolConsultant produces tool/implementation plan.
AdversarialPanelist reviews research plan and executable plan together.
Mediator routes critiques to the correct owner.
Owners revise.
Repeat until accepted, redirected, or declared unable to answer.
```

Mediator remains part of Loop 2 because it owns reconciliation.

Adversary critiques. It does not own the rewrite.

## Fix 8: Formalize Mediator Callbacks To Panelists

Panelists are stateless LLM calls. They do not remember prior rounds unless the
orchestrator gives them structured context.

When the Mediator asks for more reasoning or more literature, it should send a
structured context packet.

Callback types:

```text
ask_panelist_for_more_reasoning
ask_panelist_for_more_literature
```

Callback context:

```text
Original task:
  User query
  Data summary
  Method constraints, if any

Panelist state:
  Panelist role
  Panelist prior reasoning
  Panelist prior conclusions
  Panelist prior confidence
  Panelist unresolved gaps

Cross-panel state:
  Key findings established by other panelists
  Cross-role flags involving this panelist
  Conflicts already resolved by the Mediator
  Conflicts still open and relevant to this callback
  Dependencies between this panelist's answer and another role's requirement

Mediated state:
  Current research plan
  Current analysis requirements
  Requirements already accepted
  Requirements under dispute

Adversarial state, if relevant:
  Adversary critique
  Specific gap assigned to this panelist
  Why the current research plan is insufficient

Literature state:
  Previously retrieved papers
  Previous retrieval intents
  Which intents were satisfied
  Which intents failed or were incomplete
  Evidence patterns already extracted
  Literature gaps remaining
```

The callback task must be narrow.

For more reasoning:

```text
Answer only this missing role-specific question.
Do not rewrite the full research plan.
Do not perform another panelist's role.
Return the new reasoning, any changed requirement, and whether this resolves the
assigned gap.
```

For more literature:

```text
Decide whether more literature is needed for the assigned gap.
If yes, use search_paper_wiki or retrieve_literature with a sharper retrieval intent.
Do not retrieve the same thing again unless the previous retrieval was inadequate.
Return the new evidence pattern, whether the gap is resolved, and any remaining
uncertainty.
```

Do not provide panelists with raw execution state by default:

```text
Do not send:
  tool plan
  implementation plan
  expected artifact paths
  package or dependency failures
  low-level feasibility details
```

Reason:

```text
Panelists should reason from the scientific requirement, not rationalize the
current implementation plan.
```

If tool feedback exposes a scientific or computational-strategy gap, the Mediator
should translate it into a role-appropriate question before sending it to a panelist.

Example:

```text
Do not send:
  The decoupler package is missing.

Send:
  The current plan requires TF activity inference, but the available execution
  path may not support that exact method. Is TF activity required for the
  scientific claim, or would motif enrichment plus target expression be sufficient
  evidence?
```

## Fix 9: Adversarial Review Should Attack The Right Targets

AdversarialPanelist should review the reasoning decisions, not only the final plan.

Targets:

```text
Hypothesis / analysis claim:
  Is the statement concrete enough to be wrong?
  Does it name entities, comparison, context, and evidence standard?

Literature verdict:
  Did the panel miss obvious prior work?
  Is answered_well / partially_answered / not_answered defensible?

Existing solution path:
  Did the plan identify the strongest prior evidence or analysis path?
  Did it reconstruct how prior work made the claim credible?

Extension or de novo path:
  Is the extension actually tied to the user's dataset and question?
  If de novo work is proposed, is the baseline still included?
  Is the new method or new analysis justified by a real gap?

Statistical validity:
  Are the comparison, statistical unit, effect metric, covariates, and robustness
  checks appropriate?

Executable alignment:
  Does the tool/implementation plan actually produce the evidence required by
  the research plan?
  Does it only run a method, or does it analyze the outputs enough to answer the
  user's question?
```

The adversary should not reject a plan merely because a biological conclusion is
already known.

The adversary should challenge a plan when:

```text
the evidence pattern is wrong
the analysis cannot answer the claim
the statistical unit is invalid
the method does not produce the needed evidence
required controls or validation are missing
the plan repeats known work without a useful dataset angle, method angle,
or extension
the de novo component lacks an existing baseline
```

## Fix 10: AnalyzerPanel Must Inform Plan Changes After Execution

The research plan is a phase plan, not a permanent plan.

After execution, AnalyzerPanel should evaluate the results against the accepted
research plan and evidence requirements.

AnalyzerPanel should report whether the executed outputs:

```text
support the current hypothesis or analysis claim
fail to support it
contradict prior expectations
are technically invalid
are insufficient to answer the question
reveal a confounder
suggest a stronger next question
justify extension or de novo work
```

AnalyzerPanel does not own the research-plan decision. It says what happened.
The Mediator / PhaseOrchestrator decides what the research plan should do next.

If outputs are insufficient, the system should not force a conclusion.

Post-analysis flow:

```text
Execution phase N
  -> AnalyzerPanel
      reports what happened
  -> Mediator / PhaseOrchestrator
      chooses one action:
        conclude
        ask_user_clarification
        request_tool_plan_revision
        revise_research_plan_directly
        ask_panelist_callback
        start_panel_update_round
        declare_unanswerable
        produce_next_phase_research_plan
```

ToolConsultant is responsible for tool and implementation plan revisions only
after the Mediator has changed or confirmed the research plan.

If Mediator routes an issue, use this ownership split:

```text
biological interpretation gap -> BiologistPanelist
validity or confounding issue -> StatisticianPanelist
workflow or output issue -> BioinformaticianPanelist or ToolConsultant
synthesis issue -> Mediator
```

Targeted panelist callback:

```text
Use when the current research direction is mostly still valid but one role-specific
gap needs a narrow answer.

max_callback_rounds_after_analysis = 2
max_callbacks_per_round = 3
max_callbacks_per_panelist_per_round = 1
```

Full panel update round:

```text
Use when AnalyzerPanel results may change the working model or next phase direction
broadly. ScientistPanel.update may internally run up to 3 reasoning rounds, but
the orchestrator can invoke full update at most once per execution phase.
```

If results are surprising or contradictory, the next phase should not simply rerun
the same plan. The panel should decide whether to:

```text
confirm the result
test an alternative explanation
retrieve additional literature
add validation
extend the analysis
pivot to a more informative question
propose a method adaptation or new method
```

## Fix 11: Research Phases Should Be Incremental By Default

Execution phases should evolve incrementally.

Rule:

```text
Reuse every valid upstream artifact whose inputs, parameters, code, dependencies,
and assumptions have not changed.
Rerun only the affected step and downstream dependents.
```

Use this ownership split:

```text
AnalyzerPanel:
  reports what happened in the results:
    supported
    contradicted
    inconclusive
    invalid
    missing_outputs

Mediator / PhaseOrchestrator:
  classifies what the plan should do next:
```

```text
interpretation_only:
  No rerun. Update final answer or working model.

new_downstream_analysis:
  Reuse upstream artifacts. Run only the new downstream analysis.

parameter_change:
  Rerun the affected step and downstream dependents.

upstream_preprocessing_change:
  Rerun from that preprocessing step onward.

method_replacement:
  Rerun replaced method and downstream dependents.

data_change:
  Rerun all steps that consume the changed data.
```

Only rerun everything when:

```text
raw input changed
QC/filtering changed in a way that changes the cell/gene set
normalization changed
feature selection changed
integration or embedding basis changed
cell labels used by downstream claims changed
prior artifacts are missing, stale, or untrusted
the previous artifact registry cannot validate needed artifacts
```

The next phase should produce a delta plan:

```text
reuse:
  valid upstream artifacts

rerun:
  changed steps and downstream dependents

add:
  new downstream analyses

do_not_rerun:
  steps whose inputs, params, code, and assumptions are unchanged
```

## Fix 12: Artifact Handles Are Required For Incremental Phases

The hard part of incremental execution is ensuring that the research plan, tool
plan, and generated code all refer to the same artifacts without inventing paths.

Do not let agents write raw paths when a logical artifact reference is possible.

Use artifact handles:

```text
artifact://phase_1.clustered_rna_h5ad
artifact://phase_1.multivelo_output
artifact://phase_1.t_cell_annotation
```

ArtifactRegistry owns real paths:

```json
{
  "artifact://phase_1.clustered_rna_h5ad": {
    "path": ".../path_000/04_rna_cluster_leiden/output.h5ad",
    "producer_step_id": "cluster_rna",
    "status": "valid",
    "sha256": "...",
    "phase_id": "phase_1",
    "run_id": "...",
    "reusable": true
  }
}
```

Plans should reference handles:

```json
{
  "inputs": {
    "rna_h5ad": "artifact://phase_1.clustered_rna_h5ad"
  }
}
```

Only the executor or dispatcher resolves handles to filesystem paths right before
execution.

Generated code should receive:

```text
Artifact handle:
  artifact://phase_1.clustered_rna_h5ad

Resolved local path:
  /real/path/to/output.h5ad
```

Coder prompt rule:

```text
Use only the resolved paths provided in RESOLVED_INPUTS.
Do not invent, guess, glob, or hardcode artifact paths.
```

The resolver must validate:

```text
handle exists
artifact status is valid or recomputable
path exists if status is valid
sha256 matches if available
producer step completed
artifact belongs to the expected phase/session or was explicitly marked reusable
artifact satisfies the expected modality and stage
```

## Fix 13: Use Selective Retention, Not Keep Everything

Incremental research phases need reusable checkpoints, but keeping every `.h5ad`
forever is too expensive.

Use retention tiers:

```text
required_checkpoint:
  Must keep. Needed for likely future phases or expensive upstream reuse.

final_output:
  Must keep. Used for final answer, visualization, or downstream continuation.

lightweight_summary:
  Keep. Tables, metrics, plots, metadata, manifests.

recomputable_intermediate:
  Can delete. Cheap to regenerate if needed.

ephemeral:
  Delete after run. Logs, scratch files, temporary outputs.
```

Each step output should declare retention intent:

```json
{
  "step_id": "rna_cluster",
  "outputs": {
    "clustered_h5ad": {
      "handle": "artifact://phase_1.clustered_rna_h5ad",
      "path": ".../output.h5ad",
      "retention": "required_checkpoint",
      "reason": "Needed for downstream differential abundance, annotation, and marker analysis."
    }
  }
}
```

Even if an intermediate artifact is deleted, keep its provenance:

```json
{
  "handle": "artifact://phase_1.pca_rna_h5ad",
  "path": ".../02_pca/output.h5ad",
  "status": "deleted_recomputable",
  "producer_step_id": "rna_pca",
  "inputs": [],
  "params": {},
  "can_recompute": true
}
```

Then if a later phase needs it:

```text
ArtifactResolver sees status = deleted_recomputable.
It recomputes from the nearest available checkpoint.
It restores the handle.
```

Current implementation note:

```text
The current DagExecutor defaults to keep_intermediates = false.
It may delete intermediate h5ad files while leaving paths in dag_result metadata.
This is not sufficient for safe incremental research phases.
```

## Fix 14: Dependency Preflight Belongs Before Execution

Before running a DAG, each selected tool path should declare and check its required
dependencies.

If dependencies are missing:

```text
Do not start partial execution.
Ask the user whether to install missing dependencies into the configured environment.
Install only after user approval.
Rerun preflight after installation.
Begin execution only after preflight passes.
```

This prevents avoidable failures like missing `skimage` for scrublet auto-thresholding
or missing `decoupler` for TF activity inference.

Fallbacks are not the primary solution for missing required dependencies. Fallbacks
are only appropriate when they are scientifically valid alternative methods.

## Fix 15: Expected Research Plan Shape

The Mediator's final research plan should include:

```text
concrete_analysis_claim:
  What the analysis is trying to establish.

literature_verdict:
  answered_well | partially_answered | not_answered

existing_solution_path:
  Established evidence or analysis path from literature.

existing_solution_plan:
  How to reproduce or apply that path on the user's data.

extension_or_de_novo_plan:
  What, if anything, is built on top of the existing solution.

novelty_level:
  Level 0 to Level 5.

why_extension_is_justified:
  What the user's question or dataset requires beyond the existing solution.

baseline_requirement:
  Existing method or evidence path that must still be run.

validation_requirements:
  What would make the result credible.

success_criteria:
  What result would support, weaken, contradict, or fail to answer the claim.

phase_update_policy:
  How AnalyzerPanel results should decide conclude / extend / pivot / rerun.
```

## Fix 16: Expected Research Behavior

A good discovery run should feel like this:

```text
The panel first identifies what exact claim is being tested.
It retrieves literature for targeted evidence needs.
It reconstructs the strongest existing solution path.
It decides whether prior work answered the question, partially answered it, or left it open.
It plans the existing solution first.
It adds extension or de novo components only when justified.
It sends clear requirements to ToolConsultant.
It checks that the executable plan produces the required evidence.
It executes.
It analyzes results against the original evidence requirements.
It evolves the next phase incrementally, reusing valid artifacts where possible.
```

Bad behavior:

```text
Jumping directly from user query to tools.
Calling literature retrieval with only the raw user query.
Summarizing papers without extracting evidence patterns.
Declaring a plan unsalvageable only because a biological question is known.
Inventing a new method before identifying the strongest existing baseline.
Running a method without analyzing its outputs enough to answer the question.
Rerunning the whole pipeline when only a downstream analysis changed.
Using raw stale artifact paths from previous runs.
Passing package errors directly to panelists as if they were scientific evidence.
```

## Priority Order

Suggested order for future implementation:

```text
1. Add existing-solution-first guideline to panelist shared prompts.
2. Add concrete_analysis_claim and literature_verdict to Mediator output.
3. Add the three research cases and novelty ladder to Mediator reasoning.
4. Add the three panelist literature tools and canonical paper summary schema.
5. Add Mediator callback context packets for panelist refinement.
6. Add adversarial checks for hypothesis, literature verdict, path choice, and tool alignment.
7. Add AnalyzerPanel phase-update decisions.
8. Add conservative incremental research MVP.
9. Add ArtifactRegistry handles and resolver.
10. Add full delta-plan support for incremental research phases.
11. Add selective checkpoint retention and recomputable artifact provenance.
12. Add dependency preflight before DAG execution.
```
