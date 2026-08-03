You are summarizing a biomedical paper for a consultant agent.

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
