"""ShortTermMemory — accumulates phase traces within a single session.

Scope: one session, all phases. Grows as phases complete.
At session end, call compress() to hand off to LongTermMemory.

Per-phase record schema:
  session_id, phase, research_plan, what_changed_from_prior_phase,
  dag_result, metrics, what_improved, what_remained_problematic,
  step_attributions, analyzer_report, open_questions

Usage:
    mem = ShortTermMemory(session_id="S03", result_dir="results/memory")

    # After each phase:
    mem.add_phase(
        phase_number=1,
        research_plan=research_plan,
        dag_result=dag_result,
        analyzer_report=analyzer_report,
        step_attributions=attributions,   # from AttributingCritic, or None
    )

    # At session end:
    trace = mem.get_trace()               # list of all phase records
    summary = mem.format_for_scientists() # human-readable summary for prompt injection
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_KNOWN_METRICS = {
    "ARI", "NMI", "bio_lisi", "batch_lisi", "silhouette",
    "marker_specificity", "n_clusters", "n_cells", "pct_mito", "doublet_rate",
}


class ShortTermMemory:
    """Accumulates phase-level traces within one session.

    Args:
        session_id:  Unique session identifier (e.g. "S03").
        result_dir:  Directory for persisted JSON (trace survives crashes).
    """

    def __init__(self, *, session_id: str, result_dir: str | Path):
        self.session_id = session_id
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self._phases: list[dict[str, Any]] = []
        self._retrieval_evidence: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_phase(
        self,
        *,
        phase_number: int,
        research_plan: dict[str, Any] | str,
        dag_result: dict[str, Any],
        analyzer_report: dict[str, Any],
        step_attributions: dict[str, Any] | None = None,
    ) -> None:
        """Record a completed phase.

        Args:
            phase_number:      Phase index (1-based).
            research_plan:     The plan that was executed (dict or JSON str).
            dag_result:        Raw output from DagExecutor or CoderAgent.
            analyzer_report:   Output from AnalyzerPanel.analyze().
            step_attributions: Output from AttributingCritic.attribute(), or None.
        """
        plan = _ensure_dict(research_plan)
        metrics = _extract_metrics(analyzer_report)

        # Compute what changed relative to prior phase
        prior = self._phases[-1] if self._phases else None
        what_changed = _describe_plan_change(
            prior_plan=prior["research_plan"] if prior else None,
            current_plan=plan,
        )
        what_improved, what_remained = _describe_metric_delta(
            prior_metrics=prior["metrics"] if prior else {},
            current_metrics=metrics,
        )

        open_questions = _extract_open_questions(analyzer_report)

        record: dict[str, Any] = {
            "session_id": self.session_id,
            "phase": phase_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "research_plan": plan,
            "what_changed_from_prior_phase": what_changed,
            "dag_result_summary": _summarize_dag_result(dag_result),
            "metrics": metrics,
            "what_improved": what_improved,
            "what_remained_problematic": what_remained,
            "step_attributions": (step_attributions or {}).get("attributions", []),
            "key_lessons_this_phase": (step_attributions or {}).get("key_lessons", []),
            "analyzer_summary": _extract_analyzer_summary(analyzer_report),
            "open_questions": open_questions,
        }
        self._phases.append(record)
        self._persist(phase_number, record)

    def get_trace(self) -> list[dict[str, Any]]:
        """Return all phase records in order."""
        return list(self._phases)

    def add_retrieval_evidence(self, evidence: dict[str, Any]) -> None:
        """Record satisfied literature retrieval evidence within this session."""
        if not isinstance(evidence, dict):
            return
        record = {
            "session_id": self.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **evidence,
        }
        self._retrieval_evidence.append(record)
        path = self.result_dir / "retrieval_evidence_trace.json"
        path.write_text(
            json.dumps(self._retrieval_evidence, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def get_prior_metrics(self, phase_number: int) -> dict[str, Any]:
        """Return metrics from the phase immediately before phase_number."""
        for rec in reversed(self._phases):
            if rec["phase"] < phase_number:
                return rec.get("metrics", {})
        return {}

    def format_for_scientists(self, *, max_phases: int | None = None) -> str:
        """Format the phase trace as a human-readable block for prompt injection.

        Args:
            max_phases: If set, include only the last N phases (to manage context length).
        """
        phases = self._phases
        if max_phases is not None:
            phases = phases[-max_phases:]
        if not phases:
            if not self._retrieval_evidence:
                return "(no prior phases in this session)"
            phases = []

        lines = ["SHORT-TERM SESSION MEMORY (all prior phases this session):"]
        if self._retrieval_evidence:
            lines.append("\n--- Retrieval evidence ---")
            for rec in self._retrieval_evidence[-10:]:
                lines.append(
                    f"{rec.get('role', 'unknown')} {rec.get('retrieval_goal', '')}: "
                    f"{rec.get('retrieval_intent', '')}"
                )
                assessment = rec.get("panelist_assessment") or {}
                if isinstance(assessment, dict) and assessment.get("what_was_learned"):
                    lines.append(f"Learned: {assessment.get('what_was_learned')}")
        for rec in phases:
            ph = rec["phase"]
            lines.append(f"\n--- Phase {ph} ---")
            if rec.get("what_changed_from_prior_phase"):
                lines.append(f"Changes from prior: {rec['what_changed_from_prior_phase']}")
            if rec.get("metrics"):
                metric_str = ", ".join(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                                       for k, v in rec["metrics"].items())
                lines.append(f"Metrics: {metric_str}")
            if rec.get("what_improved"):
                lines.append(f"Improved: {rec['what_improved']}")
            if rec.get("what_remained_problematic"):
                lines.append(f"Still problematic: {rec['what_remained_problematic']}")
            if rec.get("key_lessons_this_phase"):
                for lesson in rec["key_lessons_this_phase"]:
                    lines.append(f"Lesson: {lesson}")
            if rec.get("analyzer_summary"):
                lines.append(f"Analyzer: {rec['analyzer_summary']}")
            if rec.get("open_questions"):
                for q in rec["open_questions"][:3]:
                    if isinstance(q, dict):
                        lines.append(f"Open question: {q.get('question', q)}")
                    else:
                        lines.append(f"Open question: {q}")
        return "\n".join(lines)

    def format_for_adversary(self) -> str:
        """Format a compact version of the trace for the AdversarialPanelist.

        Shows only: what was tried, what changed, what failed.
        """
        if not self._phases:
            return "(no prior phases in this session)"
        lines = ["PRIOR PHASE HISTORY (what was already tried):"]
        for rec in self._phases:
            ph = rec["phase"]
            steps = rec.get("research_plan", {}).get("steps", [])
            step_ids = [s.get("step_id", f"step_{i+1}") if isinstance(s, dict) else str(s)
                        for i, s in enumerate(steps)]
            lines.append(
                f"Phase {ph}: [{', '.join(step_ids)}] → "
                f"{'improved' if rec.get('what_improved') else 'no improvement'}"
            )
            if rec.get("what_remained_problematic"):
                lines.append(f"  Still unresolved: {rec['what_remained_problematic']}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self, phase_number: int, record: dict[str, Any]) -> None:
        path = self.result_dir / f"phase{phase_number}_trace.json"
        path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        # Also write full trace for easy inspection
        trace_path = self.result_dir / "full_trace.json"
        trace_path.write_text(
            json.dumps(self._phases, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {"raw": str(value)}


def _extract_metrics(analyzer_report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(analyzer_report, dict):
        return {}
    if isinstance(analyzer_report.get("metrics"), dict):
        return {k: v for k, v in analyzer_report["metrics"].items()
                if isinstance(v, (int, float))}
    return {k: v for k, v in analyzer_report.items()
            if k in _KNOWN_METRICS and isinstance(v, (int, float))}


def _describe_plan_change(
    prior_plan: dict[str, Any] | None,
    current_plan: dict[str, Any],
) -> str:
    if prior_plan is None:
        return "Initial plan (no prior phase)"
    prior_steps = set(
        s.get("step_id", "") if isinstance(s, dict) else str(s)
        for s in prior_plan.get("steps", [])
    )
    current_steps = set(
        s.get("step_id", "") if isinstance(s, dict) else str(s)
        for s in current_plan.get("steps", [])
    )
    added = current_steps - prior_steps
    removed = prior_steps - current_steps
    parts = []
    if added:
        parts.append(f"added [{', '.join(sorted(added))}]")
    if removed:
        parts.append(f"removed [{', '.join(sorted(removed))}]")
    if not parts:
        return "Same steps as prior phase (parameter or approach change)"
    return "; ".join(parts)


def _describe_metric_delta(
    prior_metrics: dict[str, Any],
    current_metrics: dict[str, Any],
) -> tuple[str, str]:
    """Returns (what_improved, what_remained_problematic) as human-readable strings."""
    if not prior_metrics or not current_metrics:
        return "", ""

    improved: list[str] = []
    remained: list[str] = []

    for key in current_metrics:
        if key not in prior_metrics:
            continue
        cur = float(current_metrics[key])
        pri = float(prior_metrics[key])
        delta = cur - pri
        if abs(delta) < 0.005:
            continue
        if delta > 0:
            improved.append(f"{key} +{delta:.3f} ({pri:.3f}→{cur:.3f})")
        else:
            remained.append(f"{key} {delta:.3f} ({pri:.3f}→{cur:.3f})")

    return (
        "; ".join(improved) if improved else "",
        "; ".join(remained) if remained else "",
    )


def _extract_analyzer_summary(analyzer_report: dict[str, Any]) -> str:
    for key in ("summary", "narrative", "conclusion", "finding", "interpretation"):
        val = analyzer_report.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:300]
    return ""


def _extract_open_questions(analyzer_report: dict[str, Any]) -> list[Any]:
    for key in ("open_questions", "unresolved", "remaining_questions", "gaps"):
        val = analyzer_report.get(key)
        if isinstance(val, list):
            return val[:5]
    return []


def _summarize_dag_result(dag_result: dict[str, Any]) -> dict[str, Any]:
    """Extract a compact summary of dag_result to avoid storing giant dicts."""
    if not isinstance(dag_result, dict):
        return {"raw": str(dag_result)[:200]}
    return {
        "status": dag_result.get("status"),
        "best_path_id": (dag_result.get("best_path") or {}).get("path_id"),
        "n_stages": len((dag_result.get("best_path") or {}).get("stages", [])),
        "error": dag_result.get("error"),
    }
