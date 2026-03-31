"""Evaluator prompt templates — 4 specialists + critic."""

PRIOR_EVALUATOR_SYSTEM_PROMPT = (
    "You evaluate prior construction code. Focus on: resource relevance, "
    "construction quality, downstream utility, marginal value.\n"
    "Engage with CHAT_HISTORY. Never repeat suggestions from NOTES.\n"
    "Return ONE JSON object only:\n"
    '{"role": "prior", "has_change": <bool>, "feedback": "<actionable string>"}'
)

DATA_SCIENCE_EVALUATOR_SYSTEM_PROMPT = (
    "You evaluate data preprocessing code. Focus on: feature selection, "
    "prior alignment, normalization, preprocessing correctness.\n"
    "Engage with CHAT_HISTORY. Never repeat suggestions from NOTES.\n"
    "Return ONE JSON object only:\n"
    '{"role": "data_science", "feedback": "<actionable string>"}'
)

MODEL_EVALUATOR_SYSTEM_PROMPT = (
    "You evaluate model training code. Focus on: prior integration, "
    "architecture fit, training health, loss design, optimization.\n"
    "Engage with CHAT_HISTORY. Never repeat suggestions from NOTES.\n"
    "Return ONE JSON object only:\n"
    '{"role": "model", "feedback": "<actionable string>"}'
)

BIOLOGY_EVALUATOR_SYSTEM_PROMPT = (
    "You evaluate downstream analysis code. Focus on: clustering approach, "
    "biological coherence, DEG quality, metric computation.\n"
    "Engage with CHAT_HISTORY. Never repeat suggestions from NOTES.\n"
    "Return ONE JSON object only:\n"
    '{"role": "biology", "feedback": "<actionable string>"}'
)

CRITIC_SYSTEM_PROMPT = (
    "You are the principal investigator synthesizing four specialist evaluations.\n"
    "Resolve conflicts, reject unsupported suggestions, produce ONE action plan.\n"
    "Prioritize changes most likely to improve METRICS.\n"
    "Omit scripts that need no change.\n"
    "Return ONE JSON object only:\n"
    '{"step": <int>, "global_rationale": "<str>", '
    '"targets": {"<filename>": {"feedback": "<str>"}, ...}}'
)

# ── Format strings ─────────────────────────────────────────────────

PRIOR_FORMAT_STRING = (
    "|TASK|: {task}\n|STEP|: {step}\n|PLAN|: {suggestion}\n"
    "|PERFORMANCE|: {performance}\n|PRIOR_CODE|: {prior_code}\n"
    "|PRIOR_SCHEMA|: {prior_schema}\n|PRIOR_RESOURCES|: {prior_resources}\n"
    "|DATA_SUMMARY|: {data_summary}\n|CLUSTER_SUMMARY|: {cluster_summary}\n"
    "|TRAINING_LOGS|: {training_logs}\n|PIPELINE_SUMMARY|: {pipeline_summary}\n"
    "|NOTES|: {notes}\n|CHAT_HISTORY|: {chat_history}\n"
)

DATA_SCIENCE_FORMAT_STRING = (
    "|TASK|: {task}\n|STEP|: {step}\n|PLAN|: {suggestion}\n"
    "|PERFORMANCE|: {performance}\n|PREPROCESS_CODE|: {preprocess_code}\n"
    "|PRIOR_SCHEMA|: {prior_schema}\n|PRIOR_RESOURCES|: {prior_resources}\n"
    "|PREPROCESS_META|: {preprocess_meta}\n|PIPELINE_SUMMARY|: {pipeline_summary}\n"
    "|NOTES|: {notes}\n|CHAT_HISTORY|: {chat_history}\n"
)

MODEL_FORMAT_STRING = (
    "|TASK|: {task}\n|STEP|: {step}\n|PLAN|: {suggestion}\n"
    "|PERFORMANCE|: {performance}\n|PREPROCESS_CODE|: {preprocess_code}\n"
    "|MODEL_CODE|: {model_code}\n|TRAINING_LOGS|: {training_logs}\n"
    "|PIPELINE_SUMMARY|: {pipeline_summary}\n"
    "|NOTES|: {notes}\n|CHAT_HISTORY|: {chat_history}\n"
)

BIOLOGY_FORMAT_STRING = (
    "|TASK|: {task}\n|STEP|: {step}\n|PLAN|: {suggestion}\n"
    "|PERFORMANCE|: {performance}\n|DOWNSTREAM_CODE|: {downstream_code}\n"
    "|CLUSTER_SUMMARY|: {cluster_summary}\n"
    "|NOTES|: {notes}\n|CHAT_HISTORY|: {chat_history}\n"
)

CRITIC_FORMAT_STRING = (
    "|TASK|: {task}\n|STEP|: {step}\n|PLAN|: {suggestion}\n"
    "|DATA_SUMMARY|: {data_summary}\n|PRIOR_RESOURCES|: {prior_resources}\n"
    "|PERFORMANCE|: {performance}\n|TRAINING_LOGS|: {training_logs}\n"
    "|PIPELINE_SUMMARY|: {pipeline_summary}\n"
    "|SCRIPT_SUMMARIES|: {script_summaries}\n"
    "|CHAT_HISTORY|: {chat_history}\n|NOTES|: {notes}\n"
)

# ── Config map for Evaluator class ─────────────────────────────────

EVALUATOR_CONFIG = {
    "prior": {
        "system_prompt": PRIOR_EVALUATOR_SYSTEM_PROMPT,
        "format_string": PRIOR_FORMAT_STRING,
        "fields": ["step", "suggestion", "performance", "prior_code",
                    "prior_schema", "prior_resources", "data_summary",
                    "cluster_summary", "training_logs", "pipeline_summary",
                    "notes", "chat_history"],
    },
    "data_science": {
        "system_prompt": DATA_SCIENCE_EVALUATOR_SYSTEM_PROMPT,
        "format_string": DATA_SCIENCE_FORMAT_STRING,
        "fields": ["step", "suggestion", "performance", "preprocess_code",
                    "prior_schema", "prior_resources", "preprocess_meta",
                    "pipeline_summary", "notes", "chat_history"],
    },
    "model": {
        "system_prompt": MODEL_EVALUATOR_SYSTEM_PROMPT,
        "format_string": MODEL_FORMAT_STRING,
        "fields": ["step", "suggestion", "performance", "preprocess_code",
                    "model_code", "training_logs", "pipeline_summary",
                    "notes", "chat_history"],
    },
    "biology": {
        "system_prompt": BIOLOGY_EVALUATOR_SYSTEM_PROMPT,
        "format_string": BIOLOGY_FORMAT_STRING,
        "fields": ["step", "suggestion", "performance", "downstream_code",
                    "cluster_summary", "notes", "chat_history"],
    },
    "critic": {
        "system_prompt": CRITIC_SYSTEM_PROMPT,
        "format_string": CRITIC_FORMAT_STRING,
        "fields": ["step", "suggestion", "data_summary", "prior_resources",
                    "performance", "training_logs", "pipeline_summary",
                    "script_summaries", "chat_history", "notes"],
    },
}