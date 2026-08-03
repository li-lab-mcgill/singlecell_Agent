# Cases To Consider

## 1. A Known Question Is Not Automatically An Unsalvageable Plan

A plan is not unsalvageable merely because the biological question is already
known.

It is unsalvageable only when both the question and the proposed analytical
contribution are redundant, or when the plan cannot produce any new evidence,
perspective, validation, or methodological improvement.

The adversary should not reject a plan simply because the broad biological
question has already been studied. Existing knowledge can be a valid starting
point.

A plan should survive if it contributes novelty along at least one axis:

- **Question novelty**: asks a new biological question.
- **Analysis novelty**: applies a different analytical framing, contrast,
  resolution, modality, validation strategy, or robustness check.
- **Method novelty**: uses or compares a method in a way that changes what can
  be inferred.
- **Dataset/context novelty**: tests a known claim in a new cohort, disease
  state, tissue, modality, perturbation, or cell population.
- **Evidence novelty**: strengthens, refutes, qualifies, or mechanistically
  explains an established finding.

So the adversary should ask:

> Even if the headline question is known, does this plan generate a meaningfully
> new analysis or interpretation?

`unsalvageable` should mean:

> The plan repeats an already established finding using an analysis that is also
> routine, expected, and unlikely to add new biological, statistical,
> computational, or contextual insight.

It should not mean:

> The topic has appeared in the literature before.

When the adversary finds that a claim is already established, it must distinguish
between **known question** and **redundant plan**.

A plan is redirected only if it lacks novelty in both:

1. the biological question being asked, and
2. the analytical or methodological route used to answer it.

If the question is known but the analysis is new, the plan should be revised to
make the analytical contribution explicit.

If the question is novel but the method is standard, the plan may still proceed
because novelty comes from the biological claim.

If both are known, the panel should redirect toward the next open question or a
more informative analysis.

Core principle:

> The adversary should reject redundancy, not familiarity. A familiar biological
> question can still be worth pursuing if the planned analysis adds new
> resolution, context, validation, mechanism, or methodological insight.
> `unsalvageable` is reserved for plans that would only re-demonstrate an
> established result with no new analytical contribution.

## 2. Not Every User Request Is A Discovery-Oriented Research Question

The ScientistPanel should first classify the user's intent before launching the
full debate.

Not every user request is a discovery-oriented research question.

The panel should distinguish between:

### Execution / Assistance Requests

The user wants help running a known workflow.

Examples:

- "Run cell type annotation."
- "Cluster this RNA dataset."
- "Normalize and make a UMAP."
- "Run differential expression between these groups."
- "Use CellTypist on this file."

These do **not** require novelty, extensive paper retrieval, or adversarial
debate. The goal is correctness, tool choice, parameter sanity, and clear
outputs.

### Research / Discovery Requests

The user wants to answer an open biological or methodological question.

Examples:

- "What cell state drives inflammation?"
- "Which regulatory program explains disease progression?"
- "Is this batch correction preserving biology?"
- "What novel mechanism can this multiome dataset reveal?"

These may require literature, panel disagreement, novelty checking, and
adversarial review.

### Ambiguous Requests

The user asks something that could be either operational or discovery-oriented.

Examples:

- "Analyze this PBMC dataset."
- "Find interesting biology."
- "What should I do next?"

These should trigger a lighter clarification or a short initial panel pass.

Key rule:

> The ScientistPanel should not assume every task is a publishable discovery
> project.

If the user asks for a standard analysis, the system should behave like a
careful bioinformatics assistant, not like a grant-review committee.

Before invoking full ScientistPanel debate, the system performs an **intent
triage**:

- If the request is operational, use a lightweight planning path.
- If the request is discovery-oriented, use the full ScientistPanel.
- If the request is ambiguous, use a brief triage response or minimal panel pass.

For operational requests, the panel's job is not to establish novelty. It should
only check:

- What modality is involved?
- What input data exists?
- What preprocessing is required?
- Which tool is appropriate?
- What parameters are needed?
- What outputs should be produced?
- What common failure modes should be avoided?

No broad literature retrieval is needed unless the user asks for method
selection justification or the task depends on a specialized biological
reference.

The panel can infer "no extensive debate needed" when the user's request:

- names a standard workflow: annotation, clustering, QC, normalization, UMAP, DE
- names a specific tool or method
- does not ask "why", "what drives", "discover", "novel", "mechanism",
  "hypothesis", or "interpret"
- has a clear procedural endpoint
- can be answered by executing a known pipeline

Example:

> "Help me run cell type annotation."

This should become:

```text
Intent: operational workflow
Panel mode: lightweight
Literature retrieval: skip by default
Adversarial novelty review: skip
Plan focus: choose annotation method, validate input, run annotation, report confidence and markers
```

But:

> "What unknown immune cell state might explain treatment resistance?"

This becomes:

```text
Intent: discovery research
Panel mode: full ScientistPanel
Literature retrieval: required
Adversarial review: required
Plan focus: novelty, mechanism, falsification, evidence
```

Core principle:

> Literature retrieval and adversarial novelty review are reserved for
> discovery-oriented questions. For routine execution requests, the system
> should skip extensive debate and proceed with a concise technical plan focused
> on correctness, prerequisites, and reproducibility.
