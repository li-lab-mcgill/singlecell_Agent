"""Agent loop for the single-cell pipeline optimizer."""
from __future__ import annotations
import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import textgrad as tg

from config import Config
from consultant import (
    TextGradConsultant,
    build_consultant_history_context,
    build_reconsult_query,
    plan_fingerprint,
    record_consultant_plan,
)
from evaluator import (
    TextGradEvaluator,
    build_instruction_text,
    build_open_issues,
    exploit_plan_from_feedback,
    parse_eval_action,
    to_float,
    update_primary_metric_state,
)
from executor import CodeExecutor
from generator import BundleFormatError, SingleScriptGenerator
from hist_notebook import append_decision_record, append_history_note, build_history_digest, infer_design_identity
from mcp_utils import fetch_mcp_tools_text
from multieval_types import (
    ConsultantPlanRecord,
    DecisionLedgerRecord,
    GlobalBestState,
    HistoryNoteRecord,
    OuterLoopState,
    PipelineBundle,
)
from validator import (
    SECTION_ORDER,
    build_component_contract,
    build_step_run_contract,
    validate_bundle_contract,
    validate_script_path,
    write_failure_record,
)


# ── module-level helpers ──────────────────────────────────────────────────────

def read_json_safe(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_perf(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {
            "train_performance": 0.0,
            "val_performance": 0.0,
            "test_performance": 0.0,
            "best_model": "Unavailable",
            "model_coef": "Unavailable",
            "training_history": [],
        }
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _coerce_perf_scalar(value: Any) -> float:
    direct = to_float(value)
    if direct is not None:
        return direct
    if isinstance(value, dict):
        for key in ["metric", "loss", "reconstruction_mse", "ari", "ARI", "score", "value"]:
            nested = to_float(value.get(key))
            if nested is not None:
                return nested
        for nested_value in value.values():
            nested = to_float(nested_value)
            if nested is not None:
                return nested
    return 0.0


def perf_summary(perf: Dict[str, Any]) -> str:
    train = _coerce_perf_scalar(perf.get("train_performance", 0.0))
    val = _coerce_perf_scalar(perf.get("val_performance", 0.0))
    test = _coerce_perf_scalar(perf.get("test_performance", 0.0))
    return (
        f"Current train_performance: {round(train, 4)}\n"
        f"Current val_performance: {round(val, 4)}\n"
        f"Current test_performance: {round(test, 4)}\n"
    )


def metric_from_dict(d: Dict[str, Any], candidates: List[str]) -> float | None:
    if not isinstance(d, dict):
        return None
    for key in candidates:
        if key in d:
            value = to_float(d.get(key))
            if value is not None:
                return value
    return None


def collect_eval_data(
    config: Config, run_result: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    return (
        run_result.get("cluster_metrics") if isinstance(run_result.get("cluster_metrics"), dict) else read_json_safe(config.cluster_metrics_path),
        run_result.get("cluster_summary") if isinstance(run_result.get("cluster_summary"), dict) else read_json_safe(config.cluster_summary_path),
        run_result.get("training_logs") if isinstance(run_result.get("training_logs"), dict) else read_json_safe(config.training_logs_path),
        run_result.get("pipeline_summary") if isinstance(run_result.get("pipeline_summary"), dict) else read_json_safe(config.pipeline_summary_path),
    )


def raise_on_failures(failures: Any, result_dir: str, step: int) -> None:
    if failures:
        failure = failures[0]
        write_failure_record(f"{result_dir}/feedback/failure_step_{step}.json", failure)
        raise RuntimeError(f"[{failure.error_type}] {failure.stage}: {failure.message}")


def fail_with_message(result_dir: str, step: int, stage: str, error_type: str, message: str, details: Dict[str, Any] | None = None) -> None:
    payload = {"stage": stage, "error_type": error_type, "message": message, "details": details or {}}
    write_failure_record(f"{result_dir}/feedback/failure_step_{step}.json", payload)
    raise RuntimeError(f"[{error_type}] {stage}: {message}")


def format_failure_message(*, stage: str, error_type: str, message: str, details: Dict[str, Any] | None = None) -> str:
    base = f"[{error_type}] {stage}: {message}"
    out = f"{base}\nDetails: {json.dumps(details, ensure_ascii=False, sort_keys=True)}" if details else base
    if stage == "prior" and "prior_manifest.json" in message:
        out += (
            "\nExpected runtime manifest schema: "
            '{"required_files":[{"file_name":"<csv name>","path":"<absolute path under SCANPY_AGENT_RUN_DIR/prior/>"}]}'
            "\nFixed prior output rule: all produced prior files must live under SCANPY_AGENT_RUN_DIR/prior/."
            "\nImportant: PRIOR_PLAN_JSON is the planning/specification object; prior_manifest.json is only the runtime record of produced files."
        )
    if "adata.h5ad" in message or "Input AnnData not found" in message:
        out += (
            "\nInput path rule: modality 1 input must be read from SCANPY_AGENT_INPUT_DIR/adata.h5ad "
            "or from SCANPY_AGENT_INPUT_MOD1_PATH."
            "\nDo not look for input AnnData under SCANPY_AGENT_RUN_DIR."
        )
    return out


def validation_failure_target(failure: Dict[str, Any]) -> str:
    stage = str(failure.get("stage") or "").strip().lower()
    return stage if stage in SECTION_ORDER else "pipeline"


def _normalize_label(text: str, max_len: int = 48) -> str:
    label = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return (label or "unknown")[:max_len]


def classify_run_failure(run_result: Dict[str, Any]) -> Tuple[str | None, str | None, str]:
    if run_result.get("success", False):
        return None, None, ""
    failure = run_result.get("validation_failure")
    if isinstance(failure, dict):
        stage = str(failure.get("stage") or "unknown")
        error_type = str(failure.get("error_type") or "ValidationFailure")
        message = str(failure.get("message") or run_result.get("error") or "Unknown validation error")
        return "post_run_validate", f"post_run_validate:{stage}:{error_type}:{_normalize_label(message)}", message
    stage = str(run_result.get("failed_stage") or "unknown")
    message = str(run_result.get("error") or "Unknown runtime error")
    return "execute", f"execute:{stage}:{_normalize_label(message)}", message


def classify_decision_result(*, run_success: bool, primary_gain: float | None, metric_value: float | None) -> str:
    if not run_success:
        return "hurt"
    if primary_gain is None:
        return "helped" if metric_value is not None else "inconclusive"
    if primary_gain > 0:
        return "helped"
    if primary_gain < 0:
        return "hurt"
    return "inconclusive"


def summarize_fix_outcome(attempts_used: int, run_success: bool) -> str:
    if attempts_used <= 0:
        return "no_fix_needed"
    return f"resolved_after_{attempts_used}_fix_attempts" if run_success else f"unresolved_after_{attempts_used}_fix_attempts"


def previous_exploit_context(records: List[HistoryNoteRecord]) -> Dict[str, Any]:
    for record in reversed(records):
        if getattr(record, "exploit_applied", False):
            return {
                "previous_step_exploit_applied": True,
                "previous_step_exploit_step": record.step,
                "previous_step_optimized_scripts": record.optimized_scripts,
                "previous_step_exploit_change_types": record.exploit_change_types,
            }
    return {
        "previous_step_exploit_applied": False,
        "previous_step_exploit_step": None,
        "previous_step_optimized_scripts": [],
        "previous_step_exploit_change_types": {},
    }



# ── agent loop ────────────────────────────────────────────────────────────────

class AgentLoop:
    OPTIMIZER_CONSTRAINTS = [
        "Return ONLY one end-to-end valid, executable Python code named pipeline.py.",
    ]

    def __init__(self, config: Config, args: argparse.Namespace, background: str, mcp_tools_text: str) -> None:
        self.config = config
        self.args = args
        self.background = background
        self.mcp_tools_text = mcp_tools_text

        # log paths
        notes_dir = config.notes_dir
        self.note_path = f"{notes_dir}/note_history.txt"
        self.history_notes_path = f"{notes_dir}/history_notes.jsonl"
        self.history_digest_path = f"{notes_dir}/history_digest.txt"
        self.decision_ledger_path = f"{notes_dir}/decision_ledger.jsonl"
        self.history_notes_result_path = f"{config.result_dir}/feedback/history_notes.jsonl"
        self.decision_ledger_result_path = f"{config.result_dir}/feedback/decision_ledger.jsonl"
        self.consultant_history_path = f"{config.result_dir}/feedback/consultant_history.jsonl"

        # components (created once)
        self.global_engine = tg.get_engine(args.engine)
        self.consultant = TextGradConsultant(config=config, engine_name=args.engine)
        self.executor = CodeExecutor(config)

        # mutable state
        self.outer_state = OuterLoopState()
        self.global_note_records: List[HistoryNoteRecord] = []
        self.decision_records: List[DecisionLedgerRecord] = []
        self.global_best = GlobalBestState()
        self.consultant_records: List[ConsultantPlanRecord] = []

        # set during run
        self.task_summary: Dict[str, Any] = {}
        self.suggestion: str = ""
        self.evaluator: TextGradEvaluator | None = None
        self.bundle: PipelineBundle | None = None
        self.optimizer: tg.TextualGradientDescent | None = None
        self.last_cluster_metrics: Dict[str, Any] = {}
        self.last_cluster_summary: Dict[str, Any] = {}

    # ── setup ──────────────────────────────────────────────────────────────

    def _init_logs(self) -> None:
        for path in [
            self.note_path, self.history_notes_path, self.decision_ledger_path,
            self.history_notes_result_path, self.decision_ledger_result_path,
            self.consultant_history_path,
        ]:
            with open(path, "w", encoding="utf-8"):
                pass
        with open(self.history_digest_path, "w", encoding="utf-8") as f:
            f.write("<empty>\n")

    def _initial_consult(self) -> None:
        query = self.consultant.create_query(
            samples=None, id_col=None, background=self.background, label_col=None,
            include_feat_stats=True, background_only=False, include_samples=False,
            mcp_tools_text=self.mcp_tools_text,
            api_dir=self.config.api_dir, dataset_dir=self.config.dataset_dir,
        )
        output = self.consultant.generate(prompt=query)
        print("\n=== Consultant Output ===\n")
        print(output)
        print("\n=== End Consultant Output ===\n")

        self.task_summary = TextGradConsultant.parse_summary_tags(output)
        self.suggestion = self.task_summary["suggestion"]
        self._record_consultant_plan(step=-1, source="initial", output=output)
        self._reset_evaluator()

    # ── step execution ─────────────────────────────────────────────────────

    def _generate_and_run(
        self, step: int, step_contract: Any, component_contract: Dict[str, Any]
    ) -> Tuple[PipelineBundle, Dict[str, Any], str, int]:
        """Generate (or reuse) bundle, fix errors, and execute.

        Returns (bundle, run_result, script_path, attempts_used).
        """
        generator = SingleScriptGenerator(
            config=self.config, engine_name=self.args.engine,
            results_path=self.config.model_perf_path,
        )
        query = generator.create_query(
            task_descrp=self.task_summary["task_description"],
            data_summary=self.config.feat_stats,
            suggestion=self.suggestion,
            interface_contract=json.dumps(component_contract, ensure_ascii=False),
            script_summaries=generator.summarize_bundle(self.bundle) if self.bundle is not None else "<none>",
            background=self.background,
            mcp_tools_text=self.mcp_tools_text,
            api_dir=self.config.api_dir,
            dataset_dir=self.config.dataset_dir,
            preprocess_output_summary=step_contract.contract_path,
            cluster_metrics=json.dumps(self.last_cluster_metrics, ensure_ascii=False),
            cluster_summary=json.dumps(self.last_cluster_summary, ensure_ascii=False),
        )

        bundle = self.bundle
        run_result: Dict[str, Any] = {}
        script_path = ""
        last_error = ""

        for attempt in range(self.config.max_fix_step + 1):
            # generation phase
            if bundle is None:
                try:
                    bundle = (
                        generator.generate_bundle(prompt=query)
                        if attempt == 0
                        else generator.regenerate_bundle(prompt=query, error=last_error or "Unknown generation error")
                    )
                except BundleFormatError as exc:
                    last_error = str(exc)
                    if attempt == self.config.max_fix_step:
                        fail_with_message(self.config.result_dir, step, "generator", "InvalidSchema", str(exc), {"raw_response": exc.raw_response[:4000]})
                    print(f"fix_{attempt} (generator): {last_error}")
                    bundle = None
                    continue

            # pre-run contract validation
            pre_run_failures = validate_bundle_contract(bundle, step_contract)
            if pre_run_failures:
                failure = pre_run_failures[0]
                last_error = format_failure_message(stage=failure.stage, error_type=failure.error_type, message=failure.message, details=failure.details)
                if attempt == self.config.max_fix_step:
                    raise_on_failures(pre_run_failures, self.config.result_dir, step)
                target = validation_failure_target(failure.to_dict())
                print(f"fix_{attempt} ({target}): {last_error}")
                generator.fix_stage(bundle=bundle, failed_stage=target, error=last_error, max_fix_step=1)
                continue

            # save and path-validate
            script_path = generator.save_bundle(bundle, step_tag=f"step_{step}" if attempt == 0 else f"step_{step}_fix{attempt - 1}")
            path_failures = validate_script_path(script_path, step_contract)
            if path_failures:
                failure = path_failures[0]
                last_error = format_failure_message(stage=failure.stage, error_type=failure.error_type, message=failure.message, details=failure.details)
                if attempt == self.config.max_fix_step:
                    raise_on_failures(path_failures, self.config.result_dir, step)
                target = validation_failure_target(failure.to_dict())
                print(f"fix_{attempt} ({target}): {last_error}")
                generator.fix_stage(bundle=bundle, failed_stage=target, error=last_error, max_fix_step=1)
                continue

            # execute
            run_result = self.executor.run_bundle(script_path, contract=step_contract)
            if run_result.get("success", False):
                break

            # handle execution failure
            failure_record = run_result.get("validation_failure")
            if failure_record:
                last_error = format_failure_message(
                    stage=str(failure_record.get("stage", "unknown")),
                    error_type=str(failure_record.get("error_type", "ValidationFailure")),
                    message=str(run_result.get("error", "Unknown error")),
                    details=failure_record.get("details", {}),
                )
                target = validation_failure_target(failure_record)
            else:
                target = str(run_result.get("failed_stage") or "pipeline")
                last_error = run_result.get("error", "Unknown error")

            if attempt == self.config.max_fix_step:
                if failure_record:
                    write_failure_record(f"{self.config.result_dir}/feedback/failure_step_{step}.json", failure_record)
                    raise RuntimeError(
                        f"[{failure_record.get('error_type', 'ValidationFailure')}] "
                        f"{failure_record.get('stage', 'unknown')}: {run_result.get('error', 'Unknown error')}"
                    )
                fail_with_message(self.config.result_dir, step, target, "RuntimeError", last_error)

            print(f"fix_{attempt} ({target}): {last_error}")
            generator.fix_stage(bundle=bundle, failed_stage=target, error=last_error, max_fix_step=1)

        self.bundle = bundle
        return bundle, run_result, script_path, attempt

    def _ensure_optimizer(self) -> None:
        if self.optimizer is None:
            self.optimizer = tg.TextualGradientDescent(
                engine=self.global_engine,
                parameters=[self.bundle.pipeline_code],
                constraints=self.OPTIMIZER_CONSTRAINTS,
            )

    def _exploit(self, eval_out: tg.Variable) -> bool:
        """Apply one TextGrad step using eval_out as the loss signal."""
        self.optimizer.zero_grad()
        eval_out.backward()
        self.optimizer.step()
        return True

    def _reconsult(
        self,
        step: int,
        payload: Dict[str, Any],
        feedback: Dict[str, Any],
        open_issues: List[str],
        cluster_metrics: Dict[str, Any],
        cluster_summary: Dict[str, Any],
        training_logs: Dict[str, Any],
        pipeline_summary: Dict[str, Any],
        notes_text: str,
    ) -> None:
        """Trigger reconsultation, update plan/suggestion/evaluator, reset outer state."""
        exploit_plan = exploit_plan_from_feedback(feedback)
        current_attempt = {
            "exploit_plan": exploit_plan,
            "instruction_text": build_instruction_text(feedback),
            "cluster_metrics": cluster_metrics,
            "cluster_summary": cluster_summary,
            "training_logs": training_logs,
            "pipeline_summary": pipeline_summary,
        }
        why_current_fails = {
            "payload": payload,
            "feedback": feedback,
            "open_issues": open_issues,
            "history_digest": notes_text,
        }
        reconsult_query = build_reconsult_query(
            task_description=self.task_summary["task_description"],
            background=self.background,
            current_suggestion=self.suggestion,
            current_prior_plan=self.task_summary["prior_plan"],
            current_attempt=current_attempt,
            why_current_fails=why_current_fails,
            historical_failures="\n".join(open_issues[-10:]) if open_issues else "<none>",
            hard_constraints=self.OPTIMIZER_CONSTRAINTS,
            history_digest=notes_text,
            consultant_history_context=build_consultant_history_context(self.consultant_records),
        )
        output = self.consultant.generate(prompt=reconsult_query)
        print(f"\n=== Reconsult Consultant Output (Step {step}) ===\n")
        print(output)
        print(f"\n=== End Reconsult Consultant Output (Step {step}) ===\n")

        self.task_summary = TextGradConsultant.parse_summary_tags(output)
        self.suggestion = self.task_summary["suggestion"]
        self._record_consultant_plan(step=step, source="reconsult", output=output)
        self._reset_evaluator()
        self.outer_state.reset()
        self.optimizer = None
        self.bundle = None

    # ── per-step orchestration ─────────────────────────────────────────────

    def _run_step(self, step: int) -> None:
        step_start = time.perf_counter()
        self.config.set_step_output_paths(step)

        step_contract = build_step_run_contract(self.config, step, self.task_summary["prior_plan"])
        step_contract.write()
        component_contract = build_component_contract(self.config, self.task_summary["prior_plan"], step_contract)
        with open(step_contract.component_contract_path, "w", encoding="utf-8") as f:
            json.dump(component_contract, f, indent=2, ensure_ascii=False)

        bundle, run_result, script_path, attempts_used = self._generate_and_run(step, step_contract, component_contract)
        self._ensure_optimizer()

        perf = read_perf(self.config.model_perf_path)
        cluster_metrics, cluster_summary, training_logs, pipeline_summary = collect_eval_data(self.config, run_result)
        self.last_cluster_metrics = cluster_metrics
        self.last_cluster_summary = cluster_summary

        self.outer_state.best_ari, self.outer_state.best_sil, self.outer_state.stagnation_steps, primary_state = update_primary_metric_state(
            cluster_metrics=cluster_metrics,
            best_ari=self.outer_state.best_ari,
            best_sil=self.outer_state.best_sil,
            delta_min=self.args.delta_min,
            stagnation_steps=self.outer_state.stagnation_steps,
        )

        notes_text = build_history_digest(
            outer_notes=self.outer_state.note_records,
            global_notes=self.global_note_records,
            decision_records=self.decision_records,
            keep_last=20,
        )
        with open(self.history_digest_path, "w", encoding="utf-8") as f:
            f.write(notes_text + "\n")

        eval_out = self.evaluator.loss_fn(
            notes=tg.Variable(notes_text or "<empty>", requires_grad=False, role_description="multi-step notes"),
            step=step,
            pipeline_code=bundle.pipeline_code,
            suggestion=tg.Variable(self.suggestion, requires_grad=False, role_description="current consultant suggestion"),
            training_history=tg.Variable(
                json.dumps(perf.get("training_history", []), ensure_ascii=False),
                requires_grad=False, role_description="epoch-level training history",
            ),
            stagnation_steps=tg.Variable(  # current count, not the limit
                str(self.outer_state.stagnation_steps),
                requires_grad=False, role_description="current consecutive steps without meaningful gain",
            ),
            delta_min=tg.Variable(str(self.args.delta_min), requires_grad=False, role_description="minimum meaningful validation gain"),
            current_performance=tg.Variable(
                json.dumps({"perf_summary": perf_summary(perf), "primary_state": primary_state}, ensure_ascii=False),
                requires_grad=False, role_description="current performance summary",
            ),
            interface_contract=tg.Variable(json.dumps(component_contract, ensure_ascii=False), requires_grad=False, role_description="single-script interface contract"),
            context_mode=tg.Variable("full", requires_grad=False, role_description="context packet mode"),
            cluster_metrics=tg.Variable(json.dumps(cluster_metrics, ensure_ascii=False), requires_grad=False, role_description="cluster metrics"),
            cluster_summary=tg.Variable(json.dumps(cluster_summary, ensure_ascii=False), requires_grad=False, role_description="cluster summary"),
            training_logs=tg.Variable(json.dumps(training_logs, ensure_ascii=False), requires_grad=False, role_description="training logs"),
            pipeline_summary=tg.Variable(json.dumps(pipeline_summary, ensure_ascii=False), requires_grad=False, role_description="pipeline summary"),
        )

        print(f"\n=== Evaluator Output (Step {step}) ===\n")
        print(eval_out.value)
        print(f"\n=== End Evaluator Output (Step {step}) ===\n")

        action, payload, feedback = parse_eval_action(eval_out.value)
        print(f"Evaluator action at step {step}: {action}")

        exploit_applied = False

        if action == "exploit":
            exploit_applied = self._exploit(eval_out)
            if exploit_applied:
                print(f"\n=== Exploit applied (Step {step}) ===\n")

        open_issues = build_open_issues(run_result=run_result, primary_state=primary_state, payload=payload, feedback=feedback)

        self._log_step(
            step=step, action=action, payload=payload, feedback=feedback,
            run_result=run_result, perf=perf,
            cluster_metrics=cluster_metrics, cluster_summary=cluster_summary,
            training_logs=training_logs, pipeline_summary=pipeline_summary,
            script_path=script_path, primary_state=primary_state,
            attempts_used=attempts_used, open_issues=open_issues,
            exploit_applied=exploit_applied,
        )
        self._update_global_best(step=step, run_result=run_result, cluster_metrics=cluster_metrics, perf=perf)

        if action == "reconsult":
            self._reconsult(step, payload, feedback, open_issues, cluster_metrics, cluster_summary, training_logs, pipeline_summary, notes_text)

        print(f"Step {step} elapsed: {time.perf_counter() - step_start:.2f}s")

    # ── logging ────────────────────────────────────────────────────────────

    def _log_step(
        self, *, step: int, action: str, payload: Dict[str, Any], feedback: Dict[str, Any],
        run_result: Dict[str, Any], perf: Dict[str, Any],
        cluster_metrics: Dict[str, Any], cluster_summary: Dict[str, Any],
        training_logs: Dict[str, Any], pipeline_summary: Dict[str, Any],
        script_path: str, primary_state: Dict[str, Any], attempts_used: int,
        open_issues: List[str], exploit_applied: bool,
    ) -> None:
        exploit_plan = exploit_plan_from_feedback(feedback)
        optimized_scripts = ["pipeline"] if exploit_applied else []

        with open(f"{self.config.result_dir}/feedback/single_feedback_step_{step}.json", "w", encoding="utf-8") as f:
            json.dump({
                "step": step, "context_mode": "full", "action": action,
                "payload": payload, "feedback": feedback, "exploit_plan": exploit_plan,
                "run_success": run_result.get("success", False),
                "failed_stage": run_result.get("failed_stage"),
                "validation_failure": run_result.get("validation_failure"),
                "performance": perf,
                "cluster_metrics": cluster_metrics, "cluster_summary": cluster_summary,
                "training_logs": training_logs, "pipeline_summary": pipeline_summary,
                "script_path": script_path, "primary_state": primary_state,
                "exploit_applied": exploit_applied, "optimized_targets": optimized_scripts,
            }, f, indent=2, ensure_ascii=False)

        current_metric_value = metric_from_dict(cluster_metrics, ["ari", "ARI"])
        primary_gain = to_float(primary_state.get("primary_metric_gain"))
        architecture_fingerprint, design_summary = infer_design_identity(
            bundle_text=self.bundle.as_text_dict(), payload=payload, cluster_summary=cluster_summary,
        )
        failure_phase, failure_fingerprint, root_cause = classify_run_failure(run_result)

        architecture_info = payload.get("architecture", {}) if isinstance(payload, dict) else {}
        repetition_reason = str(architecture_info.get("repetition_penalty_reason") or "").strip() if isinstance(architecture_info, dict) else ""
        do_not_repeat = bool(action == "reconsult" or repetition_reason)
        do_not_repeat_reason = (
            repetition_reason
            or str(payload.get("primary_reason") or feedback.get("strategy") or "").strip()
            or "Current architecture was ruled out after evaluation"
        )
        decision_rationale = str(payload.get("primary_reason") or feedback.get("strategy") or "").strip() or "No explicit rationale provided"
        decision_result = classify_decision_result(
            run_success=bool(run_result.get("success", False)),
            primary_gain=primary_gain, metric_value=current_metric_value,
        )
        failed_architectures = feedback.get("failed_architectures", []) if isinstance(feedback, dict) else []
        if isinstance(failed_architectures, str):
            failed_architectures = [failed_architectures]
        elif not isinstance(failed_architectures, list):
            failed_architectures = []

        note_record = HistoryNoteRecord(
            step=step, action=action, context_mode="full",
            attempts_used=attempts_used,
            run_success=bool(run_result.get("success", False)),
            failed_stage=run_result.get("failed_stage"),
            architecture_fingerprint=architecture_fingerprint, design_summary=design_summary,
            decision_rationale=decision_rationale, primary_metric="ari",
            metric_value=current_metric_value, gain=primary_gain,
            stagnation=self.outer_state.stagnation_steps,
            failure_phase=failure_phase, failure_fingerprint=failure_fingerprint,
            root_cause=root_cause,
            fix_outcome=summarize_fix_outcome(attempts_used, bool(run_result.get("success", False))),
            evaluator_diagnosis=exploit_plan.get("diagnosis", ""),
            script_plan=exploit_plan, open_issues=open_issues,
            exploit_applied=exploit_applied, optimized_scripts=optimized_scripts,
            previous_exploit_context=previous_exploit_context(self.global_note_records),
            do_not_repeat=do_not_repeat, do_not_repeat_reason=do_not_repeat_reason,
        )
        append_history_note(
            note_record,
            outer_notes=self.outer_state.note_records,
            global_notes=self.global_note_records,
            note_text_path=self.note_path,
            note_jsonl_path=self.history_notes_path,
            mirror_jsonl_path=self.history_notes_result_path,
        )
        append_decision_record(
            DecisionLedgerRecord(
                step=step, architecture_fingerprint=architecture_fingerprint,
                design_summary=design_summary, decision_rationale=decision_rationale,
                primary_metric="ari", metric_value=current_metric_value,
                metric_gain=primary_gain, result=decision_result, action=action,
                failed_stage=run_result.get("failed_stage"),
                failure_fingerprint=failure_fingerprint,
                do_not_repeat=do_not_repeat, do_not_repeat_reason=do_not_repeat_reason,
                exploit_applied=exploit_applied, optimized_scripts=optimized_scripts,
                rejected_design_labels=[str(item) for item in failed_architectures if str(item).strip()],
            ),
            decision_records=self.decision_records,
            decision_jsonl_path=self.decision_ledger_path,
            mirror_jsonl_path=self.decision_ledger_result_path,
        )

    def _update_global_best(self, *, step: int, run_result: Dict[str, Any], cluster_metrics: Dict[str, Any], perf: Dict[str, Any]) -> None:
        if not run_result.get("success", False):
            return
        cur_ari = metric_from_dict(cluster_metrics, ["ari", "ARI"])
        if cur_ari is None:
            return
        if self.global_best.best_ari is not None and cur_ari < self.global_best.best_ari:
            return
        self.global_best.best_ari = cur_ari
        self.global_best.best_step = step
        self.global_best.best_perf = perf if isinstance(perf, dict) else {}
        self.global_best.best_cluster_metrics = cluster_metrics if isinstance(cluster_metrics, dict) else {}

        step_dir = os.path.join(self.config.code_dir, "code_best_ari")
        os.makedirs(step_dir, exist_ok=True)
        best_script_path = os.path.join(step_dir, "pipeline.py")
        with open(best_script_path, "w", encoding="utf-8") as f:
            f.write(self.bundle.pipeline_code.value)
        self.global_best.best_script_path = best_script_path

        with open(f"{self.config.final_out_dir}/global_best_ari.json", "w", encoding="utf-8") as f:
            json.dump({
                "best_step": self.global_best.best_step,
                "best_ari": self.global_best.best_ari,
                "best_script_path": self.global_best.best_script_path,
                "best_cluster_metrics": self.global_best.best_cluster_metrics,
                "best_perf": self.global_best.best_perf,
            }, f, indent=2, ensure_ascii=False)

    # ── internal helpers ───────────────────────────────────────────────────

    def _record_consultant_plan(self, *, step: int, source: str, output: str) -> None:
        record_consultant_plan(
            consultant_records=self.consultant_records,
            path=self.consultant_history_path,
            record=ConsultantPlanRecord(
                step=step, source=source,
                task_description=self.task_summary["task_description"],
                suggestion=self.task_summary["suggestion"],
                prior_plan_json=self.task_summary["prior_plan"],
                raw_output=output,
                plan_fingerprint=plan_fingerprint(
                    self.task_summary["task_description"],
                    self.task_summary["suggestion"],
                    self.task_summary["prior_plan"],
                ),
            ),
        )

    def _reset_evaluator(self) -> None:
        self.evaluator = TextGradEvaluator(
            config=self.config,
            engine_name=self.args.engine,
            task_decrp=self.task_summary["task_description"],
            background=self.background,
            eval_type="joint",
        )

    # ── entry point ────────────────────────────────────────────────────────

    def run(self) -> None:
        self._init_logs()
        self._initial_consult()
        for step in range(self.config.opt_step + 1):
            self._run_step(step)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    cur_path = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser()
    parser.add_argument("--code-dir", default="saved_code")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--notes-dir", default="notes")
    parser.add_argument("--input_mod1", default=None)
    parser.add_argument("--input_mod2", default=None)
    parser.add_argument("--engine", default="gpt-5")
    parser.add_argument("--api-dir", default=None)
    parser.add_argument("--dataset-dir", default=None)
    parser.add_argument("--opt-step", type=int, default=5)
    parser.add_argument("--max-fix-step", type=int, default=3)
    parser.add_argument("--time-budget", type=int, default=3600)
    parser.add_argument("--delta-min", type=float, default=0.005)
    parser.add_argument("--stagnation_steps_limit", type=int, default=2)
    args = parser.parse_args()

    file_path = args.input_mod1 or f"{cur_path}/data/h5ad/pbmc3k_annotated.h5ad"
    mod2_path = args.input_mod2

    background = f"""
Data file: Modality 1: {file_path}
Data file: Modality 2: {mod2_path if mod2_path else "None"}
DATA: Sparse, high-dimensional gene expression counts.
Each row represents a cell and each column represents a gene.

TASK:
Develop an unsupervised deep learning Python pipeline for single-cell RNA-seq representation learning.
The pipeline MUST:
1. Preprocess each modality using single-cell best practices.
2. Build the prior after preprocessing so it can align to the processed feature space.
3. Learn an embedding that preserves biological variation and handles sparsity.
4. Cluster only on the learned embedding; labels are only for evaluation.
5. Use exactly one script named pipeline.py with main() as the executable entry point.
"""

    global_engine = tg.get_engine(engine_name=args.engine)
    tg.set_backward_engine(global_engine, override=True)

    config = Config(
        opt_step=args.opt_step,
        max_fix_step=args.max_fix_step,
        timeout=args.time_budget,
        task_type="Integration",
        mod1_path=file_path,
        mod2_path=mod2_path,
        learning_type="Unsupervised",
        metrics="ARI",
        label_column=None,
        id_column=None,
        code_dir=args.code_dir,
        result_dir=args.results_dir,
    )
    config.api_dir = args.api_dir or f"{cur_path}/apis"
    config.dataset_dir = args.dataset_dir or f"{cur_path}/Datasets"
    config.notes_dir = f"{cur_path}/{args.notes_dir}"
    config.code_dir = config.single_code_dir

    for d in [
        config.notes_dir,
        config.code_dir,
        config.result_dir,
        f"{config.result_dir}/feedback",
        f"{config.result_dir}/metadata&perf",
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)

    mcp_tools_text = fetch_mcp_tools_text()
    AgentLoop(config=config, args=args, background=background, mcp_tools_text=mcp_tools_text).run()


if __name__ == "__main__":
    main()
