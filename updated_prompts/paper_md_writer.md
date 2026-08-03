Extract structured information from this paper summary to create a wiki entry.

---
PAPER:
Title: {title}
Doc ID: {doc_id}
Published: {published}
Source: {source}
URL: {url}
DOI: {doi}
Source IDs: {source_ids}
Full text status: {full_text_status}
Retrieval goal: {retrieval_goal}
Retrieval intent: {retrieval_intent}
Abstract: {abstract}
Objective: {objective}
Background: {background}
Analysis: {analysis}
Benchmark methods: {benchmark_methods}
Main findings: {main_findings}
Limitations: {limitations}
Figure captions: {figure_captions}
Evidence contribution: {evidence_contribution}
Covered evidence patterns: {covered_evidence_patterns}
Missing evidence: {missing_evidence}

---
AVAILABLE TASK IDs (from the tool wiki — select only those this paper directly applies to):
{task_ids}

---
EXISTING PAPERS IN WIKI (check if this paper extends any of them):
{existing_papers_summary}

---
Return ONLY a JSON object with these fields:

{{
  "paper_id": "<sanitized ID: first_author_lastname_year, lowercase, underscores only, max 40 chars>",
  "doi": "<DOI if available>",
  "url": "<paper URL if available>",
  "source_ids": {{"doc_id": "<doc id>", "pmid": "<pmid>", "pmcid": "<pmcid>", "semantic_scholar_id": "<id>", "openalex_id": "<id>"}},
  "full_text_status": "pmc_xml | preprint_jats | open_pdf | abstract_only",
  "tasks": ["<task_id from the list above that this paper directly addresses>"],
  "retrieval_goals": ["<retrieval goal this paper supported>"],
  "retrieval_intents": ["<retrieval intent this paper helped answer>"],
  "extends": ["<paper_id from existing wiki papers that this paper directly builds on>"],
  "summary": "<2-3 sentence description of what the paper does and why it matters>",
  "background": "<scientific background and why this paper was needed>",
  "method_and_dataset": "<what method, on what data type, approximate size, and experimental design; what assumptions the method makes>",
  "analysis": "<specific analyses, workflows, statistical models, comparisons, or computational steps used>",
  "benchmark_methods": "<other methods, baselines, reference workflows, or comparator analyses this paper compared against; empty if not extractable>",
  "key_findings": "<what the paper specifically concluded — not what it introduced, but what it proved>",
  "limitations": "<specific limitations of the paper>",
  "metrics_used": "<metrics, evaluation criteria, statistical units, readouts, or endpoints used; empty if not extractable>",
  "figure_captions": "<important figure-caption evidence, workflow details, metrics, or validation details; empty if not extractable>"
}}

Rules:
- paper_id: derive from first author lastname + year from the title/published date.
  If author/year not determinable, use a short slug from the title (max 40 chars, lowercase, underscores).
- tasks: only include task IDs from the provided list. At least 1 required. Max 3.
- extends: only include paper_ids from the provided existing wiki papers list. Empty list if none apply.
- key_findings: be specific about numbers, cell types, conditions where reported.
- benchmark_methods: list named baselines and comparator methods when available,
  including classical baselines, previous SOTA tools, ablations, reference
  pipelines, or manual/expert baselines. Use "" if the paper did not compare
  against other methods or the summary does not say.
- metrics_used: include concrete measures such as AUC, ARI, macro-F1, effect size,
  abundance fraction, pseudobulk model output, statistical unit, validation endpoint,
  runtime, memory, or other reported criteria. Use "" if no metric is available.
- If a field cannot be determined from the summary, use "" (empty string) or [] (empty list).
