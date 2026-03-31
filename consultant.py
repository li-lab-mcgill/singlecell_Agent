"""Consultant agent — prior design + pipeline planning + reconsultation."""
import json
import re
from typing import List, Any, Dict

import textgrad as tg

from config import Config
from consultant_prompts import (
    MAIN_SYSTEM_PROMPT,
    PRIOR_SYSTEM_PROMPT,
    QUERY_TEMPLATE,
    RECONSULT_TEMPLATE,
)


def _extract_tags(text: str, tags: List[str]) -> Dict[str, str]:
    result = {}
    for tag in tags:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text or "", re.DOTALL | re.IGNORECASE)
        result[tag] = m.group(1).strip() if m else ""
    return result


class Consultant:
    """Prior consultation, main pipeline consultation, and reconsultation."""

    def __init__(self, config: Config, consultant_type: str = "main"):
        self.config = config
        self.type = consultant_type
        self.engine = tg.get_engine(config.engine_name, max_tokens=5000)
        self.system_prompt = PRIOR_SYSTEM_PROMPT if consultant_type == "prior" else MAIN_SYSTEM_PROMPT

    def consult(
        self,
        background: str,
        prior_plan: str = "<none>",
        prior_output_summary: str = "<none>",
    ) -> Dict[str, Any]:
        query = QUERY_TEMPLATE.format(
            task_type="Integration", learning_type="Unsupervised",
            label_col="None (evaluation only)", id_col="None",
            metrics=self.config.metrics,
            api_dir=self.config.api_dir, dataset_dir=self.config.dataset_dir,
            data_summary=self.config.data_summary,
            prior_resource_summary=self.config.prior_resource_summary,
            prior_resource_paths=self._resource_paths(),
            prior_plan=prior_plan, prior_output_summary=prior_output_summary,
            background=background,
        )
        response = self.engine.generate(content=query, system_prompt=self.system_prompt, temperature=0.2)
        return self._parse(response)

    def reconsult(
        self, *, task_description: str, background: str,
        current_suggestion: str, current_results: str,
        failure_analysis: str, history: str,
    ) -> Dict[str, Any]:
        query = RECONSULT_TEMPLATE.format(
            task_description=task_description, background=background,
            current_suggestion=current_suggestion, current_results=current_results,
            failure_analysis=failure_analysis, history=history,
        )
        response = self.engine.generate(content=query, system_prompt=self.system_prompt, temperature=0.2)
        return self._parse(response)

    def _parse(self, response: str) -> Dict[str, Any]:
        if self.type == "prior":
            tags = _extract_tags(response, ["TASK_DESCRIPTION", "SUGGESTION", "PRIOR_SCHEMA_JSON"])
            try:
                schema = json.loads(tags.get("PRIOR_SCHEMA_JSON", "{}"))
            except json.JSONDecodeError:
                schema = {}
            return {
                "task_description": tags["TASK_DESCRIPTION"],
                "suggestion": tags["SUGGESTION"],
                "prior_schema": schema,
                "raw": response,
            }
        else:
            tags = _extract_tags(response, ["TASK_DESCRIPTION", "SUGGESTION"])
            return {
                "task_description": tags["TASK_DESCRIPTION"],
                "suggestion": tags["SUGGESTION"],
                "raw": response,
            }

    def _resource_paths(self) -> str:
        names = ["MsigDB.csv", "NeST.tsv", "GO_terms.csv", "Cell_marker_Human.xlsx", "meta_info.csv"]
        return ", ".join(f"{self.config.dataset_dir}/{n}" for n in names)