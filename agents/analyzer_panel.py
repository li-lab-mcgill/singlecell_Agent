"""Analyzer Panel — interprets DAG execution results.

Two-round structure:
  Round 1a: ResultsInterpreter (runs first — reads outputs + interprets figures)
  Round 1b: LiteratureGrounder + DatabaseValidator in parallel
            (both read ResultsInterpreter output before starting)
  Round 2:  AnalyzerMediator (single LLM call — synthesizes all outputs)

The final analyzer report is passed to ScientistPanel.update() to decide
whether to continue, pivot, or conclude.

Usage:
    panel = AnalyzerPanel(
        engine_name="gpt-4o",
        fast_engine_name="gpt-4o-mini",
        rag_store=store,
        result_dir="results/analyzer",
        client=client,
    )
    report = panel.analyze(
        user_question="What cell types drive inflammation in IBD?",
        research_plan={"steps": [...], "required_visualizations": [...]},
        dag_result=dag_result_dict,
        figure_paths=["/path/to/umap.png", "/path/to/dotplot.png"],
        working_model={"consensus_hypothesis": "...", ...},
        phase_number=1,
    )
    # report["results_summary"], report["hypothesis_status"], etc.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

from agents.llm_utils import single_llm_call
from agents.paper_judge import PaperJudge
from agents.runner import ToolCallingAgentRunner
from agents.tool_base import AgentToolRegistry
from agents.analyzer_tools import (
    build_results_interpreter_registry,
    build_literature_grounder_registry,
    build_database_validator_registry,
)
from rag.literature_retriever import LiteratureRetriever
from rag.store_backend import RAGStore
from prompts.analyzer_prompts import (
    ANALYZER_SHARED_SYSTEM,
    RESULTS_INTERPRETER_PROMPT,
    LITERATURE_GROUNDER_PROMPT,
    DATABASE_VALIDATOR_PROMPT,
    ANALYZER_MEDIATOR_PROMPT,
)


class AnalyzerPanel:
    """Orchestrates the Analyzer Panel.

    Round 1a: ResultsInterpreter (solo — interprets figures and numerical outputs)
    Round 1b: LiteratureGrounder + DatabaseValidator (parallel, both see Round 1a output)
    Round 2:  AnalyzerMediator (single LLM call)
    """

    def __init__(
        self,
        *,
        engine_name: str,
        fast_engine_name: str | None = None,
        vlm_engine_name: str | None = None,
        rag_store: RAGStore,
        result_dir: str | Path,
        client: Any | None = None,
    ):
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required")
        self.client = client or OpenAI()
        self.engine_name = engine_name
        self.fast_engine_name = fast_engine_name or engine_name
        # VLM for figure interpretation — use gpt-4o or caller-specified model
        self.vlm_engine_name = vlm_engine_name or "gpt-4o"
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)

        self.retriever = LiteratureRetriever(
            rag_store=rag_store,
            engine_name=self.fast_engine_name,
            client=self.client,
            cache_dir=self.result_dir / "lit_cache",
        )
        self.judge = PaperJudge(
            engine_name=self.fast_engine_name,
            client=self.client,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        *,
        user_question: str,
        research_plan: dict[str, Any] | str,
        dag_result: dict[str, Any] | str,
        figure_paths: list[str] | None = None,
        working_model: dict[str, Any] | str,
        phase_number: int,
    ) -> dict[str, Any]:
        """Run the full analyzer panel. Returns analyzer report dict."""
        research_plan_str = _to_str(research_plan)
        dag_result_str = _to_str(_summarize_dag_result(dag_result))
        working_model_str = _to_str(working_model)
        figure_paths_str = _format_figure_paths(figure_paths or [])

        # Round 1a: ResultsInterpreter — runs first (interprets figures + outputs)
        results_output = self._run_results_interpreter(
            user_question=user_question,
            research_plan_str=research_plan_str,
            dag_result_str=dag_result_str,
            figure_paths_str=figure_paths_str,
            working_model_str=working_model_str,
            phase_number=phase_number,
        )
        self._save(f"phase{phase_number}_round1a_results_interpreter", {"output": results_output})

        # Round 1b: LiteratureGrounder + DatabaseValidator in parallel
        # Both receive ResultsInterpreter output
        lit_output, db_output = self._run_round1b_parallel(
            user_question=user_question,
            research_plan_str=research_plan_str,
            working_model_str=working_model_str,
            results_interpreter_output=results_output,
            phase_number=phase_number,
        )
        self._save(f"phase{phase_number}_round1b_literature_grounder", {"output": lit_output})
        self._save(f"phase{phase_number}_round1b_database_validator", {"output": db_output})

        # Round 2: AnalyzerMediator
        report = self._run_mediator(
            user_question=user_question,
            research_plan_str=research_plan_str,
            dag_result_str=dag_result_str,
            working_model_str=working_model_str,
            results_output=results_output,
            literature_output=lit_output,
            database_output=db_output,
            phase_number=phase_number,
        )
        self._save(f"phase{phase_number}_round2_mediator", report)
        return report

    # ------------------------------------------------------------------
    # Round 1a — ResultsInterpreter
    # ------------------------------------------------------------------

    def _run_results_interpreter(
        self,
        *,
        user_question: str,
        research_plan_str: str,
        dag_result_str: str,
        figure_paths_str: str,
        working_model_str: str,
        phase_number: int,
    ) -> str:
        prompt = (
            RESULTS_INTERPRETER_PROMPT.strip()
            + "\n\nORIGINAL USER QUESTION:\n\n" + user_question
            + "\n\nRESEARCH PLAN THAT WAS EXECUTED (steps + required visualizations):\n\n" + research_plan_str
            + "\n\nANALYSIS OUTPUTS (dag_result summary):\n\n" + dag_result_str
            + "\n\nFIGURE FILES PRODUCED (paths):\n\n" + figure_paths_str
            + "\n\nWORKING MODEL (hypotheses being tested):\n\n" + working_model_str
        )
        registry = build_results_interpreter_registry(
            retriever=self.retriever,
            judge=self.judge,
            client=self.client,
            vlm_engine=self.vlm_engine_name,
        )
        runner = self._make_runner(
            name=f"results_interpreter_phase{phase_number}",
            registry=registry,
            tag="RESULTS",
        )
        text = runner.run(
            initial_user_input=prompt,
            response_handler=lambda t: _tag_done_handler(t, "RESULTS"),
        )
        return _ensure_str(text)

    # ------------------------------------------------------------------
    # Round 1b — LiteratureGrounder + DatabaseValidator in parallel
    # ------------------------------------------------------------------

    def _run_round1b_parallel(
        self,
        *,
        user_question: str,
        research_plan_str: str,
        working_model_str: str,
        results_interpreter_output: str,
        phase_number: int,
    ) -> tuple[str, str]:

        def _run_lit() -> str:
            prompt = (
                LITERATURE_GROUNDER_PROMPT.strip()
                + "\n\nORIGINAL USER QUESTION:\n\n" + user_question
                + "\n\nRESEARCH PLAN THAT WAS EXECUTED:\n\n" + research_plan_str
                + "\n\nWORKING MODEL (hypotheses being tested):\n\n" + working_model_str
                + "\n\nRESULTS INTERPRETER FINDINGS:\n\n" + results_interpreter_output
            )
            registry = build_literature_grounder_registry(
                retriever=self.retriever,
                judge=self.judge,
            )
            runner = self._make_runner(
                name=f"literature_grounder_phase{phase_number}",
                registry=registry,
                tag="LITERATURE",
            )
            text = runner.run(
                initial_user_input=prompt,
                response_handler=lambda t: _tag_done_handler(t, "LITERATURE"),
            )
            return _ensure_str(text)

        def _run_db() -> str:
            prompt = (
                DATABASE_VALIDATOR_PROMPT.strip()
                + "\n\nORIGINAL USER QUESTION:\n\n" + user_question
                + "\n\nWORKING MODEL (hypotheses being tested):\n\n" + working_model_str
                + "\n\nRESULTS INTERPRETER FINDINGS (what claims emerged from the results):\n\n" + results_interpreter_output
            )
            registry = build_database_validator_registry(
                retriever=self.retriever,
                judge=self.judge,
            )
            runner = self._make_runner(
                name=f"database_validator_phase{phase_number}",
                registry=registry,
                tag="DATABASE",
            )
            text = runner.run(
                initial_user_input=prompt,
                response_handler=lambda t: _tag_done_handler(t, "DATABASE"),
            )
            return _ensure_str(text)

        with ThreadPoolExecutor(max_workers=2) as pool:
            f_lit = pool.submit(_run_lit)
            f_db = pool.submit(_run_db)
            # Collect both results independently so a failure in one does not
            # prevent the other from contributing to the Mediator.
            try:
                lit_output = f_lit.result()
            except Exception as exc:
                lit_output = f"<literature_error>LiteratureGrounder failed: {exc}</literature_error>"
            try:
                db_output = f_db.result()
            except Exception as exc:
                db_output = f"<database_error>DatabaseValidator failed: {exc}</database_error>"

        return lit_output, db_output

    # ------------------------------------------------------------------
    # Round 2 — AnalyzerMediator
    # ------------------------------------------------------------------

    def _run_mediator(
        self,
        *,
        user_question: str,
        research_plan_str: str,
        dag_result_str: str,
        working_model_str: str,
        results_output: str,
        literature_output: str,
        database_output: str,
        phase_number: int,
    ) -> dict[str, Any]:
        prompt = (
            ANALYZER_MEDIATOR_PROMPT.strip()
            + "\n\nORIGINAL USER QUESTION:\n\n" + user_question
            + "\n\nPHASE NUMBER:\n\n" + str(phase_number)
            + "\n\nRESEARCH PLAN THAT WAS EXECUTED:\n\n" + research_plan_str
            + "\n\nDAG / EXECUTION RESULT SUMMARY:\n\n" + dag_result_str
            + "\n\nWORKING MODEL (hypotheses being tested):\n\n" + working_model_str
            + "\n\nRESULTS INTERPRETER OUTPUT:\n\n" + results_output
            + "\n\nLITERATURE GROUNDER OUTPUT:\n\n" + literature_output
            + "\n\nDATABASE VALIDATOR OUTPUT:\n\n" + database_output
        )
        text = single_llm_call(self.client, self.engine_name, prompt)
        return _normalize_analyzer_report(_extract_tag_json(text, "ANALYZER"))

    # ------------------------------------------------------------------
    # Infrastructure
    # ------------------------------------------------------------------

    def _make_runner(
        self,
        name: str,
        registry: AgentToolRegistry,
        tag: str,
    ) -> ToolCallingAgentRunner:
        return ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=ANALYZER_SHARED_SYSTEM.strip(),
            tool_specs=registry.tool_specs(),
            tool_executor=registry.executor(),
            transcript_path=str(self.result_dir / f"{name}_transcript.jsonl"),
            tool_trace_path=str(self.result_dir / f"{name}_tool_trace.jsonl"),
            client=self.client,
            max_iterations=20,
            max_tool_calls=16,
        )

    def _save(self, name: str, data: Any) -> None:
        path = self.result_dir / f"{name}.json"
        payload = data if isinstance(data, (dict, list)) else {"raw": data}
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summarize_dag_result(dag_result: dict[str, Any] | str) -> dict[str, Any]:
    """Extract the most relevant parts of dag_result for the prompt."""
    if isinstance(dag_result, str):
        try:
            dag_result = json.loads(dag_result)
        except Exception:
            return {"raw": dag_result[:3000]}

    if not isinstance(dag_result, dict):
        return {"raw": str(dag_result)[:3000]}

    # Keep best_path summary, artifact paths, and stage results
    summary: dict[str, Any] = {}
    if "best_path" in dag_result:
        bp = dag_result["best_path"]
        stage_results = bp.get("stage_results", [])
        failed_stages = [
            s["stage"] for s in stage_results
            if isinstance(s, dict) and isinstance(s.get("result"), dict)
            and s["result"].get("status") in ("failed", "error")
        ]
        summary["best_path"] = {
            "metrics": bp.get("metrics", {}),
            "objective_score": bp.get("objective_score"),
            "stage_results": stage_results,
            "failed_stages": failed_stages or None,
            "artifacts": bp.get("artifacts", {}),
        }
    if "status" in dag_result:
        summary["status"] = dag_result["status"]
    if "error" in dag_result:
        summary["error"] = dag_result["error"]
    return summary or {"raw": str(dag_result)[:3000]}


_RESULT_VERDICTS = {
    "supported",
    "contradicted",
    "inconclusive",
    "invalid",
    "missing_outputs",
}

_EVIDENCE_REQUIREMENT_STATUSES = {"satisfied", "partial", "missing", "invalid"}

_PROBLEM_STAGES = {
    "none",
    "qc",
    "normalization",
    "feature_selection",
    "embedding",
    "clustering",
    "annotation",
    "abundance",
    "trajectory",
    "velocity",
    "differential_test",
    "visualization",
    "interpretation",
    "unknown",
}

_PROBLEM_TYPES = {
    "none",
    "parameter_error",
    "missing_covariate",
    "invalid_output",
    "weak_validation",
    "wrong_method",
    "unsupported_claim",
    "missing_output",
    "dependency_failure",
    "data_limitation",
    "unknown",
}


def _normalize_analyzer_report(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict):
        report = {"raw": _ensure_str(report), "parse_error": "Analyzer output was not a JSON object"}
    out = dict(report)
    out["results_summary"] = _ensure_str(out.get("results_summary") or out.get("overall_interpretation", ""))
    out["interpretation_loop"] = _as_list(out.get("interpretation_loop"))
    out["claim_updates"] = _normalize_claim_updates(out.get("claim_updates") or out.get("hypothesis_status"))
    out["evidence_requirement_status"] = [
        _normalize_evidence_requirement(item)
        for item in _as_list(out.get("evidence_requirement_status"))
    ]
    out["result_verdict"] = _enum_or_default(
        out.get("result_verdict"),
        allowed=_RESULT_VERDICTS,
        default=_infer_result_verdict(out),
    )
    out["problem_localization"] = _normalize_problem_localization(out.get("problem_localization"))
    out["recommended_plan_changes"] = _as_list(out.get("recommended_plan_changes"))
    out["future_directions"] = _as_list(out.get("future_directions"))
    out["improvements"] = _as_list(out.get("improvements"))
    out["missing_outputs"] = _as_list(out.get("missing_outputs"))
    out["artifact_evidence_index"] = _as_list(out.get("artifact_evidence_index"))
    out.setdefault("literature_context", "")
    out.setdefault("database_evidence", "")
    return out


def _normalize_claim_updates(value: Any) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    allowed = {"supported", "refuted", "inconclusive", "partially_supported"}
    for idx, item in enumerate(_as_list(value)):
        if not isinstance(item, dict):
            item = {"support_summary": _ensure_str(item)}
        status = item.get("status")
        if status == "contradicted":
            status = "refuted"
        updates.append(
            {
                "claim_id": str(item.get("claim_id") or f"C{idx + 1}").strip(),
                "status": _enum_or_default(status, allowed=allowed, default="inconclusive"),
                "support_summary": _ensure_str(item.get("support_summary") or item.get("evidence") or ""),
                "contradicting_evidence": _as_list(item.get("contradicting_evidence")),
                "unresolved_requirements": _as_list(item.get("unresolved_requirements")),
            }
        )
    return updates


def _normalize_evidence_requirement(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {"requirement": _ensure_str(item)}
    return {
        "requirement": _ensure_str(item.get("requirement", "")),
        "status": _enum_or_default(
            item.get("status"),
            allowed=_EVIDENCE_REQUIREMENT_STATUSES,
            default="partial",
        ),
        "evidence": _ensure_str(item.get("evidence", "")),
        "needed_next": _ensure_str(item.get("needed_next", "")),
        "linked_research_step_id": item.get("linked_research_step_id"),
        "linked_tool_step_id": item.get("linked_tool_step_id"),
        "linked_artifact_handle": item.get("linked_artifact_handle"),
    }


def _normalize_problem_localization(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    return {
        "problem_stage": _enum_or_default(value.get("problem_stage"), allowed=_PROBLEM_STAGES, default="unknown"),
        "problem_type": _enum_or_default(value.get("problem_type"), allowed=_PROBLEM_TYPES, default="unknown"),
        "affected_research_step_ids": _as_list(value.get("affected_research_step_ids")),
        "affected_tool_step_ids": _as_list(value.get("affected_tool_step_ids")),
        "affected_artifact_handles": _as_list(value.get("affected_artifact_handles")),
        "nearest_valid_artifact_before_problem": value.get("nearest_valid_artifact_before_problem"),
        "reuse_upstream_possible": _as_bool(value.get("reuse_upstream_possible"), default=True),
    }


def _infer_result_verdict(report: dict[str, Any]) -> str:
    missing_outputs = report.get("missing_outputs")
    if isinstance(missing_outputs, list) and missing_outputs:
        return "missing_outputs"
    requirements = _as_list(report.get("evidence_requirement_status"))
    statuses = {
        str(item.get("status", "")).strip()
        for item in requirements
        if isinstance(item, dict)
    }
    if "invalid" in statuses:
        return "invalid"
    if "missing" in statuses:
        return "missing_outputs"
    hyp = _as_list(report.get("claim_updates") or report.get("hypothesis_status"))
    hyp_statuses = {
        str(item.get("status", "")).strip()
        for item in hyp
        if isinstance(item, dict)
    }
    if "refuted" in hyp_statuses:
        return "contradicted"
    if "supported" in hyp_statuses:
        return "supported"
    return "inconclusive"


def _enum_or_default(value: Any, *, allowed: set[str], default: str) -> str:
    text = str(value or "").strip()
    return text if text in allowed else default


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _format_figure_paths(paths: list[str]) -> str:
    if not paths:
        return "No figures produced."
    return "\n".join(f"- {p}" for p in paths)


def _to_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return str(value or "").strip()


def _ensure_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


# Single source of truth for which alias spellings a given canonical tag accepts.
# Both `_extract_tag_json` (parsing) and `_tag_done_handler` (completion gating) must
# agree on this set — otherwise a model that emits a tolerated alias tag can pass
# extraction but never satisfy the done-handler, exhausting max_iterations.
_TAG_ALIASES: dict[str, list[str]] = {
    "ANALYZER": ["ANALYZER", "ANALYZER_OUTPUT"],
}


def _tag_candidates(tag: str) -> list[str]:
    """Return every tag spelling that should be treated as equivalent to `tag`."""
    candidates = _TAG_ALIASES.get(tag, [tag])
    ordered: list[str] = []
    for candidate in [*candidates, tag]:
        if candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _extract_tag_json(text: str, tag: str) -> dict[str, Any]:
    match = None
    for candidate in _tag_candidates(tag):
        pattern = rf"<{re.escape(candidate)}>(.*?)</{re.escape(candidate)}>"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            break
    if not match:
        return {"raw": text, "parse_error": f"No <{tag}> block found"}
    raw = match.group(1).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Attempt repair: insert missing commas between "} \n  "key" patterns
        repaired = re.sub(r'("|\]|\})\s*\n(\s*")', r'\1,\n\2', raw)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return {"raw": raw, "parse_error": "JSON decode failed"}


def _tag_done_handler(text: str, tag: str) -> dict[str, Any]:
    for candidate in _tag_candidates(tag):
        open_tag = f"<{candidate}>"
        close_tag = f"</{candidate}>"
        if open_tag in text and close_tag in text:
            return {"done": True, "result": text}
    return {
        "done": False,
        "next_user_input": (
            f"Your response must contain a <{tag}>...</{tag}> block "
            f"with your structured output. Please produce it now."
        ),
    }
