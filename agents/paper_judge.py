"""PaperJudge — parallel LLM paper-level evidence assessor for the Scientist panel.

Runs after retrieve_literature() returns a set of paper summaries. Each paper is
judged against an explicit retrieval_intent + retrieval_goal. PaperJudge does not
decide whether a retrieval is complete; the panelist owns that synthesis.

Usage:
    judge = PaperJudge(engine_name="gpt-4o-mini", client=client)
    labeled = judge.judge(
        papers=summaries,          # list of dicts from _generate_paper_summary
        role="biologist",
        retrieval_goal="evidence_pattern",
        retrieval_intent="How did prior studies define T cells?",
        threshold=0.75,
    )
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from agents.prompt_loader import load_updated_prompt

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]


_JUDGE_SYSTEM_PROMPT = load_updated_prompt("paper_judge_system")
_JUDGE_PROMPT = load_updated_prompt("paper_judge")


# ---------------------------------------------------------------------------
# PaperJudge
# ---------------------------------------------------------------------------

class PaperJudge:
    """Parallel LLM relevance filter.

    Args:
        engine_name: Model name (e.g. "gpt-4o-mini"). Use a fast/cheap model —
                     this runs one call per paper.
        client:      OpenAI-compatible client. If None, creates one from env.
        max_workers: Number of parallel LLM calls (default 10).
        threshold:   Minimum confidence to keep a paper (default 0.75).
    """

    def __init__(
        self,
        *,
        engine_name: str,
        client: Any | None = None,
        max_workers: int = 10,
        threshold: float = 0.75,
    ):
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required for PaperJudge")
        self.client = client or OpenAI()
        self.engine_name = engine_name
        self.max_workers = max_workers
        self.threshold = threshold

    def judge(
        self,
        *,
        papers: list[dict[str, Any]],
        role: str,
        retrieval_intent: str | None = None,
        retrieval_goal: str | None = None,
        base_query: str | None = None,
        question: str | None = None,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Judge a list of paper summaries for relevance.

        Args:
            papers:    List of paper summary dicts (title, objective, background,
                       analysis, main_findings, limitations, doc_id, url, published,
                       source, abstract, ...).
            role:      Panelist role.
            retrieval_intent: Specific question this paper should help answer.
            retrieval_goal: Why this literature is being retrieved.
            base_query: Search phrase used to fetch candidates.
            question:  Backward-compatible alias for retrieval_intent.
            threshold: Override instance threshold for this call.

        Returns:
            Filtered list of papers that passed relevance judgment, each with
            additional fields: relevant, confidence, reason, evidence_contribution,
            covered_evidence_patterns, missing_evidence, suggested_query_terms,
            suggested_exclusions.
            Papers with user_provided=True bypass the threshold but still get labeled.
        """
        cutoff = threshold if threshold is not None else self.threshold
        role_key = role.lower().strip()
        intent = str(retrieval_intent or question or base_query or "").strip()
        goal = _normalize_retrieval_goal(retrieval_goal)
        query = str(base_query or intent).strip()

        if not papers:
            return []

        # Run all judgments in parallel
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(papers))) as pool:
            future_map = {
                pool.submit(
                    self._judge_one,
                    paper=paper,
                    role=role_key,
                    retrieval_goal=goal,
                    retrieval_intent=intent,
                    base_query=query,
                ): paper
                for paper in papers
            }
            results: list[dict[str, Any]] = []
            for future in as_completed(future_map):
                paper = future_map[future]
                verdict = future.result()
                labeled = {**paper, **verdict}
                results.append(labeled)

        # Sort to preserve original order (futures complete out of order)
        paper_index = {str(p.get("doc_id") or ""): i for i, p in enumerate(papers)}
        results.sort(key=lambda r: paper_index.get(str(r.get("doc_id") or ""), 0))

        # Filter: keep relevant + confident, always keep user-provided anchors
        kept = [
            r for r in results
            if r.get("user_provided") or (
                r.get("relevant", False) and float(r.get("confidence", 0.0)) >= cutoff
            )
        ]
        return kept

    def _judge_one(
        self,
        *,
        paper: dict[str, Any],
        role: str,
        retrieval_goal: str,
        retrieval_intent: str,
        base_query: str,
    ) -> dict[str, Any]:
        """Single LLM relevance call for one paper. Returns verdict dict."""
        prompt = _JUDGE_PROMPT.format(
            role=role,
            retrieval_goal=retrieval_goal,
            retrieval_intent=retrieval_intent,
            base_query=base_query,
            doc_id=str(paper.get("doc_id", "") or ""),
            title=str(paper.get("title", "") or ""),
            published=str(paper.get("published", "") or ""),
            source=str(paper.get("source", "") or ""),
            url=str(paper.get("url", "") or ""),
            full_text_status=str(paper.get("full_text_status", "") or "abstract_only"),
            abstract=str(paper.get("abstract", "") or ""),
            objective=str(paper.get("objective", "") or paper.get("abstract", "") or ""),
            background=str(paper.get("background", "") or ""),
            method_and_dataset=str(paper.get("method_and_dataset", "") or ""),
            analysis=str(paper.get("analysis", "") or paper.get("key_methods", "") or ""),
            benchmark_methods=str(paper.get("benchmark_methods", "") or ""),
            main_findings=str(paper.get("main_findings", "") or ""),
            limitations=str(paper.get("limitations", "") or ""),
            figure_captions=str(paper.get("figure_captions", "") or ""),
        )
        try:
            response = self.client.responses.create(
                model=self.engine_name,
                input=[
                    {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            text = str(getattr(response, "output_text", "") or "").strip()
            if not text:
                for item in getattr(response, "output", []):
                    content = getattr(item, "content", None)
                    if isinstance(content, str):
                        text = content
                        break
                    elif isinstance(content, list):
                        for part in content:
                            t = getattr(part, "text", None)
                            if isinstance(t, str):
                                text = t
                                break
            verdict = _parse_verdict(text)
            return _apply_confidence_policy(verdict, paper=paper, retrieval_goal=retrieval_goal)
        except Exception as exc:
            return _empty_verdict(reason=f"Judge error: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce value to float, tolerating None/non-numeric without raising."""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    """Coerce value to bool, tolerating stringy booleans like "false"."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def _parse_verdict(text: str) -> dict[str, Any]:
    """Parse LLM verdict JSON with fallbacks."""
    cleaned = str(text or "").strip()
    # Strip markdown fences
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    # Try direct JSON parse
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return {
                "relevant": _as_bool(payload.get("relevant", False)),
                "confidence": _safe_float(payload.get("confidence"), 0.0),
                "retrieval_intent_fit": _normalize_intent_fit(payload.get("retrieval_intent_fit") or payload.get("intent_fit")),
                "usefulness": _normalize_retrieval_goal(payload.get("usefulness")),
                "return_to_panelist": False,
                "reason": str(payload.get("reason", "") or ""),
                "evidence_contribution": str(payload.get("evidence_contribution") or payload.get("useful_evidence_patterns") or ""),
                "covered_evidence_patterns": _valid_evidence_patterns(payload.get("covered_evidence_patterns") or payload.get("useful_evidence_patterns") or []),
                "missing_evidence": _string_list(payload.get("missing_evidence") or payload.get("missing_information") or []),
                "suggested_query_terms": _string_list(payload.get("suggested_query_terms", [])),
                "suggested_exclusions": _string_list(payload.get("suggested_exclusions", [])),
            }
    except Exception:
        pass
    # Fallback: regex extraction
    relevant = bool(re.search(r'"relevant"\s*:\s*true', cleaned, re.IGNORECASE))
    conf_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', cleaned)
    confidence = float(conf_match.group(1)) if conf_match else 0.0
    reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', cleaned)
    reason = reason_match.group(1) if reason_match else ""
    return {
        "relevant": relevant,
        "confidence": confidence,
        "retrieval_intent_fit": "direct" if relevant and confidence >= 0.75 else "partial" if relevant else "off_target",
        "usefulness": "",
        "return_to_panelist": relevant,
        "reason": reason,
        "evidence_contribution": "",
        "covered_evidence_patterns": [],
        "missing_evidence": [],
        "suggested_query_terms": [],
        "suggested_exclusions": [],
    }


_VALID_RETRIEVAL_GOALS = {
    "method_selection",
    "evidence_pattern",
    "prior_findings",
    "contradiction",
    "validation",
    "extension_opportunity",
    "broad_background",
}

_VALID_EVIDENCE_PATTERN_FIELDS = {
    "entity_definition",
    "comparison_design",
    "statistical_unit",
    "effect_metric",
    "controls_covariates",
    "validation",
    "boundary_conditions",
}

_VALID_INTENT_FIT = {"direct", "partial", "weak", "off_target"}


def _normalize_retrieval_goal(value: str | None) -> str:
    goal = str(value or "").strip().lower()
    return goal if goal in _VALID_RETRIEVAL_GOALS else "prior_findings"


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _valid_evidence_patterns(value: Any) -> list[str]:
    return [item for item in _string_list(value) if item in _VALID_EVIDENCE_PATTERN_FIELDS]


def _normalize_intent_fit(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in _VALID_INTENT_FIT else "off_target"


def _empty_verdict(*, reason: str = "") -> dict[str, Any]:
    return {
        "relevant": False,
        "confidence": 0.0,
        "retrieval_intent_fit": "off_target",
        "usefulness": "",
        "return_to_panelist": False,
        "reason": reason,
        "evidence_contribution": "",
        "covered_evidence_patterns": [],
        "missing_evidence": [],
        "suggested_query_terms": [],
        "suggested_exclusions": [],
    }


def _apply_confidence_policy(
    verdict: dict[str, Any],
    *,
    paper: dict[str, Any],
    retrieval_goal: str,
) -> dict[str, Any]:
    """Cap abstract-only confidence unless prior-findings retrieval can use abstracts."""
    result = dict(verdict)
    full_text_status = str(paper.get("full_text_status") or "abstract_only")
    if full_text_status == "abstract_only" and retrieval_goal not in {"prior_findings", "broad_background"}:
        result["confidence"] = min(float(result.get("confidence", 0.0) or 0.0), 0.70)
        if result.get("missing_evidence") == []:
            result["missing_evidence"] = ["Full text was not available; detailed evidence pattern is incomplete."]
    if not result.get("retrieval_intent_fit") or result.get("retrieval_intent_fit") == "off_target":
        confidence = float(result.get("confidence", 0.0) or 0.0)
        if result.get("relevant") and confidence >= 0.75:
            result["retrieval_intent_fit"] = "direct"
        elif result.get("relevant") and confidence > 0:
            result["retrieval_intent_fit"] = "partial"
    result["return_to_panelist"] = bool(result.get("relevant")) and result.get("retrieval_intent_fit") in {"direct", "partial"}
    return result
