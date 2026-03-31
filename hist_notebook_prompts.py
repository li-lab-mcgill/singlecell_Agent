"""Notebook prompt templates."""

NOTEBOOK_PROMPT = """
You are an expert deep learning engineer. Produce a concise technical summary.
Return plain text with headers: Current Behavior, Step Change, Observed Outputs.
"""

NOTEBOOK_QUERY = """
TASK: {task_description}
Role: {code_role}
Code at Step {cur_step}:
{cur_code}
Code at Previous Step {prev_step}:
{prev_code}
"""

NOTE_SUMMARIZE_SYS_PROMPT = (
    "Compress the given note into one concise sentence preserving "
    "the most important technical and outcome information. "
    "Do NOT add information not present in the note."
)

NOTE_CLEAN_SYS_PROMPT = (
    "You are an Optimization Notes Curator. Reduce note explosion by "
    "keeping high-impact info (performance changes, failure modes, "
    "strategy shifts) and compressing the rest. "
    "Output only curated notes. Do NOT introduce new information."
)