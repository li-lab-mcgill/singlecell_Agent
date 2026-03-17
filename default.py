import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List

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
        for key in [
            "metric",
            "loss",
            "reconstruction_mse",
            "ari",
            "ARI",
            "score",
            "value",
        ]:
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


def collect_eval_data(config: Config, run_result: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    return (
        run_result.get("cluster_metrics") if isinstance(run_result.get("cluster_metrics"), dict) else read_json_safe(config.cluster_metrics_path),
        run_result.get("cluster_summary") if isinstance(run_result.get("cluster_summary"), dict) else read_json_safe(config.cluster_summary_path),
        run_result.get("training_logs") if isinstance(run_result.get("training_logs"), dict) else read_json_safe(config.training_logs_path),
        run_result.get("pipeline_summary") if isinstance(run_result.get("pipeline_summary"), dict) else read_json_safe(config.pipeline_summary_path),
    )


def maybe_update_global_best(*, global_best: GlobalBestState, run_success: bool, step: int, cluster_metrics: Dict[str, Any], perf: Dict[str, Any], bundle: PipelineBundle, generator: SingleScriptGenerator, final_out_dir: str) -> GlobalBestState:
    if not run_success:
        return global_best
    cur_ari = metric_from_dict(cluster_metrics, ["ari", "ARI"])
    if cur_ari is None:
        return global_best
    if global_best.best_ari is not None and cur_ari < global_best.best_ari:
        return global_best
    global_best.best_ari = cur_ari
    global_best.best_step = step
    global_best.best_script_path = generator.save_bundle(bundle, step_tag="best_ari")
    global_best.best_perf = perf if isinstance(perf, dict) else {}
    global_best.best_cluster_metrics = cluster_metrics if isinstance(cluster_metrics, dict) else {}
    summary = {
        "best_step": global_best.best_step,
        "best_ari": global_best.best_ari,
        "best_script_path": global_best.best_script_path,
        "best_cluster_metrics": global_best.best_cluster_metrics,
        "best_perf": global_best.best_perf,
    }
    with open(f"{final_out_dir}/global_best_ari.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return global_best


def raise_on_failures(failures, result_dir: str, step: int) -> None:
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
    if not details:
        out = base
    else:
        out = f"{base}\nDetails: {json.dumps(details, ensure_ascii=False, sort_keys=True)}"
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
    if stage in SECTION_ORDER:
        return stage
    return "pipeline"


def _normalize_label(text: str, max_len: int = 48) -> str:
    label = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return (label or "unknown")[:max_len]


def classify_run_failure(run_result: Dict[str, Any]) -> tuple[str | None, str | None, str]:
    if run_result.get("success", False):
        return None, None, ""
    failure = run_result.get("validation_failure")
    if isinstance(failure, dict):
        stage = str(failure.get("stage") or "unknown")
        error_type = str(failure.get("error_type") or "ValidationFailure")
        message = str(failure.get("message") or run_result.get("error") or "Unknown validation error")
        fingerprint = f"post_run_validate:{stage}:{error_type}:{_normalize_label(message)}"
        return "post_run_validate", fingerprint, message
    stage = str(run_result.get("failed_stage") or "unknown")
    message = str(run_result.get("error") or "Unknown runtime error")
    fingerprint = f"execute:{stage}:{_normalize_label(message)}"
    return "execute", fingerprint, message


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
    if run_success:
        return f"resolved_after_{attempts_used}_fix_attempts"
    return f"unresolved_after_{attempts_used}_fix_attempts"


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


def infer_exploit_change_type(*, instructions: List[str], diagnosis: str, strategy: str) -> str:
    text = " ".join([diagnosis, strategy, *instructions]).lower()
    structural_keywords = ["architecture", "encoder", "decoder", "latent", "rewrite", "refactor", "new function", "loss term", "pipeline"]
    return "structural" if any(keyword in text for keyword in structural_keywords) else "tuning"


def _sanitize_exploit_instruction(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    cleaned = re.sub(r"^\s*in\s+[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)\s*[:,]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*in\s+[A-Za-z_][A-Za-z0-9_]*\s*[:,]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(dataloader|prior|model|train|clustering)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _build_prior_resource_instructions(dataset_dir: str | None) -> List[str]:
    if not dataset_dir:
        return []
    return [
        f"Prior data resources are available under {dataset_dir}.",
        f"MsigDB.csv is available at {os.path.join(dataset_dir, 'MsigDB.csv')} with columns ID, Name, Count, Genes.",
        f"NeST.tsv is available at {os.path.join(dataset_dir, 'NeST.tsv')} with columns NEST ID, name_new, Genes.",
        f"GO_terms.csv is available at {os.path.join(dataset_dir, 'GO_terms.csv')} with columns GO, Genes, Gene_Count, Term_Description.",
        f"Cell_marker_Human.xlsx is available at {os.path.join(dataset_dir, 'Cell_marker_Human.xlsx')}.",
        f"meta_info.csv is available at {os.path.join(dataset_dir, 'meta_info.csv')}.",
    ]


def build_exploit_gradient_text(*, instructions: List[str], diagnosis: str, strategy: str, expected_effect: str, current_performance: str, focus_areas: List[str] | None = None, bottleneck_reason: str = "", dataset_dir: str | None = None) -> str:
    flat_instructions = _build_prior_resource_instructions(dataset_dir)
    flat_instructions.extend(_sanitize_exploit_instruction(item) for item in instructions if str(item).strip())
    flat_instructions = [item for item in flat_instructions if item]
    if not flat_instructions:
        flat_instructions = ["No change needed"]
    lines = ["Optimize instructions:"]
    for item in flat_instructions:
        lines.append(f"- {item}")
    return "\n".join(lines)


def attach_exploit_signal_and_metadata(*, pipeline_var: tg.Variable, keep_fixed: List[str], change_next: List[str], diagnosis: str, strategy: str, expected_effect: str, current_performance_text: str, focus_areas: List[str], bottleneck_reason: str, dataset_dir: str | None = None) -> tuple[Dict[str, str], Dict[str, str], Dict[str, Dict[str, Any]]]:
    instructions = [str(item).strip() for item in [*keep_fixed, *change_next] if str(item).strip()]
    change_type = infer_exploit_change_type(instructions=instructions, diagnosis=diagnosis, strategy=strategy)
    gradient_text = build_exploit_gradient_text(
        instructions=instructions,
        diagnosis=diagnosis,
        strategy=strategy,
        expected_effect=expected_effect,
        current_performance=current_performance_text,
        focus_areas=focus_areas,
        bottleneck_reason=bottleneck_reason,
        dataset_dir=dataset_dir,
    )
    grad_var = tg.Variable(
        gradient_text,
        requires_grad=False,
        role_description="gradient for pipeline",
    )
    pipeline_var.gradients.add(grad_var)
    pipeline_var.gradients_context[grad_var] = None
    summary = instructions[0] if instructions else "No change needed"
    payload = {
        "change_type": change_type,
        "summary": summary,
        "focus_areas": [str(item).strip() for item in focus_areas if str(item).strip()],
        "bottleneck_reason": bottleneck_reason,
        "keep_fixed": [str(item).strip() for item in keep_fixed if str(item).strip()],
        "change_next": [str(item).strip() for item in change_next if str(item).strip()],
        "gradient_text": gradient_text,
    }
    return {"pipeline": change_type}, {"pipeline": f"{change_type}: {summary}"}, {"pipeline": payload}


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

    Path(config.notes_dir).mkdir(parents=True, exist_ok=True)
    Path(config.code_dir).mkdir(parents=True, exist_ok=True)
    Path(config.result_dir).mkdir(parents=True, exist_ok=True)
    Path(f"{config.result_dir}/feedback").mkdir(parents=True, exist_ok=True)
    Path(f"{config.result_dir}/metadata&perf").mkdir(parents=True, exist_ok=True)

    note_path = f"{config.notes_dir}/note_history.txt"
    history_notes_path = f"{config.notes_dir}/history_notes.jsonl"
    history_digest_path = f"{config.notes_dir}/history_digest.txt"
    decision_ledger_path = f"{config.notes_dir}/decision_ledger.jsonl"
    history_notes_result_path = f"{config.result_dir}/feedback/history_notes.jsonl"
    decision_ledger_result_path = f"{config.result_dir}/feedback/decision_ledger.jsonl"
    consultant_history_path = f"{config.result_dir}/feedback/consultant_history.jsonl"
    for path in [
        note_path,
        history_notes_path,
        decision_ledger_path,
        history_notes_result_path,
        decision_ledger_result_path,
        consultant_history_path,
    ]:
        with open(path, "w", encoding="utf-8"):
            pass
    with open(history_digest_path, "w", encoding="utf-8") as f:
        f.write("<empty>\n")

    consultant = TextGradConsultant(config=config, engine_name=args.engine)
    mcp_tools_text = fetch_mcp_tools_text()
    consultant_query = consultant.create_query(
        samples=None,
        id_col=None,
        background=background,
        label_col=None,
        include_feat_stats=True,
        background_only=False,
        include_samples=False,
        mcp_tools_text=mcp_tools_text,
        api_dir=config.api_dir,
        dataset_dir=config.dataset_dir,
    )
    consultant_output = consultant.generate(prompt=consultant_query)
    print("\n=== Consultant Output ===\n")
    print(consultant_output)
    print("\n=== End Consultant Output ===\n")
    task_summary = TextGradConsultant.parse_summary_tags(consultant_output)

    consultant_records: List[ConsultantPlanRecord] = []
    record_consultant_plan(
        consultant_records=consultant_records,
        path=consultant_history_path,
        record=ConsultantPlanRecord(
            step=-1,
            source="initial",
            task_description=task_summary["task_description"],
            suggestion=task_summary["suggestion"],
            prior_plan_json=task_summary["prior_plan"],
            raw_output=consultant_output,
            plan_fingerprint=plan_fingerprint(
                task_summary["task_description"],
                task_summary["suggestion"],
                task_summary["prior_plan"],
            ),
        ),
    )

    evaluator = TextGradEvaluator(
        config=config,
        engine_name=args.engine,
        task_decrp=task_summary["task_description"],
        background=background,
        eval_type="joint",
    )
    executor = CodeExecutor(config)

    outer_state = OuterLoopState()
    global_note_records: List[HistoryNoteRecord] = []
    decision_records: List[DecisionLedgerRecord] = []
    global_best = GlobalBestState()
    last_cluster_metrics: Dict[str, Any] = {}
    last_cluster_summary: Dict[str, Any] = {}
    suggestion = task_summary["suggestion"]
    bundle: PipelineBundle | None = None

    optimizer_constraints = [
        "Return ONLY one end-to-end valid, executable Python code named pipeline.py.",
    ]

    for step in range(config.opt_step + 1):
        step_start = time.perf_counter()
        config.set_step_output_paths(step)
        step_contract = build_step_run_contract(config, step, task_summary["prior_plan"])
        step_contract.write()
        component_contract = build_component_contract(config, task_summary["prior_plan"], step_contract)
        with open(step_contract.component_contract_path, "w", encoding="utf-8") as f:
            json.dump(component_contract, f, indent=2, ensure_ascii=False)

        generator = SingleScriptGenerator(config=config, engine_name=args.engine, results_path=config.model_perf_path)
        query = generator.create_query(
            task_descrp=task_summary["task_description"],
            data_summary=config.feat_stats,
            suggestion=suggestion,
            interface_contract=json.dumps(component_contract, ensure_ascii=False),
            script_summaries=generator.summarize_bundle(bundle) if bundle is not None else "<none>",
            background=background,
            mcp_tools_text=mcp_tools_text,
            api_dir=config.api_dir,
            dataset_dir=config.dataset_dir,
            preprocess_output_summary=step_contract.contract_path,
            cluster_metrics=json.dumps(last_cluster_metrics, ensure_ascii=False),
            cluster_summary=json.dumps(last_cluster_summary, ensure_ascii=False),
        )

        run_result: Dict[str, Any] = {}
        script_path = ""
        last_error_message = ""
        for attempt in range(config.max_fix_step + 1):
            if bundle is None:
                try:
                    if attempt == 0:
                        bundle = generator.generate_bundle(prompt=query)
                    else:
                        bundle = generator.regenerate_bundle(prompt=query, error=last_error_message or "Unknown bundle generation error")
                except BundleFormatError as exc:
                    last_error_message = str(exc)
                    if attempt == config.max_fix_step:
                        fail_with_message(config.result_dir, step, "generator", "InvalidSchema", str(exc), {"raw_response": exc.raw_response[:4000]})
                    print(f"fix_{attempt} (generator): {last_error_message}")
                    bundle = None
                    continue

            pre_run_failures = validate_bundle_contract(bundle, step_contract)
            if pre_run_failures:
                failure = pre_run_failures[0]
                last_error_message = format_failure_message(
                    stage=failure.stage,
                    error_type=failure.error_type,
                    message=failure.message,
                    details=failure.details,
                )
                if attempt == config.max_fix_step:
                    raise_on_failures(pre_run_failures, config.result_dir, step)
                target_stage = validation_failure_target(failure.to_dict())
                print(f"fix_{attempt} ({target_stage}): {last_error_message}")
                generator.fix_stage(bundle=bundle, failed_stage=target_stage, error=last_error_message, max_fix_step=1)
                continue

            script_path = generator.save_bundle(bundle, step_tag=f"step_{step}" if attempt == 0 else f"step_{step}_fix{attempt-1}")
            path_failures = validate_script_path(script_path, step_contract)
            if path_failures:
                failure = path_failures[0]
                last_error_message = format_failure_message(
                    stage=failure.stage,
                    error_type=failure.error_type,
                    message=failure.message,
                    details=failure.details,
                )
                if attempt == config.max_fix_step:
                    raise_on_failures(path_failures, config.result_dir, step)
                target_stage = validation_failure_target(failure.to_dict())
                print(f"fix_{attempt} ({target_stage}): {last_error_message}")
                generator.fix_stage(bundle=bundle, failed_stage=target_stage, error=last_error_message, max_fix_step=1)
                continue

            run_result = executor.run_bundle(script_path, contract=step_contract)
            if run_result.get("success", False):
                break

            failure_record = run_result.get("validation_failure")
            if failure_record:
                last_error_message = format_failure_message(
                    stage=str(failure_record.get("stage", "unknown")),
                    error_type=str(failure_record.get("error_type", "ValidationFailure")),
                    message=str(run_result.get("error", "Unknown error")),
                    details=failure_record.get("details", {}),
                )
                target_stage = validation_failure_target(failure_record)
            else:
                target_stage = str(run_result.get("failed_stage") or "pipeline")
                last_error_message = run_result.get("error", "Unknown error")

            if attempt == config.max_fix_step:
                if failure_record:
                    write_failure_record(f"{config.result_dir}/feedback/failure_step_{step}.json", failure_record)
                    raise RuntimeError(
                        f"[{failure_record.get('error_type', 'ValidationFailure')}] "
                        f"{failure_record.get('stage', 'unknown')}: {run_result.get('error', 'Unknown error')}"
                    )
                fail_with_message(config.result_dir, step, target_stage, "RuntimeError", last_error_message)

            print(f"fix_{attempt} ({target_stage}): {last_error_message}")
            generator.fix_stage(bundle=bundle, failed_stage=target_stage, error=last_error_message, max_fix_step=1)

        perf = read_perf(config.model_perf_path)
        pstat = perf_summary(perf)
        cluster_metrics, cluster_summary, training_logs, pipeline_summary = collect_eval_data(config, run_result)
        last_cluster_metrics = cluster_metrics
        last_cluster_summary = cluster_summary

        outer_state.best_ari, outer_state.best_sil, outer_state.stagnation_steps, primary_state = update_primary_metric_state(
            cluster_metrics=cluster_metrics,
            best_ari=outer_state.best_ari,
            best_sil=outer_state.best_sil,
            delta_min=args.delta_min,
            stagnation_steps=outer_state.stagnation_steps,
        )

        notes_text = build_history_digest(
            outer_notes=outer_state.note_records,
            global_notes=global_note_records,
            decision_records=decision_records,
            keep_last=20,
        )
        with open(history_digest_path, "w", encoding="utf-8") as f:
            f.write(notes_text + "\n")

        notes_var = tg.Variable(notes_text or "<empty>", requires_grad=False, role_description="multi-step notes")
        suggestion_var = tg.Variable(suggestion, requires_grad=False, role_description="current consultant suggestion")
        training_history_var = tg.Variable(
            json.dumps(perf.get("training_history", []), ensure_ascii=False),
            requires_grad=False,
            role_description="epoch-level training history",
        )
        stagnation_steps_var = tg.Variable(args.stagnation_steps_limit, requires_grad=False, role_description="stagnation step limit")
        delta_min_var = tg.Variable(str(args.delta_min), requires_grad=False, role_description="minimum meaningful validation gain")
        current_performance_var = tg.Variable(
            json.dumps({"perf_summary": pstat, "primary_state": primary_state}, ensure_ascii=False),
            requires_grad=False,
            role_description="current performance summary",
        )
        interface_contract_var = tg.Variable(
            json.dumps(component_contract, ensure_ascii=False),
            requires_grad=False,
            role_description="single-script interface contract",
        )
        context_mode_var = tg.Variable("full", requires_grad=False, role_description="context packet mode")
        cluster_metrics_var = tg.Variable(json.dumps(cluster_metrics, ensure_ascii=False), requires_grad=False, role_description="cluster metrics")
        cluster_summary_var = tg.Variable(json.dumps(cluster_summary, ensure_ascii=False), requires_grad=False, role_description="cluster summary")
        training_logs_var = tg.Variable(json.dumps(training_logs, ensure_ascii=False), requires_grad=False, role_description="training logs")
        pipeline_summary_var = tg.Variable(json.dumps(pipeline_summary, ensure_ascii=False), requires_grad=False, role_description="pipeline summary")

        eval_out = evaluator.loss_fn(
            notes=notes_var,
            step=step,
            pipeline_code=bundle.pipeline_code,
            suggestion=suggestion_var,
            training_history=training_history_var,
            stagnation_steps=stagnation_steps_var,
            delta_min=delta_min_var,
            current_performance=current_performance_var,
            interface_contract=interface_contract_var,
            context_mode=context_mode_var,
            cluster_metrics=cluster_metrics_var,
            cluster_summary=cluster_summary_var,
            training_logs=training_logs_var,
            pipeline_summary=pipeline_summary_var,
        )

        print(f"\n=== Evaluator Output (Step {step}) ===\n")
        print(eval_out.value)
        print(f"\n=== End Evaluator Output (Step {step}) ===\n")
        action, payload, feedback = parse_eval_action(eval_out.value)
        print(f"Evaluator action at step {step}: {action}")
        exploit_plan = exploit_plan_from_feedback(feedback)
        diagnosis = exploit_plan.get("diagnosis", "")
        strategy = exploit_plan.get("strategy", "")
        expected_effect = exploit_plan.get("expected_metric_effect", "")
        focus_areas = exploit_plan.get("focus_areas", []) if action == "exploit" else []
        bottleneck_reason = exploit_plan.get("bottleneck_reason", "") if action == "exploit" else ""
        keep_fixed = exploit_plan.get("keep_fixed", []) if action == "exploit" else []
        change_next = exploit_plan.get("change_next", []) if action == "exploit" else []
        optimized_sections = ["pipeline"] if action == "exploit" and (keep_fixed or change_next) else []
        exploit_applied = False
        exploit_change_types: Dict[str, str] = {}
        exploit_summary: Dict[str, str] = {}
        critique_payloads: Dict[str, Dict[str, Any]] = {}

        if action == "exploit" and optimized_sections:
            exploit_optimizer = tg.TextualGradientDescent(
                engine=global_engine,
                parameters=[bundle.pipeline_code],
                constraints=optimizer_constraints,
            )
            exploit_optimizer.zero_grad()
            exploit_change_types, exploit_summary, critique_payloads = attach_exploit_signal_and_metadata(
                pipeline_var=bundle.pipeline_code,
                keep_fixed=keep_fixed,
                change_next=change_next,
                diagnosis=diagnosis,
                strategy=strategy,
                expected_effect=expected_effect,
                current_performance_text=current_performance_var.value,
                focus_areas=focus_areas,
                bottleneck_reason=bottleneck_reason,
                dataset_dir=config.dataset_dir,
            )
            exploit_optimizer.step()
            exploit_applied = True
            gradient_text = critique_payloads.get("pipeline", {}).get("gradient_text", "")
            if gradient_text:
                print(f"\n=== Code Gradient (Step {step}) ===\n")
                print(gradient_text)
                print(f"\n=== End Code Gradient (Step {step}) ===\n")

        step_log = {
            "step": step,
            "context_mode": "full",
            "action": action,
            "payload": payload,
            "feedback": feedback,
            "exploit_plan": exploit_plan,
            "run_success": run_result.get("success", False),
            "failed_stage": run_result.get("failed_stage"),
            "validation_failure": run_result.get("validation_failure"),
            "performance": perf,
            "cluster_metrics": cluster_metrics,
            "cluster_summary": cluster_summary,
            "training_logs": training_logs,
            "pipeline_summary": pipeline_summary,
            "script_path": script_path,
            "primary_state": primary_state,
            "exploit_applied": exploit_applied,
            "optimized_targets": optimized_sections,
            "exploit_change_types": exploit_change_types,
            "critique_payloads": critique_payloads,
        }
        with open(f"{config.result_dir}/feedback/single_feedback_step_{step}.json", "w", encoding="utf-8") as f:
            json.dump(step_log, f, indent=2, ensure_ascii=False)

        open_issues = build_open_issues(run_result=run_result, primary_state=primary_state, payload=payload, feedback=feedback)
        attempts_used = attempt
        current_metric_value = metric_from_dict(cluster_metrics, ["ari", "ARI"])
        primary_gain = to_float(primary_state.get("primary_metric_gain"))
        architecture_fingerprint, design_summary = infer_design_identity(
            bundle_text=bundle.as_text_dict(),
            payload=payload,
            cluster_summary=cluster_summary,
        )
        failure_phase, failure_fingerprint, root_cause = classify_run_failure(run_result)
        architecture_info = payload.get("architecture", {}) if isinstance(payload, dict) else {}
        repetition_reason = ""
        if isinstance(architecture_info, dict):
            repetition_reason = str(architecture_info.get("repetition_penalty_reason") or "").strip()
        do_not_repeat = bool(action == "reconsult" or repetition_reason)
        do_not_repeat_reason = repetition_reason or str(payload.get("primary_reason") or diagnosis or "").strip() or "Current architecture was ruled out after evaluation"
        decision_rationale = str(payload.get("primary_reason") or feedback.get("strategy") or diagnosis or "").strip() or "No explicit rationale provided"
        decision_result = classify_decision_result(
            run_success=bool(run_result.get("success", False)),
            primary_gain=primary_gain,
            metric_value=current_metric_value,
        )
        failed_architectures = feedback.get("failed_architectures", []) if isinstance(feedback, dict) else []
        if isinstance(failed_architectures, str):
            failed_architectures = [failed_architectures]
        elif not isinstance(failed_architectures, list):
            failed_architectures = []
        prev_exploit_context = previous_exploit_context(global_note_records)
        note_record = HistoryNoteRecord(
            step=step,
            action=action,
            context_mode="full",
            attempts_used=attempts_used,
            run_success=bool(run_result.get("success", False)),
            failed_stage=run_result.get("failed_stage"),
            architecture_fingerprint=architecture_fingerprint,
            design_summary=design_summary,
            decision_rationale=decision_rationale,
            primary_metric="ari",
            metric_value=current_metric_value,
            gain=primary_gain,
            stagnation=outer_state.stagnation_steps,
            failure_phase=failure_phase,
            failure_fingerprint=failure_fingerprint,
            root_cause=root_cause,
            fix_outcome=summarize_fix_outcome(attempts_used, bool(run_result.get("success", False))),
            evaluator_diagnosis=diagnosis,
            script_plan=exploit_plan,
            open_issues=open_issues,
            exploit_applied=exploit_applied,
            optimized_scripts=optimized_sections,
            exploit_change_types=exploit_change_types,
            exploit_summary=exploit_summary,
            previous_exploit_context=prev_exploit_context,
            do_not_repeat=do_not_repeat,
            do_not_repeat_reason=do_not_repeat_reason,
        )
        append_history_note(
            note_record,
            outer_notes=outer_state.note_records,
            global_notes=global_note_records,
            note_text_path=note_path,
            note_jsonl_path=history_notes_path,
            mirror_jsonl_path=history_notes_result_path,
        )
        append_decision_record(
            DecisionLedgerRecord(
                step=step,
                architecture_fingerprint=architecture_fingerprint,
                design_summary=design_summary,
                decision_rationale=decision_rationale,
                primary_metric="ari",
                metric_value=current_metric_value,
                metric_gain=primary_gain,
                result=decision_result,
                action=action,
                failed_stage=run_result.get("failed_stage"),
                failure_fingerprint=failure_fingerprint,
                do_not_repeat=do_not_repeat,
                do_not_repeat_reason=do_not_repeat_reason,
                exploit_applied=exploit_applied,
                optimized_scripts=optimized_sections,
                exploit_change_types=exploit_change_types,
                exploit_summary=exploit_summary,
                rejected_design_labels=[str(item) for item in failed_architectures if str(item).strip()],
            ),
            decision_records=decision_records,
            decision_jsonl_path=decision_ledger_path,
            mirror_jsonl_path=decision_ledger_result_path,
        )

        maybe_update_global_best(
            global_best=global_best,
            run_success=bool(run_result.get("success", False)),
            step=step,
            cluster_metrics=cluster_metrics,
            perf=perf,
            bundle=bundle,
            generator=generator,
            final_out_dir=config.final_out_dir,
        )

        if action == "reconsult":
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
                "failure_fingerprint": failure_fingerprint,
                "history_digest": notes_text,
            }
            historical_failures = "\n".join(open_issues[-10:]) if open_issues else "<none>"
            consultant_history_context = build_consultant_history_context(consultant_records)
            reconsult_query = build_reconsult_query(
                task_description=task_summary["task_description"],
                background=background,
                current_suggestion=suggestion,
                current_prior_plan=task_summary["prior_plan"],
                current_attempt=current_attempt,
                why_current_fails=why_current_fails,
                historical_failures=historical_failures,
                hard_constraints=optimizer_constraints,
                history_digest=notes_text,
                consultant_history_context=consultant_history_context,
            )
            reconsult_output = consultant.generate(prompt=reconsult_query)
            print(f"\n=== Reconsult Consultant Output (Step {step}) ===\n")
            print(reconsult_output)
            print(f"\n=== End Reconsult Consultant Output (Step {step}) ===\n")
            task_summary = TextGradConsultant.parse_summary_tags(reconsult_output)
            suggestion = task_summary["suggestion"]
            record_consultant_plan(
                consultant_records=consultant_records,
                path=consultant_history_path,
                record=ConsultantPlanRecord(
                    step=step,
                    source="reconsult",
                    task_description=task_summary["task_description"],
                    suggestion=task_summary["suggestion"],
                    prior_plan_json=task_summary["prior_plan"],
                    raw_output=reconsult_output,
                    plan_fingerprint=plan_fingerprint(
                        task_summary["task_description"],
                        task_summary["suggestion"],
                        task_summary["prior_plan"],
                    ),
                ),
            )
            evaluator = TextGradEvaluator(
                config=config,
                engine_name=args.engine,
                task_decrp=task_summary["task_description"],
                background=background,
                eval_type="joint",
            )
            outer_state.reset()
            bundle = None

        elapsed = time.perf_counter() - step_start
        print(f"Step {step} elapsed: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
