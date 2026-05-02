from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from agents.runner import ToolCallingAgentRunner
from agents.tools import build_analyst_registry
from agents.analyst import parse_evaluation_guidance_response
from prompts.analyst_prompts import ANALYST_GUIDANCE_PROMPT, ANALYST_SYSTEM_PROMPT, ANALYST_TOOL_USE_PROMPT


class AnalystAgent:
    def __init__(
        self,
        *,
        engine_name: str,
        paper_backend: Any,
        result_dir: str,
        single_cell_backend: Any | None = None,
        client: Any | None = None,
    ):
        feedback_dir = Path(result_dir) / "feedback"
        self.paper_backend = paper_backend
        self.result_dir = feedback_dir
        registry = build_analyst_registry(paper_backend, backend=single_cell_backend)
        self.runner = ToolCallingAgentRunner(
            model=engine_name,
            system_prompt="\n\n".join([ANALYST_SYSTEM_PROMPT.strip(), ANALYST_TOOL_USE_PROMPT.strip()]),
            tool_specs=registry.tool_specs(),
            tool_executor=registry.executor(),
            transcript_path=str(feedback_dir / "analyst_transcript.jsonl"),
            tool_trace_path=str(feedback_dir / "analyst_tool_trace.jsonl"),
            client=client,
            max_iterations=48,
            max_tool_calls=64,
        )

    def generate_evaluation_guidance(self, *, background: str, dataset_profile: str, prior_resource_summary: str) -> Any:
        prompt = ANALYST_GUIDANCE_PROMPT.format(
            goal_and_query=background.strip(),
            dataset_profile=dataset_profile,
            prior_resource_summary=prior_resource_summary,
            dataset_rag_context="Use tools instead of relying on pasted dataset RAG context.",
            benchmark_rag_context="Use tools instead of relying on pasted benchmark RAG context.",
            marker_db_context="Use tools instead of relying on pasted marker context.",
        )
        retries = {"count": 0}

        def _handle_response(text: str) -> Dict[str, Any]:
            try:
                guidance = parse_evaluation_guidance_response(text, background.strip(), dataset_profile)
            except Exception as exc:
                if retries["count"] >= 1:
                    raise
                retries["count"] += 1
                return {
                    "done": False,
                    "next_user_input": (
                        "Your previous response was invalid. Return only one valid JSON object that matches the required schema. "
                        f"Validation error: {exc}"
                    ),
                }

            output_path = self.result_dir / "evaluation_guidance.json"
            output_path.write_text(json.dumps(guidance.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            return {"done": True, "result": guidance}

        return self.runner.run(initial_user_input=prompt, response_handler=_handle_response)
