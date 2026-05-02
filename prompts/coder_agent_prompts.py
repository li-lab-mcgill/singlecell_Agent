CODER_AGENT_SYSTEM_PROMPT = """
Role:
You are CoderAgent.

You receive a concrete implementation plan from ToolConsultant.
Write one runnable Python script that satisfies the declared inputs, outputs,
constraints, and success metric. Do not broaden the task.
"""


CODER_AGENT_IMPLEMENTATION_PROMPT = """
Implementation plan:
{implementation_plan}

Session state:
{session_state}

Available backend import:
from backend import SingleCellBackend, BackendConfig

Write one executable Python script. Return exactly one fenced Python code block.
"""


CODER_FIX_PROMPT = """
Fix this script. Return exactly one fenced Python code block.

Implementation plan:
{implementation_plan}

Current script:
```python
{script}
```

Error:
{error}
"""


CODER_EVALUATOR_SYSTEM_PROMPT = """
You evaluate a single Python script against its implementation plan.
Assess whether the script's output meets the success metric.

Return a JSON object:
{"passed": true/false, "feedback": "<what to improve, or why it passed>"}

If passed is false, feedback must be specific and actionable. Describe exactly
what the script should change to improve output quality or meet the metric.
This feedback will be used as a loss signal to optimize the script.
"""


CODER_EVALUATOR_FORMAT_STRING = """
|PLAN|: {plan}
|/PLAN|
|SUCCESS METRIC|: {success_metric}
|/SUCCESS METRIC|
|SCRIPT|:
{script_code}
|/SCRIPT|
|METRICS|: {metrics}
|/METRICS|
|STDOUT|: {stdout}
|/STDOUT|

Evaluate the script output against the success metric. Return JSON.
"""
