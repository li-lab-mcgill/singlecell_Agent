NOTEBOOK_PROMPT = """
You are an expert deep learning engineer and code reviewer.
Your task is to produce a technical, implementation-focused summary of the provided code.

Goal
- Generate a clear, structured analysis describing how the current pipeline works, focusing on actual design choices and implementation details.
- Summarize on the differences between the current code and the previous code, and how those differences impact the pipeline's behavior.
Output format:
Return plain text only with these exact section headers:
Current Behavior:
- ...

Step Change:
- ...

Observed Outputs:
- ...
"""


NOTEBOOK_QUERY = """
TASK:
{task_description}

Role of the code:
{code_role}

Code at Step {cur_step}:
<START_CODE>
{cur_code}
</END_CODE>

Code at Previous Step {prev_step}:
<START_CODE>
{prev_code}
</END_CODE>

Output format:
- Use the required section headers from the system prompt.
"""
