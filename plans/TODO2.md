# TODO2: RAG and Paper Retrieval Redesign

## Goal

The RAG system should support scientist-style reasoning, not just broad paper search.

The desired behavior is:

```text
Panelists reason about what literature they need.
Panelists first inspect existing paper wiki memory.
Panelists retrieve fresh papers only when wiki memory is insufficient.
PaperJudge labels each paper's usefulness for the explicit retrieval intent.
Panelists read the judged papers and decide whether they have enough information.
Useful papers are persisted to the paper wiki for future sessions.
```

Core principle:

```text
Retrieval is part of panelist reasoning, not a preprocessing step.
```

## Current Behavior To Refine

Current fresh retrieval path:

```text
Panelist calls retrieve_literature(base_query, background, top_k)
  -> LiteratureRetriever
  -> Semantic Scholar / OpenAlex
  -> runtime vector index
  -> LLM summaries
  -> PaperJudge
  -> useful papers optionally written to paper wiki
```

Current accumulated memory path:

```text
paper wiki
  -> traverse_paper_wiki(task_id)
  -> get_related_papers(paper_id)
```

Target accumulated memory path:

```text
paper wiki
  -> query_paper_wiki(
       user_question,
       data_summary,
       role,
       retrieval_goal,
       retrieval_intent,
       top_k
     )
  -> structured paper wiki entries
```

Target behavior:

```text
1. Panelist reads related paper wiki entries.
2. Panelist identifies what is already known and what is missing.
3. Panelist writes a retrieval intent only if wiki memory is insufficient.
4. Fresh retrieval fetches and enriches candidate papers.
5. PaperJudge judges each paper against the retrieval intent.
6. Panelist reasons over the retrieved papers and PaperJudge feedback.
7. Panelist decides whether enough information has been fetched.
8. Useful papers are persisted to the paper wiki.
9. Satisfied retrieval evidence is logged to short-term memory.
```

## Fix 1: Add Explicit Retrieval Intent

The panelist should not call `retrieve_literature` with a generic version of the user query.

Before retrieval, the panelist must reason:

```text
What kind of paper do I need, and what question should this paper help me answer?
```

Update the tool contract from:

```python
retrieve_literature(
    base_query=...,
    background=...,
    top_k=...
)
```

to:

```python
retrieve_literature(
    retrieval_intent=...,
    retrieval_goal=...,
    base_query=...,
    background=...,
    top_k=...
)
```

Definitions:

```text
retrieval_intent:
  The specific question the panelist needs literature to answer.

retrieval_goal:
  The reason for retrieval. One of:
    - method_selection
    - evidence_pattern
    - prior_findings
    - contradiction
    - validation
    - extension_opportunity

base_query:
  Search phrase generated from the retrieval intent.

background:
  User question + data summary + why this retrieval intent matters.

top_k:
  Maximum papers to return after ranking and judging.
```

Strong rule:

```text
Panelists retrieve for explicit reasoning needs, not for the user query verbatim.
```

## Fix 2: Use Three Distinct Panelist Agents

The three panelists must be three distinct agents backed by separate LLM calls:

```text
BiologistPanelist
StatisticianPanelist
BioinformaticianPanelist
```

They should not be simulated as one LLM writing three perspectives in a single response.

Reason:

```text
Role separation is part of the system design, not just a prompt style.
```

Each panelist may retrieve multiple times, but every retrieval must stay within that panelist's role boundary.

Strong rule:

```text
A panelist can retrieve repeatedly, but it cannot change hats.
```

The Biologist may refine biological retrievals.

The Statistician may refine statistical retrievals.

The Bioinformatician may refine computational and methodological retrievals.

If a retrieval exposes a need outside the panelist's role, the panelist should flag it for the relevant panelist or the Reconciler. It should not perform that other role's work.

Each panelist output should include a structured cross-role handoff field:

```json
{
  "role": "biologist",
  "retrieval_intents": [],
  "cross_role_flags": [
    {
      "needed_role": "statistician",
      "reason": "Need donor-level differential abundance evidence pattern."
    }
  ]
}
```

Strong rule:

```text
If the needed reasoning belongs to another role, do not perform it.
Flag it as a cross_role_flag for the Mediator or Reconciler.
```

At this stage, do not add a separate role-boundary LLM call. Role boundaries should be enforced through panelist prompts, structured output, and testing with adversarial examples.

## Fix 3: Retrieval Budget

Retrieval must be bounded. A full discovery session should not allow unbounded external API calls or unbounded LLM judging.

Default retrieval budget:

```text
max_retrieval_intents_per_panelist: 3
max_retries_per_intent: 2
max_total_retrieval_calls_per_panelist: 6
```

The panelist can spend this budget across role-specific intents. It should stop early when it has enough information.

If the budget is exhausted, the panelist must state:

```text
what was retrieved
what remains unresolved
which role, if any, should follow up
```

## Fix 4: Role-Bounded Retrieval Intents

The panelists should have complementary retrieval intents. They should not all retrieve the same generic user query.

### BiologistPanelist

The Biologist should reason about biological findings, biological background, entity definitions, cell states, tissue/disease context, marker genes, pathways, and biological interpretation.

Biologist retrieval intents may include:

```text
1. How have the relevant cells, subtypes, states, or programs been biologically defined?
2. What prior biological findings are known in this disease, tissue, organism, or modality?
3. Which cell states or biological mechanisms are implicated?
4. What biological extension would make the current dataset useful beyond confirming a known result?
5. What marker genes, pathways, cell-state signatures, or biological validations are relevant?
```

The Biologist should not retrieve for statistical model selection or computational tool benchmarking.

### StatisticianPanelist

The Statistician should reason about design validity, statistical unit, inference, confounding, robustness, and failure modes.

Statistician retrieval intents may include:

```text
1. What comparison design supports the claim?
2. What is the correct statistical unit: cell, sample, donor, patient, pseudobulk, mixed model?
3. What covariates or confounders must be controlled?
4. What compositional, pseudoreplication, batch, or sample-size pitfalls apply?
5. What robustness or sensitivity analyses are expected?
```

The Statistician should not retrieve for biological cell-state interpretation unless it is needed to evaluate statistical validity.

### BioinformaticianPanelist

The Bioinformatician should reason about tools, workflows, computational methods, implementation constraints, modality-specific analysis, and benchmarking.

Bioinformatician retrieval intents may include:

```text
1. What tools or workflows are appropriate for this analysis?
2. What annotation, integration, differential abundance, differential expression, trajectory, motif, or GRN methods are suitable?
3. What computational benchmarks or failure modes are relevant?
4. What preprocessing or modality-specific requirements must be satisfied?
5. What downstream analyses can operationalize the biological question?
```

The Bioinformatician should not take over biological interpretation or statistical inference design beyond computational feasibility and method choice.

## Fix 5: Wiki First, Then Fresh Retrieval

The panelist should first inspect existing paper wiki memory before issuing fresh retrieval.

Flow:

```text
1. Panelist identifies a role-specific literature need.
2. Panelist calls query_paper_wiki with role, retrieval_goal, and retrieval_intent.
3. Panelist reads existing paper summaries.
4. Panelist decides whether the wiki contains enough information.
5. If not enough, panelist writes a fresh retrieval_intent and calls retrieve_literature.
```

The wiki query should be scoped. The panelist should not traverse the entire paper wiki.

Recommended contract:

```python
query_paper_wiki(
    user_question=...,
    data_summary=...,
    role="biologist | statistician | bioinformatician",
    retrieval_goal=...,
    retrieval_intent=...,
    top_k=...
)
```

Default limits:

```text
default top_k: 5
max top_k: 10
```

The wiki query should return structured entries, not only titles:

```text
title
source ids / DOI / URL
full_text_status
retrieval_goal(s)
retrieval_intent(s)
question answered
methods used
key findings
limitations
evidence patterns
what it extends or contradicts
```

The panelist decides wiki sufficiency by reasoning, not through a separate coverage judge.

The panelist should state:

```text
what the wiki already covered
what remained missing
why fresh retrieval is needed, if it is needed
```

Do not add a separate `WikiCoverageScorer` component at this stage.

## Fix 6: Panelist-Controlled Retrieval Refinement

There should be no hidden automatic retry loop inside `PaperJudge` or `retrieve_literature`.

The panelist owns the reasoning loop:

```text
panelist reasons
  -> identifies a role-specific retrieval intent
  -> retrieves papers
  -> reads PaperJudge feedback
  -> decides whether enough role-specific information is available
  -> if not, issues a sharper role-specific retrieval call
  -> continues reasoning
  -> retrieves again only when a new role-specific information need appears
```

PaperJudge provides feedback that helps the panelist decide whether to retrieve again.

But the panelist decides:

```text
retry retrieval
stop retrieval
switch to a different role-specific intent
flag a cross-role gap for Reconciler
```

Do not add a separate LLM call whose only job is retrieval coverage judging at this stage.

## Fix 7: Improve PaperJudge

Current PaperJudge behavior:

```text
paper-by-paper relevance filter
summary-only input
role-specific question based on role + base_query
```

Target PaperJudge behavior:

```text
paper-by-paper relevance and evidence-fit assessor
input includes retrieval_intent and retrieval_goal
output explains what the paper contributes and what is missing
```

PaperJudge should judge one paper at a time. It should not do cross-paper synthesis.

Reason:

```text
Paper-level judgment answers:
  Is this paper useful for this retrieval intent?

Panelist reasoning answers:
  Did I retrieve enough information, or do I need another retrieval?
```

PaperJudge should receive:

```text
role
retrieval_goal
retrieval_intent
base_query
paper fields:
  - title
  - objective
  - background
  - analysis
  - main_findings
  - limitations
  - doc_id
  - url
  - published
  - source
  - abstract
  - full_text_status, when available
```

Do not include a judge-mode field unless multiple concrete judge modes are actually implemented.

PaperJudge should not expose hidden chain-of-thought. Its prompt should require it to reason internally and return only structured JSON.

If:

```text
full_text_status == "abstract_only"
```

then detailed evidence claims must be limited. Confidence should be capped unless the retrieval intent can genuinely be satisfied from the abstract.

Default confidence cap:

```text
abstract_only_max_confidence: 0.70
```

Exception:

```text
retrieval_goal == "prior_findings"
```

For evidence-pattern, validation, statistical-unit, covariate, or exact-method claims, abstract-only papers should normally be treated as incomplete evidence.

PaperJudge should return per paper:

```json
{
  "relevant": true,
  "confidence": 0.84,
  "reason": "This paper directly addresses the retrieval intent.",
  "evidence_contribution": "Defines T cells using CD3D/CD3E/TRAC and compares disease vs control abundance.",
  "covered_evidence_patterns": ["entity_definition", "comparison_design"],
  "missing_evidence": [
    "No donor-level mixed model",
    "No independent validation cohort"
  ],
  "suggested_query_terms": [
    "patient-level differential abundance",
    "compositional analysis",
    "mixed effects model"
  ],
  "suggested_exclusions": [
    "TCR repertoire only",
    "activation marker only"
  ]
}
```

`covered_evidence_patterns` must be a subset of the evidence-pattern field names defined in Fix 12.

Valid values:

```text
entity_definition
comparison_design
statistical_unit
effect_metric
controls_covariates
validation
boundary_conditions
```

Do not include:

```text
claim_supported
analysis_used
```

Reason:

```text
claim_supported is the conclusion.
analysis_used is a higher-level workflow summary.
covered_evidence_patterns should mark which evidence dimensions this paper helps fill.
```

PaperJudge should not directly mutate the query and should not decide whether retrieval is complete.

## Fix 8: Full-Text Retrieval Policy

Fresh paper retrieval should use broad metadata sources for candidate discovery:

```text
PubMed / Entrez
Semantic Scholar
OpenAlex
bioRxiv / medRxiv
```

Clarification:

```text
PubMed and PMC are part of the same NCBI database family but serve different roles.

PubMed / Entrez:
  metadata and abstract search over biomedical literature.

PMC / PubMed Central:
  open-access full-text archive, used for XML full-text enrichment.
```

PubMed should be included as a metadata source because it can recover biomedical papers that Semantic Scholar or OpenAlex miss, and because it provides the PMID needed to resolve PMC full text.

For each candidate, try full-text enrichment in this order:

```text
1. PMC XML by PMID/PMCID
2. bioRxiv / medRxiv JATS XML
3. open-access PDF URL from Semantic Scholar / OpenAlex
4. abstract-only fallback
```

PDF parsing policy:

```text
PMC XML and preprint JATS are preferred because they preserve section structure.
Open-access PDFs are lower-quality fallback full text.
PDF parsing is in scope, but evidence extracted from PDFs should carry lower confidence
than evidence extracted from structured XML/JATS unless section recovery is clean.
```

Preferred implementation options:

```text
Primary PDF parser: PyMuPDF / fitz
Optional higher-quality parser: marker or GROBID, if later introduced as a service
Fallback parser: pdfplumber
```

PDF parsing must record:

```text
pdf_url
pdf_parser
section_recovery_status:
  - structured_sections
  - headings_detected
  - plain_text_only
  - failed
```

Do not treat a PDF URL as full text until the PDF has been downloaded, parsed, and text extraction has succeeded.

Every paper should carry:

```text
full_text_status:
  - pmc_xml
  - preprint_jats
  - open_pdf
  - abstract_only
```

Policy:

```text
Abstracts can suggest relevance.
Full text is required for evidence-pattern extraction.
```

For adversary, statistician, bioinformatician, and analyzer/literature-grounder reasoning, prefer papers where:

```text
full_text_status != "abstract_only"
```

## Fix 9: Deduplicate Inside `retrieve_literature`

Deduplication must happen inside `retrieve_literature` after merging wiki papers and fresh retrieval results, before returning papers to the panelist.

Reason:

```text
The panelist should receive a clean paper set.
Duplicate papers should not appear multiple times in the same reasoning context.
```

Deduplicate by:

```text
DOI
PMID
PMCID
Semantic Scholar paper ID
OpenAlex work ID
normalized title
```

Deduplicate again on paper wiki write for safety.

Merge priority:

```text
1. Prefer full-text records over abstract-only records.
2. Prefer existing wiki records if they already contain structured evidence patterns.
3. Preserve all source IDs from duplicate records.
4. Preserve all retrieval_intents that the paper supported.
```

## Fix 10: Preserve Useful Papers In Paper Wiki

Every paper that passes PaperJudge with sufficient confidence should be persisted to the paper wiki with structured fields.

Persistence threshold:

```text
relevant == true
confidence >= 0.75
```

For `abstract_only` papers:

```text
Persist only if confidence >= 0.75 after applying the abstract-only confidence cap,
or if the paper is a key anchor for prior_findings and no full-text alternative is available.
```

Never persist a paper only because it was retrieved. It must pass PaperJudge for at least one explicit retrieval intent.

The paper wiki entry should include:

```text
title
source ids / DOI / URL
full_text_status
tasks it supports
retrieval_goal(s) it supported
retrieval_intent(s) it helped answer
question answered
methods used
key findings
limitations
evidence pattern
what it extends or contradicts
```

The paper wiki should become cumulative memory:

```text
Fresh retrieval = discover what might be relevant now.
Paper wiki = remember what was already judged useful before.
```

## Fix 11: Log Satisfied Retrieval Evidence To Short-Term Memory

After the panelist decides that a retrieval intent is satisfied, automatically log the retrieval result into short-term memory.

The logging trigger should be orchestrator-owned, not panelist-owned.

Mechanism:

```text
1. Panelist returns structured output with panelist_assessment.
2. Orchestrator checks panelist_assessment.enough_information.
3. If enough_information == true, orchestrator writes retrieval_evidence to short-term memory.
4. The panelist should not be responsible for remembering to call a logging tool.
```

Log:

```json
{
  "event_type": "retrieval_evidence",
  "role": "biologist | statistician | bioinformatician | adversary | analyzer",
  "retrieval_goal": "...",
  "retrieval_intent": "...",
  "base_query": "...",
  "papers": [
    {
      "doc_id": "...",
      "title": "...",
      "url": "...",
      "source": "...",
      "full_text_status": "...",
      "confidence": 0.84,
      "evidence_contribution": "..."
    }
  ],
  "panelist_assessment": {
    "enough_information": true,
    "what_was_learned": "...",
    "remaining_gap": "",
    "next_retrieval_intent": null
  }
}
```

This lets downstream components inspect what was retrieved and why without re-reading the entire panelist reasoning chain.

Consumers:

```text
AttributingCritic
ShortTermMemory
ContextManager
AdversarialPanelist
AnalyzerPanel
ScientistPanel.update
```

The short-term memory trace should preserve:

```text
which retrieval intents were satisfied
which papers supported them
which gaps remained
which role produced the evidence
```

## Fix 12: Evidence Patterns

Evidence patterns describe how prior papers supported a claim.

They answer:

```text
How did the paper make this claim credible?
```

Evidence pattern fields:

```text
claim_supported:
  The exact claim the paper supports.
  Example: "CD8 cytotoxic T cells are expanded in disease PBMC."

entity_definition:
  How the biological object was defined.
  Example: T cells defined by CD3D/CD3E/TRAC, reference labels, CellTypist, manual annotation.

comparison_design:
  What groups or conditions were compared.
  Example: disease vs healthy, responder vs non-responder, treated vs untreated.

statistical_unit:
  What unit supported inference.
  Example: cells, samples, donors, patients, pseudobulk, mixed model random effect.

effect_metric:
  What quantity measured the claim.
  Example: cell fraction, absolute abundance, cluster proportion, DA score, expression shift,
  accessibility shift, pathway score, regulatory activity.

controls_covariates:
  What confounders or covariates were handled.
  Example: batch, donor, tissue site, disease severity, treatment, sequencing depth,
  sample composition.

validation:
  What made the claim trustworthy.
  Example: marker sanity check, reference labels, independent cohort, flow cytometry,
  CITE-seq, ATAC, spatial data, robustness across resolutions.

boundary_conditions:
  When the evidence applies or fails.
  Example: PBMC only, requires donor labels, not valid without control group,
  only RNA-level evidence, no causal inference.

analysis_used:
  The actual analysis that produced the evidence.
  Example: reference annotation -> per-donor cell fractions -> disease/control comparison.
```

Panelists extract evidence patterns from useful papers.

## Fix 13: Plan Requirements

Plan requirements translate evidence patterns into obligations for the current analysis.

They answer:

```text
Given what prior papers showed, what must our plan include to test this properly?
```

Plan requirement fields:

```text
required_entity_definition:
  How the current plan must define the entity.
  Example: annotate T cells using markers and/or reference labels; verify CD3D/CD3E/TRAC.

required_comparison:
  What comparison the current plan must run.
  Example: disease vs healthy at sample/donor level.

required_statistical_unit:
  What inference unit the current plan must use.
  Example: donor-level or sample-level proportions, not individual cells as independent replicates.

required_metric:
  What effect metric the current plan must compute.
  Example: T cell fraction per sample, subtype proportion, differential abundance statistic.

required_covariates:
  What metadata should be controlled if available.
  Example: batch, donor, tissue site, treatment, severity.

required_validation:
  What sanity checks or validation the current plan must include.
  Example: marker expression dotplot, reference-label agreement, resolution sensitivity.

required_outputs:
  What concrete outputs the plan must produce.
  Example: UMAP with T cell labels, per-sample abundance table, disease/control test result,
  marker validation plot.

required_limitations:
  What the plan must not overclaim.
  Example: no causal claim from observational data; no patient-level inference without donor metadata.

extension_opportunity:
  What analysis could add value beyond re-testing a known claim.
  Example: subtype-specific expansion, exhaustion/cytotoxicity scoring, paired ATAC motif analysis.
```

Mediator owns the conversion from evidence patterns into plan requirements.

AdversarialPanelist checks whether the proposed plan satisfies those requirements.

Required ordering:

```text
1. Panelists inspect wiki and retrieve papers if needed.
2. PaperJudge judges papers one at a time.
3. Panelists extract evidence patterns from useful papers.
4. Mediator converts evidence patterns into plan requirements.
5. Mediator drafts the analysis plan.
6. AdversarialPanelist checks whether the plan satisfies the plan requirements.
7. If challenged, the plan is revised through the adversarial loop defined in TODO.md Fix 10.
```

Strong rule:

```text
The adversary should not run before plan requirements exist.
The adversary evaluates the plan against requirements, not against vague novelty.
```

Strong rule:

```text
Evidence patterns describe how prior papers supported a claim.
Plan requirements translate those patterns into obligations for the current analysis.
```

## Fix 14: Owner Responsibilities

Use this ownership split:

```text
Panelists:
  - read existing paper wiki entries
  - propose role-specific retrieval intents
  - retrieve fresh papers when needed
  - extract evidence patterns from useful papers
  - decide whether enough information was fetched
  - flag cross-role gaps without taking over another role

PaperJudge:
  - judge one paper at a time
  - assess relevance and evidence fit against retrieval_goal + retrieval_intent
  - explain evidence contribution and missing evidence
  - suggest query terms if the paper is partial or off-target

retrieve_literature:
  - fetch candidates
  - enrich full text when possible
  - merge wiki and fresh retrieval results
  - deduplicate before returning papers to the panelist
  - return judged papers to the panelist

Mediator:
  - synthesize panelist outputs
  - convert evidence patterns into plan requirements
  - produce a research plan that satisfies those requirements

AdversarialPanelist:
  - check whether the plan satisfies the plan requirements
  - reject invalid analysis, not familiar questions
  - redirect known findings into sharper required analyses

ShortTermMemory:
  - store satisfied retrieval evidence
  - preserve what was retrieved, why, and by which role
```

## Fix 15: Example

User question:

```text
Do T cells expand in this disease dataset?
```

Retrieval-side sketch:

```text
BiologistPanelist wiki check:
  Found prior papers showing broad T cell expansion.
  Missing: how T cells were defined and whether subtype/state expansion was tested.

BiologistPanelist retrieval:
  retrieval_goal: evidence_pattern
  retrieval_intent: How did prior studies define T cells and validate T cell expansion?
  base_query: T cell expansion disease PBMC CD3D CD3E TRAC single-cell

StatisticianPanelist wiki check:
  Found biological claims about T cell expansion.
  Missing: whether the evidence used donor-level or cell-level statistical units.

StatisticianPanelist retrieval:
  retrieval_goal: evidence_pattern
  retrieval_intent: What statistical unit and abundance model did prior studies use for cell-type expansion?
  base_query: single-cell differential abundance patient-level cell proportion mixed model

BioinformaticianPanelist wiki check:
  Found prior annotation claims.
  Missing: which tools can operationalize subtype abundance and marker validation in the current data.

BioinformaticianPanelist retrieval:
  retrieval_goal: method_selection
  retrieval_intent: What tools can test T cell subtype abundance and marker validation in scRNA-seq?
  base_query: scRNA-seq T cell annotation differential abundance CellTypist Milo scCODA
```

PaperJudge example:

```json
{
  "relevant": true,
  "confidence": 0.86,
  "reason": "The paper directly supports the retrieval intent by defining T cells and testing disease/control abundance.",
  "evidence_contribution": "Defines T cells using CD3D/CD3E/TRAC and compares per-patient abundance across disease and healthy samples.",
  "covered_evidence_patterns": [
    "entity_definition",
    "comparison_design",
    "statistical_unit",
    "effect_metric",
    "validation"
  ],
  "missing_evidence": [
    "Does not test T cell subtype-specific expansion.",
    "Does not include paired ATAC regulatory evidence."
  ],
  "suggested_query_terms": [
    "T cell subtype expansion",
    "paired scRNA scATAC PBMC",
    "disease T cell regulatory programs"
  ],
  "suggested_exclusions": [
    "bulk RNA-seq only",
    "TCR repertoire only"
  ]
}
```

Panelist assessment:

```json
{
  "enough_information": true,
  "what_was_learned": "Prior studies support broad T cell expansion using marker/reference annotation and patient-level abundance comparisons.",
  "remaining_gap": "The extension opportunity is subtype/state-specific expansion and RNA/ATAC regulatory support.",
  "next_retrieval_intent": null
}
```

Prior evidence pattern:

```text
claim_supported:
  T cells expand in disease PBMC.

entity_definition:
  T cells identified using CD3D/CD3E/TRAC and reference annotation.

comparison_design:
  disease vs healthy.

statistical_unit:
  patient-level cell fractions.

effect_metric:
  T cell proportion per patient.

controls_covariates:
  batch and treatment.

validation:
  marker expression and independent cohort.
```

Plan requirements:

```text
required_entity_definition:
  annotate T cells and verify CD3D/CD3E/TRAC expression.

required_comparison:
  compare disease vs healthy.

required_statistical_unit:
  aggregate cell fractions per donor/sample.

required_metric:
  test T cell proportion difference.

required_covariates:
  include batch/treatment if present.

required_validation:
  produce marker plot and sensitivity check.

required_limitations:
  do not claim causal expansion mechanism.

extension_opportunity:
  test which T cell subtype or state drives the expansion.
```

Bad adversary behavior:

```text
Prior papers already found T cell expansion.
Therefore the plan is unsalvageable.
```

Correct adversary behavior:

```text
Prior papers already found broad T cell expansion.
The plan must not merely re-prove this at cell level.
It should validate the known evidence pattern in the current dataset and then extend it:
which T cell subtype/state expands, whether expansion is sample-level, and whether RNA/ATAC
evidence supports a regulatory or activation mechanism.
```
