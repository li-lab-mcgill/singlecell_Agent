"""ResearchLoop — orchestrates the full research → execute → analyze cycle.

Unified pipeline position:
  SessionRouter → SessionDispatcher → ResearchLoop
    → ScientistPanel / MediatorAgent / AdversarialPanelist
    → ToolConsultantAgent → DagExecutor / CoderAgent

Flow per phase:
  1. ResearchLoop._run_formulation_stage() coordinates panelists, mediator,
     adversary review, and ResearchState commit after accepted candidate.
  2. ToolConsultantAgent.decide(research_plan) → dag_plan or implementation_plan
  3. Execution:
       dag_plan           → DagExecutor.execute()
       implementation_plan → CoderAgent.run()
  4. AnalyzerPanel.analyze() → analyzer_report
  5. (optional) AttributingCritic.attribute() → per-step GOOD/BAD/NEEDS_REVISION
  6. (optional) ShortTermMemory.add_phase() → phase trace
  7. (optional) ContextManager.update_from_phase() → layered evidence/hypothesis/warnings
  8. MediatorAgent.post_analysis() → next research action

Loop terminates when next_action is "done" or "abstain", or max_phases is reached.

Usage:
    loop = ResearchLoop(
        scientist_panel=scientist_panel,
        analyzer_panel=analyzer_panel,
        tool_consultant=tool_consultant,
        dag_executor=dag_executor,
        coder=coder,                      # CoderAgent for custom implementation tasks
        attributing_critic=critic,        # optional — per-step attribution
        short_term_memory=mem,            # optional — phase trace
        context_manager=ctx,              # optional — evidence/hypothesis context
        input_h5ad_path="/data/pbmc.h5ad",
        data_summary={"n_cells": 8432, "tissue": "PBMC", "disease": "healthy"},
        result_dir="results/loop",
        max_phases=5,
    )
    result = loop.run(
        user_question="What cell types are present in my PBMC dataset?",
        pipeline_mode="full",   # or "brief" | "lightweight" | "skip_panel"
    )
    print(result["final_report"])
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.session_recorder import SessionRecorder
from agents.state_graph import StateGraphManager
from agents.mediator_agent import MediatorAgent
from agents.panelist_tools import build_paper_detail_tool_registry
from agents.research_state import ResearchState
from backend.workspace_profiler import profile_workspace


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_ROLES = {"biologist", "statistician", "bioinformatician"}


class ResearchLoop:
    """Orchestrates the ScientistPanel → ToolConsultant → DAG/Coder → AnalyzerPanel loop.

    Args:
        scientist_panel:    ScientistPanel instance for specialist panelist runs.
        analyzer_panel:     AnalyzerPanel instance.
        tool_consultant:    ToolConsultantAgent instance (optionally experience-guided).
        dag_executor:       DagExecutor instance (for dag_plan tasks).
        coder:              CoderAgent instance (simpler fallback for implementation_plan tasks).
                            Used for implementation_plan tasks.
        attributing_critic: AttributingCritic instance (optional — per-step attribution per phase).
        short_term_memory:  ShortTermMemory instance (optional — phase trace within session).
        context_manager:    ContextManager instance (optional — layered evidence/hypothesis context).
        input_h5ad_path:    Path to the primary input h5ad file (used for execution).
        data_paths:         Optional list of additional data file paths.
                            Directories are scanned for supported file types automatically.
        data_summary:       Optional dict with biological context: tissue, disease, modality, notes.
                            Structural facts (columns, dtypes, etc.) are always read from the files.
        result_dir:         Directory for loop-level bookkeeping JSON files.
        max_phases:         Hard cap on the number of phases (default 5).
    """

    def __init__(
        self,
        *,
        scientist_panel: Any,
        analyzer_panel: Any,
        tool_consultant: Any,
        alignment_reviewer: Any | None = None,
        dag_executor: Any | None = None,
        coder: Any | None = None,
        optimizing_coder: Any | None = None,
        attributing_critic: Any | None = None,
        short_term_memory: Any | None = None,
        context_manager: Any | None = None,
        input_h5ad_path: str,
        data_paths: list[str] | None = None,
        data_summary: dict[str, Any] | str | None = None,
        result_dir: str | Path,
        max_phases: int = 5,
        session_recorder: SessionRecorder | None = None,
        state_graph_manager: StateGraphManager | None = None,
        mediator_agent: Any | None = None,
        adversarial_panelist: Any | None = None,
    ):
        self.scientist_panel = scientist_panel
        self.analyzer_panel = analyzer_panel
        self.tool_consultant = tool_consultant
        self.alignment_reviewer = alignment_reviewer
        self.dag_executor = dag_executor
        self.coder = coder
        self.optimizing_coder = optimizing_coder  # retained for API compatibility; routing uses CoderAgent
        self.attributing_critic = attributing_critic
        self.short_term_memory = short_term_memory
        self.context_manager = context_manager
        self.input_h5ad_path = str(input_h5ad_path)

        # Profile all provided data files; primary h5ad is always included
        all_paths = [input_h5ad_path] + (data_paths or [])
        self.data_summary = profile_workspace(all_paths, data_summary)

        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.max_phases = int(max_phases)
        self.session_recorder = session_recorder
        self.state_graph_manager = state_graph_manager
        self.mediator_agent = mediator_agent
        self.adversarial_panelist = adversarial_panelist

        if self.short_term_memory is not None and hasattr(self.scientist_panel, "set_short_term_memory"):
            self.scientist_panel.set_short_term_memory(self.short_term_memory)

        # Track prior phase metrics for delta-based attribution (also via short_term_memory)
        self._prior_phase_metrics: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        user_question: str,
        original_user_message: str | None = None,
        session_context: dict[str, Any] | None = None,
        research_state: ResearchState | None = None,
        workspace_decision: dict[str, Any] | None = None,
        anchor_papers: list[dict[str, Any]] | None = None,
        pipeline_mode: str = "full",
    ) -> dict[str, Any]:
        """Run the full research loop.

        Args:
            user_question:  The scientific question driving this session.
            anchor_papers:  Optional list of pre-retrieved paper dicts to seed RAG.
            pipeline_mode:  Research-loop mode. "skip_panel" creates a direct
                            operational plan; other modes run the formulation
                            stage through ResearchLoop.

        Returns:
            {
              "status":           "done" | "abstain" | "max_phases_reached",
              "final_report":     <last AnalyzerPanel report dict>,
              "phases_completed": <int>,
              "phase_log":        [<per-phase summary>],
              "pipeline_mode":    <pipeline_mode used>,
            }
        """
        agent_user_question = _agent_user_question(
            resolved_intent=user_question,
            original_user_message=original_user_message,
        )
        if research_state is None:
            recorder = self._ensure_session_recorder(user_question=user_question)
            state_graph = self._ensure_state_graph(recorder)
            research_state = ResearchState(
                user_question=user_question,
                data_summary=self.data_summary,
                recorder=recorder,
                graph=state_graph,
                original_user_message=original_user_message or user_question,
                resolved_intent=user_question,
                session_context=session_context or {},
            )
        else:
            recorder = research_state.recorder
            state_graph = research_state.graph
            research_state.user_question = user_question
            research_state.resolved_intent = user_question
            research_state.original_user_message = original_user_message or research_state.original_user_message or user_question
            research_state.session_context = session_context or research_state.session_context
            self.session_recorder = recorder
            self.state_graph_manager = state_graph
        recorder.start_turn(user_message=original_user_message or user_question)
        if workspace_decision:
            research_state.session_context = {
                **(research_state.session_context or {}),
                "research_workspace_decision": workspace_decision,
            }
            recorder.save_json("route/research_workspace_decision_latest.json", workspace_decision)

        # ── Phase 0: formulate initial research plan ──────────────────
        formulation_result = self._run_formulation_stage(
            research_state=research_state,
            user_question=agent_user_question,
            anchor_papers=anchor_papers or [],
            mode=pipeline_mode,
        )
        legacy_mediator_flow = bool(formulation_result.get("_legacy_scientist_panel_formulate"))
        self._save("phase0_formulate", formulation_result)

        if formulation_result.get("status") == "unanswerable":
            recorder.set_status("completed")
            self._save("loop_summary", {"status": "abstain", "phases_completed": 0, "pipeline_mode": pipeline_mode})
            return {
                "status": "abstain",
                "final_report": {"summary": "No defensible research plan could be formed.", "formulation_result": formulation_result},
                "post_analysis_decision": {},
                "phases_completed": 0,
                "phase_log": [],
                "pipeline_mode": pipeline_mode,
            }

        brief = formulation_result.get("mediator_output") or formulation_result
        research_context = _extract_research_context(
            {
                **(brief if isinstance(brief, dict) else {}),
                "selected_research_plan": formulation_result.get("selected_research_plan", {}),
                "alternative_research_plans": formulation_result.get("alternative_research_plans", []),
                "evidence_state": formulation_result.get("evidence_state", {}),
            },
            agent_user_question,
        )
        research_plan: dict[str, Any] = research_context["selected_research_plan"]
        plan_json_ref = recorder.save_json("nodes/plan_001/research_plan.json", research_plan)
        plan_md_ref = recorder.save_text("nodes/plan_001/research_plan.md", _plan_to_markdown(research_plan, agent_user_question))
        active_node_id = research_state.commit_initial_plan(
            selected_plan=research_plan,
            alternatives=research_context.get("alternative_research_plans", []),
            plan_ref=plan_md_ref,
            plan_json_ref=plan_json_ref,
            evidence_state=research_context.get("evidence_state", {}),
            trajectory_decision=formulation_result.get("trajectory_decision", {}),
            trace_refs={"formulate": "phase0_formulate.json", "adversary": formulation_result.get("adversary_result", {})},
        )
        recorder.set_active_node(active_node_id)
        recorder.append_progress("research_plan", "Initialized selected research plan.", {"node_id": active_node_id, "plan": plan_json_ref})

        # working_model starts as the full formulate() output
        working_model: dict[str, Any] | str = {"evidence_state": research_state.evidence_state, "mediator_output": brief}

        # Track the current input h5ad — may advance as phases produce outputs
        current_input_h5ad = self.input_h5ad_path
        previous_dag_plan: dict[str, Any] | None = None
        previous_post_analysis_decision: dict[str, Any] | None = None

        phase_log: list[dict[str, Any]] = []
        analyzer_report: dict[str, Any] = {}

        for phase_number in range(1, self.max_phases + 1):

            # ── Step 1: ToolConsultant → dag_plan or implementation_plan ─
            user_message = _format_research_plan(research_plan, agent_user_question, research_context=research_context)
            session_state = self._build_session_state(
                current_input_h5ad=current_input_h5ad,
                previous_dag_plan=previous_dag_plan,
                research_context=research_context,
                post_analysis_decision=previous_post_analysis_decision,
                state_graph_context=research_state.context_for_tool_consultant(
                    rerun_intent=(previous_post_analysis_decision or {}).get("rerun_intent") if previous_post_analysis_decision else None
                ),
            )
            decision = self.tool_consultant.decide(
                user_message=user_message,
                session_state=session_state,
                session_tag=f"phase{phase_number}_tool_consultant",
            )
            self._save(f"phase{phase_number}_decision", decision)
            self._record_tool_decision(
                research_state,
                decision,
                source="tool_consultant_initial",
                phase_number=phase_number,
                trace_ref=f"phase{phase_number}_decision.json",
            )
            tool_plan_ref = recorder.save_json(f"nodes/{active_node_id}/tool_plan.json", decision)
            state_graph.attach_tool_plan(
                active_node_id,
                tool_plan_ref=tool_plan_ref,
                implementation_plan_ref=(
                    recorder.save_text(
                        f"nodes/{active_node_id}/implementation_plan.md",
                        _to_markdown_block(decision.get("implementation_plan")),
                    )
                    if decision.get("implementation_plan")
                    else None
                ),
            )
            recorder.append_progress("tool_plan", "ToolConsultant produced executable plan.", {"node_id": active_node_id, "tool_plan": tool_plan_ref})

            decision = self._review_and_maybe_revise_decision(
                user_question=agent_user_question,
                research_context=research_context,
                decision=decision,
                session_state=session_state,
                user_message=user_message,
                phase_number=phase_number,
            )
            self._save(f"phase{phase_number}_aligned_decision", decision)
            recorder.save_json(f"traces/tool_consultant/phase{phase_number}_decision.json", decision)
            self._record_tool_decision(
                research_state,
                decision,
                source="tool_consultant_aligned",
                phase_number=phase_number,
                trace_ref=f"traces/tool_consultant/phase{phase_number}_decision.json",
            )

            # ── Step 2: Execute ──────────────────────────────────────────
            dag_result, figure_paths, execution_status = self._execute(
                decision=decision,
                current_input_h5ad=current_input_h5ad,
                phase_number=phase_number,
            )
            self._save(f"phase{phase_number}_dag_result", dag_result)
            execution_id = f"exec_{phase_number:03d}"
            execution_result_ref = recorder.save_json(f"executions/{execution_id}/dag_result.json", dag_result)
            if decision.get("dag_plan"):
                recorder.save_json(f"executions/{execution_id}/dag_plan.json", decision.get("dag_plan"))
            if decision.get("implementation_plan"):
                recorder.save_json(f"executions/{execution_id}/coder_report.json", dag_result)
            execution_summary_ref = recorder.save_json(
                f"nodes/{active_node_id}/execution_summary.json",
                {
                    "execution_id": execution_id,
                    "status": execution_status,
                    "result_ref": execution_result_ref,
                    "figure_paths": figure_paths,
                },
            )
            state_graph.attach_execution(active_node_id, execution_ref=execution_result_ref, execution_summary_ref=execution_summary_ref)
            recorder.append_progress("execution", f"Execution finished with status: {execution_status}.", {"node_id": active_node_id, "execution": execution_result_ref})

            # Advance input h5ad if the DAG produced a new processed file
            next_h5ad = _extract_best_h5ad(dag_result)
            if next_h5ad:
                current_input_h5ad = next_h5ad

            # Remember the dag_plan for session_state on next iteration
            previous_dag_plan = decision.get("dag_plan")

            # ── Step 3: AnalyzerPanel ────────────────────────────────────
            # If adversarial alignment blocks execution, no computational
            # results exist. Do not run the AnalyzerPanel/LiteratureGrounder
            # on an empty phase; send a structured blocked report directly to
            # the Mediator decision step below.
            if execution_status == "blocked" or dag_result.get("status") == "blocked":
                analyzer_report = _blocked_execution_report(
                    dag_result=dag_result,
                    decision=decision,
                    research_plan=research_plan,
                )
            else:
                analyzer_report = self.analyzer_panel.analyze(
                    user_question=agent_user_question,
                    research_plan=research_plan,
                    dag_result=dag_result,
                    figure_paths=figure_paths,
                    working_model=working_model,
                    phase_number=phase_number,
                )
            self._save(f"phase{phase_number}_analyzer_report", analyzer_report)
            analyzer_ref = recorder.save_json(f"nodes/{active_node_id}/analyzer_report.json", analyzer_report)
            analyzer_md_ref = recorder.save_text(f"nodes/{active_node_id}/analyzer_report.md", _analyzer_report_to_markdown(analyzer_report))
            recorder.save_json(f"traces/analyzer/{active_node_id}_parsed_report.json", analyzer_report)
            self._record_analyzer_report(
                research_state,
                analyzer_report,
                source="analyzer",
                phase_number=phase_number,
                trace_ref=f"traces/analyzer/{active_node_id}_parsed_report.json",
            )
            state_graph.attach_analyzer(active_node_id, analyzer_report_ref=analyzer_ref, analyzer_report_md_ref=analyzer_md_ref)
            analyzer_progress_message = (
                "Execution was blocked; synthesized blocked report for Mediator."
                if analyzer_report.get("result_verdict") == "blocked"
                else "AnalyzerPanel produced report."
            )
            recorder.append_progress("analyzer", analyzer_progress_message, {"node_id": active_node_id, "analyzer_report": analyzer_ref})

            # ── Step 3b: AttributingCritic (optional) ────────────────────
            attributions: dict[str, Any] = {}
            if self.attributing_critic is not None:
                attributions = self.attributing_critic.attribute(
                    stage_results=dag_result,
                    research_plan=research_plan,
                    prior_phase_metrics=self._prior_phase_metrics,
                    phase_number=phase_number,
                )
                self._save(f"phase{phase_number}_attributions", attributions)
                # Update prior metrics from analyzer report for next phase
                self._prior_phase_metrics = _extract_metrics(analyzer_report)

            # ── Step 3c: ShortTermMemory (optional) ──────────────────────
            if self.short_term_memory is not None:
                self.short_term_memory.add_phase(
                    phase_number=phase_number,
                    research_plan=research_plan,
                    dag_result=dag_result,
                    analyzer_report=analyzer_report,
                    step_attributions=attributions if attributions else None,
                )

            # ── Step 3d: ContextManager (optional) ───────────────────────
            if self.context_manager is not None:
                update_working_model = working_model  # will be updated after step 4
                self.context_manager.update_from_phase(
                    phase_number=phase_number,
                    working_model=update_working_model,
                    analyzer_report=analyzer_report,
                    attributions=attributions if attributions else None,
                )

            # ── Step 4: Mediator post-analysis decision ─────────────────
            if legacy_mediator_flow:
                post_decision = self._decide_after_analysis(
                    user_question=agent_user_question,
                    phase_number=phase_number,
                    analyzer_report=analyzer_report,
                    working_model=working_model,
                    research_context=research_context,
                    decision=decision,
                    dag_result=dag_result,
                )
                post_decision = self._run_legacy_post_analysis_callback_loop(
                    user_question=agent_user_question,
                    phase_number=phase_number,
                    analyzer_report=analyzer_report,
                    working_model=working_model,
                    research_context=research_context,
                    decision=decision,
                    dag_result=dag_result,
                    post_decision=post_decision,
                )
            else:
                mediator = self._ensure_mediator_agent()
                post_decision = mediator.post_analysis(
                    post_analysis_context=research_state.context_for_mediator_post_analysis(
                        phase_number=phase_number,
                        analyzer_report=analyzer_report,
                        dag_result_summary=_summarize_execution_for_mediator(dag_result),
                        tool_decision=decision,
                        artifact_registry_summary=None,
                    )
                )
                self._record_mediator_output(
                    research_state,
                    post_decision,
                    source="post_analysis",
                    phase_number=phase_number,
                    trace_ref=f"phase{phase_number}_post_analysis_decision.json",
                )
                post_decision = self._review_post_analysis_candidate_if_needed(
                    research_state=research_state,
                    phase_number=phase_number,
                    post_decision=post_decision,
                    analyzer_report=analyzer_report,
                    dag_result=dag_result,
                    tool_decision=decision,
                )
            self._save(f"phase{phase_number}_post_analysis_decision", post_decision)
            if isinstance(post_decision.get("evidence_state"), dict) and post_decision.get("evidence_state"):
                research_state.update_evidence_state(post_decision["evidence_state"])
                post_decision["evidence_state"] = research_state.evidence_state
                research_context["evidence_state"] = research_state.evidence_state
                working_model = {"evidence_state": research_state.evidence_state}
            next_decision_ref = recorder.save_json(f"nodes/{active_node_id}/next_decision.json", post_decision)
            recorder.save_json(f"traces/mediator/phase{phase_number}_post_analysis_decision.json", post_decision)
            state_graph.attach_next_decision(active_node_id, decision_ref=next_decision_ref)

            update_result: dict[str, Any] = {}
            next_action = _next_action_from_post_analysis_decision(post_decision)
            graph_node_after_decision = state_graph.apply_post_analysis_decision(
                decision=post_decision,
                active_plan=research_plan,
                decision_ref=next_decision_ref,
            )

            self._save(f"phase{phase_number}_update", {"skipped": True, "reason": "post_analysis_decision", "decision_type": post_decision.get("decision_type")})

            phase_log.append({
                "phase": phase_number,
                "execution_status": execution_status,
                "next_action": next_action,
                "post_analysis_decision": post_decision.get("decision_type"),
                "claim_updates": analyzer_report.get("claim_updates", []),
            })

            if next_action in ("done", "abstain", "awaiting_user"):
                if next_action == "awaiting_user":
                    recorder.set_status("awaiting_user", active_node_id=graph_node_after_decision)
                else:
                    recorder.set_status("completed", active_node_id=graph_node_after_decision)
                final_ref = recorder.save_json(
                    "reports/final_answer.json",
                    {
                        "status": next_action,
                        "final_report": analyzer_report,
                        "post_analysis_decision": post_decision,
                    },
                )
                recorder.set_final_response(final_ref)
                self._save("loop_summary", {"status": next_action, "phases_completed": phase_number, "pipeline_mode": pipeline_mode})
                return {
                    "status": next_action,
                    "final_report": analyzer_report,
                    "post_analysis_decision": post_decision,
                    "phases_completed": phase_number,
                    "phase_log": phase_log,
                    "pipeline_mode": pipeline_mode,
                }

            next_plan = post_decision.get("updated_selected_research_plan")
            if isinstance(next_plan, dict) and next_plan.get("steps"):
                research_plan = next_plan
                active_node_id = graph_node_after_decision
                research_state.selected_research_plan = research_plan
                research_state.active_node_id = active_node_id
                if active_node_id:
                    new_plan_json_ref = recorder.save_json(f"nodes/{active_node_id}/research_plan.json", research_plan)
                    new_plan_md_ref = recorder.save_text(f"nodes/{active_node_id}/research_plan.md", _plan_to_markdown(research_plan, agent_user_question))
                    state_graph.set_plan_refs(active_node_id, plan_ref=new_plan_md_ref, plan_json_ref=new_plan_json_ref)
                    recorder.set_active_node(active_node_id)
                research_context = _extract_research_context(
                    {
                        "selected_research_plan": next_plan,
                        "research_plan": next_plan,
                        "alternative_research_plans": research_context.get("alternative_research_plans", []),
                        "analysis_requirements": research_context.get("analysis_requirements", []),
                        "validation_requirements": research_context.get("validation_requirements", []),
                        "success_criteria": research_context.get("success_criteria", {}),
                        "evidence_state": research_state.evidence_state,
                    },
                    agent_user_question,
                )
            research_context["last_post_analysis_decision"] = post_decision
            previous_post_analysis_decision = post_decision

        # Hit max_phases without "done" — return what we have
        recorder.set_status("max_phases_reached", active_node_id=active_node_id)
        self._save("loop_summary", {"status": "max_phases_reached", "phases_completed": self.max_phases, "pipeline_mode": pipeline_mode})
        return {
            "status": "max_phases_reached",
            "final_report": analyzer_report,
            "phases_completed": self.max_phases,
            "phase_log": phase_log,
            "pipeline_mode": pipeline_mode,
        }

    # ------------------------------------------------------------------
    # Execution dispatch
    # ------------------------------------------------------------------

    def _run_formulation_stage(
        self,
        *,
        research_state: ResearchState,
        user_question: str,
        anchor_papers: list[dict[str, Any]],
        mode: str,
    ) -> dict[str, Any]:
        """Run panelists, Mediator, adversary, and return an uncommitted candidate."""
        if mode == "skip_panel":
            plan = {
                "plan_id": "operational_direct",
                "summary": f"Execute the requested workflow: {user_question}",
                "reason_selected": "The request was routed as direct operational execution.",
                "steps": [user_question],
                "required_visualizations": [],
            }
            return {
                "status": "accepted",
                "selected_research_plan": plan,
                "trajectory_decision": {"action": "initialize_plan", "branch_from_node_id": None, "reason": "direct operational plan"},
                "mediator_output": {"selected_research_plan": plan, "formulation_status": "ready_for_adversary"},
                "adversary_result": {"adversary_verdict": "skipped", "verdict": "skipped"},
                "panelist_outputs": {},
                "callback_history": [],
                "research_gap_resolution": [],
                "limitations": [],
                "evidence_state": {},
            }

        mediator = self._ensure_mediator_agent()
        adversary = self._ensure_adversarial_panelist()
        panelist_outputs = self.scientist_panel.run_initial_panelists(
            user_question=user_question,
            data_summary=self.data_summary,
            anchor_papers=anchor_papers,
        )
        research_state.record_panelist_outputs(panelist_outputs)
        mediator_output = mediator.formulate(
            formulation_context=research_state.context_for_mediator_formulation()
        )
        self._record_mediator_output(research_state, mediator_output, source="formulation", trace_ref="mediator_formulation.json")
        callback_history: list[dict[str, Any]] = []
        mediator_output, callback_history = self._complete_mediator_callbacks(
            research_state=research_state,
            mediator=mediator,
            mediator_output=mediator_output,
            callback_history=callback_history,
        )

        if mediator_output.get("formulation_status") != "ready_for_adversary":
            if not isinstance(mediator_output.get("selected_research_plan"), dict):
                return {
                    "status": "unanswerable",
                    "selected_research_plan": {},
                    "trajectory_decision": {"action": "declare_unanswerable", "branch_from_node_id": None, "reason": "Mediator callback budget exhausted without a candidate research plan."},
                    "mediator_output": mediator_output,
                    "adversary_result": {},
                    "panelist_outputs": panelist_outputs,
                    "callback_history": callback_history,
                    "research_gap_resolution": mediator_output.get("research_gap_resolution", []),
                    "limitations": mediator_output.get("limitations", []),
                    "evidence_state": mediator_output.get("evidence_state", {}),
                    "alternative_research_plans": mediator_output.get("alternative_research_plans", []),
                }
            mediator_output["formulation_status"] = "ready_for_adversary"
            mediator_output["callback_budget_exhausted"] = True

        return self._run_adversary_until_accepted(
            research_state=research_state,
            mediator_output=mediator_output,
            adversary=adversary,
            mediator=mediator,
            callback_history=callback_history,
            panelist_outputs=panelist_outputs,
        )

    def _run_adversary_until_accepted(
        self,
        *,
        research_state: ResearchState,
        mediator_output: dict[str, Any],
        adversary: Any,
        mediator: MediatorAgent,
        callback_history: list[dict[str, Any]],
        panelist_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        max_rounds = int(getattr(adversary, "max_rounds", 2) or 2)
        candidate_plan = mediator_output.get("selected_research_plan") or {}
        trajectory_decision = mediator_output.get("trajectory_decision") or {
            "action": "initialize_plan",
            "branch_from_node_id": None,
            "reason": "candidate plan ready for adversarial review",
        }
        last_adversary_result: dict[str, Any] = {}
        for round_number in range(1, max_rounds + 1):
            adversary_context = research_state.context_for_adversary(
                candidate_plan=candidate_plan,
                candidate_trajectory_decision=trajectory_decision,
            )
            adversary_result = adversary.run(adversary_context=adversary_context)
            last_adversary_result = adversary_result
            research_state.record_adversary_output(adversary_result)
            verdict = str(adversary_result.get("adversary_verdict") or adversary_result.get("verdict") or "").strip()
            if verdict in {"survives", "skipped"}:
                return _candidate_resolution_to_formulation_result(
                    resolution={
                        "status": "accepted",
                        "selected_research_plan": candidate_plan,
                        "trajectory_decision": trajectory_decision,
                        "reason": "adversary_survives" if verdict == "survives" else "adversary_skipped",
                        "adversarial_review_status": verdict,
                        "adversarial_review_interpretation": "reviewed_no_blocking_flaw"
                        if verdict == "survives"
                        else "not_reviewed",
                    },
                    mediator_output=mediator_output,
                    adversary_result=adversary_result,
                    panelist_outputs=panelist_outputs,
                    callback_history=callback_history,
                )
            revised = mediator.revise_from_adversary(
                adversary_revision_context=research_state.context_for_mediator_adversary_revision(
                    adversary_critique=adversary_result,
                    adversary_revision_round=round_number,
                    max_adversary_revision_rounds=max_rounds,
                    candidate_plan=candidate_plan,
                    candidate_trajectory_decision=trajectory_decision,
                )
            )
            self._record_mediator_output(
                research_state,
                revised,
                source="adversary_revision",
                phase_number=None,
                trace_ref=f"mediator_adversary_revision_round{round_number}.json",
            )
            revised, callback_history = self._complete_mediator_callbacks(
                research_state=research_state,
                mediator=mediator,
                mediator_output=revised,
                callback_history=callback_history,
            )
            resolution = _resolve_candidate_revision(
                previous_plan=candidate_plan,
                previous_trajectory=trajectory_decision,
                revised_output=revised,
                adversary_verdict=verdict,
                force_terminal=round_number >= max_rounds,
            )
            if resolution["status"] in {"accepted", "unanswerable"}:
                return _candidate_resolution_to_formulation_result(
                    resolution=resolution,
                    mediator_output=revised,
                    adversary_result=adversary_result,
                    panelist_outputs=panelist_outputs,
                    callback_history=callback_history,
                )
            candidate_plan = resolution["selected_research_plan"]
            trajectory_decision = resolution["trajectory_decision"]
            mediator_output = revised
        raise RuntimeError(f"Adversary loop exhausted without terminal resolution: {last_adversary_result}")

    def _review_post_analysis_candidate_if_needed(
        self,
        *,
        research_state: ResearchState,
        phase_number: int,
        post_decision: dict[str, Any],
        analyzer_report: dict[str, Any],
        dag_result: dict[str, Any],
        tool_decision: dict[str, Any],
    ) -> dict[str, Any]:
        if _canonical_post_decision(post_decision) != "self_revise_plan":
            return post_decision
        candidate_plan = post_decision.get("updated_selected_research_plan")
        trajectory_decision = post_decision.get("trajectory_decision")
        if not isinstance(candidate_plan, dict) or not isinstance(trajectory_decision, dict):
            return post_decision
        mediator = self._ensure_mediator_agent()
        adversary = self._ensure_adversarial_panelist()
        max_rounds = int(getattr(adversary, "max_rounds", 2) or 2)
        for round_number in range(1, max_rounds + 1):
            adversary_result = adversary.run(
                adversary_context=research_state.context_for_adversary(
                    candidate_plan=candidate_plan,
                    candidate_trajectory_decision=trajectory_decision,
                )
            )
            research_state.record_adversary_output(adversary_result)
            self._save(f"phase{phase_number}_post_analysis_adversary_round{round_number}", adversary_result)
            verdict = str(adversary_result.get("adversary_verdict") or adversary_result.get("verdict") or "").strip()
            if verdict in {"survives", "skipped"}:
                return _candidate_resolution_to_post_decision(
                    post_decision=post_decision,
                    resolution={
                        "status": "accepted",
                        "selected_research_plan": candidate_plan,
                        "trajectory_decision": trajectory_decision,
                        "reason": "adversary_survives" if verdict == "survives" else "adversary_skipped",
                        "adversarial_review_status": verdict,
                        "adversarial_review_interpretation": "reviewed_no_blocking_flaw"
                        if verdict == "survives"
                        else "not_reviewed",
                    },
                    adversary_result=adversary_result,
                    revised_output={},
                )
            if verdict == "unsalvageable":
                post_decision = mediator.post_analysis(
                    post_analysis_context=research_state.context_for_mediator_post_analysis(
                        phase_number=phase_number,
                        analyzer_report=analyzer_report,
                        dag_result_summary=_summarize_execution_for_mediator(dag_result),
                        tool_decision=tool_decision,
                        artifact_registry_summary=None,
                        adversary_critique=adversary_result,
                    )
                )
                self._save(f"phase{phase_number}_post_analysis_unsalvageable_revision_round{round_number}", post_decision)
                self._record_mediator_output(
                    research_state,
                    post_decision,
                    source="post_analysis_after_unsalvageable",
                    phase_number=phase_number,
                    trace_ref=f"phase{phase_number}_post_analysis_unsalvageable_revision_round{round_number}.json",
                )
                if _canonical_post_decision(post_decision) != "self_revise_plan":
                    return post_decision
                next_candidate = post_decision.get("updated_selected_research_plan")
                next_trajectory = post_decision.get("trajectory_decision")
                if not isinstance(next_candidate, dict) or not isinstance(next_trajectory, dict):
                    return post_decision
                candidate_plan = next_candidate
                trajectory_decision = next_trajectory
                continue
            revised = mediator.revise_from_adversary(
                adversary_revision_context=research_state.context_for_mediator_adversary_revision(
                    adversary_critique=adversary_result,
                    adversary_revision_round=round_number,
                    max_adversary_revision_rounds=max_rounds,
                    candidate_plan=candidate_plan,
                    candidate_trajectory_decision=trajectory_decision,
                )
            )
            self._record_mediator_output(
                research_state,
                revised,
                source="post_analysis_adversary_revision",
                phase_number=phase_number,
                trace_ref=f"mediator_adversary_revision_round{round_number}.json",
            )
            revised, _ = self._complete_mediator_callbacks(
                research_state=research_state,
                mediator=mediator,
                mediator_output=revised,
                callback_history=research_state.current_callback_history(),
            )
            resolution = _resolve_candidate_revision(
                previous_plan=candidate_plan,
                previous_trajectory=trajectory_decision,
                revised_output=revised,
                adversary_verdict=verdict,
                force_terminal=round_number >= max_rounds,
            )
            if resolution["status"] == "unanswerable":
                return _candidate_resolution_to_post_decision(
                    post_decision=post_decision,
                    resolution=resolution,
                    adversary_result=adversary_result,
                    revised_output=revised,
                )
            candidate_plan = resolution["selected_research_plan"]
            trajectory_decision = resolution["trajectory_decision"]
            if round_number >= max_rounds:
                return _candidate_resolution_to_post_decision(
                    post_decision=post_decision,
                    resolution=resolution,
                    adversary_result=adversary_result,
                    revised_output=revised,
                )
        return _post_analysis_budget_exhausted_decision(post_decision=post_decision, adversary_result=adversary_result)

    def _complete_mediator_callbacks(
        self,
        *,
        research_state: ResearchState,
        mediator: MediatorAgent,
        mediator_output: dict[str, Any],
        callback_history: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        callback_round_limit = max(0, int(getattr(self.scientist_panel, "max_mediator_callback_rounds", 3)))
        for round_number in range(1, callback_round_limit + 1):
            if mediator_output.get("formulation_status") != "needs_panelist_callback":
                break
            callbacks = _limited_callback_requests(
                mediator_output.get("callback_requests", []),
                max_callbacks=int(getattr(self.scientist_panel, "max_callbacks_per_round", 3)),
            )
            if not callbacks:
                break
            callback_outputs = []
            for callback in callbacks:
                role = str(callback.get("role") or "").strip().lower()
                if not role:
                    continue
                output = self.scientist_panel.run_panelist_callback(
                    role,
                    {
                        "callback": callback,
                        "context": {
                            "mediator_output": mediator_output,
                            "research_state": research_state.context_for_mediator_formulation(),
                            "assigned_gap": callback.get("assigned_gap", ""),
                        },
                        "round_number": round_number,
                    },
                )
                callback_outputs.append({"callback": callback, "output": output})
            callback_history.extend(callback_outputs)
            mediator_output = mediator.synthesize_callbacks(
                formulation_context=research_state.context_for_mediator_formulation(),
                callback_outputs=callback_outputs,
                round_number=round_number,
            )
            self._record_mediator_output(
                research_state,
                mediator_output,
                source="callback_synthesis",
                trace_ref=f"mediator_callback_synthesis_round{round_number}.json",
            )
            research_state.record_callback_history(callback_history)
        return mediator_output, callback_history

    def _record_mediator_output(
        self,
        research_state: ResearchState,
        output: dict[str, Any],
        *,
        source: str,
        phase_number: int | None = None,
        trace_ref: str | None = None,
    ) -> None:
        research_state.record_mediator_output(
            {
                "source": source,
                "phase_number": phase_number,
                "trace_ref": trace_ref,
                "output": output,
            }
        )

    def _record_tool_decision(
        self,
        research_state: ResearchState,
        decision: dict[str, Any],
        *,
        source: str,
        phase_number: int,
        trace_ref: str | None = None,
    ) -> None:
        research_state.record_tool_decision(
            {
                "source": source,
                "phase_number": phase_number,
                "trace_ref": trace_ref,
                "decision": decision,
            }
        )

    def _record_analyzer_report(
        self,
        research_state: ResearchState,
        report: dict[str, Any],
        *,
        source: str,
        phase_number: int,
        trace_ref: str | None = None,
    ) -> None:
        research_state.record_analyzer_report(
            {
                "source": source,
                "phase_number": phase_number,
                "trace_ref": trace_ref,
                "report": report,
            }
        )

    def _run_legacy_post_analysis_callback_loop(
        self,
        *,
        user_question: str,
        phase_number: int,
        analyzer_report: dict[str, Any],
        working_model: dict[str, Any] | str,
        research_context: dict[str, Any],
        decision: dict[str, Any],
        dag_result: dict[str, Any],
        post_decision: dict[str, Any],
    ) -> dict[str, Any]:
        if not hasattr(self.scientist_panel, "run_post_analysis_callbacks"):
            return post_decision
        max_rounds = max(0, int(getattr(self.scientist_panel, "max_callback_rounds_after_analysis", 2)))
        current_decision = post_decision
        current_working_model: dict[str, Any] | str = working_model
        for _round_number in range(1, max_rounds + 1):
            if _canonical_post_decision(current_decision) != "call_panelists":
                break
            callback_result = self.scientist_panel.run_post_analysis_callbacks(
                user_question=user_question,
                data_summary=self.data_summary,
                phase_number=phase_number,
                post_analysis_decision=current_decision,
                working_model=current_working_model,
                research_context=research_context,
                analyzer_report=analyzer_report,
            )
            current_working_model = callback_result if isinstance(callback_result, dict) else current_working_model
            current_decision = self._decide_after_analysis(
                user_question=user_question,
                phase_number=phase_number,
                analyzer_report=analyzer_report,
                working_model=current_working_model,
                research_context=research_context,
                decision=decision,
                dag_result=dag_result,
            )
        return current_decision

    def _execute(
        self,
        *,
        decision: dict[str, Any],
        current_input_h5ad: str,
        phase_number: int,
    ) -> tuple[dict[str, Any], list[str], str]:
        """Run dag_plan or implementation_plan. Returns (dag_result, figure_paths, status)."""

        dag_plan = decision.get("dag_plan")
        impl_plan = decision.get("implementation_plan")

        if decision.get("execution_blocked"):
            return {
                "status": "blocked",
                "error": "Execution blocked by adversarial alignment review.",
                "adversarial_alignment_review": decision.get("adversarial_alignment_review", {}),
            }, [], "blocked"

        if dag_plan:
            if self.dag_executor is None:
                return {"status": "failed", "error": "dag_executor not configured"}, [], "failed"
            # Inject the current input h5ad if not already set
            dag_plan = dict(dag_plan)
            dag_plan.setdefault("input_h5ad_path", current_input_h5ad)
            if decision.get("output_retention_policy"):
                dag_plan["output_retention_policy"] = decision.get("output_retention_policy")
            try:
                dag_result = self.dag_executor.execute(
                    dag_plan=dag_plan,
                    session_tag=f"phase{phase_number}_dag",
                )
                dag_result["output_retention_policy"] = decision.get("output_retention_policy", [])
                dag_result["adversarial_alignment_review"] = decision.get("adversarial_alignment_review", {})
                figure_paths = _extract_figures(dag_result)
                status = dag_result.get("status", "completed")
                return dag_result, figure_paths, status
            except Exception as exc:
                result = {"status": "failed", "error": str(exc)}
                return result, [], "failed"

        if impl_plan:
            active_coder = self.coder
            if active_coder is None:
                return {"status": "failed", "error": "no coder configured"}, [], "failed"
            try:
                coder_result = active_coder.run(
                    implementation_plan=impl_plan,
                    session_state={"input_h5ad_path": current_input_h5ad},
                    session_tag=f"phase{phase_number}_coder",
                )
                coder_result["output_retention_policy"] = decision.get("output_retention_policy", [])
                coder_result["adversarial_alignment_review"] = decision.get("adversarial_alignment_review", {})
                figure_paths = _extract_figures(coder_result)
                status = coder_result.get("status", "completed")
                return coder_result, figure_paths, status
            except Exception as exc:
                result = {"status": "failed", "error": str(exc)}
                return result, [], "failed"

        return {"status": "failed", "error": "ToolConsultant produced neither dag_plan nor implementation_plan"}, [], "failed"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_session_state(
        self,
        *,
        current_input_h5ad: str,
        previous_dag_plan: dict[str, Any] | None,
        research_context: dict[str, Any] | None = None,
        post_analysis_decision: dict[str, Any] | None = None,
        state_graph_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state: dict[str, Any] = {
            "input_h5ad_path": current_input_h5ad,
            "data_summary": self.data_summary,
            "previous_plan_type": "none",
            "previous_plan": "<none>",
        }
        if previous_dag_plan:
            state["previous_plan_type"] = "composable"
            state["previous_plan"] = json.dumps(
                {"dag_plan": previous_dag_plan}, indent=2, ensure_ascii=False
            )
        if research_context:
            state["selected_research_plan"] = research_context.get("selected_research_plan", {})
            state["deferred_novel_analysis_design"] = {
                "excluded_from_current_tool_plan": True,
                "reason": "novel_analysis_design is deferred until the selected plan concludes and becomes a child node.",
            }
            state["alternative_research_plans"] = research_context.get("alternative_research_plans", [])
            state["evidence_state"] = research_context.get("evidence_state", {})
            state["analysis_requirements"] = research_context.get("analysis_requirements", [])
            state["validation_requirements"] = research_context.get("validation_requirements", [])
            state["success_criteria"] = research_context.get("success_criteria", {})
            state["research_plan_context"] = research_context
        if post_analysis_decision:
            state["last_post_analysis_decision"] = post_analysis_decision
        if state_graph_context:
            state["state_graph_context"] = state_graph_context
        if self.short_term_memory is not None:
            state["phase_trace"] = self.short_term_memory.format_for_scientists()
        if self.context_manager is not None:
            state["scientific_context"] = self.context_manager.to_prompt_str()
        return state

    def _decide_after_analysis(
        self,
        *,
        user_question: str,
        phase_number: int,
        analyzer_report: dict[str, Any],
        working_model: dict[str, Any] | str,
        research_context: dict[str, Any],
        decision: dict[str, Any],
        dag_result: dict[str, Any],
    ) -> dict[str, Any]:
        if hasattr(self.scientist_panel, "decide_after_analysis"):
            graph_context = {}
            if getattr(self, "state_graph_manager", None) is not None:
                graph_context = self.state_graph_manager.context_for_mediator()
            return self.scientist_panel.decide_after_analysis(
                user_question=user_question,
                data_summary=self.data_summary,
                phase_number=phase_number,
                analyzer_report=analyzer_report,
                working_model=working_model,
                research_context=research_context,
                tool_decision=decision,
                dag_result=dag_result,
                state_graph_context=graph_context,
                artifact_registry_summary=None,
            )
        return {
            "decision": "accept_and_conclude",
            "decision_type": "accept_and_conclude",
            "rationale": "ScientistPanel does not expose decide_after_analysis; conservatively concluding with the Analyzer report instead of running an implicit full update.",
            "evidence_state": {},
            "updated_selected_research_plan": {},
            "panelist_callback_requests": [],
            "callbacks": [],
            "clarifying_questions": [],
            "confidence": 0.0,
        }

    def _ensure_session_recorder(self, *, user_question: str) -> SessionRecorder:
        recorder = getattr(self, "session_recorder", None)
        if recorder is None:
            recorder = SessionRecorder(root_dir=self.result_dir / "runs")
            self.session_recorder = recorder
        return recorder

    def _ensure_state_graph(self, recorder: SessionRecorder) -> StateGraphManager:
        manager = getattr(self, "state_graph_manager", None)
        if manager is None:
            manager = StateGraphManager(session_dir=recorder.session_dir)
            self.state_graph_manager = manager
        return manager

    def _ensure_mediator_agent(self) -> MediatorAgent:
        mediator = getattr(self, "mediator_agent", None)
        if mediator is not None:
            return mediator
        client = getattr(self.scientist_panel, "client", None)
        engine_name = getattr(self.scientist_panel, "engine_name", None) or "gpt-4o"
        # ScientistPanel already resolves fast_engine_name (falling back to its own
        # engine_name), so reuse that instead of introducing a second source of truth.
        fast_engine_name = getattr(self.scientist_panel, "fast_engine_name", None) or engine_name
        registry = build_paper_detail_tool_registry(retriever=self.scientist_panel.retriever)
        mediator = MediatorAgent(
            engine_name=engine_name,
            fast_engine_name=fast_engine_name,
            client=client,
            result_dir=self.result_dir / "mediator",
            panelist_callback_executor=getattr(self.scientist_panel, "run_panelist_callback", None),
            paper_tool_specs=registry.tool_specs(),
            paper_tool_executor=registry.executor(),
            max_schema_repair_attempts=2,
        )
        self.mediator_agent = mediator
        return mediator

    def _ensure_adversarial_panelist(self) -> Any:
        adversary = getattr(self, "adversarial_panelist", None)
        if adversary is None:
            raise RuntimeError("AdversarialPanelist must be passed to ResearchLoop at construction.")
        return adversary

    def _review_and_maybe_revise_decision(
        self,
        *,
        user_question: str,
        research_context: dict[str, Any],
        decision: dict[str, Any],
        session_state: dict[str, Any],
        user_message: str,
        phase_number: int,
    ) -> dict[str, Any]:
        if decision.get("blocking_questions"):
            decision["execution_blocked"] = True
            decision["tool_plan_alignment_review"] = {
                "verdict": "blocked",
                "target": "inputs_dependencies",
                "blocker_type": "user_input_missing",
                "core_critique": "ToolConsultant returned blocking questions before executable planning.",
                "required_revision": decision.get("blocking_questions"),
            }
            return decision
        reviewer = self.alignment_reviewer or getattr(getattr(self.scientist_panel, "adversarial_panelist", None), "review_alignment", None)
        if reviewer is None:
            decision.setdefault("tool_plan_alignment_review", _default_alignment_review("No alignment reviewer configured."))
            decision.setdefault("adversarial_alignment_review", decision["tool_plan_alignment_review"])
            return decision

        review = _run_alignment_review(
            reviewer=reviewer,
            user_question=user_question,
            research_context=research_context,
            decision=decision,
        )
        decision["tool_plan_alignment_review"] = review
        decision["adversarial_alignment_review"] = review
        self._save(f"phase{phase_number}_alignment_review", review)
        if review.get("verdict") == "survives":
            return decision

        if _alignment_targets_tool_revision(review):
            revision_state = dict(session_state)
            revision_state["tool_plan_alignment_review"] = review
            revision_state["adversarial_alignment_review"] = review
            revision_state["previous_tool_decision"] = decision
            revised = self.tool_consultant.decide(
                user_message=(
                    user_message
                    + "\n\nAdversarial alignment critique to address before execution:\n"
                    + json.dumps(review, indent=2, ensure_ascii=False)
                ),
                session_state=revision_state,
                session_tag=f"phase{phase_number}_tool_consultant_alignment_revision",
            )
            self._save(f"phase{phase_number}_decision_alignment_revision", revised)
            second_review = _run_alignment_review(
                reviewer=reviewer,
                user_question=user_question,
                research_context=research_context,
                decision=revised,
            )
            revised["tool_plan_alignment_review"] = second_review
            revised["adversarial_alignment_review"] = second_review
            revised["previous_adversarial_alignment_review"] = review
            self._save(f"phase{phase_number}_alignment_review_after_revision", second_review)
            if second_review.get("verdict") in {"needs_tool_revision", "blocked"}:
                revised["execution_blocked"] = True
                revised["alignment_unresolved_after_revision"] = True
            return revised

        decision["alignment_blocker_requires_mediator"] = review.get("blocker_type") in {"required_data_missing", "ambiguous_plan_requirement"}
        if review.get("verdict") == "blocked":
            decision["execution_blocked"] = True
        return decision

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

def _format_research_plan(
    research_plan: dict[str, Any] | str,
    user_question: str,
    *,
    research_context: dict[str, Any] | None = None,
) -> str:
    """Format research_plan as a user_message for ToolConsultantAgent.decide().

    Steps can be plain strings (legacy) or structured dicts with fields:
      step_id, biological_goal, statistical_requirement, computational_approach,
      novelty_statement (from the complementary panelist schema).
    Both forms are rendered into readable prose for the ToolConsultant.
    """
    if isinstance(research_plan, str):
        return research_plan.strip()

    steps = research_plan.get("steps") or []
    viz = research_plan.get("required_visualizations") or []
    caveat = str(research_plan.get("caveat") or "").strip()

    lines = [f"Research question: {user_question}", "", "Execute the selected active research plan:"]
    if research_context:
        claim = str(research_context.get("concrete_analysis_claim") or "").strip()
        if claim:
            lines.append(f"\nConcrete analysis claim: {claim}")
        requirements = research_context.get("analysis_requirements") or []
        if requirements:
            lines.append("\nAnalysis requirements:")
            for item in requirements:
                lines.append(f"- {item}")
        validation = research_context.get("validation_requirements") or []
        if validation:
            lines.append("\nValidation requirements:")
            for item in validation:
                lines.append(f"- {item}")
        success = research_context.get("success_criteria") or {}
        if isinstance(success, dict) and success:
            lines.append("\nSuccess criteria:")
            for key, value in success.items():
                lines.append(f"- {key}: {value}")
    for i, step in enumerate(steps, 1):
        if isinstance(step, dict):
            # Structured step from complementary panelist schema
            step_id = str(step.get("step_id") or f"step_{i}")
            bio = str(step.get("biological_goal") or "").strip()
            stat = str(step.get("statistical_requirement") or "").strip()
            comp = str(step.get("computational_approach") or "").strip()
            novel = str(step.get("novelty_statement") or "").strip()
            lines.append(f"{i}. [{step_id}]")
            if bio:
                lines.append(f"   Biological goal: {bio}")
            if stat:
                lines.append(f"   Statistical requirement: {stat}")
            if comp:
                lines.append(f"   Computational approach: {comp}")
            if novel:
                lines.append(f"   Novelty: {novel}")
        else:
            # Legacy plain string step
            lines.append(f"{i}. {step}")

    if viz:
        lines.append("\nRequired visualizations (must be produced as output files):")
        for v in viz:
            if isinstance(v, dict):
                fig = str(v.get("figure") or "")
                reveals = str(v.get("reveals") or "")
                criterion = str(v.get("decision_criterion") or "")
                lines.append(f"- {fig}")
                if reveals:
                    lines.append(f"  Reveals: {reveals}")
                if criterion:
                    lines.append(f"  Decision criterion: {criterion}")
            else:
                lines.append(f"- {v}")

    if caveat:
        lines.append(f"\nCaveat: {caveat}")

    return "\n".join(lines)


def _plan_to_markdown(plan: dict[str, Any], user_question: str) -> str:
    lines = [f"# Research Plan", "", f"Question: {user_question}", ""]
    summary = str(plan.get("summary") or "").strip()
    if summary:
        lines.extend(["## Summary", "", summary, ""])
    steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    if steps:
        lines.extend(["## Steps", ""])
        for index, step in enumerate(steps, 1):
            if isinstance(step, dict):
                label = step.get("step_id") or f"step_{index}"
                lines.append(f"{index}. {label}")
                for key in ("biological_goal", "statistical_requirement", "computational_approach", "novelty_statement"):
                    if step.get(key):
                        lines.append(f"   - {key}: {step[key]}")
            else:
                lines.append(f"{index}. {step}")
    visualizations = plan.get("required_visualizations") if isinstance(plan.get("required_visualizations"), list) else []
    if visualizations:
        lines.extend(["", "## Required Visualizations", ""])
        for item in visualizations:
            lines.append(f"- {item}")
    caveat = str(plan.get("caveat") or "").strip()
    if caveat:
        lines.extend(["", "## Caveat", "", caveat])
    return "\n".join(lines).strip() + "\n"


def _to_markdown_block(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return "```json\n" + json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n```\n"


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
    outputs = value.get("outputs")
    if isinstance(outputs, dict):
        summary["outputs"] = outputs
    return summary or {"raw": json.dumps(value, ensure_ascii=False, default=str)[:3000]}


def _analyzer_report_to_markdown(report: dict[str, Any]) -> str:
    lines = ["# Analyzer Report", ""]
    summary = str(report.get("results_summary") or report.get("summary") or "").strip()
    if summary:
        lines.extend(["## Summary", "", summary, ""])
    verdict = str(report.get("result_verdict") or "").strip()
    if verdict:
        lines.extend(["## Verdict", "", verdict, ""])
    requirements = report.get("evidence_requirement_status")
    if isinstance(requirements, list) and requirements:
        lines.extend(["## Evidence Requirements", ""])
        for item in requirements:
            if isinstance(item, dict):
                lines.append(f"- {item.get('requirement', '')}: {item.get('status', '')}")
                if item.get("evidence"):
                    lines.append(f"  Evidence: {item['evidence']}")
                if item.get("needed_next"):
                    lines.append(f"  Needed next: {item['needed_next']}")
    if not summary and not verdict:
        lines.append(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return "\n".join(lines).strip() + "\n"


def _extract_research_context(brief: dict[str, Any], user_question: str) -> dict[str, Any]:
    if not isinstance(brief, dict):
        return {
            "user_question": user_question,
            "selected_research_plan": {"steps": []},
            "alternative_research_plans": [],
            "analysis_requirements": [],
            "validation_requirements": [],
            "success_criteria": {},
        }
    selected = brief.get("selected_research_plan")
    if not isinstance(selected, dict):
        selected = brief.get("research_plan") if isinstance(brief.get("research_plan"), dict) else {"steps": []}
    return {
        "user_question": user_question,
        "concrete_analysis_claim": brief.get("concrete_analysis_claim") or brief.get("consensus_hypothesis") or "",
        "best_effort_claim": brief.get("best_effort_claim", ""),
        "clarification_needed": bool(brief.get("clarification_needed", False)),
        "literature_verdict": brief.get("literature_verdict", ""),
        "research_case": brief.get("research_case", ""),
        "existing_solution_path": brief.get("existing_solution_path", {}),
        "existing_solution_plan": brief.get("existing_solution_plan", {}),
        "extension_or_de_novo_plan": brief.get("extension_or_de_novo_plan", {}),
        "baseline_requirement": brief.get("baseline_requirement", ""),
        "selected_research_plan": selected,
        "novel_analysis_design": brief.get("novel_analysis_design", {}),
        "future_research_directions": brief.get("future_research_directions", []),
        "evidence_state": brief.get("evidence_state", {}),
        "alternative_research_plans": brief.get("alternative_research_plans", []),
        "analysis_requirements": brief.get("analysis_requirements", []),
        "validation_requirements": brief.get("validation_requirements", []),
        "success_criteria": brief.get("success_criteria", {}),
        "open_risks": brief.get("open_risks", []),
    }


def _next_action_from_post_analysis_decision(decision: dict[str, Any]) -> str:
    decision_type = _canonical_post_decision(decision)
    if decision_type == "accept_and_conclude":
        return "done"
    if decision_type == "declare_unanswerable":
        return "abstain"
    if decision_type == "ask_user":
        return "awaiting_user"
    return "continue"


def _agent_user_question(*, resolved_intent: str, original_user_message: str | None = None) -> str:
    original = str(original_user_message or "").strip()
    resolved = str(resolved_intent or "").strip()
    if original and resolved and original != resolved:
        return f"Original user message:\n{original}\n\nResolved intent:\n{resolved}"
    return resolved or original


def _canonical_post_decision(decision: dict[str, Any]) -> str:
    text = str(decision.get("decision") or decision.get("decision_type") or "").strip()
    return {
        "conclude": "accept_and_conclude",
        "interpretation_only": "accept_and_conclude",
        "ask_user_clarification": "ask_user",
        "revise_plan": "self_revise_plan",
        "produce_next_research_plan": "self_revise_plan",
    }.get(text, text)


def _resolve_candidate_revision(
    *,
    previous_plan: dict[str, Any],
    previous_trajectory: dict[str, Any],
    revised_output: dict[str, Any],
    adversary_verdict: str,
    force_terminal: bool,
) -> dict[str, Any]:
    revised_plan = revised_output.get("selected_research_plan")
    if not isinstance(revised_plan, dict):
        revised_plan = previous_plan
    revised_trajectory = revised_output.get("trajectory_decision")
    if not isinstance(revised_trajectory, dict):
        revised_trajectory = previous_trajectory

    action = str(revised_trajectory.get("action") or "").strip()
    if action == "declare_unanswerable":
        return {
            "status": "unanswerable",
            "selected_research_plan": revised_plan,
            "trajectory_decision": revised_trajectory,
            "reason": revised_trajectory.get("reason") or "Mediator declared this candidate unanswerable.",
        }

    if adversary_verdict == "unsalvageable" and not _materially_different_research_plan(previous_plan, revised_plan):
        return {
            "status": "unanswerable" if force_terminal else "needs_revision",
            "selected_research_plan": revised_plan if force_terminal else previous_plan,
            "trajectory_decision": (
                {
                    "action": "declare_unanswerable",
                    "branch_from_node_id": revised_trajectory.get("branch_from_node_id"),
                    "reason": "Adversary marked the candidate unsalvageable and Mediator did not produce a materially different plan.",
                }
                if force_terminal
                else previous_trajectory
            ),
            "reason": "unsalvageable_without_material_revision",
        }

    return {
        "status": "accepted" if force_terminal else "needs_revision",
        "selected_research_plan": revised_plan,
        "trajectory_decision": revised_trajectory,
        "reason": "candidate_revision_validated",
    }


def _materially_different_research_plan(previous_plan: dict[str, Any], revised_plan: dict[str, Any]) -> bool:
    fields = ("summary", "steps", "evidence_requirements", "required_visualizations", "success_criteria")
    previous_projection = {field: previous_plan.get(field) for field in fields}
    revised_projection = {field: revised_plan.get(field) for field in fields}
    return json.dumps(previous_projection, sort_keys=True, default=str) != json.dumps(revised_projection, sort_keys=True, default=str)


def _candidate_resolution_to_formulation_result(
    *,
    resolution: dict[str, Any],
    mediator_output: dict[str, Any],
    adversary_result: dict[str, Any],
    panelist_outputs: dict[str, Any],
    callback_history: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": resolution["status"],
        "selected_research_plan": resolution["selected_research_plan"],
        "trajectory_decision": resolution["trajectory_decision"],
        "mediator_output": mediator_output,
        "adversary_result": adversary_result,
        "panelist_outputs": panelist_outputs,
        "callback_history": callback_history,
        "research_gap_resolution": mediator_output.get("research_gap_resolution", []),
        "limitations": mediator_output.get("limitations", []),
        "evidence_state": mediator_output.get("evidence_state", {}),
        "alternative_research_plans": mediator_output.get("alternative_research_plans", []),
        "resolution_reason": resolution.get("reason", ""),
        "adversarial_review_status": resolution.get("adversarial_review_status", ""),
        "adversarial_review_interpretation": resolution.get("adversarial_review_interpretation", ""),
    }


def _candidate_resolution_to_post_decision(
    *,
    post_decision: dict[str, Any],
    resolution: dict[str, Any],
    adversary_result: dict[str, Any],
    revised_output: dict[str, Any],
) -> dict[str, Any]:
    out = dict(post_decision)
    if resolution["status"] == "unanswerable":
        out["decision"] = "declare_unanswerable"
        out["decision_type"] = "declare_unanswerable"
        out["trajectory_decision"] = resolution["trajectory_decision"]
        out["unanswerable_reason"] = resolution.get("reason", "")
    else:
        out["updated_selected_research_plan"] = resolution["selected_research_plan"]
        out["trajectory_decision"] = resolution["trajectory_decision"]
    out["adversary_result"] = adversary_result
    if isinstance(revised_output.get("evidence_state"), dict) and revised_output.get("evidence_state"):
        out["evidence_state"] = revised_output["evidence_state"]
    out["research_gap_resolution"] = revised_output.get("research_gap_resolution", out.get("research_gap_resolution", []))
    out["resolution_reason"] = resolution.get("reason", "")
    out["adversarial_review_status"] = resolution.get("adversarial_review_status", "")
    out["adversarial_review_interpretation"] = resolution.get("adversarial_review_interpretation", "")
    return out


def _post_analysis_budget_exhausted_decision(
    *,
    post_decision: dict[str, Any],
    adversary_result: dict[str, Any],
) -> dict[str, Any]:
    out = dict(post_decision)
    out["decision"] = "declare_unanswerable"
    out["decision_type"] = "declare_unanswerable"
    out["adversary_result"] = adversary_result
    out["resolution_reason"] = "adversary_budget_exhausted_without_defensible_revision"
    out["adversarial_review_status"] = str(
        adversary_result.get("adversary_verdict") or adversary_result.get("verdict") or ""
    ).strip()
    out["adversarial_review_interpretation"] = "reviewed_blocking_flaw"
    out["unanswerable_reason"] = (
        "Post-analysis plan revision budget was exhausted without producing a candidate that survived adversarial review."
    )
    out["trajectory_decision"] = {
        "action": "declare_unanswerable",
        "branch_from_node_id": (post_decision.get("trajectory_decision") or {}).get("branch_from_node_id")
        if isinstance(post_decision.get("trajectory_decision"), dict)
        else None,
        "reason": out["unanswerable_reason"],
    }
    return out


def _blocked_execution_report(
    *,
    dag_result: dict[str, Any],
    decision: dict[str, Any],
    research_plan: dict[str, Any],
) -> dict[str, Any]:
    """Create an Analyzer-shaped report for pre-execution alignment blocks.

    This is intentionally not an AnalyzerPanel interpretation. It is a control
    signal for the Mediator: execution did not happen, so the next action must
    revise the tool/implementation plan, revise the research plan, ask for
    clarification, or declare the task currently unanswerable.
    """
    review = dag_result.get("adversarial_alignment_review") or decision.get("adversarial_alignment_review") or {}
    required_revision = review.get("required_revision") or dag_result.get("error") or "Execution was blocked before computational analysis."
    target = review.get("target") or "execution_plan"
    failure_mode = review.get("failure_mode") or "blocked_execution"
    return {
        "results_summary": "Execution was blocked before any computational step ran.",
        "claim_updates": [
            {
                "claim_id": "C1",
                "status": "inconclusive",
                "support_summary": "No QC, preprocessing, embedding, validation, clustering, or figures were produced.",
                "contradicting_evidence": [],
                "unresolved_requirements": [required_revision],
            }
        ],
        "evidence_requirement_status": [
            {
                "requirement": f"Resolve adversarial alignment critique targeting {target}.",
                "status": "missing",
                "evidence": required_revision,
                "needed_next": required_revision,
            }
        ],
        "result_verdict": "blocked",
        "problem_localization": {
            "problem_stage": target,
            "problem_type": failure_mode,
        },
        "missing_outputs": [
            "No computational outputs were produced because execution was blocked before step_0.",
        ],
        "adversarial_alignment_review": review,
        "control_flow_note": (
            "This blocked report should be handled by the Mediator. "
            "Do not run literature grounding or interpret missing figures as scientific results."
        ),
    }


def _limited_callback_requests(value: Any, *, max_callbacks: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        if role not in _ROLES:
            continue
        out.append(item)
        if len(out) >= max_callbacks:
            break
    return out


def _run_alignment_review(
    *,
    reviewer: Any,
    user_question: str,
    research_context: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    if hasattr(reviewer, "review_alignment"):
        raw = reviewer.review_alignment(
            user_question=user_question,
            research_plan=research_context,
            tool_plan=decision.get("dag_plan"),
            implementation_plan=decision.get("implementation_plan"),
        )
    else:
        raw = reviewer(
            user_question=user_question,
            research_plan=research_context,
            tool_plan=decision.get("dag_plan"),
            implementation_plan=decision.get("implementation_plan"),
        )
    return _normalize_alignment_review(raw)


def _normalize_alignment_review(review: Any) -> dict[str, Any]:
    if not isinstance(review, dict):
        return _default_alignment_review(f"Invalid alignment review: {review}")
    out = dict(review)
    verdict = str(out.get("verdict") or "").strip()
    if verdict == "needs_revision":
        verdict = "needs_tool_revision"
    if verdict == "unsalvageable":
        verdict = "blocked"
    if verdict not in {"survives", "needs_tool_revision", "blocked"}:
        verdict = "needs_tool_revision"
    out["verdict"] = verdict
    failure_mode = str(out.get("failure_mode") or "").strip()
    if failure_mode not in {
        "none",
        "weak_evidence",
        "missing_analysis",
        "invalid_statistical_unit",
        "overclaim",
        "missing_control",
        "tool_mismatch",
        "alternative_explanation",
        "literature_mismatch",
        "retention_gap",
    }:
        failure_mode = "none" if verdict == "survives" else "tool_mismatch"
    out["failure_mode"] = failure_mode
    target = str(out.get("target") or "").strip()
    if target == "research_plan":
        target = "inputs_dependencies"
    if target not in {"tool_plan", "implementation_plan", "inputs_dependencies"}:
        target = "tool_plan"
    out["target"] = target
    blocker_type = str(out.get("blocker_type") or "").strip()
    if blocker_type not in {"user_input_missing", "dependency_missing", "required_data_missing", "ambiguous_plan_requirement"}:
        blocker_type = "ambiguous_plan_requirement" if verdict == "blocked" and target == "inputs_dependencies" else ""
    out["blocker_type"] = blocker_type
    out.setdefault("core_critique", "")
    out.setdefault("weakest_assumption", "")
    out.setdefault("required_revision", "")
    out.setdefault("questions_for_panelists", [])
    out.setdefault("questions_for_toolconsultant", [])
    out.setdefault("reasoning_trace_summary", "")
    return out


def _default_alignment_review(reason: str) -> dict[str, Any]:
    return {
        "verdict": "survives",
        "core_critique": reason,
        "weakest_assumption": "",
        "failure_mode": "none",
        "target": "tool_plan",
        "required_revision": "",
        "questions_for_panelists": [],
        "questions_for_toolconsultant": [],
        "reasoning_trace_summary": reason,
    }


def _alignment_targets_tool_revision(review: dict[str, Any]) -> bool:
    if review.get("verdict") == "survives":
        return False
    if review.get("target") in {"tool_plan", "implementation_plan"}:
        return True
    return review.get("failure_mode") in {"tool_mismatch", "retention_gap"}


def _extract_figures(result: dict[str, Any]) -> list[str]:
    """Extract image file paths from a dag_result or coder_result dict."""
    figures: list[str] = []
    seen: set[str] = set()

    def _walk(obj: Any) -> None:
        if isinstance(obj, str):
            p = Path(obj)
            if p.suffix.lower() in _IMAGE_SUFFIXES and obj not in seen:
                seen.add(obj)
                figures.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)

    _walk(result)
    return figures


def _extract_metrics(analyzer_report: dict[str, Any]) -> dict[str, Any]:
    """Extract numeric metrics from an analyzer report for delta-based attribution.

    Looks for a top-level "metrics" dict, or common metric keys directly on the report.
    Returns an empty dict if no metrics are found.
    """
    if not isinstance(analyzer_report, dict):
        return {}
    if isinstance(analyzer_report.get("metrics"), dict):
        return {k: v for k, v in analyzer_report["metrics"].items() if isinstance(v, (int, float))}
    # Fall back to scanning top-level keys for known metric names
    known = {"ARI", "NMI", "bio_lisi", "batch_lisi", "silhouette", "marker_specificity",
             "n_clusters", "n_cells", "pct_mito", "doublet_rate"}
    return {k: v for k, v in analyzer_report.items() if k in known and isinstance(v, (int, float))}


def _extract_best_h5ad(dag_result: dict[str, Any]) -> str | None:
    """Return the output h5ad from the best DAG path, if available."""
    if not isinstance(dag_result, dict):
        return None
    best = dag_result.get("best_path")
    if not isinstance(best, dict):
        return None
    resolved = best.get("resolved_outputs") or {}
    if resolved.get("output_h5ad_path"):
        return str(resolved["output_h5ad_path"])
    # Fall back to scanning artifacts
    artifacts = best.get("artifacts") or {}
    for v in artifacts.values():
        if isinstance(v, str) and v.endswith(".h5ad") and Path(v).exists():
            return v
    return None
