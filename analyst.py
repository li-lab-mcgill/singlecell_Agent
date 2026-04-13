from __future__ import annotations

import json
import logging
from typing import List

import textgrad as tg

from analyst_prompts import ANALYST_SYSTEM_PROMPT, ANALYST_GUIDANCE_PROMPT
from evaluation_plan import normalize_evaluation_plan
from multieval_types import EvaluatorGuidance, EvaluationGuidance

logger = logging.getLogger(__name__)

EVALUATOR_ROLES = ["biology", "data_science", "model", "prior", "critic"]


class Analyst:
    def __init__(self, engine_name: str):
        self.engine = tg.get_engine(engine_name, max_tokens=5000)

    def generate_evaluation_guidance(
        self,
        goal_and_query: str,
        dataset_profile: str,
        prior_resource_summary: str,
        dataset_rag_context: str = "",
        benchmark_rag_context: str = "",
        marker_db_context: str = "",
    ) -> EvaluationGuidance:
        prompt = ANALYST_GUIDANCE_PROMPT.format(
            goal_and_query=goal_and_query,
            dataset_profile=dataset_profile,
            prior_resource_summary=prior_resource_summary,
            dataset_rag_context=dataset_rag_context or "RAG_DATASET_CONTEXT\n<none>",
            benchmark_rag_context=benchmark_rag_context or "RAG_BENCHMARK_CONTEXT\n<none>",
            marker_db_context=marker_db_context or "(no marker database context available)",
        )

        response = self.engine.generate(
            content=prompt,
            system_prompt=ANALYST_SYSTEM_PROMPT.strip(),
            temperature=0.2,
        )

        return self._parse_response(response, goal_and_query, dataset_profile)

    def _parse_response(
        self, response: str, goal: str, dataset_profile: str
    ) -> EvaluationGuidance:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError("Analyst response is not valid JSON") from None
        normalized_payload = normalize_evaluation_plan(payload)

        guidance_list: List[EvaluatorGuidance] = []
        for entry in normalized_payload.get("guidance_per_evaluator", []):
            role = str(entry.get("evaluator_role", "")).strip()
            if role not in EVALUATOR_ROLES:
                continue
            guidance_list.append(
                EvaluatorGuidance(
                    evaluator_role=role,
                    what_to_look_for=str(entry.get("what_to_look_for", "")),
                    what_good_looks_like=str(entry.get("what_good_looks_like", "")),
                )
            )

        return EvaluationGuidance(
            goal=str(normalized_payload.get("goal", goal)),
            dataset_summary=str(normalized_payload.get("dataset_summary", dataset_profile[:500])),
            guidance_per_evaluator=guidance_list,
            expected_downstream_outputs=str(normalized_payload.get("expected_downstream_outputs", "")),
            query_decomposition=normalized_payload.get("query_decomposition", {}),
            evaluation_experiments=normalized_payload.get("evaluation_experiments", []),
            downstream_requirements=normalized_payload.get("downstream_requirements", {}),
            combined_metric_spec=normalized_payload.get("combined_metric_spec", {}),
        )
