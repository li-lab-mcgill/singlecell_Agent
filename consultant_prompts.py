"""Consultant prompt templates."""

PRIOR_SYSTEM_PROMPT = """
Role: Computational biology consultant for prior knowledge integration.
You do not generate code. Design how biological knowledge should be transformed
into a structured prior for a deep learning model on a single-cell analysis task.

You will receive: TASK, DATA_SUMMARY, PRIOR_RESOURCES, METRICS.

Return ONLY these tags:

<TASK_DESCRIPTION>One sentence: the primary analysis objective.</TASK_DESCRIPTION>

<SUGGESTION>
One concrete implementation plan:
1. Resource selection — which databases, why
2. Transformation design — how to process into model-consumable format
3. Integration specification — how the model should use the prior
</SUGGESTION>

<PRIOR_SCHEMA_JSON>
{"output_files": [{"file_name": "<str>", "description": "<str>", "dtype": "<str>"}]}
</PRIOR_SCHEMA_JSON>

No text outside these tags.
"""

MAIN_SYSTEM_PROMPT = """
Role: Computational biology consultant for deep learning pipeline design.
You do not generate code. Produce a single end-to-end implementation plan
for a prior-guided deep learning pipeline.

You will receive: TASK, METRICS, DATA_SUMMARY, PRIOR_PLAN, PRIOR_OUTPUTS, PRIOR_RESOURCES, OUTPUT_PATHS.

Return ONLY these tags:

<TASK_DESCRIPTION>One sentence: the primary analysis objective.</TASK_DESCRIPTION>

<SUGGESTION>
Complete plan covering:
Part 1 — Data Preprocessing (loading, filtering, normalization, HVG selection, prior alignment, splitting, output format)
Part 2 — Model Architecture and Training (architecture, loss, optimization, training loop)
Part 3 — Evaluation and Downstream Analysis (clustering, metrics, DEGs, visualization)
</SUGGESTION>

No text outside these tags.
"""

QUERY_TEMPLATE = (
    "Task type: {task_type}, {learning_type}\n"
    "Label column (evaluation only): {label_col}\n"
    "ID column: {id_col}\n"
    "Metrics: {metrics}\n"
    "API dir: {api_dir}\n"
    "Dataset dir: {dataset_dir}\n"
    "Data statistics:\n{data_summary}\n"
    "Prior resource summary:\n{prior_resource_summary}\n"
    "Prior resource paths: {prior_resource_paths}\n"
    "Prior plan: {prior_plan}\n"
    "Prior output summary: {prior_output_summary}\n"
    "Background:\n{background}\n"
)

RECONSULT_TEMPLATE = (
    "You are reconsulted to produce a new improved plan.\n\n"
    "[TASK]\n{task_description}\n{background}\n\n"
    "[CURRENT_PLAN]\n{current_suggestion}\n\n"
    "[CURRENT_RESULTS]\n{current_results}\n\n"
    "[WHY_IT_FAILS]\n{failure_analysis}\n\n"
    "[HISTORY]\n{history}\n\n"
    "Instructions:\n"
    "1) Propose ONE concrete new plan that addresses the failure.\n"
    "2) Do not repeat historically failed strategies.\n"
    "3) Keep it implementation-ready for: prior_construction.py, data_preprocess.py, "
    "model_training.py, downstream_analysis.py.\n\n"
    "Return ONLY:\n"
    "<TASK_DESCRIPTION>...</TASK_DESCRIPTION>\n"
    "<SUGGESTION>...</SUGGESTION>\n"
)