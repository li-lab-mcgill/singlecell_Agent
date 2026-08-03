"""Scientist Panel — orchestrates panelist formulation, mediation, and callbacks.

The prompt source of truth is `updated_prompts/`.

Flow:
  run_initial_panelists() + MediatorAgent.formulate():
    1. Biologist + Statistician + Bioinformatician formulate in parallel
       (run_initial_panelists()).
    2. MediatorAgent synthesizes a selected_research_plan and evidence_state.
    3. Bounded Mediator-requested panelist callbacks run if needed
       (run_panelist_callback()).
    4. AdversarialPanelist (owned by ResearchLoop) reviews the mediated
       research plan.

  decide_after_analysis():
    Mediator reads Analyzer output and chooses one of the five post-analysis
    decisions: accept_and_conclude, call_panelists, self_revise_plan, ask_user,
    or declare_unanswerable.

Usage:
    panel = ScientistPanel(
        engine_name="gpt-4o",
        fast_engine_name="gpt-4o-mini",
        rag_store=store,
        result_dir="results/panel",
        client=client,
    )

    panelist_outputs = panel.run_initial_panelists(
        user_question="What cell types drive inflammation in my IBD dataset?",
        data_summary=data_summary_dict,
        anchor_papers=[],
    )
    # panelist_outputs → passed to MediatorAgent.formulate() by ResearchLoop

"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    from json_repair import repair_json as _repair_json
except ImportError:
    _repair_json = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

from agents.llm_utils import single_llm_call
from agents.paper_judge import PaperJudge
from agents.paper_md_writer import PaperMDWriter
from agents.panelist_tools import build_panelist_tool_registry
from agents.runner import ToolCallingAgentRunner
from agents.tool_base import AgentToolRegistry
from rag.literature_retriever import LiteratureRetriever
from rag.store_backend import RAGStore
from wiki.index import query_tasks as _wiki_query_tasks
from prompts.panelist_prompts import (
    PANELIST_SHARED_SYSTEM,
    BIOLOGIST_ROUND1_PROMPT,
    STATISTICIAN_ROUND1_PROMPT,
    BIOINFORMATICIAN_ROUND1_PROMPT,
    PANELIST_CALLBACK_PROMPT,
)
from prompts.mediator_prompts import (
    MEDIATOR_SHARED_SYSTEM,
    MEDIATOR_FORMULATION_PROMPT,
    MEDIATOR_POST_ANALYSIS_PROMPT,
)

_ROLES = ["biologist", "statistician", "bioinformatician"]

_ROUND1_PROMPTS = {
    "biologist": BIOLOGIST_ROUND1_PROMPT,
    "statistician": STATISTICIAN_ROUND1_PROMPT,
    "bioinformatician": BIOINFORMATICIAN_ROUND1_PROMPT,
}


class ScientistPanel:
    """Orchestrates the Scientist Panel debate.

    run_initial_panelists(): three panelists formulate in parallel; the
    resulting outputs are handed to MediatorAgent (owned by ResearchLoop) for
    mediation, callbacks, and adversarial review.
    decide_after_analysis(): mediator-only post-analysis decision.
    """

    def __init__(
        self,
        *,
        engine_name: str,
        fast_engine_name: str | None = None,
        rag_store: RAGStore,
        result_dir: str | Path,
        client: Any | None = None,
        max_mediator_callback_rounds: int = 3,
        max_callbacks_per_round: int = 3,
        max_callbacks_per_panelist_per_round: int = 1,
        max_callback_rounds_after_analysis: int = 2,
        short_term_memory: Any | None = None,
    ):
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required")
        self.client = client or OpenAI()
        self.engine_name = engine_name
        self.fast_engine_name = fast_engine_name or engine_name
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.short_term_memory = short_term_memory
        self.max_mediator_callback_rounds = max(0, int(max_mediator_callback_rounds))
        self.max_callbacks_per_round = max(1, int(max_callbacks_per_round))
        self.max_callbacks_per_panelist_per_round = max(1, int(max_callbacks_per_panelist_per_round))
        self.max_callback_rounds_after_analysis = max(0, int(max_callback_rounds_after_analysis))

        # Shared retriever — one RAGStore shared across all panelists
        self.retriever = LiteratureRetriever(
            rag_store=rag_store,
            engine_name=self.fast_engine_name,
            client=self.client,
            cache_dir=self.result_dir / "lit_cache",
        )

        # PaperJudge — one instance, role passed at call time
        self.judge = PaperJudge(
            engine_name=self.fast_engine_name,
            client=self.client,
        )

        # PaperMDWriter — writes relevant papers to wiki/papers/ after each retrieval
        # Collects all available task IDs from the tool wiki for task-linking
        _all_task_ids = [t["id"] for t in _wiki_query_tasks()]
        self.paper_md_writer = PaperMDWriter(
            engine_name=self.fast_engine_name,
            client=self.client,
            session_id="unknown",   # updated per-run via set_session_id()
            task_ids=_all_task_ids,
        )

        self._last_adversarial_result: dict[str, Any] | None = None

    def set_session_id(self, session_id: str) -> None:
        """Update the session ID recorded in paper wiki entries."""
        self.paper_md_writer.session_id = session_id

    def set_short_term_memory(self, memory: Any | None) -> None:
        """Attach optional short-term memory for retrieval evidence logging."""
        self.short_term_memory = memory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_initial_panelists(
        self,
        *,
        user_question: str,
        data_summary: dict[str, Any] | str,
        anchor_papers: list[dict[str, Any]] | None = None,
    ) -> dict[str, str]:
        """Run the three specialist panelists once and return raw role outputs."""
        data_summary_str = _to_str(data_summary)
        anchor_str = _format_anchor_papers(anchor_papers or [])
        outputs = self._run_round1_formulate(
            user_question=user_question,
            data_summary_str=data_summary_str,
            anchor_str=anchor_str,
        )
        self._save("initial_panelists", outputs)
        return outputs

    def run_panelist_callback(self, role: str, callback_input: dict[str, Any]) -> dict[str, Any]:
        """Run one targeted panelist callback for MediatorAgent internal tools."""
        callback = dict(callback_input.get("callback") or callback_input)
        callback.setdefault("role", role)
        # MediatorAgent emits short callback_type aliases ("reasoning" /
        # "literature"). Normalize here — the earliest common point before
        # dispatch — using the same mapping _extract_callback_requests uses,
        # so "literature" callbacks reliably hit _run_panelist_callback's
        # retrieval-tool branch instead of silently falling back to the
        # plain-LLM branch.
        callback["callback_type"] = _canonical_callback_type(callback.get("callback_type"))
        context = callback_input.get("context")
        if not isinstance(context, dict):
            context = {
                "callback": callback,
                "assigned_gap": callback.get("assigned_gap", ""),
                "background": callback.get("background", ""),
            }
        return self._run_panelist_callback(
            role=role,
            callback=callback,
            context=context,
            round_number=int(callback_input.get("round_number", 1) or 1),
        )

    def _formulate_brief(
        self,
        *,
        user_question: str,
        data_summary: dict[str, Any] | str,
        anchor_papers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Brief panel: panelists + mediator. No callbacks or adversarial review.

        Used for ambiguous requests where some panel debate is useful but full adversarial is unnecessary.
        Escalation: if the mediator self-assesses low confidence, the caller may escalate to "full".
        """
        data_summary_str = _to_str(data_summary)
        anchor_str = _format_anchor_papers(anchor_papers or [])

        round1_outputs = self._run_round1_formulate(
            user_question=user_question,
            data_summary_str=data_summary_str,
            anchor_str=anchor_str,
        )
        self._save("formulate_brief_round1", round1_outputs)

        initial_draft = self._run_mediator_formulation(
            user_question=user_question,
            data_summary_str=data_summary_str,
            panelist_outputs=round1_outputs,
        )
        initial_draft["_panel_mode"] = "brief"
        initial_draft = _mark_callbacks_skipped(initial_draft, reason="brief mode does not run mediator callbacks")
        self._save("formulate_brief_final", initial_draft)
        return initial_draft

    def _formulate_lightweight(
        self,
        *,
        user_question: str,
        data_summary: dict[str, Any] | str,
        anchor_papers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Single biologist panelist + mediator. Fastest non-trivial path.

        Used for operational requests that still benefit from one specialist sanity-check.
        """
        data_summary_str = _to_str(data_summary)
        anchor_str = _format_anchor_papers(anchor_papers or [])

        # Only the biologist runs (no statistician or bioinformatician)
        biologist_prompt = (
            BIOLOGIST_ROUND1_PROMPT.strip()
            + "\n\nUSER QUESTION:\n\n" + user_question
            + "\n\nDATA SUMMARY:\n\n" + data_summary_str
            + "\n\nUSER-PROVIDED ANCHOR PAPERS (must engage with these):\n\n" + anchor_str
        )
        registry: AgentToolRegistry = build_panelist_tool_registry(
            retriever=self.retriever,
            judge=self.judge,
            paper_md_writer=self.paper_md_writer,
            role="biologist",
        )
        runner = ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=PANELIST_SHARED_SYSTEM,
            tool_specs=registry.tool_specs(),
            tool_executor=registry.executor(),
            transcript_path=str(self.result_dir / "formulate_lightweight_biologist_transcript.jsonl"),
            tool_trace_path=str(self.result_dir / "formulate_lightweight_biologist_tool_trace.jsonl"),
            client=self.client,
            max_iterations=10,
            max_tool_calls=20,
        )
        biologist_out = runner.run(initial_user_input=biologist_prompt, response_handler=None)
        biologist_text = str(biologist_out.get("result") or biologist_out)

        lightweight_outputs = {"biologist": biologist_text, "statistician": "", "bioinformatician": ""}
        self._save("formulate_lightweight_round1", lightweight_outputs)

        initial_draft = self._run_mediator_formulation(
            user_question=user_question,
            data_summary_str=data_summary_str,
            panelist_outputs=lightweight_outputs,
        )
        initial_draft["_panel_mode"] = "lightweight"
        initial_draft = _mark_callbacks_skipped(initial_draft, reason="lightweight mode does not run mediator callbacks")
        self._save("formulate_lightweight_final", initial_draft)
        return initial_draft

    def _formulate_skip_panel(
        self,
        *,
        user_question: str,
        data_summary: dict[str, Any] | str,
    ) -> dict[str, Any]:
        """Skip the panel entirely. Return a minimal plan derived directly from the user question.

        Used for clear operational requests (e.g., "Run QC on this file") where no scientific
        debate is needed. The ToolConsultantAgent handles all planning downstream.
        """
        data_summary_str = _to_str(data_summary)
        minimal_plan = {
            "concrete_analysis_claim": f"Execute: {user_question}",
            "selected_research_plan": {
                "plan_id": "operational_direct",
                "summary": f"Execute the requested workflow: {user_question}",
                "reason_selected": "The request was routed as direct operational execution.",
                "steps": [user_question],
                "required_visualizations": [],
                "caveat": "",
            },
            "_panel_mode": "skip_panel",
            "_adversarial_verdict": "skipped",
            "_adversarial_rounds": 0,
        }
        minimal_plan = _normalize_research_plan_schema(minimal_plan)
        self._save("formulate_skip_panel", minimal_plan)
        return minimal_plan

    def decide_after_analysis(
        self,
        *,
        user_question: str,
        data_summary: dict[str, Any] | str,
        phase_number: int,
        analyzer_report: dict[str, Any] | str,
        working_model: dict[str, Any] | str,
        research_context: dict[str, Any] | None = None,
        tool_decision: dict[str, Any] | None = None,
        dag_result: dict[str, Any] | str | None = None,
        state_graph_context: dict[str, Any] | None = None,
        artifact_registry_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mediator-only post-analysis decision.

        This is the Phase 5 update_from_analysis mode. It decides the next
        research move before the expensive full panel update is invoked.
        """
        prompt = (
            MEDIATOR_POST_ANALYSIS_PROMPT.strip()
            + "\n\nUSER QUESTION:\n\n" + user_question
            + "\n\nDATA SUMMARY:\n\n" + _to_str(data_summary)
            + "\n\nPHASE NUMBER:\n\n" + str(phase_number)
            + "\n\nCURRENT RESEARCH CONTEXT:\n\n" + _to_str(research_context or {})
            + "\n\nWORKING MODEL:\n\n" + _to_str(working_model)
            + "\n\nTOOLCONSULTANT DECISION:\n\n" + _to_str(tool_decision or {})
            + "\n\nDAG / EXECUTION RESULT SUMMARY:\n\n" + _to_str(_summarize_execution_for_mediator(dag_result))
            + "\n\nANALYZER REPORT:\n\n" + _to_str(analyzer_report)
            + "\n\nSTATEGRAPH TRAJECTORY CONTEXT IF AVAILABLE:\n\n" + _to_str(state_graph_context or {})
            + "\n\nARTIFACT REGISTRY SUMMARY IF AVAILABLE:\n\n" + _to_str(artifact_registry_summary or {})
        )
        text = single_llm_call(self.client, self.engine_name, prompt, system=MEDIATOR_SHARED_SYSTEM)
        result = _normalize_post_analysis_decision(_extract_tag_json(text, "MEDIATOR_POST_ANALYSIS"))
        self._save(f"post_analysis_phase{phase_number}_mediator_decision", result)
        return result

    def run_post_analysis_callbacks(
        self,
        *,
        user_question: str,
        data_summary: dict[str, Any] | str,
        phase_number: int,
        post_analysis_decision: dict[str, Any],
        working_model: dict[str, Any] | str,
        research_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run bounded targeted callbacks requested after Analyzer feedback."""
        callbacks = _normalize_post_analysis_decision(post_analysis_decision).get("callbacks", [])
        research_context = research_context or {}
        current_plan = {
            "concrete_analysis_claim": research_context.get("concrete_analysis_claim", ""),
            "research_case": research_context.get("research_case", ""),
            "selected_research_plan": research_context.get("selected_research_plan", {}),
            "research_plan": research_context.get("selected_research_plan", {}),
            "alternative_research_plans": research_context.get("alternative_research_plans", []),
            "analysis_requirements": research_context.get("analysis_requirements", []),
            "validation_requirements": research_context.get("validation_requirements", []),
            "evidence_patterns": research_context.get("evidence_patterns", []),
            "evidence_gaps": research_context.get("evidence_gaps", []),
            "open_risks": research_context.get("open_risks", []),
            "callbacks": callbacks,
            "mediator_decision": "needs_panelist_callback" if callbacks else "accept",
        }
        result = self._run_mediator_callback_loop(
            user_question=user_question,
            data_summary_str=_to_str(data_summary),
            panelist_outputs=_panel_outputs_from_working_model(working_model),
            current_plan=current_plan,
            max_rounds=self.max_callback_rounds_after_analysis,
        )
        self._save(f"post_analysis_phase{phase_number}_callbacks", result)
        return result

    # ------------------------------------------------------------------
    # formulate() panelists — all panelists do RAG
    # ------------------------------------------------------------------

    def _run_round1_formulate(
        self,
        *,
        user_question: str,
        data_summary_str: str,
        anchor_str: str,
    ) -> dict[str, str]:
        """Run all three panelists in parallel. Returns {role: raw_text}."""

        def _run_one(role: str) -> str:
            text = self._run_panelist_formulation(
                role=role,
                user_question=user_question,
                data_summary_str=data_summary_str,
                anchor_str=anchor_str,
            )
            self._log_retrieval_evidence(
                role=role,
                tag="ROUND1",
                panelist_text=_ensure_str(text),
                tool_trace_path=self.result_dir / f"{role}_round1_tool_trace.jsonl",
            )
            return _ensure_str(text)

        return _run_parallel(_run_one, _ROLES)

    def _run_panelist_formulation(
        self,
        *,
        role: str,
        user_question: str,
        data_summary_str: str,
        anchor_str: str,
    ) -> str:
        role_prompt = _ROUND1_PROMPTS[role].strip()
        registry = build_panelist_tool_registry(
            role=role,
            retriever=self.retriever,
            judge=self.judge,
            paper_md_writer=self.paper_md_writer,
        )
        runner = self._make_runner(role=role, registry=registry, tag="ROUND1")
        prompt = (
            role_prompt
            + "\n\nUSER QUESTION:\n\n" + user_question
            + "\n\nDATA SUMMARY:\n\n" + data_summary_str
            + "\n\nUSER-PROVIDED ANCHOR PAPERS:\n\n" + anchor_str
        )
        text = runner.run(
            initial_user_input=prompt,
            response_handler=lambda t: _tag_done_handler(t, "ROUND1"),
        )
        return str(text)

    # ------------------------------------------------------------------
    # formulate() Mediator
    # ------------------------------------------------------------------

    def _run_mediator_formulation(
        self,
        *,
        user_question: str,
        data_summary_str: str,
        panelist_outputs: dict[str, str],
    ) -> dict[str, Any]:
        prompt = (
            MEDIATOR_FORMULATION_PROMPT.strip()
            + "\n\nUSER QUESTION:\n\n" + user_question
            + "\n\nDATA SUMMARY:\n\n" + data_summary_str
            + "\n\nBIOLOGIST FORMULATION OUTPUT:\n\n" + panelist_outputs.get("biologist", "")
            + "\n\nSTATISTICIAN FORMULATION OUTPUT:\n\n" + panelist_outputs.get("statistician", "")
            + "\n\nBIOINFORMATICIAN FORMULATION OUTPUT:\n\n" + panelist_outputs.get("bioinformatician", "")
        )
        text = single_llm_call(self.client, self.engine_name, prompt, system=MEDIATOR_SHARED_SYSTEM)
        return _normalize_research_plan_schema(_extract_tag_json(text, "MEDIATOR"))

    def _run_mediator_callback_loop(
        self,
        *,
        user_question: str,
        data_summary_str: str,
        panelist_outputs: dict[str, str],
        current_plan: dict[str, Any],
        max_rounds: int | None = None,
    ) -> dict[str, Any]:
        """Run bounded targeted callbacks requested by the Mediator."""
        plan = _normalize_research_plan_schema(current_plan)
        completed_rounds = 0
        callback_history: list[dict[str, Any]] = []
        round_limit = self.max_mediator_callback_rounds if max_rounds is None else max(0, int(max_rounds))
        if round_limit <= 0:
            plan["_callback_rounds"] = 0
            plan["_callback_budget_exhausted"] = bool(_extract_callback_requests(plan, max_callbacks=1, max_per_role=1))
            return plan

        for round_number in range(1, round_limit + 1):
            callbacks = _extract_callback_requests(
                plan,
                max_callbacks=self.max_callbacks_per_round,
                max_per_role=self.max_callbacks_per_panelist_per_round,
            )
            if not callbacks:
                break
            completed_rounds = round_number
            callback_outputs: list[dict[str, Any]] = []
            for callback in callbacks:
                role = callback["role"]
                context = self._build_panelist_callback_context(
                    user_question=user_question,
                    data_summary_str=data_summary_str,
                    panelist_outputs=panelist_outputs,
                    current_plan=plan,
                    callback=callback,
                    callback_history=callback_history,
                )
                output = self._run_panelist_callback(
                    role=role,
                    callback=callback,
                    context=context,
                    round_number=round_number,
                )
                callback_outputs.append(
                    {
                        "callback": callback,
                        "context": context,
                        "output": output,
                    }
                )
            self._save(f"formulate_callback_round{round_number}", callback_outputs)
            callback_history.extend(callback_outputs)
            plan = self._run_mediator_callback_synthesis(
                user_question=user_question,
                data_summary_str=data_summary_str,
                prior_plan=plan,
                callback_outputs=callback_outputs,
                callback_history=callback_history,
                round_number=round_number,
            )

        remaining_callbacks = _extract_callback_requests(
            plan,
            max_callbacks=1,
            max_per_role=1,
        )
        plan["_callback_rounds"] = completed_rounds
        plan["_callback_history"] = [
            {
                "round": i + 1,
                "role": item.get("callback", {}).get("role", ""),
                "callback_type": item.get("callback", {}).get("callback_type", ""),
                "assigned_gap": item.get("callback", {}).get("assigned_gap", ""),
                "gap_resolved": bool((item.get("output") or {}).get("gap_resolved", False)),
            }
            for i, item in enumerate(callback_history)
        ]
        plan["_callback_budget_exhausted"] = bool(remaining_callbacks) and completed_rounds >= round_limit
        return plan

    def _build_panelist_callback_context(
        self,
        *,
        user_question: str,
        data_summary_str: str,
        panelist_outputs: dict[str, str],
        current_plan: dict[str, Any],
        callback: dict[str, Any],
        callback_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        role = str(callback.get("role") or "").strip().lower()
        other_roles = {r: panelist_outputs.get(r, "") for r in _ROLES if r != role}
        return {
            "original_task": {
                "user_question": user_question,
                "data_summary": data_summary_str,
                "current_research_iteration": int(len(callback_history or [])) + 1,
                "reason_for_callback": callback.get("callback_source") or "mediator_gap",
            },
            "panelist_state": {
                "role": role,
                "prior_role_reasoning": panelist_outputs.get(role, ""),
                "prior_role_claims": _extract_json_field_from_tag(panelist_outputs.get(role, ""), "ROUND1", "role_claims"),
                "prior_role_uncertainties": _extract_json_field_from_tag(panelist_outputs.get(role, ""), "ROUND1", "role_uncertainties"),
            },
            "cross_panel_state": {
                "what_other_panelists_established": other_roles,
                "conflicts_still_open": current_plan.get("open_risks", []),
            },
            "mediated_state": {
                "concrete_analysis_claim": current_plan.get("concrete_analysis_claim", ""),
                "research_case": current_plan.get("research_case", ""),
                "selected_research_plan": current_plan.get("selected_research_plan", {}),
                "alternative_research_plans_summary": current_plan.get("alternative_research_plans", []),
                "accepted_analysis_requirements": current_plan.get("analysis_requirements", []),
                "disputed_or_missing_requirements": current_plan.get("open_risks", []),
                "callback_question": callback.get("assigned_gap", ""),
            },
            "adversarial_state": _build_adversarial_state(getattr(self, "_last_adversarial_result", None)),
            "literature_state": {
                "papers_already_used": _collect_papers_from_panel_outputs(panelist_outputs),
                "remaining_literature_gaps": current_plan.get("evidence_gaps", []) or callback.get("remaining_literature_gaps", []),
            },
            "callback": callback,
        }

    def _run_panelist_callback(
        self,
        *,
        role: str,
        callback: dict[str, Any],
        context: dict[str, Any],
        round_number: int,
    ) -> dict[str, Any]:
        callback_type = str(callback.get("callback_type") or "").strip()
        # Compact (no indent): this JSON blob is concatenated straight into the
        # LLM prompt below, not written to disk — pretty-printing it only burns
        # input tokens without adding any information the model needs.
        context_str = json.dumps(context, ensure_ascii=False)
        if callback_type == "ask_panelist_for_more_literature":
            registry = build_panelist_tool_registry(
                role=role,
                retriever=self.retriever,
                judge=self.judge,
                paper_md_writer=self.paper_md_writer,
            )
            runner = self._make_runner(role, registry, tag=f"CALLBACK_ROUND{round_number}")
            text = runner.run(
                initial_user_input=PANELIST_CALLBACK_PROMPT.strip() + "\n\n" + context_str,
                response_handler=lambda t: _tag_done_handler(t, "CALLBACK"),
            )
            self._log_retrieval_evidence(
                role=role,
                tag="CALLBACK",
                panelist_text=_ensure_str(text),
                tool_trace_path=self.result_dir / f"{role}_callback_round{round_number}_tool_trace.jsonl",
            )
        else:
            text = single_llm_call(
                self.client,
                self.engine_name,
                PANELIST_CALLBACK_PROMPT.strip() + "\n\n" + context_str,
                system=PANELIST_SHARED_SYSTEM,
            )
        parsed = _extract_tag_json(_ensure_str(text), "CALLBACK")
        parsed.setdefault("role", role)
        parsed.setdefault("assigned_gap", callback.get("assigned_gap", ""))
        parsed.setdefault("gap_resolved", False)
        return parsed

    def _run_mediator_callback_synthesis(
        self,
        *,
        user_question: str,
        data_summary_str: str,
        prior_plan: dict[str, Any],
        callback_outputs: list[dict[str, Any]],
        round_number: int,
        callback_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        prompt = (
            MEDIATOR_FORMULATION_PROMPT.strip()
            + "\n\nUSER QUESTION:\n\n" + user_question
            + "\n\nDATA SUMMARY:\n\n" + data_summary_str
            + "\n\nPRIOR MEDIATED RESEARCH PLAN:\n\n" + json.dumps(prior_plan, indent=2, ensure_ascii=False)
            + "\n\nACCUMULATED CALLBACK HISTORY:\n\n" + json.dumps(callback_history or [], indent=2, ensure_ascii=False)
            + "\n\nTARGETED CALLBACK OUTPUTS:\n\n" + json.dumps(callback_outputs, indent=2, ensure_ascii=False)
        )
        text = single_llm_call(self.client, self.engine_name, prompt, system=MEDIATOR_SHARED_SYSTEM)
        result = _normalize_research_plan_schema(_extract_tag_json(text, "MEDIATOR"))
        result["_last_callback_round"] = round_number
        return result

    # ------------------------------------------------------------------
    # Infrastructure
    # ------------------------------------------------------------------

    def _make_runner(
        self,
        role: str,
        registry: AgentToolRegistry,
        tag: str = "ROUND1",
    ) -> ToolCallingAgentRunner:
        return ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=PANELIST_SHARED_SYSTEM.strip(),
            tool_specs=registry.tool_specs(),
            tool_executor=registry.executor(),
            transcript_path=str(self.result_dir / f"{role}_{tag.lower()}_transcript.jsonl"),
            tool_trace_path=str(self.result_dir / f"{role}_{tag.lower()}_tool_trace.jsonl"),
            client=self.client,
            max_iterations=10,
            max_tool_calls=16,
        )

    def _save(self, name: str, data: Any) -> None:
        path = self.result_dir / f"{name}.json"
        payload = data if isinstance(data, (dict, list)) else {"raw": data}
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _log_retrieval_evidence(
        self,
        *,
        role: str,
        tag: str,
        panelist_text: str,
        tool_trace_path: Path,
    ) -> None:
        """Orchestrator-owned logging for satisfied retrieval evidence.

        Panelists state whether an intent is satisfied in structured output. This
        method combines that assessment with the retrieve_literature tool trace and
        writes it to ShortTermMemory when available.
        """
        memory = self.short_term_memory
        if memory is None or not hasattr(memory, "add_retrieval_evidence"):
            return
        parsed = _extract_tag_json(panelist_text, tag)
        assessments = _extract_retrieval_assessments(parsed)
        if not assessments:
            return
        trace_calls = _read_retrieval_tool_calls(tool_trace_path)
        for assessment in assessments:
            panelist_assessment = assessment.get("panelist_assessment") or {}
            if not isinstance(panelist_assessment, dict) or not panelist_assessment.get("enough_information"):
                continue
            retrieval_intent = str(assessment.get("retrieval_intent") or "").strip()
            retrieval_goal = str(assessment.get("retrieval_goal") or "").strip()
            matching_call = _match_retrieval_call(trace_calls, retrieval_intent, retrieval_goal)
            papers = matching_call.get("result", []) if matching_call else []
            if isinstance(papers, dict):
                papers = papers.get("papers", [])
            if not isinstance(papers, list):
                papers = []
            evidence = {
                "event_type": "retrieval_evidence",
                "role": role,
                "retrieval_goal": retrieval_goal,
                "retrieval_intent": retrieval_intent,
                "base_query": assessment.get("base_query") or (matching_call.get("arguments", {}) if matching_call else {}).get("base_query", ""),
                "papers": [_compact_retrieval_paper(p) for p in papers],
                "panelist_assessment": panelist_assessment,
            }
            memory.add_retrieval_evidence(evidence)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_parallel(fn: Any, roles: list[str]) -> dict[str, str]:
    """Run fn(role) for all roles in parallel. fn must return a str. Returns {role: result}.

    A single panelist failure returns an error placeholder rather than crashing
    the whole round; the Mediator receives degraded but parseable input.
    """
    with ThreadPoolExecutor(max_workers=len(roles)) as pool:
        futures = {pool.submit(fn, role): role for role in roles}
        outputs: dict[str, str] = {}
        for future in as_completed(futures):
            role = futures[future]
            try:
                outputs[role] = future.result()
            except Exception as exc:
                outputs[role] = f"<{role}_error>Agent failed: {exc}</{role}_error>"
    return outputs


def _to_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return str(value or "").strip()


def _summarize_execution_for_mediator(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return {"raw": value[:3000]}
    if not isinstance(value, dict):
        return {}
    summary: dict[str, Any] = {}
    for key in ("status", "error", "message", "output_retention_policy", "adversarial_alignment_review"):
        if key in value:
            summary[key] = value.get(key)
    best_path = value.get("best_path")
    if isinstance(best_path, dict):
        summary["best_path"] = {
            "status": best_path.get("status"),
            "artifacts": best_path.get("artifacts", {}),
            "resolved_outputs": best_path.get("resolved_outputs", {}),
        }
    artifacts = value.get("artifacts")
    if isinstance(artifacts, dict):
        summary["artifacts"] = artifacts
    return summary or {"raw": _ensure_str(value)[:3000]}


def _panel_outputs_from_working_model(working_model: Any) -> dict[str, str]:
    if isinstance(working_model, dict):
        for key in ("panelist_outputs", "_panelist_outputs"):
            value = working_model.get(key)
            if isinstance(value, dict):
                return {role: _ensure_str(value.get(role, "")) for role in _ROLES}
    return {role: "" for role in _ROLES}


def _ensure_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _format_anchor_papers(papers: list[dict[str, Any]]) -> str:
    if not papers:
        return "None provided."
    lines = []
    for i, p in enumerate(papers, 1):
        lines.append(
            f"{i}. {p.get('title', 'Untitled')} ({p.get('published', 'unknown date')})\n"
            f"   {p.get('abstract', '')[:300]}"
        )
    return "\n".join(lines)


def _extract_tag_json(text: str, tag: str) -> dict[str, Any]:
    match = None
    for candidate in _tag_aliases(tag):
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
        except json.JSONDecodeError as exc:
            if _repair_json is not None:
                try:
                    return json.loads(_repair_json(raw))
                except Exception:
                    pass
            return {"raw": raw, "parse_error": str(exc)}


_LITERATURE_VERDICTS = {"answered_well", "partially_answered", "not_answered"}
_RESEARCH_CASES = {"prior_answered", "established_method_fits", "no_adequate_existing_solution"}
_POST_ANALYSIS_DECISIONS = {
    "accept_and_conclude",
    "call_panelists",
    "self_revise_plan",
    "ask_user",
    "declare_unanswerable",
}
_EVIDENCE_QUALITIES = {"strong", "moderate", "weak"}
_ARTIFACT_TYPES = {
    "raw_h5ad",
    "qc_h5ad",
    "normalized_h5ad",
    "clustered_h5ad",
    "annotated_h5ad",
    "multimodal_h5ad",
    "table",
    "none",
}


def _adapt_updated_mediator_formulation(out: dict[str, Any]) -> dict[str, Any]:
    """Adapt updated_prompts/mediator_formulation.md output to runtime fields."""
    hypothesis = out.get("hypothesis")
    if isinstance(hypothesis, dict):
        out.setdefault("concrete_analysis_claim", hypothesis.get("concrete_analysis_claim", ""))
        out.setdefault("falsification_criterion", hypothesis.get("falsification_criterion", ""))

    if "selected_research_plan" not in out and isinstance(out.get("plan"), dict):
        plan = out.get("plan") or {}
        main_method = plan.get("main_method") if isinstance(plan.get("main_method"), dict) else {}
        core_steps = _as_list(main_method.get("core_steps") if isinstance(main_method, dict) else [])
        downstream = _as_list(plan.get("downstream_analyses"))
        steps: list[Any] = []
        for step in core_steps:
            if isinstance(step, dict):
                item = dict(step)
                item.setdefault("step_type", "main_method")
                steps.append(item)
            else:
                steps.append(step)
        for step in downstream:
            if isinstance(step, dict):
                item = dict(step)
                item.setdefault("step_type", "downstream_analysis")
                item.setdefault("step_id", item.get("analysis_id", ""))
                item.setdefault("step_name", item.get("analysis_name", ""))
                steps.append(item)
            else:
                steps.append(step)
        out["selected_research_plan"] = {
            "plan_id": "plan_a",
            "summary": _plan_summary({"steps": steps}) or str(out.get("background", {}).get("framing", "") if isinstance(out.get("background"), dict) else "").strip(),
            "reason_selected": str(main_method.get("verdict_reasoning", "") if isinstance(main_method, dict) else ""),
            "steps": steps,
            "required_visualizations": _expected_outputs_from_validations(out.get("validation_metrics")),
            "success_criteria": out.get("success_criteria", {}),
            "limitations": out.get("limitations", []),
            "caveat": "",
        }

    if "alternative_research_plans" not in out and isinstance(out.get("alternative_plans"), list):
        out["alternative_research_plans"] = out.get("alternative_plans", [])

    if "evidence_state" not in out:
        out["evidence_state"] = _build_initial_evidence_state_from_formulation(out)
    return out


def _expected_outputs_from_validations(validations: Any) -> list[str]:
    outputs: list[str] = []
    for item in _as_list(validations):
        if isinstance(item, dict):
            text = str(item.get("expected_output") or "").strip()
            if text:
                outputs.append(text)
    return outputs


def _build_initial_evidence_state_from_formulation(out: dict[str, Any]) -> dict[str, Any]:
    claim_text = ""
    hypothesis = out.get("hypothesis")
    if isinstance(hypothesis, dict):
        claim_text = str(hypothesis.get("concrete_analysis_claim") or "").strip()
    claim_text = claim_text or str(out.get("concrete_analysis_claim") or out.get("consensus_hypothesis") or "").strip()
    analysis_claims = _as_list(out.get("analysis_claims"))
    if not analysis_claims and claim_text:
        analysis_claims = [
            {
                "claim_id": "C1",
                "claim_text": claim_text,
                "status": "pending",
                "support_summary": "",
                "contradicting_evidence": [],
                "unresolved_requirements": [],
            }
        ]
    return {
        "analysis_claims": analysis_claims,
        "open_questions": _as_list(out.get("open_questions") or out.get("open_risks")),
        "literature_evidence": _as_list(out.get("literature_evidence")),
        "execution_evidence": _as_list(out.get("execution_evidence")),
        "current_belief": str(out.get("current_belief") or out.get("verdict_rationale") or claim_text or "").strip(),
    }


def _normalize_evidence_state(value: Any, *, fallback_claim: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    claims: list[dict[str, Any]] = []
    allowed = {"pending", "supported", "refuted", "inconclusive", "partially_supported"}
    for idx, item in enumerate(_as_list(value.get("analysis_claims"))):
        if not isinstance(item, dict):
            item = {"claim_text": str(item)}
        claim_text = str(item.get("claim_text") or item.get("hypothesis") or "").strip()
        if not claim_text:
            continue
        claim_id = str(item.get("claim_id") or f"C{idx + 1}").strip()
        claims.append(
            {
                "claim_id": claim_id,
                "claim_text": claim_text,
                "status": _enum_or_default(item.get("status"), allowed=allowed, default="pending"),
                "support_summary": str(item.get("support_summary") or "").strip(),
                "contradicting_evidence": _as_list(item.get("contradicting_evidence")),
                "unresolved_requirements": _as_list(item.get("unresolved_requirements")),
            }
        )
    if not claims and fallback_claim:
        claims.append(
            {
                "claim_id": "C1",
                "claim_text": str(fallback_claim),
                "status": "pending",
                "support_summary": "",
                "contradicting_evidence": [],
                "unresolved_requirements": [],
            }
        )
    return {
        "analysis_claims": claims,
        "open_questions": _as_list(value.get("open_questions")),
        "literature_evidence": _as_list(value.get("literature_evidence")),
        "execution_evidence": _as_list(value.get("execution_evidence")),
        "current_belief": str(value.get("current_belief") or "").strip(),
    }


def _claim_ids_from_evidence_state(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    ids = []
    for claim in _as_list(value.get("analysis_claims")):
        if isinstance(claim, dict) and claim.get("claim_id"):
            ids.append(str(claim["claim_id"]))
    return ids


def _ensure_step_claim_links(steps: Any, *, claim_ids: list[str] | None = None) -> list[Any]:
    out = []
    default_ids = claim_ids or []
    for step in _as_list(steps):
        if isinstance(step, dict):
            item = dict(step)
            if "addresses_claims" not in item:
                item["addresses_claims"] = list(default_ids)
                if not default_ids:
                    item["claim_linkage"] = "best_effort_unmapped"
            elif not isinstance(item.get("addresses_claims"), list):
                item["addresses_claims"] = _as_list(item.get("addresses_claims"))
            out.append(item)
        else:
            out.append(step)
    return out


def _normalize_research_plan_schema(plan: Any) -> dict[str, Any]:
    """Normalize Mediator formulation output to the TODO3 Phase 1 contract.

    The prompts are moving from a legacy `consensus_hypothesis`/`research_plan`
    contract toward `concrete_analysis_claim`/`selected_research_plan`. This
    normalizer preserves downstream compatibility while keeping one canonical
    active plan for newer code.
    """
    if not isinstance(plan, dict):
        plan = {"raw": _ensure_str(plan), "parse_error": "Mediator output was not a JSON object"}
    out: dict[str, Any] = dict(plan)
    out = _adapt_updated_mediator_formulation(out)

    out["clarification_needed"] = _as_bool(out.get("clarification_needed"), default=False)
    out["clarifying_questions"] = _as_list(out.get("clarifying_questions"))
    out["analysis_requirements"] = _as_list(out.get("analysis_requirements"))
    out["validation_requirements"] = _as_list(out.get("validation_requirements"))
    callbacks, invalid_callbacks = _normalize_callbacks(out.get("callbacks"))
    out["callbacks"] = callbacks
    if invalid_callbacks:
        out["_invalid_callbacks"] = invalid_callbacks
    out["alternative_research_plans"] = [
        _normalize_alternative_plan(item) for item in _as_list(out.get("alternative_research_plans"))
    ]
    out["open_risks"] = _as_list(out.get("open_risks"))

    out["literature_verdict"] = _enum_or_default(
        out.get("literature_verdict"),
        allowed=_LITERATURE_VERDICTS,
        default="partially_answered",
    )
    out["research_case"] = _enum_or_default(
        out.get("research_case"),
        allowed=_RESEARCH_CASES,
        default="established_method_fits",
    )
    out["novelty_level"] = _clamp_int(out.get("novelty_level"), default=0, minimum=0, maximum=5)

    selected = out.get("selected_research_plan")
    research = out.get("research_plan")
    if isinstance(selected, dict):
        selected_plan = _normalize_plan_block(selected)
    elif isinstance(research, dict):
        selected_plan = _normalize_plan_block(research)
    else:
        selected_plan = _normalize_plan_block({})
    out["selected_research_plan"] = selected_plan
    out["research_plan"] = dict(selected_plan)
    out["selected_research_plan"]["steps"] = _ensure_step_claim_links(
        out["selected_research_plan"].get("steps"),
        claim_ids=_claim_ids_from_evidence_state(out.get("evidence_state")),
    )
    out["research_plan"] = dict(out["selected_research_plan"])

    concrete = str(out.get("concrete_analysis_claim") or "").strip()
    best_effort = str(out.get("best_effort_claim") or "").strip()
    legacy_hypothesis = str(out.get("consensus_hypothesis") or "").strip()
    if not concrete:
        concrete = legacy_hypothesis
    out["concrete_analysis_claim"] = concrete
    if "best_effort_claim" not in out:
        out["best_effort_claim"] = ""

    if best_effort and not concrete:
        out["clarification_needed"] = True
        if not str(out.get("uncertainty_reason") or "").strip():
            out["uncertainty_reason"] = "Only a best-effort claim could be inferred from the request."
    else:
        out.setdefault("uncertainty_reason", "")

    if not legacy_hypothesis:
        out["consensus_hypothesis"] = concrete or best_effort or _plan_summary(selected_plan)

    out.setdefault("existing_solution_path", {})
    out.setdefault("existing_solution_plan", {})
    out.setdefault("extension_or_de_novo_plan", {})
    out.setdefault("why_extension_is_justified", "")
    out.setdefault("baseline_requirement", "")
    out.setdefault("verdict_rationale", "")
    out.setdefault("selection_rationale", "")
    out.setdefault("success_criteria", {})
    out["evidence_state"] = _normalize_evidence_state(out.get("evidence_state"), fallback_claim=out.get("concrete_analysis_claim") or out.get("consensus_hypothesis") or _plan_summary(selected_plan))
    out.setdefault(
        "plan_switch_policy",
        {
            "revise_current_plan_when": [],
            "promote_alternative_plan_when": [],
            "ask_user_when": [],
        },
    )
    if not isinstance(out["plan_switch_policy"], dict):
        out["plan_switch_policy"] = {
            "revise_current_plan_when": [],
            "promote_alternative_plan_when": [],
            "ask_user_when": [],
        }
    out["plan_switch_policy"].setdefault("revise_current_plan_when", [])
    out["plan_switch_policy"].setdefault("promote_alternative_plan_when", [])
    out["plan_switch_policy"].setdefault("ask_user_when", [])

    if "confidence" not in out and "panel_confidence" in out:
        out["confidence"] = out.get("panel_confidence")
    out["confidence"] = _clamp_float(out.get("confidence"), default=0.0, minimum=0.0, maximum=1.0)
    out["panel_confidence"] = _clamp_float(out.get("panel_confidence"), default=out["confidence"], minimum=0.0, maximum=1.0)
    out.setdefault("next_action", "continue")
    if str(out.get("mediator_decision") or "").strip() not in {"accept", "needs_panelist_callback"}:
        out["mediator_decision"] = "needs_panelist_callback" if out["callbacks"] else "accept"
    return out


def _normalize_post_analysis_decision(decision: Any) -> dict[str, Any]:
    if not isinstance(decision, dict):
        decision = {"raw": _ensure_str(decision), "parse_error": "Post-analysis decision was not a JSON object"}
    out = dict(decision)
    decision_value = _canonical_post_analysis_decision(out.get("decision") or out.get("decision_type"))
    out["decision"] = _enum_or_default(
        decision_value,
        allowed=_POST_ANALYSIS_DECISIONS,
        default="accept_and_conclude",
    )
    # Internal compatibility: ResearchLoop still uses decision_type as the
    # dispatch field while the prompt/schema exposes one canonical `decision`.
    out["decision_type"] = out["decision"]
    out["rationale"] = str(out.get("rationale") or "").strip()
    out["evidence_state"] = _normalize_evidence_state(out.get("evidence_state"))
    updated_plan = out.get("updated_selected_research_plan")
    out["updated_selected_research_plan"] = _normalize_plan_block(updated_plan) if isinstance(updated_plan, dict) else {}
    if out["decision"] == "self_revise_plan" and not out["updated_selected_research_plan"].get("steps"):
        out["schema_error"] = "self_revise_plan requires updated_selected_research_plan.steps"
    callbacks_payload = out.get("panelist_callbacks")
    if isinstance(callbacks_payload, dict):
        callbacks_payload = callbacks_payload.get("callbacks")
    callbacks, invalid_callbacks = _normalize_callbacks(callbacks_payload or out.get("callbacks"))
    out["panelist_callback_requests"] = callbacks
    out["callbacks"] = callbacks
    if invalid_callbacks:
        out["_invalid_callbacks"] = invalid_callbacks
    out["clarifying_questions"] = _as_list(out.get("clarifying_questions"))
    out["continue_from_node_id"] = out.get("continue_from_node_id")
    out["continue_from_artifact"] = out.get("continue_from_artifact")
    out["unanswerable_reason"] = str(out.get("unanswerable_reason") or "").strip()
    out["what_would_be_needed"] = str(out.get("what_would_be_needed") or "").strip()
    out["final_answer_summary"] = str(out.get("final_answer_summary") or "").strip()
    out["confidence"] = _clamp_float(out.get("confidence"), default=0.0, minimum=0.0, maximum=1.0)
    return out


def _canonical_post_analysis_decision(value: Any) -> str:
    text = str(value or "").strip()
    return {
        "conclude": "accept_and_conclude",
        "interpretation_only": "accept_and_conclude",
        "ask_panelist_callback": "call_panelists",
        "start_panel_update_round": "call_panelists",
        "ask_user_clarification": "ask_user",
        "revise_plan": "self_revise_plan",
        "produce_next_research_plan": "self_revise_plan",
        "new_downstream_analysis": "self_revise_plan",
        "parameter_change": "self_revise_plan",
        "method_replacement": "self_revise_plan",
        "upstream_preprocessing_change": "self_revise_plan",
        "data_change": "self_revise_plan",
    }.get(text, text)


def _normalize_working_model_update(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    hypothesis_status = value.get("hypothesis_status")
    if not isinstance(hypothesis_status, dict):
        hypothesis_status = {}
    allowed_status = {"supported", "refuted", "inconclusive", "partially_supported"}
    normalized_hypothesis_status: dict[str, str] = {}
    for hypothesis, status in hypothesis_status.items():
        hypothesis_text = str(hypothesis or "").strip()
        if not hypothesis_text:
            continue
        normalized_hypothesis_status[hypothesis_text] = _enum_or_default(
            status,
            allowed=allowed_status,
            default="inconclusive",
        )
    return {
        "current_belief": str(value.get("current_belief") or "").strip(),
        "evidence_quality": _enum_or_default(
            value.get("evidence_quality"),
            allowed=_EVIDENCE_QUALITIES,
            default="weak",
        ),
        "established_findings": _as_list(value.get("established_findings")),
        "refuted_claims": _as_list(value.get("refuted_claims")),
        "open_questions": _as_list(value.get("open_questions")),
        "hypothesis_status": normalized_hypothesis_status,
    }


def _normalize_plan_block(plan: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(plan)
    normalized.setdefault("plan_id", "plan_a")
    normalized.setdefault("summary", _plan_summary(normalized))
    normalized.setdefault("reason_selected", "")
    normalized["steps"] = _as_list(normalized.get("steps"))
    normalized["required_visualizations"] = _as_list(normalized.get("required_visualizations"))
    normalized.setdefault("caveat", "")
    return normalized


def _normalize_alternative_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict):
        plan = {"summary": str(plan)}
    normalized = dict(plan)
    normalized.setdefault("plan_id", "")
    normalized.setdefault("summary", "")
    normalized.setdefault("when_to_use", "")
    normalized.setdefault("why_not_selected_now", "")
    normalized["evidence_requirements"] = _as_list(normalized.get("evidence_requirements"))
    normalized["expected_starting_artifact_type"] = _enum_or_default(
        normalized.get("expected_starting_artifact_type"),
        allowed=_ARTIFACT_TYPES,
        default="none",
    )
    return normalized


_CALLBACK_TYPE_ALIASES = {
    "reasoning": "ask_panelist_for_more_reasoning",
    "literature": "ask_panelist_for_more_literature",
}


def _canonical_callback_type(value: Any) -> str:
    """Normalize short callback_type aliases to their full canonical form.

    MediatorAgent (and post-analysis callbacks) emit short aliases
    ("reasoning" / "literature"). This is the single source of truth for that
    mapping — _normalize_callbacks, _extract_callback_requests, and the public
    run_panelist_callback entry point (MediatorAgent's panelist_callback_executor)
    all call this so a "literature" callback reliably resolves to
    "ask_panelist_for_more_literature" and hits _run_panelist_callback's
    retrieval-tool branch regardless of which caller normalizes it first.
    """
    text = str(value or "").strip()
    return _CALLBACK_TYPE_ALIASES.get(text, text)


def _normalize_callbacks(value: Any) -> tuple[list[dict[str, Any]], list[Any]]:
    raw_callbacks = _as_list(value)
    callbacks: list[dict[str, Any]] = []
    invalid: list[Any] = []
    for item in raw_callbacks:
        if not isinstance(item, dict):
            if item not in (None, ""):
                invalid.append(item)
            continue
        role = str(item.get("role") or item.get("to_role") or "").strip().lower()
        callback_type = _canonical_callback_type(item.get("callback_type"))
        assigned_gap = str(item.get("assigned_gap") or item.get("gap") or "").strip()
        if role not in _ROLES or callback_type not in {
            "ask_panelist_for_more_reasoning",
            "ask_panelist_for_more_literature",
        } or not assigned_gap:
            invalid.append(dict(item))
            continue
        normalized = dict(item)
        normalized["role"] = role
        normalized["callback_type"] = callback_type
        normalized["assigned_gap"] = assigned_gap
        normalized.setdefault("callback_source", "mediator_gap")
        normalized.setdefault("why_needed", "")
        normalized.setdefault("expected_output", "")
        callbacks.append(normalized)
    return callbacks, invalid


def _mark_callbacks_skipped(plan: dict[str, Any], *, reason: str) -> dict[str, Any]:
    out = _normalize_research_plan_schema(plan)
    callbacks = _extract_callback_requests(out, max_callbacks=100, max_per_role=100)
    if callbacks:
        out["_callbacks_skipped"] = True
        out["_callback_budget_exhausted"] = True
        out["_callback_skip_reason"] = reason
        out["_skipped_callbacks"] = callbacks
        out["mediator_decision"] = "needs_panelist_callback"
    else:
        out.setdefault("_callbacks_skipped", False)
    return out


def _extract_callback_requests(
    plan: dict[str, Any],
    *,
    max_callbacks: int,
    max_per_role: int,
) -> list[dict[str, Any]]:
    if not isinstance(plan, dict):
        return []
    raw_callbacks = plan.get("callbacks") or []
    if not isinstance(raw_callbacks, list):
        raw_callbacks = [raw_callbacks]
    role_counts: dict[str, int] = {}
    callbacks: list[dict[str, Any]] = []
    for item in raw_callbacks:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or item.get("to_role") or "").strip().lower()
        if role not in _ROLES:
            continue
        callback_type = _canonical_callback_type(item.get("callback_type"))
        if callback_type not in {"ask_panelist_for_more_reasoning", "ask_panelist_for_more_literature"}:
            callback_type = "ask_panelist_for_more_reasoning"
        if role_counts.get(role, 0) >= max_per_role:
            continue
        normalized = dict(item)
        normalized["role"] = role
        normalized["callback_type"] = callback_type
        normalized.setdefault("callback_source", "mediator_gap")
        normalized["assigned_gap"] = str(normalized.get("assigned_gap") or normalized.get("gap") or "").strip()
        normalized.setdefault("why_needed", "")
        normalized.setdefault("expected_output", "")
        callbacks.append(normalized)
        role_counts[role] = role_counts.get(role, 0) + 1
        if len(callbacks) >= max_callbacks:
            break
    return callbacks


def _extract_json_field_from_tag(text: str, tag: str, field: str) -> Any:
    payload = _extract_tag_json(str(text or ""), tag)
    if isinstance(payload, dict):
        return payload.get(field, [])
    return []


def _build_adversarial_state(adv_result: dict[str, Any] | None) -> dict[str, Any]:
    """Extract adversarial critique summary from the last adversarial loop result."""
    if not adv_result:
        return {"critique_summary": "", "critique_target": "", "failure_mode": "", "required_revision": ""}
    verdict = str(adv_result.get("verdict") or "")
    challenge = adv_result.get("last_challenge") or {}
    challenges = challenge.get("challenges") if isinstance(challenge, dict) else []
    if not isinstance(challenges, list):
        challenges = []
    first_challenge = challenges[0] if challenges and isinstance(challenges[0], dict) else {}
    critique_summary = str((challenge or {}).get("summary") or "").strip()
    required_revision = str((challenge or {}).get("recommended_revision") or "").strip()
    plan = adv_result.get("plan") or {}
    revision_notes = str(plan.get("revision_notes") or "").strip()
    if not critique_summary:
        critique_summary = revision_notes
    if not required_revision:
        required_revision = revision_notes
    return {
        "critique_summary": critique_summary,
        "critique_target": str(first_challenge.get("target") or "research_plan"),
        "failure_mode": verdict if verdict != "survives" else "",
        "required_revision": required_revision,
    }


def _collect_papers_from_panel_outputs(outputs: dict[str, str]) -> list[dict[str, Any]]:
    papers: list[dict[str, Any]] = []
    for text in outputs.values():
        for tag in ("ROUND3", "ROUND1", "CALLBACK", "UPDATE"):
            payload = _extract_tag_json(str(text or ""), tag)
            if not isinstance(payload, dict) or payload.get("parse_error"):
                continue
            for evidence in _extract_retrieval_assessments(payload):
                for paper in _papers_from_retrieval_evidence(evidence):
                    papers.append(paper)
            break
    return _dedupe_compact_papers(papers)


def _papers_from_retrieval_evidence(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    raw = evidence.get("papers") or evidence.get("retrieved_papers") or []
    if isinstance(raw, dict):
        raw = raw.get("papers", [])
    if not isinstance(raw, list):
        return []
    compact: list[dict[str, Any]] = []
    for paper in raw:
        if not isinstance(paper, dict):
            continue
        compact.append(
            {
                "paper_id": paper.get("paper_id") or paper.get("doc_id"),
                "doc_id": paper.get("doc_id") or paper.get("paper_id"),
                "title": paper.get("title", ""),
                "doi": paper.get("doi", ""),
                "retrieval_intent": evidence.get("retrieval_intent", ""),
                "retrieval_goal": evidence.get("retrieval_goal", ""),
            }
        )
    return compact


def _dedupe_compact_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for paper in papers:
        key = str(paper.get("doi") or paper.get("paper_id") or paper.get("doc_id") or paper.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(paper)
    return result


def _plan_summary(plan: dict[str, Any]) -> str:
    summary = str(plan.get("summary") or "").strip()
    if summary:
        return summary
    steps = _as_list(plan.get("steps"))
    if steps:
        first = steps[0]
        if isinstance(first, dict):
            return str(first.get("biological_goal") or first.get("step") or first.get("summary") or "").strip()
        return str(first).strip()
    return ""


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return default


def _enum_or_default(value: Any, *, allowed: set[str], default: str) -> str:
    text = str(value or "").strip()
    return text if text in allowed else default


def _clamp_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clamp_float(value: Any, *, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _tag_done_handler(
    text: str,
    tag: str,
    tool_trace_path: "Path | None" = None,
    min_tool_calls: int = 0,
) -> dict[str, Any]:
    """Response handler for ToolCallingAgentRunner — done when tag block is present
    and the minimum number of tool calls has been satisfied."""
    has_output = any(
        f"<{c}>" in text and f"</{c}>" in text
        for c in _tag_aliases(tag)
    )
    if has_output:
        # Check minimum tool call requirement
        if min_tool_calls > 0 and tool_trace_path is not None:
            try:
                n_calls = sum(1 for line in Path(str(tool_trace_path)).read_text(encoding="utf-8").splitlines() if line.strip())
            except FileNotFoundError:
                n_calls = 0
            if n_calls < min_tool_calls:
                return {
                    "done": False,
                    "next_user_input": (
                        f"You produced the output block after only {n_calls} tool call(s), "
                        f"but the intent loop requires at least {min_tool_calls} "
                        f"You must continue the intent loop and retrieve more literature "
                        f"before producing your final output."
                    ),
                }
        return {"done": True, "result": text}
    open_tag = f"<{_tag_aliases(tag)[0]}>"
    close_tag = f"</{_tag_aliases(tag)[0]}>"
    return {
        "done": False,
        "next_user_input": (
            f"Your response must contain a {open_tag}...{close_tag} block "
            f"with your structured output. Please produce it now."
        ),
    }


def _tag_aliases(tag: str) -> list[str]:
    aliases = {
        "ROUND1": ["ROUND1", "BIOLOGIST_OUTPUT", "STATISTICIAN_OUTPUT", "BIOINFORMATICIAN_OUTPUT"],
        "ROUND3": ["ROUND3", "BIOLOGIST_OUTPUT", "STATISTICIAN_OUTPUT", "BIOINFORMATICIAN_OUTPUT"],
        "UPDATE": ["UPDATE", "BIOLOGIST_OUTPUT", "STATISTICIAN_OUTPUT", "BIOINFORMATICIAN_OUTPUT"],
        "CALLBACK": ["CALLBACK", "CALLBACK_OUTPUT"],
        "MEDIATOR": ["MEDIATOR", "MEDIATOR_OUTPUT"],
        "MEDIATOR_POST_ANALYSIS": ["MEDIATOR_POST_ANALYSIS", "POST_ANALYSIS_DECISION", "MEDIATOR_POST_ANALYSIS_OUTPUT"],
    }
    return aliases.get(tag, [tag])


def _extract_retrieval_assessments(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw = payload.get("retrieval_evidence") or []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _read_retrieval_tool_calls(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    calls: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if payload.get("tool_name") == "retrieve_literature":
                calls.append(payload)
    except Exception:
        return []
    return calls


def _match_retrieval_call(
    calls: list[dict[str, Any]],
    retrieval_intent: str,
    retrieval_goal: str,
) -> dict[str, Any]:
    intent = str(retrieval_intent or "").strip().lower()
    goal = str(retrieval_goal or "").strip().lower()
    for call in reversed(calls):
        args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        if intent and intent == str(args.get("retrieval_intent") or "").strip().lower():
            return call
        if goal and goal == str(args.get("retrieval_goal") or "").strip().lower():
            return call
    return calls[-1] if calls else {}


def _compact_retrieval_paper(paper: Any) -> dict[str, Any]:
    if not isinstance(paper, dict):
        return {}
    return {
        "doc_id": paper.get("doc_id") or paper.get("paper_id"),
        "title": paper.get("title"),
        "url": paper.get("url"),
        "source": paper.get("source"),
        "full_text_status": paper.get("full_text_status"),
        "confidence": paper.get("confidence"),
        "evidence_contribution": paper.get("evidence_contribution") or paper.get("summary"),
    }
