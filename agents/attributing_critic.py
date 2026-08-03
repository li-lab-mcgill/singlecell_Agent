"""AttributingCritic — per-step attribution of DAG/coder results.

Runs after AnalyzerPanel.analyze() in each phase of the ResearchLoop.
Produces per-step attributions with judgment, contribution score, and lesson candidates.

Lesson candidates are passed to the ShortTermMemory (Gap 7) which accumulates them
across phases. At session end, LongTermMemory (Gap 8) compresses the best ones.

Usage:
    critic = AttributingCritic(
        engine_name="gpt-4o",
        client=client,
        result_dir="results/critic",
    )
    attributions = critic.attribute(
        stage_results=dag_result,
        research_plan=research_plan,
        prior_phase_metrics={"ARI": 0.62, "bio_lisi": 0.55},
        phase_number=2,
    )
    # attributions["attributions"] → list of per-step attribution dicts
    # attributions["key_lessons"]  → list of generalizable lessons
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

from agents.llm_utils import single_llm_call
from prompts.critic_prompts import CRITIC_SYSTEM, CRITIC_ATTRIBUTION_PROMPT


class AttributingCritic:
    """Per-step critic that judges execution results against research plan goals.

    Args:
        engine_name:  LLM model to use.
        client:       OpenAI-compatible client.
        result_dir:   Directory for saved attribution JSON files.
    """

    def __init__(
        self,
        *,
        engine_name: str,
        client: Any | None = None,
        result_dir: str | Path,
    ):
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required for AttributingCritic")
        self.client = client or OpenAI()
        self.engine_name = engine_name
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def attribute(
        self,
        *,
        stage_results: dict[str, Any],
        research_plan: dict[str, Any] | str,
        prior_phase_metrics: dict[str, Any] | None = None,
        phase_number: int,
    ) -> dict[str, Any]:
        """Attribute per-step results for a single research phase.

        Args:
            stage_results:        dict from DagExecutor or CoderAgent — all step outputs.
            research_plan:        dict (or JSON string) with steps, goals, and visualizations.
            prior_phase_metrics:  metrics from the previous phase for delta computation.
                                  Pass None or {} for phase 1.
            phase_number:         Current phase number.

        Returns:
            {
              "phase": <int>,
              "attributions": [<per-step attribution dicts>],
              "overall_phase_judgment": "GOOD" | "BAD" | "NEEDS_REVISION",
              "key_lessons": [<generalizable lesson strings>],
            }
        """
        prior_metrics = prior_phase_metrics or {}
        prior_phase_num = phase_number - 1

        plan_str = _to_str(research_plan)
        results_str = _to_str(stage_results)
        prior_str = (
            json.dumps(prior_metrics, indent=2, ensure_ascii=False)
            if prior_metrics
            else f"(no prior metrics — this is phase {phase_number})"
        )

        prompt = CRITIC_ATTRIBUTION_PROMPT.format(
            phase_number=phase_number,
            research_plan=plan_str,
            stage_results=results_str,
            prior_phase_number=prior_phase_num,
            prior_phase_metrics=prior_str,
        )

        text = single_llm_call(self.client, self.engine_name, prompt, system=CRITIC_SYSTEM)
        result = _extract_tag_json(text, "CRITIC")

        self._save(f"phase{phase_number}_attributions", result)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save(self, name: str, data: Any) -> None:
        path = self.result_dir / f"{name}.json"
        payload = data if isinstance(data, (dict, list)) else {"raw": str(data)}
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _to_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return str(value or "").strip()


def _extract_tag_json(text: str, tag: str) -> dict[str, Any]:
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return {"raw": text, "parse_error": f"No <{tag}> block found"}
    raw = match.group(1).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        repaired = re.sub(r'("|\]|\})\s*\n(\s*")', r'\1,\n\2', raw)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return {"raw": raw, "parse_error": "JSON decode failed"}
