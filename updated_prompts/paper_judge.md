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

If full_text_status is abstract_only, do not claim detailed methods, covariates,
statistical unit, or validation unless the abstract explicitly states them.

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
}}
