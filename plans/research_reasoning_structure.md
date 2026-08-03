# Research Reasoning Structure

This document describes the intended high-level structure of the research reasoning system. It is not an implementation plan. It defines the major agents, their responsibilities, and the reasoning flow between scientific reasoning, literature retrieval, mediation, adversarial review, and executable planning.

## Core Principle

The system separates four kinds of work:

```text
Scientific reasoning
Literature retrieval and canonical paper summarization
Requirement synthesis
Executable planning
```

Panelists should reason scientifically. They should not manage retrieval mechanics directly, and they should not decide the final executable tool plan.

Literature retrieval should be handled through a small panelist-facing tool surface:
`search_paper_wiki`, `retrieve_literature`, and `fetch_paper_content`.

Executable planning should be handled by ToolConsultant after scientific requirements have been formed.

## Top-Level Routing

```text
User query
  -> SessionRouter
      -> direct_response
      -> operational_task
      -> discovery_task
      -> clarification_required
```

### Operational Task

An operational task is known execution only.

Examples:

```text
Run CellTypist annotation.
Generate UMAP plots.
Run QC on this h5ad.
```

Operational tasks go directly to ToolConsultant.

```text
operational_task
  -> ToolConsultant
  -> dependency preflight
  -> DagExecutor / CoderAgent
  -> ResultSummarizer
```

### Discovery Task

A discovery task requires scientific reasoning.

Examples:

```text
Determine whether chromatin primes RNA expression.
Assess whether NK cells show a progenitor-to-effector trajectory.
Identify which TFs may drive the observed cell-state transition.
Test whether T cells expand in disease and whether the evidence is robust.
```

Discovery tasks go to ScientistPanel.

### Clarification Required

If the user request could reasonably mean either simple execution or scientific interpretation, the system should ask the user to choose between two concrete interpretations.

Example:

```text
I can interpret this in two ways:

1. Execution-only:
   Run MultiVelo and return computed outputs and plots.

2. Discovery analysis:
   Use MultiVelo outputs to evaluate whether chromatin accessibility leads,
   lags, or matches RNA expression dynamics.

Which one do you want?
```

The dispatcher should not silently upgrade, downgrade, or reinterpret ambiguous requests.

## ScientistPanel

The ScientistPanel is used for discovery tasks.

It contains three independent panelists:

```text
BiologistPanelist
StatisticianPanelist
BioinformaticianPanelist
```

These should be distinct reasoning agents, not one model pretending to hold three perspectives in a single response.

Each panelist owns a different reasoning domain.

## Panelist Responsibilities

### BiologistPanelist

The BiologistPanelist reasons about biological meaning.

It owns:

```text
cell types
cell states
marker genes
developmental trajectories
disease biology
tissue context
pathways
biological validation
known biological findings
biological novelty or extension
```

It answers:

```text
What biological claim is being evaluated?
What biological entities must be defined?
What prior biological knowledge matters?
What biological evidence would make the claim meaningful?
What biological validation is required?
```

It should not choose statistical tests or implementation details.

### StatisticianPanelist

The StatisticianPanelist reasons about validity of evidence.

It owns:

```text
comparison design
statistical unit
sample-level versus cell-level inference
pseudoreplication
batch effects
covariates
confounders
effect metrics
robustness checks
sensitivity analyses
minimum evidence requirements
```

It answers:

```text
What comparison is needed?
What is the correct unit of inference?
What would make the result statistically invalid?
What controls or covariates are required?
What robustness checks are needed?
```

It should not decide biological interpretation or implementation details, except where those details affect validity.

### BioinformaticianPanelist

The BioinformaticianPanelist reasons about computational strategy.

It owns:

```text
workflow structure
modality-specific analysis design
preprocessing requirements
integration strategy
trajectory or velocity strategy
GRN or motif strategy
data compatibility
required intermediate outputs
computational risks
```

It answers:

```text
What computational outputs are needed to support the claim?
What workflow structure can produce those outputs?
What data compatibility checks are required?
What computational failure modes matter?
```

It should not replace ToolConsultant. It defines computational requirements and expected outputs. ToolConsultant later maps those requirements to concrete tools, DAG steps, dependencies, and code.

## Panelist Literature Tools

Panelists should not receive a large set of overlapping paper-wiki tools.

Instead, each panelist receives three literature tools:

```text
search_paper_wiki
retrieve_literature
fetch_paper_content
```

The panelist owns the literature intent and the scientific use of the returned
summaries. The literature tools own retrieval mechanics, deduplication, canonical
summarization, wiki persistence, and full-content access.

### search_paper_wiki

Search accumulated paper memory and return canonical structured paper summaries.
The paper wiki should not contain duplicate papers, but this tool should still
deduplicate defensively before returning results.

### retrieve_literature

Fresh external retrieval only. The panelist provides:

```text
retrieval_intent
retrieval_goal
requirements
background
exclude_ids
```

Definitions:

```text
retrieval_intent:
  The specific question the panelist needs literature to answer.

retrieval_goal:
  Why the panelist needs the literature.
  Examples: prior_findings, evidence_pattern, method_selection,
  validation, contradiction, extension_opportunity.

requirements:
  What kind of paper or evidence would be useful.

background:
  User query, data summary, current reasoning state, and why this intent matters.

exclude_ids:
  Paper IDs, DOIs, PMIDs, PMCIDs, Semantic Scholar IDs, OpenAlex IDs, and normalized
  titles already known from wiki search or earlier retrieval in the same panelist loop.
```

The tool:

```text
fresh retrieval
deduplication
full-text enrichment when available
canonical paper summarization
paper wiki persistence
```

It returns canonical paper summaries, not a separate relevance judgment. There is
no default PaperJudge step in the panelist literature loop. The panelist reads the
summaries and incorporates useful evidence into its reasoning.

### fetch_paper_content

Fetch section-level or targeted full-text content from the vector database or
parsed paper store for either wiki papers or newly retrieved papers.

Use it when a paper summary is not enough and the panelist needs exact methods,
results, discussion, or targeted evidence.

### Canonical Paper Summary

All papers returned to panelists should use the same structure:

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

The panelist then decides whether to:

```text
continue reasoning
retrieve again with a sharper intent
fetch deeper content from a specific paper
flag another role
finish its role-specific output
```

## Evidence Patterns

The purpose of literature retrieval is not only to learn conclusions. It is to learn how prior conclusions were established.

For useful literature, the system extracts evidence patterns.

An evidence pattern includes:

```text
claim_supported
entity_definition
comparison_design
statistical_unit
effect_metric
controls_covariates
analysis_used
validation
boundary_conditions
```

Example:

```text
Prior paper conclusion:
  T cells expand in this disease.

Evidence pattern:
  T cells were defined by reference annotation and CD3D/CD3E/TRAC markers.
  Expansion was measured as T cell fraction per sample.
  Disease and control samples were compared at the donor level.
  Batch and donor effects were considered.
  Marker expression and an external reference were used for validation.
```

The system should use this evidence pattern to decide what the current analysis must include.

It should not reject the current analysis merely because the biological question is already known. Prior research is useful because it shows what evidence is required.

## Panelist Output

Each panelist outputs role-specific reasoning and requirements.

The output should include:

```text
role-specific findings
literature evidence used
evidence patterns extracted
analysis requirements from that role
open questions
cross-role flags
confidence
```

Cross-role flags are used when a panelist identifies a need outside its domain.

Example:

```text
BiologistPanelist:
  Need StatisticianPanelist to define whether expansion should be tested
  using donor-level fractions or a compositional model.
```

Panelists should not perform another role's work.

## Mediator

The Mediator reads the three panelist outputs and produces unified analysis requirements.

It converts:

```text
BiologistPanelist:
  what biological claim matters

StatisticianPanelist:
  what makes the evidence valid

BioinformaticianPanelist:
  what computational outputs are needed
```

into:

```text
analysis_requirements
```

The Mediator does not execute tools. It does not choose final package-level implementation.

Its output should state what the analysis must prove, measure, control, validate, and produce.

The Mediator is also the coordinator for refinement. It is not only a final
summarizer. If the current evidence is insufficient, the Mediator can route a
specific missing question back to the appropriate panelist.

Mediator options include:

```text
accept_current_plan
revise_mediated_requirements
ask_panelist_for_more_reasoning
ask_panelist_for_more_literature
ask_toolconsultant_for_revision
ask_user_for_clarification
declare_unanswerable_with_current_data
```

Callback budgets:

```text
max_mediator_callback_rounds = 3
max_callbacks_per_round = 3
max_callbacks_per_panelist_per_round = 1
max_callback_rounds_after_analysis = 2
```

When asking a panelist for more work, the Mediator must send a narrow,
gap-directed callback. The panelist should not restart the whole discussion.

Example:

```text
To evaluate chromatin priming with MultiVelo, the analysis must:

1. Run MultiVelo on matched RNA/ATAC cells.
2. Extract gene-wise accessibility and expression dynamics.
3. Quantify whether accessibility changes precede RNA changes along latent time.
4. Stratify the evidence by cell state.
5. Connect candidate TFs to motif accessibility and target gene expression.
6. Report cases as priming, lagging, lockstep, or unsupported.
7. Include sensitivity checks for cell-state ordering and data quality.
```

## Panelist Callback Context

Panelists are separate LLM calls. They do not retain memory unless the orchestrator
passes prior reasoning back to them.

Whenever the Mediator asks a panelist for more reasoning or more literature, the
panelist receives a structured context packet. This packet should provide enough
memory to avoid repetition, but it should not include the raw full transcript by
default.

Callback types:

```text
ask_panelist_for_more_reasoning
ask_panelist_for_more_literature
```

Callback source:

```text
mediator_gap
adversary_critique
analyzer_feedback
```

Callback context:

```text
Original task:
  - User query
  - Data summary
  - Method constraints, if any

Panelist state:
  - Panelist role
  - Panelist prior reasoning
  - Panelist prior conclusions
  - Panelist prior confidence
  - Panelist unresolved gaps

Cross-panel state:
  - Key findings established by other panelists
  - Cross-role flags involving this panelist
  - Conflicts already resolved by the Mediator
  - Conflicts still open and relevant to this callback
  - Dependencies between this panelist's answer and another role's requirement

Mediated state:
  - Current research plan
  - Current analysis requirements
  - Requirements already accepted
  - Requirements under dispute

Adversarial state, if relevant:
  - Adversary critique
  - Specific gap assigned to this panelist
  - Why the current research plan is insufficient

Literature state:
  - Previously retrieved papers
  - Previous retrieval intents
  - Which intents were satisfied
  - Which intents failed or were incomplete
  - Evidence patterns already extracted
  - Literature gaps remaining
```

The callback task must be narrow.

For more reasoning:

```text
Answer only this missing role-specific question.
Do not rewrite the full research plan.
Do not perform another panelist's role.
Return the new reasoning, any changed requirement, and whether this resolves the assigned gap.
```

For more literature:

```text
Decide whether more literature is needed for the assigned gap.
If yes, use search_paper_wiki, retrieve_literature, or fetch_paper_content with a sharper retrieval intent.
Do not retrieve the same thing again unless the previous retrieval was inadequate.
Return the new evidence pattern, whether the gap is resolved, and any remaining uncertainty.
```

Panelist callbacks should not include raw execution state:

```text
Do not provide the panelist with:
  - Tool plan
  - Implementation plan
  - Expected artifacts
  - Package or dependency failures
  - Low-level feasibility details
```

Reason:

```text
Panelists should reason from the scientific requirement, not rationalize the current implementation plan.
```

If tool feedback exposes a scientific or computational-strategy gap, the Mediator
should translate it into a role-appropriate question before sending it to a panelist.

Example:

```text
Do not send:
  "The decoupler package is missing."

Send:
  "The current plan requires TF activity inference, but the available execution
   path may not support that exact method. Is TF activity required for the
   scientific claim, or would motif enrichment plus target expression be
   sufficient evidence?"
```

## ToolConsultantSubagent

After the Mediator produces analysis requirements, ToolConsultant receives them.

ToolConsultant answers:

```text
Given these analysis requirements, what executable tools, DAG steps, or custom code are needed?
```

ToolConsultant owns:

```text
tool selection
DAG planning
custom code planning
input/output mapping
dependency awareness
implementation feasibility
expected artifacts
```

ToolConsultant should return:

```text
executable plan
tool plan
implementation plan
required dependencies
expected outputs
risks or infeasible requirements
```

ToolConsultant should not decide the scientific meaning of the task.

## AdversarialPanelist

The AdversarialPanelist reviews both the scientific requirements and the executable plan.

It checks:

```text
Does the scientific plan answer the user question?
Does the executable plan produce the evidence required by the scientific plan?
Are the statistical units valid?
Are required controls missing?
Are validation or sensitivity checks missing?
Does the tool plan only run a method without analyzing its outputs?
Does prior literature contradict or constrain the plan?
Is the plan redundant, invalid, or unable to support the claim?
```

The adversary should not reject a plan merely because a biological conclusion is already known.

The adversary should challenge a plan when:

```text
the evidence pattern is wrong
the analysis cannot answer the claim
the statistical unit is invalid
the method does not produce the needed evidence
required controls or validation are missing
the plan repeats known work without a distinct dataset angle, method angle, or extension
```

If the adversary challenges the plan, the critique is routed back to the owner:

```text
biological issue -> BiologistPanelist
statistical issue -> StatisticianPanelist
computational strategy issue -> BioinformaticianPanelist
tool or implementation issue -> ToolConsultant
synthesis issue -> Mediator
```

The loop continues until the plan is accepted, redirected, or declared unable to answer the request.

## Two Refinement Loops

Discovery uses two related but distinct loops.

### Loop 1: Scientific Reasoning Loop

Goal:

```text
Make the research plan scientifically coherent.
```

Flow:

```text
Panelists
  -> literature tools as needed
  -> role-specific reasoning and evidence patterns
Mediator
  -> draft research plan / analysis requirements
Mediator checks whether more evidence is needed
  -> ask_panelist_for_more_reasoning
  -> ask_panelist_for_more_literature
Mediator updates research plan
repeat until the scientific plan is coherent enough to send to ToolConsultant
```

In this loop, ToolConsultant is not yet the focus. The system is deciding what
evidence is required, not how to execute it.

### Loop 2: Execution-Feasibility Refinement Loop

Goal:

```text
Make the research plan executable without losing the science.
```

Flow:

```text
Mediator research plan / analysis requirements
  -> ToolConsultantSubagent
      -> tool plan + implementation plan
  -> AdversarialPanelist
      -> critique research plan + tool/implementation plan together
  -> Mediator
      -> route critique to the correct owner
```

The Mediator remains part of Loop 2 because the adversary may find mismatches
between the scientific requirements and the executable plan.

Examples:

```text
The tool plan runs MultiVelo but does not quantify chromatin-RNA lead-lag timing.
  -> Mediator routes to ToolConsultant for missing implementation steps.
  -> If the evidence requirement itself was underspecified, Mediator routes back
     to BioinformaticianPanelist or StatisticianPanelist.

The tool plan uses cell-level Wilcoxon for a donor-level abundance claim.
  -> Mediator routes to StatisticianPanelist for validity requirement revision
     and to ToolConsultant for executable plan revision.

The plan requires TF driver evidence but only produces motif enrichment.
  -> Mediator routes to BiologistPanelist or BioinformaticianPanelist if the
     scientific evidence requirement is unclear, then routes to ToolConsultant
     for implementation revision.
```

The adversary critiques. It does not own the rewrite. The Mediator decides which
owner must revise which part.

## Full Discovery Loop

```text
User query
  -> SessionRouter
  -> ScientistPanel
      -> BiologistPanelist
          -> literature tools as needed
      -> StatisticianPanelist
          -> literature tools as needed
      -> BioinformaticianPanelist
          -> literature tools as needed
  -> Mediator
      -> draft research plan / analysis requirements
      -> panelist callbacks if more evidence is needed
      -> unified research plan / analysis requirements
  -> ToolConsultantSubagent
      -> tool plan + implementation plan
  -> AdversarialPanelist
      -> review scientific requirements + executable plan
  -> Mediator
      -> route critique to panelists, ToolConsultant, itself, or user
  -> revisions if needed, with accepted context carried forward
  -> dependency preflight
  -> execution
  -> AnalyzerPanel
      -> reports what happened
  -> Mediator / PhaseOrchestrator
      -> conclude, ask user, revise research plan, ask targeted callbacks,
         start one full panel update round, request ToolConsultant revision,
         declare unanswerable, or produce next-phase research plan
```

## Final Responsibility Split

```text
Panelists:
  reason about the science.

Panelist literature tools:
  search wiki memory, retrieve fresh papers, deduplicate, summarize into canonical
  structure, persist to wiki, and fetch deeper content when requested.

Mediator:
  converts role-specific reasoning into unified analysis requirements.

ToolConsultant:
  converts analysis requirements into executable tools, DAGs, and code.

AdversarialPanelist:
  stress-tests both the scientific requirements and the executable plan.

AnalyzerPanel:
  interprets execution outputs against the accepted analysis requirements.
```
