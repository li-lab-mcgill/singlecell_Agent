"""ContextManager — layered scientific context for the research loop.

Maintains a structured, layered view of the session's scientific state.
Replaces ad-hoc injection of strings into prompts with a single coherent
context object that each agent can read.

Layers (from most to least stable):
  Workspace  — data files, profiler output, available tools (fixed at start)
  Task       — current question and objective (fixed at start)
  Memory     — long-term summaries loaded for this session (fixed at start)
  Evidence   — findings promoted from hypothesis to established fact (grows)
  Hypotheses — active hypotheses and their status (changes each phase)
  Critique   — per-step attributions from the most recent phase (updated)

Usage:
    ctx = ContextManager(
        user_question="What cell types are in this dataset?",
        data_summary=data_summary,
        long_term_context="PRIOR EXPERIENCE: ...",  # from LongTermMemory
    )

    # After each phase:
    ctx.update_from_phase(
        phase_number=2,
        working_model=update_result.get("updated_working_model"),
        analyzer_report=analyzer_report,
        attributions=attributions,
    )

    # Promote a confident finding to evidence:
    ctx.promote_to_evidence({"finding": "CD8+ T cells expand in active IBD"}, confidence=0.85)

    # Flag a known risk:
    ctx.mark_as_warning("rna_cluster_leiden", "resolution 0.8 produces fragmented clusters")

    # Inject into any prompt:
    prompt = ctx.to_prompt_str()
"""

from __future__ import annotations

import json
from typing import Any


class ContextManager:
    """Layered scientific context — injected into agent prompts each phase.

    Args:
        user_question:      The scientific question for this session.
        data_summary:       Workspace profile (dict or string).
        long_term_context:  Pre-formatted string from LongTermMemory.format_prior_experience().
                            Pass "" if no long-term memory available.
        max_evidence:       Maximum number of promoted findings to keep in foreground.
        max_hypotheses:     Maximum number of active hypotheses to show.
    """

    def __init__(
        self,
        *,
        user_question: str,
        data_summary: dict[str, Any] | str = "",
        long_term_context: str = "",
        max_evidence: int = 10,
        max_hypotheses: int = 5,
    ):
        self.user_question = user_question
        self.data_summary = data_summary
        self.long_term_context = long_term_context.strip()
        self.max_evidence = max_evidence
        self.max_hypotheses = max_hypotheses

        # Evidence layer — promoted findings, ordered by confidence (desc)
        self._evidence: list[dict[str, Any]] = []

        # Hypothesis layer — current working hypotheses per phase
        self._hypotheses: list[dict[str, Any]] = []

        # Critique layer — latest per-step attributions
        self._latest_critique: dict[str, Any] = {}

        # Warning registry — known risks from prior steps
        self._warnings: dict[str, str] = {}  # step_id → reason

    # ------------------------------------------------------------------
    # Update API
    # ------------------------------------------------------------------

    def update_from_phase(
        self,
        *,
        phase_number: int,
        working_model: dict[str, Any] | str | None = None,
        analyzer_report: dict[str, Any] | None = None,
        attributions: dict[str, Any] | None = None,
    ) -> None:
        """Update context after a phase completes.

        Args:
            phase_number:     Phase index (1-based).
            working_model:    Updated working model from ScientistPanel.update().
            analyzer_report:  Output from AnalyzerPanel.analyze().
            attributions:     Output from AttributingCritic.attribute().
        """
        if working_model is not None:
            self._update_hypotheses(phase_number, working_model)

        if analyzer_report is not None:
            self._auto_promote(analyzer_report)

        if attributions is not None:
            self._latest_critique = attributions

    def promote_to_evidence(self, finding: dict[str, Any], confidence: float) -> None:
        """Move a finding from the hypothesis layer to the evidence layer.

        Args:
            finding:    Dict with at minimum a "finding" key (string).
            confidence: Float [0, 1] — minimum 0.7 recommended for promotion.
        """
        entry = {**finding, "confidence": confidence, "promoted": True}
        # Avoid duplicates — check "finding" text
        finding_text = str(finding.get("finding", ""))
        if any(str(e.get("finding", "")) == finding_text for e in self._evidence):
            return
        self._evidence.append(entry)
        # Keep highest-confidence findings; trim to max_evidence
        self._evidence.sort(key=lambda e: float(e.get("confidence", 0.0)), reverse=True)
        self._evidence = self._evidence[: self.max_evidence]

    def mark_as_warning(self, step_id: str, reason: str) -> None:
        """Flag a step result as a known risk for the next phase.

        Args:
            step_id:  Step identifier from the research plan.
            reason:   Human-readable description of the risk.
        """
        self._warnings[step_id] = reason

    # ------------------------------------------------------------------
    # Prompt rendering
    # ------------------------------------------------------------------

    def to_prompt_str(self) -> str:
        """Render the full layered context as a compact string for LLM injection.

        Evidence is always in the foreground. Old hypotheses are shown in brief.
        Warnings are highlighted.
        """
        sections: list[str] = []

        # Task
        sections.append(f"RESEARCH QUESTION: {self.user_question}")

        # Long-term memory (pre-formatted)
        if self.long_term_context:
            sections.append(self.long_term_context)

        # Evidence layer
        if self._evidence:
            lines = ["ESTABLISHED EVIDENCE (high-confidence findings from prior phases):"]
            for e in self._evidence:
                conf = float(e.get("confidence", 0.0))
                lines.append(f"  [{conf:.2f}] {e.get('finding', str(e))}")
            sections.append("\n".join(lines))

        # Hypothesis layer
        if self._hypotheses:
            visible = self._hypotheses[-self.max_hypotheses:]
            lines = ["CURRENT HYPOTHESES (active scientific working model):"]
            for h in visible:
                ph = h.get("phase", "?")
                text = h.get("hypothesis", str(h))[:200]
                lines.append(f"  Phase {ph}: {text}")
            sections.append("\n".join(lines))

        # Critique layer
        if self._latest_critique.get("attributions"):
            lines = ["LATEST STEP ATTRIBUTIONS (per-step quality from most recent phase):"]
            for attr in self._latest_critique["attributions"][:6]:
                step_id = attr.get("step_id", "?")
                judgment = attr.get("judgment", "?")
                score = attr.get("contribution_score", "?")
                reason = str(attr.get("reason", ""))[:120]
                lines.append(f"  {step_id}: {judgment} (score={score}) — {reason}")
            sections.append("\n".join(lines))

        # Warnings
        if self._warnings:
            lines = ["KNOWN RISKS (do not repeat these mistakes):"]
            for step_id, reason in self._warnings.items():
                lines.append(f"  {step_id}: {reason}")
            sections.append("\n".join(lines))

        return "\n\n".join(sections)

    def get_evidence(self) -> list[dict[str, Any]]:
        """Return the evidence layer as a list of dicts."""
        return list(self._evidence)

    def get_warnings(self) -> dict[str, str]:
        """Return the warnings registry."""
        return dict(self._warnings)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_hypotheses(
        self,
        phase_number: int,
        working_model: dict[str, Any] | str,
    ) -> None:
        """Extract current hypothesis from working_model and store it."""
        if isinstance(working_model, dict):
            hypothesis = (
                working_model.get("consensus_hypothesis")
                or working_model.get("hypothesis")
                or str(working_model)[:200]
            )
        else:
            hypothesis = str(working_model)[:300]
        self._hypotheses.append({"phase": phase_number, "hypothesis": hypothesis})

    def _auto_promote(self, analyzer_report: dict[str, Any]) -> None:
        """Automatically promote high-confidence findings from analyzer report."""
        if not isinstance(analyzer_report, dict):
            return

        # Check for explicit finding fields with confidence
        for key in ("key_findings", "findings", "established_findings"):
            findings = analyzer_report.get(key)
            if isinstance(findings, list):
                for f in findings:
                    if isinstance(f, dict):
                        conf = float(f.get("confidence", 0.0))
                        if conf >= 0.75:
                            self.promote_to_evidence(f, confidence=conf)
                    elif isinstance(f, str):
                        # Plain string finding — check if hypothesis_status is "confirmed"
                        if analyzer_report.get("hypothesis_status") == "confirmed":
                            self.promote_to_evidence({"finding": f}, confidence=0.75)

        # Also extract warnings from BAD attributions (if critic ran)
        step_attrs = analyzer_report.get("step_attributions", [])
        for attr in step_attrs:
            if isinstance(attr, dict) and attr.get("judgment") == "BAD":
                step_id = attr.get("step_id", "unknown")
                issues = attr.get("issues", [])
                if issues:
                    self.mark_as_warning(step_id, issues[0])
