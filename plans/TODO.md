# TODO: Routing, ResearchLoop, and Adversarial Reasoning Fixes

## Canonical Routing Contract

The system should be execution-first. It becomes a scientist only when the user asks a discovery question, or when an ambiguous request needs exploratory framing.

Target routing:

```text
SessionRouter
  -> direct_response

  -> operational task
      -> ToolConsultantAgent
      -> DagExecutor first
      -> CoderAgent only for missing custom pieces
      -> ResultSummarizer

  -> discovery task
      -> ResearchLoop
          -> ScientistPanel
          -> ToolConsultantAgent
          -> DagExecutor or CoderAgent
          -> AnalyzerPanel
          -> ScientistPanel.update
```

Canonical mode mapping:

```text
operational -> bypass ResearchLoop
discovery   -> ResearchLoop pipeline_mode="full"
ambiguous   -> ResearchLoop pipeline_mode="brief"
```

Operational requests must not enter ScientistPanel by default. Routine work such as QC, normalization, clustering, UMAP, annotation, DE, DA, batch correction, and other standard workflows should go directly to ToolConsultantAgent and DagExecutor.

## Fix 1: Wire ResearchLoop Into the Frontend

Current issue:

- `SessionDispatcher` supports a `research_loop` branch.
- The frontend constructs `SessionDispatcher` without passing a `ResearchLoop`.
- Therefore discovery routing exists in code but is not active in the normal frontend path.

TODO:

- Construct `ScientistPanel`, `AnalyzerPanel`, and `ResearchLoop` in `frontend/server.py`.
- Pass `research_loop=self.research_loop` into `SessionDispatcher`.
- Keep the normal operational path unchanged.

Expected result:

```text
discovery task -> ResearchLoop
operational task -> direct ToolConsultant/DAG execution
```

## Fix 2: Change Dispatcher Routing Semantics

Current issue:

```python
if intent_mode == "discovery" and self.research_loop is not None:
    payload = self._handle_research_task(...)
else:
    payload = self._handle_task(...)
```

Desired behavior:

```text
direct_response -> DeterministicResponder
operational task -> execute_task()
discovery task -> _handle_research_task(pipeline_mode="full")
ambiguous task -> _handle_research_task(pipeline_mode="brief")
```

Operational requests must bypass ResearchLoop. Ambiguous requests should not be forced into a full adversarial panel. Use `brief` unless the router has strong evidence that the user wants discovery.

## Fix 3: Make pipeline_mode Explicit

Current issue:

`_handle_research_task()` has a hidden mapping that includes:

```text
operational -> lightweight
```

That is misleading because operational requests should not normally enter ResearchLoop at all.

TODO:

- Remove operational-to-ResearchLoop routing from the main path.
- Make the research mapping explicit:

```text
discovery -> full
ambiguous -> brief
```

- Keep `skip_panel` as a valid internal `ScientistPanel.formulate()` mode, but do not use it as the normal operational path.

## Fix 4: Strengthen SessionRouter Prompt

The router should classify user intent by the kind of work requested, not by whether the subject matter is biological.

Definitions:

```text
operational:
  The user wants a known workflow executed.
  The request has a procedural endpoint.
  No hypothesis formation or literature-grounded reasoning is required.

discovery:
  The user wants to answer an open-ended biological, mechanistic, or methodological question.
  The request requires hypothesis formation, literature grounding, iterative interpretation,
  or deciding what analysis would be scientifically informative.

ambiguous:
  The message does not clearly distinguish operational execution from discovery reasoning.
```

Strong rule to add:

```text
Do not classify a routine analysis request as discovery merely because it is biological.
```

Examples:

```text
"Run cell type annotation" -> operational
"Cluster this dataset and make a UMAP" -> operational
"Find what cell state drives disease severity" -> discovery
"What mechanism explains treatment resistance?" -> discovery
"Analyze this dataset" -> ambiguous
"Find interesting biology" -> ambiguous or discovery depending on context
```

## Fix 5: Keep ToolConsultant DAG-First

Preserve this rule:

```text
standard analysis -> dag_plan
custom missing piece -> implementation_plan
literature/method design only -> research_brief
```

ToolConsultant should not overuse code generation or research mode. If a request can be expressed as documented tool stages, it should produce a DAG plan.

CoderAgent should be used for custom analysis, custom plots, special post-processing, or gaps in the existing tool system.

## Fix 6: Clarify Research Executors

Current issue:

There are two meanings of "research" in the codebase:

```text
ResearchLoop = ScientistPanel/adversary/analyzer loop
SubprocessResearchExecutor = legacy default.py subprocess pipeline
```

TODO:

- Rename `SubprocessResearchExecutor` conceptually to `LegacyResearchPipelineExecutor`, or clearly document it as legacy.
- Keep it out of the main routing story unless there is a deliberate compatibility reason.
- Avoid using "research" to mean both literature/panel reasoning and legacy subprocess execution.

## Fix 7: Use CoderAgent as the Only Coder in the Routing Design

For now, ignore `OptimizingCoderAgent` in the main architecture.

Current policy:

```text
standard workflow -> DagExecutor
custom missing piece -> CoderAgent
```

This keeps the routing design simple and aligned with the currently active frontend path. Expensive multi-stage optimization should not be part of the routing contract until it is deliberately revived, tested, and wired as a first-class component.

## Fix 8: Expose Route Metadata in Frontend Results

Frontend responses should make orchestration visible.

Expose:

```text
route
intent_mode
execution_path
pipeline_mode, if applicable
```

This lets the user see whether the system chose operational execution, direct response, brief research, or full discovery reasoning.

## Fix 9: Add Dispatcher Tests

Add tests for the routing contract:

- `direct_response` calls the deterministic responder and does not call ToolConsultant or ResearchLoop.
- `operational` routes to ToolConsultant/DagExecutor and does not call ResearchLoop.
- `discovery` routes to ResearchLoop with `pipeline_mode="full"`.
- `ambiguous` routes to ResearchLoop with `pipeline_mode="brief"` when ResearchLoop is configured.
- If ResearchLoop is not configured, discovery should fail explicitly or fall back in a documented way, not silently behave like a normal operational task.

## Fix 10: Redefine the Adversary's Job

The adversary should not function as novelty police.

It should function as:

```text
1. validity reviewer
2. methodological reviewer
3. literature-grounded opportunity finder
```

Prior research is methodological evidence, not only novelty evidence.

The adversary should use papers to answer:

```text
What analysis did successful prior studies use for this kind of question?
What data modality did they rely on?
What covariates or controls mattered?
What comparison design was valid?
What tools are standard or trusted for this disease/context/modality?
What failure modes did prior papers warn about?
What analysis gap remains open?
```

## Fix 11: Redefine `unsalvageable`

`unsalvageable` is not a novelty verdict. It is a validity verdict.

A plan is not unsalvageable because the biological question is familiar or because prior papers reached a similar conclusion.

Prior research should be used to:

- prevent wasted re-derivation,
- identify required evidence,
- choose better tools and methods,
- identify missing controls,
- sharpen the analysis question,
- and suggest analyses that previous studies did not cover.

Use `unsalvageable` only when the plan is wrong, impossible, invalid, or unable to answer the user's query.

Examples:

```text
Unsalvageable:
  The plan cannot answer the user's question.
  The required data or metadata are absent.
  The method is inappropriate for the modality.
  The statistical comparison is invalid.
  The plan makes causal claims from observational data without a valid design.
  The plan is internally contradictory.
  The plan is entirely redundant in both question and analysis strategy, with no meaningful refinement available.

Needs revision:
  Prior work found the broad conclusion, but the current dataset can validate it correctly.
  Prior work found the broad conclusion, but the current plan should test a sharper subtype/state/mechanism.
  Prior work suggests a better method, control, covariate, or statistical unit.
  The plan is directionally useful but missing required evidence or validation.
```

Strong rule:

```text
Known question is not unsalvageable.
Redundant or invalid analysis is.
```

## Fix 12: Convert Prior Conclusions Into Analysis Requirements

When prior research contains a relevant conclusion, the system must extract the evidence pattern behind that conclusion.

It should not only ask whether the conclusion is known. It must ask how the conclusion was established, what analysis made it credible, and which parts of that evidence pattern are required for the current dataset.

For example:

```text
User question:
Do T cells expand in this disease dataset?

Prior papers:
T cell expansion has already been reported in this disease context.
```

Bad adversary behavior:

```text
Prior papers already found T cell expansion.
Therefore the plan is unsalvageable.
```

Correct adversary behavior:

```text
Prior papers already found T cell expansion.
How did they establish it?
What analysis is required to test that claim in this user's dataset?
What additional analysis could go beyond simple confirmation?
```

Required evidence-pattern extraction:

### 1. Entity Definition

How did prior studies define the biological entity?

Examples:

- marker genes
- reference annotation
- CellTypist / SingleR / Azimuth
- manual annotation
- protein markers
- modality-specific evidence

For T cells specifically:

- CD3D
- CD3E
- TRAC
- CD4
- CD8A
- other canonical T cell markers

### 2. Comparison Design

What groups or conditions were compared?

Examples:

- disease vs healthy
- responder vs non-responder
- early vs late stage
- treated vs untreated
- tissue site A vs tissue site B
- patient-level groups

### 3. Statistical Unit

What was treated as the unit of inference?

Examples:

- individual cells
- clusters
- samples
- patients
- pseudobulk aggregates
- mixed model with patient as random effect

The adversary should flag invalid pseudoreplication, especially plans that treat cells as independent when the biological question requires sample- or patient-level inference.

### 4. Effect Metric

What quantity supported the claim?

Examples:

- T cell fraction per sample
- absolute abundance, if available
- cluster proportion
- differential abundance model
- compositional test
- expression shift
- accessibility shift
- pathway score
- regulatory activity

### 5. Controls and Covariates

What confounders had to be addressed?

Examples:

- batch
- donor/patient
- tissue site
- disease severity
- treatment
- sequencing depth
- sample composition
- cell-cycle or technical effects

### 6. Validation

What made the conclusion trustworthy?

Examples:

- marker expression sanity check
- external reference labels
- robustness across clustering resolutions
- independent cohort
- orthogonal modality
- flow cytometry
- CITE-seq
- ATAC
- spatial data
- protein validation

## Fix 13: Required Adversary Output When Prior Work Is Relevant

When the adversary cites prior work, it should produce more than a verdict.

It should state:

```text
1. What is already known.
2. How prior studies established it.
3. Which parts of that evidence pattern are required here.
4. What is missing or weak in the current plan.
5. Whether the plan should survive, be revised, or be rejected.
6. If revised, what sharper analysis should be done next.
```

Recommended output pattern:

```text
Prior studies support the high-level conclusion, but the current plan does not yet reproduce
the evidence pattern required to test it in this dataset.

Required revision:
- define the relevant cell population using markers and/or reference labels,
- compute abundance at the sample/patient level,
- compare the correct biological groups,
- use a valid statistical unit rather than treating cells as independent,
- control for available covariates,
- validate the annotation and test robustness.

Verdict: needs_revision, not unsalvageable.
```

## Fix 14: Let Literature Suggest New Analyses

On top of finding the right tools and methods for the user's query, the system should use previous research to suggest analyses that prior studies have not covered.

Examples:

- Prior studies showed broad T cell expansion.
- The current plan should not stop at broad expansion.
- It can ask:
  - which T cell subset expands,
  - whether expansion is stage-specific,
  - whether expanded cells show exhaustion, cytotoxicity, activation, or memory programs,
  - whether paired ATAC supports regulatory drivers,
  - whether patient-level abundance correlates with severity or treatment response.

The goal is not novelty for its own sake. The goal is to use literature to make the current analysis sharper, better controlled, and more useful.

## Fix 15: Update Documentation

Document the final policy in `docs/Overview.md` or a dedicated routing document:

```text
The system is execution-first.
It becomes a scientist only when the user asks a discovery question.
It becomes a debate system only when the question benefits from hypothesis formation,
literature grounding, and iterative interpretation.
```

Also document:

```text
Prior conclusions become analysis requirements.

If a paper found X, the system should ask:
- How was X defined?
- What comparison supported X?
- What statistical unit made the test valid?
- What metric measured X?
- What controls were required?
- What validation made X credible?

Only after reconstructing that evidence pattern can the system decide whether the current plan
is valid, incomplete, redundant, or impossible.
```
