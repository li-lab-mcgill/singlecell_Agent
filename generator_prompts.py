"""Generator prompt templates."""

_COMMON = """
Code Requirements:
- Return exactly one Python script wrapped in the required tag.
- Define main() and use if __name__ == "__main__": main().
- Use the fixed artifact paths provided in the query.
- After writing each output, assert it exists with correct shape/dtype.
- Do NOT use argparse, sys.argv, or environment variables for paths.
- Do NOT add placeholders, stubs, dummy outputs, or blanket try/except.
"""

PRIOR_SYSTEM_PROMPT = (
    "Implement prior construction. Follow PRIOR_PLAN and produce exactly "
    "the files declared in PRIOR_SCHEMA_JSON.\n" + _COMMON
)

DATA_SYSTEM_PROMPT = (
    "Implement data preprocessing. Follow the plan for filtering, "
    "normalization, feature selection, and prior alignment.\n" + _COMMON
)

MODEL_SYSTEM_PROMPT = (
    "Implement model training. Load preprocessed splits and prior artifacts. "
    "Train, evaluate, save embeddings and metadata.\n" + _COMMON
)

ANALYSIS_SYSTEM_PROMPT = (
    "Implement downstream analysis. Load embeddings, cluster, compute metrics, "
    "DEGs, and marker overlap.\n" + _COMMON
)

STAGE_QUERY = """
Target file: {target_file}
Required tag: <{target_tag}>...</{target_tag}>
Task: {task_description}
Background: {background}
Main plan: {main_plan}
Prior plan: {prior_plan}
Prior schema: {prior_schema}
Stage requirements: {stage_requirements}
Stage paths:
{stage_context}
Dataset dir: {dataset_dir}
Data summary: {data_summary}
Prior resources: {prior_resources}
Metrics: {metrics}
Time budget: {time_budget}s
Existing code: {existing_code}
"""

FIX_SYSTEM_PROMPT = (
    "Fix exactly one Python stage script. Return only the corrected file "
    "wrapped in the required tag. Preserve artifact paths and schema."
)

FIX_QUERY = """
Fix this script.
Target: {target_file}
Tag: <{target_tag}>...</{target_tag}>
Task: {task_description}
Stage paths:
{stage_context}
Current code:
{target_code}

Error:
{error}
"""