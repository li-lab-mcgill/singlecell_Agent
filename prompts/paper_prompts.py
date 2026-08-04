"""Prompts for PaperJudge and PaperMDWriter (research subsystem). Single source
of truth, consolidated and refined from updated_prompts/paper_judge_system.md,
paper_judge.md, paper_md_writer_system.md, paper_md_writer.md, and
paper_md_template.md. agents/paper_judge.py and agents/paper_md_writer.py
import these five constants directly; there is no longer a second copy loaded
via agents.prompt_loader.load_updated_prompt.

FORMAT-BASED, not concat-composed (unlike prompts/mediator_prompts.py and
prompts/panelist_prompts.py): PAPER_JUDGE_PROMPT, PAPER_MD_WRITER_PROMPT, and
PAPER_MD_TEMPLATE are all filled in via `.format(**kwargs)` at their call
sites (agents/paper_judge.py::_judge_one, agents/paper_md_writer.py::_write_one
and ::_render_md). Every literal `{`/`}` in the embedded JSON schemas below is
therefore doubled (`{{`/`}}`) so `.format()` does not treat it as a field: the
placeholder set for each constant was locked from those call sites, not
guessed from the .md prose.

Machine-readable contracts preserved verbatim from the source .md files
(parsers and downstream tools depend on these):
  - PAPER_JUDGE_PROMPT's output JSON keys — relevant, confidence,
    retrieval_intent_fit, usefulness, return_to_panelist, reason,
    evidence_contribution, covered_evidence_patterns, missing_evidence,
    suggested_query_terms, suggested_exclusions — read by
    agents/paper_judge.py::_parse_verdict, and the covered_evidence_patterns
    enum (entity_definition, comparison_design, statistical_unit,
    effect_metric, controls_covariates, validation, boundary_conditions) and
    retrieval_intent_fit enum (direct | partial | weak | off_target) checked
    by `_valid_evidence_patterns` / `_normalize_intent_fit`. The explicit
    exclusion of claim_supported/analysis_used from covered_evidence_patterns
    is intentional (those are paper-level assessment fields used elsewhere in
    the wiki, not per-field evidence-pattern names) and is preserved as-is.
  - PAPER_MD_WRITER_PROMPT's output JSON keys — paper_id, doi, url,
    source_ids, full_text_status, tasks, retrieval_goals, retrieval_intents,
    extends, summary, background, method_and_dataset, analysis,
    benchmark_methods, key_findings, limitations, metrics_used,
    figure_captions — read by agents/paper_md_writer.py::_write_one /
    ::_render_md.
  - PAPER_MD_TEMPLATE's YAML frontmatter fields (paper_id, title, doi, url,
    source_ids, full_text_status, tasks, retrieval_goals, retrieval_intents,
    extends, added, session) read by wiki/paper_index.py::_load_file (the
    remaining fields land in PaperNode.metadata generically via `dict(fm)`),
    and its `## <Heading>` section markers, which tests/test_paper_md_writer.py
    asserts appear verbatim.

Pre-existing gap noted, not fixed here: PAPER_MD_TEMPLATE and the writer's
output schema both have a `method_and_dataset` field, and PAPER_JUDGE_PROMPT
feeds the judge a `method_and_dataset` value from the paper summary — but
PAPER_MD_WRITER_PROMPT's input section never surfaces `method_and_dataset` to
the extraction call, and agents/paper_md_writer.py::_write_one does not pass
it to `.format()`. Adding that placeholder here would raise KeyError at that
call site (it isn't in the kwargs), so it is intentionally left out to keep
the exact placeholder set the caller supplies. Out of scope for this
prose-only consolidation.
"""

# ---------------------------------------------------------------------------
# PaperJudge
# ---------------------------------------------------------------------------

PAPER_JUDGE_SYSTEM = """\
You are a scientific literature assessor. Judge one paper against one explicit retrieval intent. Reason internally, then return only valid JSON.\
"""

PAPER_JUDGE_PROMPT = """\
Role: {role}
Retrieval goal: {retrieval_goal}
Retrieval intent: {retrieval_intent}
Base query: {base_query}

Paper:
Doc ID: {doc_id}
Title: {title}
Published: {published}
Source: {source}
URL: {url}
Full text status: {full_text_status}
Abstract: {abstract}
Objective: {objective}
Background: {background}
Method and dataset: {method_and_dataset}
Analysis: {analysis}
Benchmark methods: {benchmark_methods}
Main findings: {main_findings}
Limitations: {limitations}
Figure captions: {figure_captions}

Assess whether this paper is useful for the retrieval intent from the {role}'s perspective.

Valid covered_evidence_patterns values:
- entity_definition
- comparison_design
- statistical_unit
- effect_metric
- controls_covariates
- validation
- boundary_conditions

Do not include claim_supported or analysis_used in covered_evidence_patterns.

If full_text_status is abstract_only, do not claim detailed methods, covariates, statistical unit, or validation unless the abstract explicitly states them.

Return ONLY a JSON object:
{{
  "relevant": true or false,
  "confidence": <float between 0.0 and 1.0>,
  "retrieval_intent_fit": "direct | partial | weak | off_target",
  "usefulness": "{retrieval_goal}",
  "return_to_panelist": true or false,
  "reason": "<one sentence explaining the relevance or irrelevance>",
  "evidence_contribution": "<what this paper contributes to the retrieval intent>",
  "covered_evidence_patterns": ["<valid evidence pattern field name>"],
  "missing_evidence": ["<important missing evidence for this intent>"],
  "suggested_query_terms": ["<terms a panelist could use if retrieval is partial>"],
  "suggested_exclusions": ["<terms to exclude if results are off target>"]
}}\
"""

# ---------------------------------------------------------------------------
# PaperMDWriter
# ---------------------------------------------------------------------------

PAPER_MD_WRITER_SYSTEM = """\
You are building a structured knowledge base of scientific papers for a single-cell genomics research agent. Your job is to extract structured information from a paper summary and produce a wiki entry.

Return only valid JSON — no prose, no markdown fences around the JSON.

Be precise and specific: extract concrete claims, not generic paraphrases. If information is missing from the summary, use empty strings — never hallucinate.\
"""

PAPER_MD_WRITER_PROMPT = """\
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
- paper_id: derive from first author lastname + year from the title/published date. If author/year not determinable, use a short slug from the title (max 40 chars, lowercase, underscores).
- tasks: only include task IDs from the provided list. At least 1 required. Max 3.
- extends: only include paper_ids from the provided existing wiki papers list. Empty list if none apply.
- key_findings: be specific about numbers, cell types, conditions where reported.
- benchmark_methods: list named baselines and comparator methods when available, including classical baselines, previous SOTA tools, ablations, reference pipelines, or manual/expert baselines. Use "" if the paper did not compare against other methods or the summary does not say.
- metrics_used: include concrete measures such as AUC, ARI, macro-F1, effect size, abundance fraction, pseudobulk model output, statistical unit, validation endpoint, runtime, memory, or other reported criteria. Use "" if no metric is available.
- If a field cannot be determined from the summary, use "" (empty string) or [] (empty list).\
"""

PAPER_MD_TEMPLATE = """\
---
paper_id: {paper_id}
title: "{title}"
doi: "{doi}"
url: "{url}"
source_ids: {source_ids_yaml}
full_text_status: "{full_text_status}"
tasks: {tasks_yaml}
retrieval_goals: {retrieval_goals_yaml}
retrieval_intents: {retrieval_intents_yaml}
extends: {extends_yaml}
added: {added}
session: {session}
---

## Summary
{summary}

## Background
{background}

## Method and dataset
{method_and_dataset}

## Analysis
{analysis}

## Benchmark methods
{benchmark_methods}

## Key findings
{key_findings}

## Limitations
{limitations}

## Metrics used
{metrics_used}

## Figure captions
{figure_captions}\
"""
