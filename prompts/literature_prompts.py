"""Prompts for summarizing biomedical papers during literature retrieval.

Two paper-summary formats, consolidated from updated_prompts/*.md:
- LITERATURE_SUMMARY_SYSTEM / LITERATURE_SUMMARY_PROMPT: used by
  LiteratureRetriever (rag/literature_retriever.py) for the Scientist Panel's
  literature retrieval pipeline. Produces a rich, PaperJudge-facing summary
  (includes benchmark_methods, supplemental_data, key_caption_evidence).
- RAG_CONTEXT_PAPER_SUMMARY: used by the Research Consultant RAG agent
  (rag/agent.py) for a more compact paper summary.
"""

LITERATURE_SUMMARY_SYSTEM = """
You are summarizing a biomedical paper. Return only valid JSON.
"""

LITERATURE_SUMMARY_PROMPT = """Summarize this paper for a research-planning agent.

Title: {title}
Published: {published}
Abstract: {abstract}
Methods: {methods}
Results: {results}
Discussion: {discussion}
Figure captions: {figure_captions}

Be specific. Preserve method-level detail when the paper provides it:
package/tool names, versions if stated, preprocessing, sample/statistical
unit, model/test/formula, covariates, thresholds, parameters, outputs,
metrics, validation, and interpretation. Do not collapse methods into one
generic sentence. Prefer the paper's own wording for tools, thresholds,
and metrics.

If the paper doesn't state something, write "not_reported" for that field
rather than inferring it. For benchmark_methods, include only methods this
paper actually compared against — not methods merely cited or built upon.
For supplemental_data, include external computational references the paper
reused.

Return a single JSON object:
{{
  "objective": "<string>",
  "background": "<string>",
  "method_and_dataset": "<data, assay, cohort/sample unit, preprocessing, experimental design, and method assumptions>",
  "analysis": "<step-by-step workflow: each major analysis step with its input, the tool/package (and version if stated), key parameters or thresholds, statistical model/test/formula and covariates, the output produced, and how it feeds into the next step or the paper's claims. Include downstream analyses such as DE, trajectory, GRN, cell-cell communication, pathway scoring, or integration if performed.>",
  "benchmark_methods": "<comparators/baselines/ablations actually evaluated against; 'not_reported' if none>",
  "supplemental_data": [
    {{
      "data_source": "<computational reference: benchmark dataset, public ChIP-seq, eQTL data, perturb-seq cohort, reference atlas, motif/pathway database, etc.>",
      "purpose": "<what computational reference role it plays in this paper's analyses>"
    }}
  ],
  "main_findings": "<string>",
  "limitations": "<string>",
  "metrics_used": "<string>",
  "key_caption_evidence": "<figure-caption excerpts that contain workflow, metric, or validation specifics; 'not_reported' if none>"
}}
"""

RAG_CONTEXT_PAPER_SUMMARY = """You are summarizing a biomedical paper for a consultant agent.

Return ONLY valid JSON:
{{
  "objective": "<string>",
  "method_and_dataset": "<data, assay, cohort/sample unit, preprocessing, experimental design, and method assumptions>",
  "key_methods": "<string>",
  "benchmark_methods": "<methods, baselines, ablations, reference workflows, or comparator analyses compared against; empty if none stated>",
  "main_findings": "<string>",
  "limitations": "<string>",
  "figure_captions": "<important figure-caption evidence, workflow details, metrics, or validation details extracted from captions; empty if none>"
}}

Paper title: {title}
Published: {published}
Abstract:
{abstract}

Methods:
{methods}

Results:
{results}

Discussion:
{discussion}

Figure captions:
{figure_captions}
"""
