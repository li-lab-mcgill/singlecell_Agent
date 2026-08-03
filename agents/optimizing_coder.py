"""OptimizingCoderAgent — CoderAgent-compatible wrapper over the TextGrad optimization loop.

Bridges the gap between ToolConsultantAgent.implementation_plan and the
CodeExecutor → StageScriptGenerator → TextGradEvaluator → TextGrad.backward() pipeline.

Interface matches CoderAgent.run() so it can be used as a drop-in in ResearchLoop._execute()
for implementation_plan tasks that require multi-step iterative optimization.

When textgrad is not installed, falls back to a generate-then-fix loop using
StageScriptGenerator + CodeExecutor directly (no gradient-based optimization).

Usage:
    opt_coder = OptimizingCoderAgent(
        engine_name="gpt-4o",
        config=pipeline_config,       # pipelines.config.Config
        result_dir="results/opt_coder",
        max_opt_steps=5,
        max_fix_steps=3,
        enable_textgrad=True,
    )

    result = opt_coder.run(
        implementation_plan=tool_consultant_decision["implementation_plan"],
        session_state={"input_h5ad_path": "/data/pbmc.h5ad"},
        session_tag="phase1_coder",
    )
    # result["status"], result["best_metrics"], result["best_script_dir"]
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict


class OptimizingCoderAgent:
    """CoderAgent-compatible wrapper that runs the TextGrad optimization loop.

    Drop-in replacement for CoderAgent when the task requires multi-stage script
    optimization (prior_construction → data_preprocess → model_training →
    downstream_analysis) backed by TextGrad gradient descent on LLM-generated code.

    Args:
        engine_name:     LLM engine for script generation and evaluation.
        config:          Pipeline Config object (pipelines.config.Config).
                         Provides paths, stage schemas, and prior configuration.
        result_dir:      Directory for per-step logs and artifacts.
        max_opt_steps:   Number of TextGrad optimization iterations (default: 5).
        max_fix_steps:   Fix-attempt retries per execution step (default: 3).
        client:          Optional OpenAI-compatible client.
        enable_textgrad: Use TextGrad backprop when available (default: True).
                         Falls back to simple generate-then-fix if False or if
                         textgrad is not installed.
    """

    def __init__(
        self,
        *,
        engine_name: str,
        config: Any,
        result_dir: str | Path,
        max_opt_steps: int = 5,
        max_fix_steps: int = 3,
        client: Any | None = None,
        enable_textgrad: bool = True,
    ):
        self.engine_name = engine_name
        self.config = config
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.max_opt_steps = max_opt_steps
        self.max_fix_steps = max_fix_steps
        self.client = client
        self.enable_textgrad = enable_textgrad

    # ------------------------------------------------------------------
    # Public API (CoderAgent-compatible)
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        implementation_plan: Dict[str, Any],
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "optimizing_coder",
    ) -> Dict[str, Any]:
        """Run the optimization loop over the implementation plan.

        Args:
            implementation_plan: ToolConsultantAgent implementation_plan dict.
                                 Used to extract the natural-language suggestion
                                 that drives StageScriptGenerator.
            session_state:       Session context (input paths, data summary, etc.).
            session_tag:         Tag for output file naming.

        Returns:
            {
              "status":          "completed" | "failed",
              "best_step":       <int>,
              "best_metrics":    <dict>,
              "best_script_dir": <str>,
              "phases":          [<per-step summary>],
              "error":           <str | None>,
            }
        """
        session_state = dict(session_state or {})
        suggestion = self._extract_suggestion(implementation_plan)
        task_description = (
            str(implementation_plan.get("task_description") or "").strip()
            or suggestion[:200]
        )

        try:
            if self.enable_textgrad and self._textgrad_available():
                return self._run_textgrad_loop(
                    suggestion=suggestion,
                    task_description=task_description,
                    session_tag=session_tag,
                )
            return self._run_simple_loop(
                suggestion=suggestion,
                task_description=task_description,
                session_tag=session_tag,
            )
        except Exception as exc:
            error_payload = {
                "status": "failed",
                "error": str(exc),
                "best_step": 0,
                "best_metrics": {},
                "best_script_dir": "",
                "phases": [],
            }
            _write_json(self.result_dir / f"{session_tag}_error.json", error_payload)
            return error_payload

    # ------------------------------------------------------------------
    # TextGrad optimization loop
    # ------------------------------------------------------------------

    def _run_textgrad_loop(
        self,
        *,
        suggestion: str,
        task_description: str,
        session_tag: str,
    ) -> Dict[str, Any]:
        """Full TextGrad optimization: generate → execute → evaluate → backprop → repeat."""
        import textgrad as tg
        from agents.generator import StageScriptGenerator
        from agents.evaluator import TextGradEvaluator, parse_critic_output
        from pipelines.executor import CodeExecutor
        from pipelines.multieval_types import GlobalBestState, STAGE_FILENAMES
        import shutil

        config = self.config
        global_engine = tg.get_engine(engine_name=self.engine_name)
        tg.set_backward_engine(global_engine, override=True)

        generator = StageScriptGenerator(config=config, engine_name=self.engine_name)
        executor = CodeExecutor(config)
        global_best = GlobalBestState()
        best_script_dir = str(self.result_dir / "best_scripts")
        phases: list[dict[str, Any]] = []

        critic_evaluator = TextGradEvaluator(
            config=config,
            engine_name=self.engine_name,
            task_decrp=task_description,
            background=suggestion,
            eval_type="critic",
        )

        code_bundle: Dict[str, Any] | None = None
        optimizers: Dict[str, Any] = {}

        for step in range(self.max_opt_steps + 1):
            resolved_layout = config.set_step_output_paths(step)
            step_start = time.perf_counter()
            script_dir = ""
            run_result: Dict[str, Any] = {}

            # Generate bundle on first step or after reconsult
            if code_bundle is None:
                code_bundle = generator.generate_bundle(
                    task_description=task_description,
                    background=suggestion,
                    main_plan=suggestion,
                    prior_plan="",
                    data_summary=getattr(config, "feat_stats", ""),
                    prior_resource_summary=getattr(config, "prior_resource_summary", ""),
                    script_summaries=StageScriptGenerator.summarize_bundle(None),
                    mcp_tools_text="",
                    api_dir=getattr(config, "api_dir", ""),
                    dataset_dir=getattr(config, "dataset_dir", ""),
                )
                active_stages = config.active_stage_filenames()
                optimizers = {
                    filename: tg.TextualGradientDescent(
                        engine=global_engine,
                        parameters=[code_bundle[filename]],
                    )
                    for filename in active_stages
                }

            # Execute with fix loop
            start_from = STAGE_FILENAMES[0]
            for attempt in range(self.max_fix_steps + 1):
                script_dir = generator.save_bundle(code_bundle, step_tag=f"step_{step}")
                run_result = executor.run_bundle(
                    script_dir,
                    resolved_artifact_layout=resolved_layout,
                    stage_schemas={},
                    start_from=start_from,
                )
                if run_result.get("success", False):
                    break
                if attempt < self.max_fix_steps:
                    target = str(
                        (run_result.get("validation_failure") or {}).get("target")
                        or run_result.get("failed_script")
                        or STAGE_FILENAMES[0]
                    )
                    error = str(run_result.get("error", "Unknown error"))
                    generator.fix_target(
                        code_bundle=code_bundle,
                        target=target,
                        error=error,
                        task_description=task_description,
                        main_plan=suggestion,
                        prior_plan="",
                        max_fix_step=1,
                    )
                    start_from = target

            run_success = bool(run_result.get("success", False))

            # TextGrad evaluation + backprop (skip on last step)
            if run_success and step < self.max_opt_steps and code_bundle is not None:
                try:
                    critic_out = critic_evaluator.loss_fn(
                        step=step,
                        suggestion=tg.Variable(
                            suggestion, requires_grad=False,
                            role_description="current consultant suggestion",
                        ),
                        raw_data_summary=tg.Variable(
                            getattr(config, "feat_stats", ""), requires_grad=False,
                            role_description="raw data summary",
                        ),
                        prior_resource_summary=tg.Variable(
                            getattr(config, "prior_resource_summary", ""), requires_grad=False,
                            role_description="prior resource summary",
                        ),
                        current_performance=tg.Variable(
                            "{}", requires_grad=False,
                            role_description="current performance",
                        ),
                        training_logs=tg.Variable(
                            "{}", requires_grad=False,
                            role_description="training logs",
                        ),
                        pipeline_summary=tg.Variable(
                            "{}", requires_grad=False,
                            role_description="pipeline summary",
                        ),
                        prior_construction_notes_history=tg.Variable(
                            "", requires_grad=False,
                            role_description="prior construction notes",
                        ),
                        data_preprocess_notes_history=tg.Variable(
                            "", requires_grad=False,
                            role_description="data preprocess notes",
                        ),
                        model_training_notes_history=tg.Variable(
                            "", requires_grad=False,
                            role_description="model training notes",
                        ),
                        downstream_analysis_notes_history=tg.Variable(
                            "", requires_grad=False,
                            role_description="downstream analysis notes",
                        ),
                        script_summaries=tg.Variable(
                            StageScriptGenerator.summarize_bundle(code_bundle),
                            requires_grad=False,
                            role_description="current script summaries",
                        ),
                        chat_history=tg.Variable(
                            "[]", requires_grad=False,
                            role_description="evaluator chat history",
                        ),
                    )
                    for opt in optimizers.values():
                        opt.zero_grad()
                    critic_out.backward()
                    for filename, opt in optimizers.items():
                        opt.step()
                except Exception:
                    pass  # gracefully degrade if evaluator fails

            # Update global best
            if run_success and script_dir:
                global_best.best_step = step
                global_best.best_script_path = best_script_dir
                try:
                    if Path(script_dir).is_dir():
                        import shutil as _shutil
                        _shutil.rmtree(best_script_dir, ignore_errors=True)
                        _shutil.copytree(script_dir, best_script_dir)
                except Exception:
                    pass

            phase_entry = {
                "step": step,
                "run_success": run_success,
                "script_dir": script_dir,
                "elapsed": time.perf_counter() - step_start,
            }
            phases.append(phase_entry)
            _write_json(self.result_dir / f"{session_tag}_step_{step}.json", phase_entry)

        overall_status = "completed" if any(p["run_success"] for p in phases) else "failed"
        result = {
            "status": overall_status,
            "best_step": global_best.best_step,
            "best_metrics": global_best.best_cluster_metrics or {},
            "best_script_dir": str(global_best.best_script_path or ""),
            "phases": phases,
        }
        _write_json(self.result_dir / f"{session_tag}_summary.json", result)
        return result

    # ------------------------------------------------------------------
    # Simple fallback loop (no TextGrad)
    # ------------------------------------------------------------------

    def _run_simple_loop(
        self,
        *,
        suggestion: str,
        task_description: str,
        session_tag: str,
    ) -> Dict[str, Any]:
        """Generate-then-fix without TextGrad. Single optimization step."""
        from agents.generator import StageScriptGenerator
        from pipelines.executor import CodeExecutor
        from pipelines.multieval_types import STAGE_FILENAMES

        config = self.config
        generator = StageScriptGenerator(config=config, engine_name=self.engine_name)
        executor = CodeExecutor(config)
        resolved_layout = config.set_step_output_paths(0)

        code_bundle = generator.generate_bundle(
            task_description=task_description,
            background=suggestion,
            main_plan=suggestion,
            prior_plan="",
            data_summary=getattr(config, "feat_stats", ""),
            prior_resource_summary=getattr(config, "prior_resource_summary", ""),
            script_summaries=StageScriptGenerator.summarize_bundle(None),
            mcp_tools_text="",
            api_dir=getattr(config, "api_dir", ""),
            dataset_dir=getattr(config, "dataset_dir", ""),
        )

        run_result: Dict[str, Any] = {}
        script_dir = ""
        start_from = STAGE_FILENAMES[0]
        for attempt in range(self.max_fix_steps + 1):
            script_dir = generator.save_bundle(code_bundle, step_tag="step_0")
            run_result = executor.run_bundle(
                script_dir,
                resolved_artifact_layout=resolved_layout,
                stage_schemas={},
                start_from=start_from,
            )
            if run_result.get("success", False):
                break
            if attempt < self.max_fix_steps:
                target = str(
                    (run_result.get("validation_failure") or {}).get("target")
                    or run_result.get("failed_script")
                    or STAGE_FILENAMES[0]
                )
                error = str(run_result.get("error", "Unknown error"))
                generator.fix_target(
                    code_bundle=code_bundle,
                    target=target,
                    error=error,
                    task_description=task_description,
                    main_plan=suggestion,
                    prior_plan="",
                    max_fix_step=1,
                )
                start_from = target

        run_success = bool(run_result.get("success", False))
        phase_entry = {
            "step": 0,
            "run_success": run_success,
            "script_dir": script_dir,
            "elapsed": 0.0,
        }
        result = {
            "status": "completed" if run_success else "failed",
            "best_step": 0 if run_success else -1,
            "best_metrics": {},
            "best_script_dir": script_dir if run_success else "",
            "phases": [phase_entry],
        }
        _write_json(self.result_dir / f"{session_tag}_summary.json", result)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_suggestion(self, implementation_plan: Dict[str, Any]) -> str:
        """Convert ToolConsultantAgent implementation_plan to plain-text suggestion."""
        parts: list[str] = []
        if implementation_plan.get("objective"):
            parts.append(f"Objective: {implementation_plan['objective']}")
        if implementation_plan.get("task_description"):
            parts.append(f"Task: {implementation_plan['task_description']}")
        steps = implementation_plan.get("steps") or []
        if steps:
            parts.append("Steps:")
            for i, step in enumerate(steps, 1):
                if isinstance(step, dict):
                    desc = step.get("description") or step.get("action") or str(step)
                    parts.append(f"  {i}. {desc}")
                else:
                    parts.append(f"  {i}. {step}")
        notes = implementation_plan.get("notes") or implementation_plan.get("constraints") or []
        if notes:
            parts.append("Constraints:")
            for note in (notes if isinstance(notes, list) else [notes]):
                parts.append(f"  - {note}")
        if not parts:
            return json.dumps(implementation_plan, ensure_ascii=False)
        return "\n".join(parts)

    @staticmethod
    def _textgrad_available() -> bool:
        try:
            import textgrad  # noqa: F401
            return True
        except ImportError:
            return False


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
