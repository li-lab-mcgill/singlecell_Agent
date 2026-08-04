"""LongTermMemory — persists compressed session summaries across sessions.

Design:
  - One JSON file per session in memory/long_term/
  - At session end, compress the full short-term phase trace into a compact record
  - Retrieval: keyword matching over question + task + data_characteristics
  - Confidence updates: when same finding confirmed in later session, confidence rises;
    when it fails to replicate, boundary conditions narrow

Usage:
    ltm = LongTermMemory(
        engine_name="gpt-4o",
        client=client,
        memory_dir="memory/long_term",
    )

    # At session end — compress and save
    record = ltm.compress_and_save(
        session_id="S03",
        user_question="What cell types drive IBD?",
        short_term_trace=mem.get_trace(),   # from ShortTermMemory.get_trace()
        data_summary=data_summary,
    )

    # At session start — load relevant prior experience
    context = ltm.format_prior_experience(
        user_question="What cell types are in this PBMC dataset?",
        data_summary=data_summary,
        max_sessions=3,
    )
    # Inject context into planning prompts
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

from agents.llm_utils import single_llm_call


_LTM_COMPRESS_SYSTEM = """\
You are a scientific memory distiller. Given a full session trace of a single-cell
analysis pipeline run, extract only the most important and generalizable findings.
You are building a growing institutional memory — focus on what is worth knowing
in a future session, not on exhaustive detail.
"""

_LTM_COMPRESS_PROMPT = """\
Compress the following session trace into a long-term memory record.

SESSION ID: {session_id}
USER QUESTION: {user_question}
DATA SUMMARY: {data_summary}

FULL PHASE TRACE:
{phase_trace}

Produce a compact, structured memory record. Focus on:
1. The best finding (most confident biological conclusion)
2. The best method path (tools/parameters that worked best)
3. Key decision points (what changed between phases and why it mattered)
4. Boundary conditions (data characteristics that determine when this approach works)
5. Open questions (what remains unresolved)
6. Lesson candidates (generalizable rules for future sessions)

Produce ONLY valid JSON:
{{
  "session_id": "{session_id}",
  "question": "{user_question}",
  "task": "<primary task from: rna_cell_type_annotation, rna_clustering, rna_batch_correction, rna_differential_expression, rna_trajectory, rna_dimensionality_reduction, or other>",
  "data_characteristics": {{
    "modality": "<RNA | ATAC | multiome | other>",
    "n_cells": <int or null>,
    "n_donors": <int or null>,
    "tissue": "<tissue type or null>",
    "disease": "<disease or healthy or null>"
  }},
  "best_finding": "<most confident biological conclusion, 1-2 sentences>",
  "best_method_path": "<tool sequence that produced the best result, e.g. scVI → BBKNN → Leiden 0.3>",
  "best_metrics": {{<metric_name>: <value>}},
  "key_decision_points": [
    {{
      "phase": <int>,
      "change": "<what changed>",
      "effect": "<quantified effect>"
    }}
  ],
  "boundary_conditions": ["<condition that determines when this approach applies or fails>"],
  "open_questions": ["<unresolved question>"],
  "lesson_candidates": [
    {{
      "when_to_use": "<conditions>",
      "content": "<what to do or avoid>",
      "confidence": <float 0-1>
    }}
  ],
  "confidence": <float 0-1>,
  "continues_from": null,
  "date": "{date_today}"
}}
"""


class LongTermMemory:
    """Persists and retrieves compressed session summaries.

    Args:
        engine_name:  LLM model for compression (use a capable model).
        client:       OpenAI-compatible client.
        memory_dir:   Directory for session JSON files (persists across sessions).
    """

    def __init__(
        self,
        *,
        engine_name: str,
        client: Any | None = None,
        memory_dir: str | Path = "memory/long_term",
    ):
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required for LongTermMemory")
        self.client = client or OpenAI()
        self.engine_name = engine_name
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Load existing records into memory
        self._records: list[dict[str, Any]] = self._load_all()

    # ------------------------------------------------------------------
    # Write path (session end)
    # ------------------------------------------------------------------

    def compress_and_save(
        self,
        *,
        session_id: str,
        user_question: str,
        short_term_trace: list[dict[str, Any]],
        data_summary: dict[str, Any] | str,
        continues_from: str | None = None,
    ) -> dict[str, Any]:
        """Compress a full short-term phase trace into a long-term record and save it.

        Args:
            session_id:        Unique session ID.
            user_question:     The scientific question answered in this session.
            short_term_trace:  List of phase records from ShortTermMemory.get_trace().
            data_summary:      Data profile (from workspace_profiler or ResearchLoop).
            continues_from:    Session ID this session continues from, if any.

        Returns:
            The compressed session record dict.
        """
        # Skip if already saved
        if any(r.get("session_id") == session_id for r in self._records):
            return next(r for r in self._records if r.get("session_id") == session_id)

        data_str = _to_str(data_summary)
        trace_str = json.dumps(short_term_trace, indent=2, ensure_ascii=False, default=str)

        prompt = _LTM_COMPRESS_PROMPT.format(
            session_id=session_id,
            user_question=user_question,
            data_summary=data_str[:1000],
            phase_trace=trace_str[:8000],  # truncate very long traces
            date_today=date.today().isoformat(),
        )

        text = single_llm_call(self.client, self.engine_name, prompt, system=_LTM_COMPRESS_SYSTEM)
        record = _parse_json(text)
        if not isinstance(record, dict):
            record = {"session_id": session_id, "question": user_question, "raw": text}

        record["session_id"] = session_id
        if continues_from is not None:
            record["continues_from"] = continues_from
        else:
            record.setdefault("continues_from", None)

        self._records.append(record)
        self._save_record(session_id, record)
        return record

    # ------------------------------------------------------------------
    # Read path (session start)
    # ------------------------------------------------------------------

    def format_prior_experience(
        self,
        *,
        user_question: str,
        data_summary: dict[str, Any] | str | None = None,
        max_sessions: int = 3,
    ) -> str:
        """Format relevant prior sessions as a prompt-injectable context block.

        Matches by keyword overlap in question + task + data_characteristics.
        Returns empty string if no relevant sessions found.

        Args:
            user_question:  The current session's question.
            data_summary:   Current session's data profile (for characteristic matching).
            max_sessions:   Maximum number of prior sessions to include.
        """
        if not self._records:
            return ""

        scored = [
            (self._relevance_score(r, user_question, data_summary), r)
            for r in self._records
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [r for score, r in scored if score > 0][:max_sessions]
        if not top:
            return ""

        lines = ["PRIOR EXPERIENCE (from long-term memory — earlier sessions on similar questions):"]
        for r in top:
            sid = r.get("session_id", "?")
            q = r.get("question", "")[:80]
            dc = r.get("data_characteristics", {})
            dc_str = ", ".join(f"{k}={v}" for k, v in dc.items() if v is not None)
            lines.append(f"\nSession {sid} — {q}")
            if dc_str:
                lines.append(f"  Data: {dc_str}")
            if r.get("best_finding"):
                lines.append(f"  Best finding: {r['best_finding']}")
            if r.get("best_method_path"):
                lines.append(f"  Best method: {r['best_method_path']}")
            if r.get("best_metrics"):
                metrics_str = ", ".join(
                    f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
                    for k, v in r["best_metrics"].items()
                )
                lines.append(f"  Metrics: {metrics_str}")
            for kd in r.get("key_decision_points", [])[:2]:
                lines.append(f"  Phase {kd.get('phase','?')}: {kd.get('change','?')} → {kd.get('effect','?')}")
            for bc in r.get("boundary_conditions", [])[:2]:
                lines.append(f"  Boundary: {bc}")
            for lc in r.get("lesson_candidates", [])[:2]:
                conf = f" (confidence {lc.get('confidence',0):.2f})" if "confidence" in lc else ""
                lines.append(f"  Lesson{conf}: {lc.get('content','')}")
            if r.get("open_questions"):
                lines.append(f"  Still open: {r['open_questions'][0]}")
        return "\n".join(lines)

    def get_all_records(self) -> list[dict[str, Any]]:
        """Return all stored session records."""
        return list(self._records)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _relevance_score(
        self,
        record: dict[str, Any],
        user_question: str,
        data_summary: Any,
    ) -> float:
        """Simple keyword overlap score. Higher = more relevant."""
        score = 0.0
        q_words = set(re.findall(r"\w+", user_question.lower()))
        rec_words = set(re.findall(r"\w+", str(record.get("question", "")).lower()))
        overlap = len(q_words & rec_words) / max(len(q_words), 1)
        score += overlap * 2.0  # question overlap is most important

        # Boost for matching data characteristics
        if isinstance(data_summary, dict) and isinstance(record.get("data_characteristics"), dict):
            dc = record["data_characteristics"]
            if data_summary.get("tissue") and data_summary.get("tissue") == dc.get("tissue"):
                score += 0.5
            if data_summary.get("disease") and data_summary.get("disease") == dc.get("disease"):
                score += 0.5
            if data_summary.get("modality") and data_summary.get("modality") == dc.get("modality"):
                score += 0.3

        # Confidence weight
        score *= float(record.get("confidence", 0.5))
        return score

    def _load_all(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(self.memory_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    records.append(data)
            except Exception:
                pass
        return records

    def _save_record(self, session_id: str, record: dict[str, Any]) -> None:
        safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", session_id)
        path = self.memory_dir / f"{safe_id}.json"
        path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return str(value or "").strip()


def _parse_json(text: str) -> Any:
    cleaned = str(text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        brace = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace:
            try:
                return json.loads(brace.group())
            except Exception:
                pass
    return {}
