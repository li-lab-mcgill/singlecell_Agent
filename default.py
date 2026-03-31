import argparse
import json
import os
import shutil
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
    critic_plan_from_payload,
    TextGradEvaluator,
    build_instruction_text,
    build_open_issues,
    parse_critic_output,
    parse_evaluator_message,
    to_float,
    update_primary_metric_state,
)
from executor import CodeExecutor
from generator import StageScriptGenerator
from hist_notebook import (
    ScriptNotebook,
    append_decision_record,
    append_history_note,
    append_script_note_record,
    build_code_diff,
    build_current_diffs_payload,
    build_history_digest,
    build_missing_code_note,
    build_script_notes_history,
    infer_design_identity,
)
from mcp_utils import fetch_mcp_tools_text
from multieval_types import (
    ConsultantPlanRecord,
    DecisionLedgerRecord,
    GlobalBestState,
    HistoryNoteRecord,
    OuterLoopState,
    ScriptNoteRecord,
    STAGE_FILENAMES,
)
from validator import write_failure_record


def read_json_safe(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_text_safe(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def read_perf(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {
            "train_performance": 0.0,
            "val_performance": 0.0,
            "test_performance": 0.0,
            "best_model": "Unavailable",
            "training_history": [],
        }
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def perf_summary(perf: Dict[str, Any]) -> str:
    return (
        f"Current train_performance: {round(float(perf.get('train_performance', 0.0) or 0.0), 4)}\n"
        f"Current val_performance: {round(float(perf.get('val_performance', 0.0) or 0.0), 4)}\n"
        f"Current test_performance: {round(float(perf.get('test_performance', 0.0) or 0.0), 4)}\n"
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


def stage_schemas_from_config(config: Config) -> Dict[str, Dict[str, Any]]:
    return {filename: config.stage_requirements(filename) for filename in STAGE_FILENAMES}


def collect_eval_data(resolved_artifact_layout: Dict[str, Any], run_result: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    outputs = resolved_artifact_layout.get("generated_outputs", {})
    return (
        run_result.get("cluster_metrics") if isinstance(run_result.get("cluster_metrics"), dict) else read_json_safe(str(outputs.get("cluster_metrics", ""))),
        run_result.get("cluster_summary") if isinstance(run_result.get("cluster_summary"), dict) else read_json_safe(str(outputs.get("cluster_summary", ""))),
        run_result.get("training_logs") if isinstance(run_result.get("training_logs"), dict) else read_json_safe(str(outputs.get("training_logs", ""))),
        run_result.get("pipeline_summary") if isinstance(run_result.get("pipeline_summary"), dict) else read_json_safe(str(outputs.get("pipeline_summary", ""))),
    )


def bundle_text_map(code_bundle: Dict[str, tg.Variable]) -> Dict[str, str]:
    return {filename: code_bundle[filename].value for filename in STAGE_FILENAMES if filename in code_bundle}


def bundle_text_map_from_dir(script_dir: str) -> Dict[str, str]:
    if not script_dir or not os.path.isdir(script_dir):
        return {}
    return {filename: read_text_safe(os.path.join(script_dir, filename)) for filename in STAGE_FILENAMES}


def classify_run_failure(run_result: Dict[str, Any]) -> tuple[str | None, str | None, str]:
    if run_result.get("success", False):
        return None, None, ""
    failure = run_result.get("validation_failure")
    if isinstance(failure, dict):
        target = str(failure.get("target") or "unknown")
        message = str(failure.get("message") or run_result.get("error") or "Unknown validation error")
        return "validate", f"validate:{target}", message
    target = str(run_result.get("failed_script") or STAGE_FILENAMES[0])
    message = str(run_result.get("error") or "Unknown runtime error")
    return "execute", f"execute:{target}", message


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


def _graph_text_var(text: str, predecessors: List[tg.Variable], role_description: str) -> tg.Variable:
    var = tg.Variable(text, requires_grad=False, role_description=role_description)
    for predecessor in predecessors:
        var.predecessors.add(predecessor)
    return var


def _wire_stage_dependencies(code_bundle: Dict[str, tg.Variable]) -> None:
    prior_code = code_bundle["prior_construction.py"]
    data_code = code_bundle["data_preprocess.py"]
    model_code = code_bundle["model_training.py"]
    downstream_code = code_bundle["downstream_analysis.py"]

    data_code.predecessors.add(prior_code)

    model_code.predecessors.add(prior_code)
    model_code.predecessors.add(data_code)

    downstream_code.predecessors.add(prior_code)
    downstream_code.predecessors.add(data_code)
    downstream_code.predecessors.add(model_code)


def _non_negotiable_constraints() -> List[str]:
    return [
        "Do not use argparse, sys.argv, command-line flags, input prompts, or any CLI path interface.",
        "Do not use ./outputs, outputs_dir, output_root, SC_AGENT_OUTPUT_DIR, SC_AGENT_DATASETS_DIR, or any environment variable for path resolution.",
        "Use only the fixed config-owned artifact paths already bound in the code.",
    ]


def _prior_resource_paths(config: Config) -> List[str]:
    dataset_dir = getattr(config, "dataset_dir", "") or ""
    if not dataset_dir:
        return []
    return [
        os.path.join(dataset_dir, name)
        for name in ["MsigDB.csv", "NeST.tsv", "GO_terms.csv", "Cell_marker_Human.xlsx", "meta_info.csv"]
    ]


def _resolved_prior_file_constraints(config: Config) -> List[str]:
    constraints: List[str] = []
    for item in config.resolved_prior_files():
        artifact_key = str(item.get("artifact_key") or "").strip()
        path = str(item.get("path") or "").strip()
        fmt = str(item.get("format") or "").strip()
        role = str(item.get("description") or item.get("role") or "").strip()
        if not role and fmt == "csv":
            cols = item.get("required_columns", [])
            if isinstance(cols, list) and cols:
                role = f"CSV with required columns: {', '.join(str(col) for col in cols)}"
        if not role and fmt == "json":
            keys = item.get("required_keys", [])
            if isinstance(keys, list) and keys:
                role = f"JSON with required keys: {', '.join(str(key) for key in keys)}"
        base = f"Prior artifact {artifact_key}: path={path}; format={fmt}"
        constraints.append(f"{base}; description={role}" if role else base)
    return constraints


def _artifact_path_descriptions() -> Dict[str, str]:
    return {
        "input_mod1_path": "Input modality 1 dataset file",
        "input_mod2_path": "Input modality 2 dataset file",
        "preprocess_metadata_path": "Preprocessing metadata JSON",
        "preprocess_train_mod1_path": "Input training split h5ad",
        "preprocess_val_mod1_path": "Input validation split h5ad",
        "preprocess_test_mod1_path": "Input test split h5ad",
        "prior_output_dir_path": "Input prior artifact directory",
        "model_performance_path": "Output model performance JSON",
        "best_model_path": "Output best-model checkpoint file",
        "embedding_path": "Output embedding NPY file",
        "embedding_metadata_path": "Output embedding metadata CSV",
        "training_logs_path": "Output training logs JSON",
        "pipeline_summary_path": "Output pipeline summary JSON",
        "cluster_assignments_path": "Output cluster assignments CSV",
        "cluster_metrics_path": "Output cluster metrics JSON",
        "cluster_summary_path": "Output cluster summary JSON",
    }


def _path_constraint_line(key: str, value: str) -> str:
    label = _artifact_path_descriptions().get(key, key)
    return f"{label}: use exactly this fixed path -> {value}"


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _feedback_has_signal(feedback: str) -> bool:
    return bool(str(feedback or "").strip())


def _build_optimizer_constraints_for_file(filename: str, path_fields: Dict[str, str], stage_schema: Dict[str, Any], config: Config) -> List[str]:
    constraints = [f"Return ONLY valid executable Python code for {filename}."]
    constraints.extend(_non_negotiable_constraints())
    if filename == "prior_construction.py":
        constraints.append(f"Current consultant prior schema JSON: {json.dumps(config.current_prior_schema, ensure_ascii=False)}")
        for key in ["input_mod1_path", "input_mod2_path", "prior_output_dir_path"]:
            value = path_fields.get(key, "")
            if str(value).strip():
                constraints.append(_path_constraint_line(key, value))
        constraints.extend(_resolved_prior_file_constraints(config))
        for resource_path in _prior_resource_paths(config):
            constraints.append(f"Prior resource path: {resource_path}")
        return constraints

    if filename == "data_preprocess.py":
        constraints.append(f"Current consultant prior schema JSON: {json.dumps(config.current_prior_schema, ensure_ascii=False)}")
        for key in ["input_mod1_path", "input_mod2_path", "preprocess_metadata_path", "preprocess_train_mod1_path", "preprocess_val_mod1_path", "preprocess_test_mod1_path", "prior_output_dir_path"]:
            value = path_fields.get(key, "")
            if str(value).strip():
                constraints.append(_path_constraint_line(key, value))
        constraints.extend(_resolved_prior_file_constraints(config))
        return constraints

    constraints.append(f"Current stage requirements JSON: {json.dumps(stage_schema, ensure_ascii=False)}")
    if filename == "model_training.py":
        constraints.append(f"Current consultant prior schema JSON: {json.dumps(config.current_prior_schema, ensure_ascii=False)}")
        for key in ["preprocess_metadata_path", "preprocess_train_mod1_path", "preprocess_val_mod1_path", "preprocess_test_mod1_path", "prior_output_dir_path", "model_performance_path", "best_model_path", "embedding_path", "embedding_metadata_path", "training_logs_path", "pipeline_summary_path"]:
            value = path_fields.get(key, "")
            if str(value).strip():
                constraints.append(_path_constraint_line(key, value))
        constraints.extend(_resolved_prior_file_constraints(config))
        return constraints

    if filename == "downstream_analysis.py":
        for key in ["input_mod1_path", "input_mod2_path", "preprocess_metadata_path", "preprocess_train_mod1_path", "preprocess_val_mod1_path", "preprocess_test_mod1_path", "model_performance_path", "embedding_path", "embedding_metadata_path", "pipeline_summary_path", "cluster_assignments_path", "cluster_metrics_path", "cluster_summary_path"]:
            value = path_fields.get(key, "")
            if str(value).strip():
                constraints.append(_path_constraint_line(key, value))
        return constraints

    return constraints


def maybe_update_global_best(*, global_best: GlobalBestState, run_success: bool, step: int, cluster_metrics: Dict[str, Any], perf: Dict[str, Any], executed_script_dir: str, best_script_dir: str, final_out_dir: str) -> GlobalBestState:
    if not run_success:
        return global_best
    cur_ari = metric_from_dict(cluster_metrics, ["ari", "ARI"])
    if cur_ari is None:
        return global_best
    if global_best.best_ari is not None and cur_ari < global_best.best_ari:
        return global_best
    if not executed_script_dir or not os.path.isdir(executed_script_dir):
        raise FileNotFoundError(f"Executed script directory is missing: {executed_script_dir}")
    shutil.rmtree(best_script_dir, ignore_errors=True)
    shutil.copytree(executed_script_dir, best_script_dir)
    global_best.best_ari = cur_ari
    global_best.best_step = step
    global_best.best_script_path = best_script_dir
    global_best.best_perf = perf if isinstance(perf, dict) else {}
    global_best.best_cluster_metrics = cluster_metrics if isinstance(cluster_metrics, dict) else {}
    with open(f"{final_out_dir}/global_best_ari.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "best_step": global_best.best_step,
                "best_ari": global_best.best_ari,
                "best_script_path": global_best.best_script_path,
                "best_cluster_metrics": global_best.best_cluster_metrics,
                "best_perf": global_best.best_perf,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    return global_best


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
    parser.add_argument("--artifact-layout", default="artifact_layout.json")
    parser.add_argument("--opt-step", type=int, default=5)
    parser.add_argument("--max-fix-step", type=int, default=3)
    parser.add_argument("--time-budget", type=int, default=3600)
    parser.add_argument("--delta-min", type=float, default=0.005)
    parser.add_argument("--stagnation_steps_limit", type=int, default=5)
    args = parser.parse_args()

    file_path = args.input_mod1 or f"{cur_path}/data/h5ad/pbmc3k_annotated.h5ad"
    mod2_path = args.input_mod2
    background = f"""
Data file: Modality 1: {file_path}
Data file: Modality 2: {mod2_path if mod2_path else "None"}
DATA: Sparse, high-dimensional gene expression counts.
Each row represents a cell and each column represents a gene.

TASK:
Develop a prior guided unsupervised deep learning Python pipeline for single-cell RNA-seq representation learning.

The pipeline MUST:
1. Use four executable scripts: prior_construction.py, data_preprocess.py, model_training.py, and downstream_analysis.py.
2. prior_construction.py builds the fixed prior bundle first.
3. data_preprocess.py performs preprocessing and consumes prior_construction.py outputs.
4. model_training.py consumes data_preprocess outputs and prior outputs.
5. downstream_analysis.py consumes outputs from all earlier scripts.
6. All scripts must use fixed config-owned artifact paths.

VISUALIZATION:
Generate UMAP from the learned embedding colored by predicted cluster and by cell_type if available.

EVALUATION:
Primary evaluation metric: ARI.
Use labels only for evaluation, never for training.
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
    config.prior_resource_summary = config.summarize_prior_resources()
    config.artifact_layout_path = args.artifact_layout if os.path.isabs(args.artifact_layout) else f"{cur_path}/{args.artifact_layout}"
    config.notes_dir = f"{cur_path}/{args.notes_dir}"
    config.code_dir = config.single_code_dir
    resolved_artifact_layout = config.set_step_output_paths(0)
    consultant_background = (
        background.strip()
        + "\n\nFixed downstream output requirements:\n"
        + json.dumps(config.downstream_requirements(), indent=2, ensure_ascii=False)
    )

    Path(config.notes_dir).mkdir(parents=True, exist_ok=True)
    Path(config.code_dir).mkdir(parents=True, exist_ok=True)
    Path(config.result_dir).mkdir(parents=True, exist_ok=True)
    Path(f"{config.result_dir}/feedback").mkdir(parents=True, exist_ok=True)

    note_path = f"{config.notes_dir}/note_history.txt"
    history_notes_path = f"{config.notes_dir}/history_notes.jsonl"
    history_digest_path = f"{config.notes_dir}/history_digest.txt"
    decision_ledger_path = f"{config.notes_dir}/decision_ledger.jsonl"
    history_notes_result_path = f"{config.result_dir}/feedback/history_notes.jsonl"
    decision_ledger_result_path = f"{config.result_dir}/feedback/decision_ledger.jsonl"
    consultant_history_path = f"{config.result_dir}/feedback/consultant_history.jsonl"
    prior_consultant_history_path = f"{config.result_dir}/feedback/prior_consultant_history.jsonl"
    script_note_paths = {
        filename: f"{config.notes_dir}/{filename.replace('.py', '')}_notes.jsonl"
        for filename in STAGE_FILENAMES
    }
    script_note_result_paths = {
        filename: f"{config.result_dir}/feedback/{filename.replace('.py', '')}_notes.jsonl"
        for filename in STAGE_FILENAMES
    }
    for path in [note_path, history_notes_path, decision_ledger_path, history_notes_result_path, decision_ledger_result_path, consultant_history_path, prior_consultant_history_path]:
        with open(path, "w", encoding="utf-8"):
            pass
    for path in list(script_note_paths.values()) + list(script_note_result_paths.values()):
        with open(path, "w", encoding="utf-8"):
            pass
    with open(history_digest_path, "w", encoding="utf-8") as f:
        f.write("<empty>\n")

    prior_consultant = TextGradConsultant(config=config, engine_name=args.engine, consultant_type="prior")
    consultant = TextGradConsultant(config=config, engine_name=args.engine, consultant_type="main")
    mcp_tools_text = fetch_mcp_tools_text()
    print(f"data_summary:\n{config.feat_stats}")
    print(f"prior_resource_summary:\n{config.prior_resource_summary}")
    prior_consultant_query = prior_consultant.create_query(
        samples=None,
        id_col=None,
        background=consultant_background,
        label_col=None,
        include_feat_stats=True,
        background_only=False,
        include_samples=False,
        mcp_tools_text=mcp_tools_text,
        api_dir=config.api_dir,
        dataset_dir=config.dataset_dir,
    )
    prior_consultant_output = prior_consultant.generate(prompt=prior_consultant_query)
    print(f"prior_consultant_output:\n{prior_consultant_output}")
    prior_task_summary = TextGradConsultant.parse_prior_summary_tags(prior_consultant_output)
    config.apply_prior_schema(prior_task_summary["prior_schema"])

    prior_consultant_records: List[ConsultantPlanRecord] = []
    record_consultant_plan(
        consultant_records=prior_consultant_records,
        path=prior_consultant_history_path,
        record=ConsultantPlanRecord(
            step=-1,
            source="initial",
            task_description=prior_task_summary["task_description"],
            suggestion=prior_task_summary["suggestion"],
            prior_schema_json=prior_task_summary["prior_schema"],
            raw_output=prior_consultant_output,
            plan_fingerprint=plan_fingerprint(prior_task_summary["task_description"], prior_task_summary["suggestion"], prior_task_summary["prior_schema"]),
        ),
    )

    consultant_query = consultant.create_query(
        samples=None,
        id_col=None,
        background=consultant_background,
        label_col=None,
        include_feat_stats=True,
        background_only=False,
        include_samples=False,
        mcp_tools_text=mcp_tools_text,
        api_dir=config.api_dir,
        dataset_dir=config.dataset_dir,
        prior_plan=prior_task_summary["suggestion"],
        prior_output_summary=json.dumps(prior_task_summary["prior_schema"], ensure_ascii=False),
    )
    consultant_output = consultant.generate(prompt=consultant_query)
    print(f"consultant_output:\n{consultant_output}")
    task_summary = TextGradConsultant.parse_main_summary_tags(consultant_output)

    consultant_records: List[ConsultantPlanRecord] = []
    record_consultant_plan(
        consultant_records=consultant_records,
        path=consultant_history_path,
        record=ConsultantPlanRecord(
            step=-1,
            source="initial",
            task_description=task_summary["task_description"],
            suggestion=task_summary["suggestion"],
            prior_schema_json={},
            raw_output=consultant_output,
            plan_fingerprint=plan_fingerprint(task_summary["task_description"], task_summary["suggestion"], {}),
        ),
    )

    prior_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="prior")
    model_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="model")
    data_science_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="data_science")
    biology_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="biology")
    critic_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="critic")
    script_notebook = ScriptNotebook(engine_name=args.engine, task_description=task_summary["task_description"])
    executor = CodeExecutor(config)
    outer_state = OuterLoopState()
    global_note_records: List[HistoryNoteRecord] = []
    decision_records: List[DecisionLedgerRecord] = []
    global_best = GlobalBestState()
    last_cluster_metrics: Dict[str, Any] = {}
    prior_suggestion = prior_task_summary["suggestion"]
    suggestion = task_summary["suggestion"]
    code_bundle: Dict[str, tg.Variable] | None = None
    optimizers: Dict[str, tg.TextualGradientDescent] = {}
    script_note_records: Dict[str, List[ScriptNoteRecord]] = {filename: [] for filename in STAGE_FILENAMES}
    previous_step_bundle_texts: Dict[str, str] = {}
    applied_change_contexts: Dict[str, str] = {filename: "initial generation" for filename in STAGE_FILENAMES}

    for step in range(config.opt_step + 1):
        step_start = time.perf_counter()
        resolved_artifact_layout = config.set_step_output_paths(step)
        generator = StageScriptGenerator(config=config, engine_name=args.engine)
        stage_schemas = stage_schemas_from_config(config)

        if code_bundle is None:
            code_bundle = generator.generate_bundle(
                task_description=task_summary["task_description"],
                background=background,
                main_plan=suggestion,
                prior_plan=prior_suggestion,
                data_summary=config.feat_stats,
                prior_resource_summary=config.prior_resource_summary,
                script_summaries=StageScriptGenerator.summarize_bundle(None),
                mcp_tools_text=mcp_tools_text,
                api_dir=config.api_dir,
                dataset_dir=config.dataset_dir,
            )
            _wire_stage_dependencies(code_bundle)
            optimizer_constraints = {
                filename: _build_optimizer_constraints_for_file(filename, generator.path_prompt_fields, stage_schemas.get(filename, {}), config)
                for filename in STAGE_FILENAMES
            }
            optimizers = {
                filename: tg.TextualGradientDescent(engine=global_engine, parameters=[code_bundle[filename]], constraints=optimizer_constraints[filename])
                for filename in STAGE_FILENAMES
            }

        run_result: Dict[str, Any] = {}
        script_dir = ""
        last_error_message = ""
        start_from = STAGE_FILENAMES[0]
        for attempt in range(config.max_fix_step + 1):
            script_dir = generator.save_bundle(code_bundle, step_tag=f"step_{step}")
            run_result = executor.run_bundle(script_dir, resolved_artifact_layout=resolved_artifact_layout, stage_schemas=stage_schemas, start_from=start_from)
            if run_result.get("success", False):
                break
            target = str((run_result.get("validation_failure") or {}).get("target") or run_result.get("failed_script") or STAGE_FILENAMES[0])
            last_error_message = run_result.get("error", "Unknown error")
            if attempt == config.max_fix_step:
                payload = run_result.get("validation_failure") or {"target": target, "error_type": "RuntimeError", "message": last_error_message, "details": {}}
                write_failure_record(f"{config.result_dir}/feedback/failure_step_{step}.json", payload)
                raise RuntimeError(f"[{payload.get('error_type', 'RuntimeError')}] {target}: {last_error_message}")
            print(f"fix_{attempt}: {last_error_message}")
            generator.fix_target(
                code_bundle=code_bundle,
                target=target,
                error=last_error_message,
                task_description=task_summary["task_description"],
                main_plan=suggestion,
                prior_plan=prior_suggestion,
                max_fix_step=1,
            )
            start_from = target

        perf = read_perf(str(resolved_artifact_layout["generated_outputs"].get("model_performance", "")))
        pstat = perf_summary(perf)
        cluster_metrics, cluster_summary, training_logs, pipeline_summary = collect_eval_data(resolved_artifact_layout, run_result)
        preprocess_metadata = read_json_safe(str(resolved_artifact_layout["generated_outputs"].get("preprocess_metadata", "")))
        last_cluster_metrics = cluster_metrics

        outer_state.best_ari, outer_state.best_sil, outer_state.stagnation_steps, primary_state = update_primary_metric_state(
            cluster_metrics=cluster_metrics,
            best_ari=outer_state.best_ari,
            best_sil=outer_state.best_sil,
            delta_min=args.delta_min,
            stagnation_steps=outer_state.stagnation_steps,
        )
        current_metric_value = metric_from_dict(cluster_metrics, ["ari", "ARI"])
        primary_gain = to_float(primary_state.get("primary_metric_gain"))
        current_bundle_texts = bundle_text_map(code_bundle)
        best_bundle_texts = bundle_text_map_from_dir(global_best.best_script_path)
        script_notes_history = {
            filename: build_script_notes_history(script_note_records[filename], current_step=step)
            for filename in STAGE_FILENAMES
        }
        script_current_diffs: Dict[str, str] = {}
        script_prev_diffs: Dict[str, str] = {}
        script_best_diffs: Dict[str, str] = {}
        for filename in STAGE_FILENAMES:
            current_text = current_bundle_texts.get(filename, "")
            prev_text = previous_step_bundle_texts.get(filename)
            best_text = best_bundle_texts.get(filename)
            current_vs_prev_diff = (
                build_code_diff(
                    prev_text,
                    current_text,
                    from_label=f"step_{step-1}:{filename}",
                    to_label=f"step_{step}:{filename}",
                )
                if prev_text is not None
                else build_missing_code_note(f"no previous version for step_{step}:{filename}")
            )
            current_vs_best_diff = (
                build_code_diff(
                    best_text,
                    current_text,
                    from_label=f"best_step:{filename}",
                    to_label=f"step_{step}:{filename}",
                )
                if best_text is not None
                else build_missing_code_note(f"no best-step version for {filename}")
            )
            script_prev_diffs[filename] = current_vs_prev_diff
            script_best_diffs[filename] = current_vs_best_diff
            script_current_diffs[filename] = build_current_diffs_payload(
                step=step,
                script=filename,
                optimization_text=applied_change_contexts.get(filename, "not optimized this step"),
                current_vs_prev_diff=current_vs_prev_diff,
                current_vs_best_diff=current_vs_best_diff,
                metric_value=current_metric_value,
                gain=primary_gain,
            )
        script_note_texts = {
            "prior_construction.py": script_notebook.create_note(
                script="prior_construction.py",
                cur_code=current_bundle_texts.get("prior_construction.py", ""),
                cur_step=step,
                prev_code=previous_step_bundle_texts.get("prior_construction.py", ""),
                prev_step=step - 1 if previous_step_bundle_texts.get("prior_construction.py") is not None else None,
                optimization_text=applied_change_contexts.get("prior_construction.py", "not optimized this step"),
                current_vs_prev_diff=script_prev_diffs.get("prior_construction.py", "N/A"),
                metric_name=config.metrics,
                metric_value=current_metric_value,
                gain=primary_gain,
                observed_outputs={
                    "prior_schema": config.current_prior_schema,
                    "prior_files": config.resolved_prior_files(),
                    "prior_resource_summary": config.prior_resource_summary,
                },
            ),
            "data_preprocess.py": script_notebook.create_note(
                script="data_preprocess.py",
                cur_code=current_bundle_texts.get("data_preprocess.py", ""),
                cur_step=step,
                prev_code=previous_step_bundle_texts.get("data_preprocess.py", ""),
                prev_step=step - 1 if previous_step_bundle_texts.get("data_preprocess.py") is not None else None,
                optimization_text=applied_change_contexts.get("data_preprocess.py", "not optimized this step"),
                current_vs_prev_diff=script_prev_diffs.get("data_preprocess.py", "N/A"),
                metric_name=config.metrics,
                metric_value=current_metric_value,
                gain=primary_gain,
                observed_outputs={
                    "preprocess_metadata": preprocess_metadata,
                    "pipeline_summary": pipeline_summary,
                    "data_schema": config.stage_requirements("data_preprocess.py"),
                },
            ),
            "model_training.py": script_notebook.create_note(
                script="model_training.py",
                cur_code=current_bundle_texts.get("model_training.py", ""),
                cur_step=step,
                prev_code=previous_step_bundle_texts.get("model_training.py", ""),
                prev_step=step - 1 if previous_step_bundle_texts.get("model_training.py") is not None else None,
                optimization_text=applied_change_contexts.get("model_training.py", "not optimized this step"),
                current_vs_prev_diff=script_prev_diffs.get("model_training.py", "N/A"),
                metric_name=config.metrics,
                metric_value=current_metric_value,
                gain=primary_gain,
                observed_outputs={
                    "current_performance": {"perf_summary": pstat, "primary_state": primary_state},
                    "training_logs": training_logs,
                    "pipeline_summary": pipeline_summary,
                    "model_schema": config.stage_requirements("model_training.py"),
                },
            ),
            "downstream_analysis.py": script_notebook.create_note(
                script="downstream_analysis.py",
                cur_code=current_bundle_texts.get("downstream_analysis.py", ""),
                cur_step=step,
                prev_code=previous_step_bundle_texts.get("downstream_analysis.py", ""),
                prev_step=step - 1 if previous_step_bundle_texts.get("downstream_analysis.py") is not None else None,
                optimization_text=applied_change_contexts.get("downstream_analysis.py", "not optimized this step"),
                current_vs_prev_diff=script_prev_diffs.get("downstream_analysis.py", "N/A"),
                metric_name=config.metrics,
                metric_value=current_metric_value,
                gain=primary_gain,
                observed_outputs={
                    "cluster_metrics": cluster_metrics,
                    "cluster_summary": cluster_summary,
                    "pipeline_summary": pipeline_summary,
                    "downstream_schema": config.stage_requirements("downstream_analysis.py"),
                },
            ),
        }

        notes_text = build_history_digest(outer_notes=outer_state.note_records, global_notes=global_note_records, decision_records=decision_records, keep_last=20)
        with open(history_digest_path, "w", encoding="utf-8") as f:
            f.write(notes_text + "\n")

        evaluator_conversation: List[Dict[str, Any]] = []
        evaluator_message_vars: List[tg.Variable] = []
        evaluator_errors: Dict[str, str] = {}
        prior_payload: Dict[str, Any] | None = None
        prior_eval_out = prior_evaluator.loss_fn(
            step=step,
            suggestion=tg.Variable(prior_suggestion, requires_grad=False, role_description="current prior consultant suggestion"),
            training_history=tg.Variable(json.dumps(perf.get("training_history", []), ensure_ascii=False), requires_grad=False, role_description="training history"),
            stagnation_steps=tg.Variable(str(outer_state.stagnation_steps), requires_grad=False, role_description="current stagnation steps"),
            delta_min=tg.Variable(str(args.delta_min), requires_grad=False, role_description="minimum meaningful validation gain"),
            current_performance=tg.Variable(json.dumps({"perf_summary": pstat, "primary_state": primary_state}, ensure_ascii=False), requires_grad=False, role_description="current performance summary"),
            prior_construction_notes_history=tg.Variable(script_notes_history["prior_construction.py"], requires_grad=False, role_description="prior construction note history"),
            prior_construction_current_diffs=tg.Variable(script_current_diffs["prior_construction.py"], requires_grad=False, role_description="current prior construction raw diffs"),
            prior_construction_code=code_bundle["prior_construction.py"],
            prior_resource_summary=tg.Variable(config.prior_resource_summary, requires_grad=False, role_description="structured summary of prior resource files"),
            raw_data_summary=tg.Variable(config.feat_stats, requires_grad=False, role_description="raw data summary"),
            cluster_summary=tg.Variable(json.dumps(cluster_summary, ensure_ascii=False), requires_grad=False, role_description="cluster summary"),
            training_logs=tg.Variable(json.dumps(training_logs, ensure_ascii=False), requires_grad=False, role_description="training logs"),
            paths=tg.Variable(json.dumps(generator.path_prompt_fields, ensure_ascii=False), requires_grad=False, role_description="fixed artifact paths"),
            prior_schema=tg.Variable(json.dumps(config.current_prior_schema, ensure_ascii=False), requires_grad=False, role_description="prior schema"),
            pipeline_summary=tg.Variable(json.dumps(pipeline_summary, ensure_ascii=False), requires_grad=False, role_description="pipeline summary"),
            chat_history=_graph_text_var("[]", [], "current step evaluator chat history"),
        )
        print(f"prior_evaluator_output_step_{step}:\n{prior_eval_out.value}")
        try:
            prior_payload = parse_evaluator_message(prior_eval_out.value, "prior")
            evaluator_conversation.append(prior_payload)
            evaluator_message_vars.append(prior_eval_out)
        except Exception as exc:
            evaluator_errors["prior"] = str(exc)

        data_science_eval_out = data_science_evaluator.loss_fn(
            step=step,
            metrics=tg.Variable(config.metrics, requires_grad=False, role_description="primary metric name"),
            time_budget=tg.Variable(str(config.timeout), requires_grad=False, role_description="time budget seconds"),
            data_preprocess_code=code_bundle["data_preprocess.py"],
            suggestion=tg.Variable(suggestion, requires_grad=False, role_description="current consultant suggestion"),
            training_history=tg.Variable(json.dumps(perf.get("training_history", []), ensure_ascii=False), requires_grad=False, role_description="training history"),
            stagnation_steps=tg.Variable(str(outer_state.stagnation_steps), requires_grad=False, role_description="current stagnation steps"),
            delta_min=tg.Variable(str(args.delta_min), requires_grad=False, role_description="minimum meaningful validation gain"),
            current_performance=tg.Variable(json.dumps({"perf_summary": pstat, "primary_state": primary_state}, ensure_ascii=False), requires_grad=False, role_description="current performance summary"),
            data_preprocess_notes_history=tg.Variable(script_notes_history["data_preprocess.py"], requires_grad=False, role_description="data preprocessing note history"),
            data_preprocess_current_diffs=tg.Variable(script_current_diffs["data_preprocess.py"], requires_grad=False, role_description="current data preprocessing raw diffs"),
            preprocessing_summary=tg.Variable(json.dumps(preprocess_metadata, ensure_ascii=False), requires_grad=False, role_description="preprocess metadata json"),
            prior_resource_summary=tg.Variable(config.prior_resource_summary, requires_grad=False, role_description="structured summary of prior resource files"),
            paths=tg.Variable(json.dumps(generator.path_prompt_fields, ensure_ascii=False), requires_grad=False, role_description="fixed artifact paths"),
            data_schema=tg.Variable(json.dumps(config.stage_requirements("data_preprocess.py"), ensure_ascii=False), requires_grad=False, role_description="data preprocessing requirements"),
            prior_schema=tg.Variable(json.dumps(config.current_prior_schema, ensure_ascii=False), requires_grad=False, role_description="prior schema"),
            pipeline_summary=tg.Variable(json.dumps(pipeline_summary, ensure_ascii=False), requires_grad=False, role_description="pipeline summary"),
            chat_history=_graph_text_var(json.dumps(evaluator_conversation, ensure_ascii=False), evaluator_message_vars, "current step evaluator chat history"),
        )
        print(f"data_science_evaluator_output_step_{step}:\n{data_science_eval_out.value}")
        data_science_payload: Dict[str, Any] | None = None
        try:
            data_science_payload = parse_evaluator_message(data_science_eval_out.value, "data_science")
            evaluator_conversation.append(data_science_payload)
            evaluator_message_vars.append(data_science_eval_out)
        except Exception as exc:
            evaluator_errors["data_science"] = str(exc)

        model_eval_out = model_evaluator.loss_fn(
            step=step,
            data_preprocess_code=code_bundle["data_preprocess.py"],
            model_training_code=code_bundle["model_training.py"],
            suggestion=tg.Variable(suggestion, requires_grad=False, role_description="current consultant suggestion"),
            training_history=tg.Variable(json.dumps(perf.get("training_history", []), ensure_ascii=False), requires_grad=False, role_description="training history"),
            stagnation_steps=tg.Variable(str(outer_state.stagnation_steps), requires_grad=False, role_description="current stagnation steps"),
            delta_min=tg.Variable(str(args.delta_min), requires_grad=False, role_description="minimum meaningful validation gain"),
            current_performance=tg.Variable(json.dumps({"perf_summary": pstat, "primary_state": primary_state}, ensure_ascii=False), requires_grad=False, role_description="current performance summary"),
            model_training_notes_history=tg.Variable(script_notes_history["model_training.py"], requires_grad=False, role_description="model training note history"),
            model_training_current_diffs=tg.Variable(script_current_diffs["model_training.py"], requires_grad=False, role_description="current model training raw diffs"),
            paths=tg.Variable(json.dumps(generator.path_prompt_fields, ensure_ascii=False), requires_grad=False, role_description="fixed artifact paths"),
            model_schema=tg.Variable(json.dumps(config.stage_requirements("model_training.py"), ensure_ascii=False), requires_grad=False, role_description="model requirements"),
            training_logs=tg.Variable(json.dumps(training_logs, ensure_ascii=False), requires_grad=False, role_description="training logs"),
            pipeline_summary=tg.Variable(json.dumps(pipeline_summary, ensure_ascii=False), requires_grad=False, role_description="pipeline summary"),
            chat_history=_graph_text_var(json.dumps(evaluator_conversation, ensure_ascii=False), evaluator_message_vars, "current step evaluator chat history"),
        )
        print(f"model_evaluator_output_step_{step}:\n{model_eval_out.value}")
        model_payload: Dict[str, Any] | None = None
        try:
            model_payload = parse_evaluator_message(model_eval_out.value, "model")
            evaluator_conversation.append(model_payload)
            evaluator_message_vars.append(model_eval_out)
        except Exception as exc:
            evaluator_errors["model"] = str(exc)

        biology_eval_out = biology_evaluator.loss_fn(
            step=step,
            metrics=tg.Variable(config.metrics, requires_grad=False, role_description="primary metric name"),
            time_budget=tg.Variable(str(config.timeout), requires_grad=False, role_description="time budget seconds"),
            downstream_analysis_code=code_bundle["downstream_analysis.py"],
            suggestion=tg.Variable(suggestion, requires_grad=False, role_description="current consultant suggestion"),
            training_history=tg.Variable(json.dumps(perf.get("training_history", []), ensure_ascii=False), requires_grad=False, role_description="training history"),
            stagnation_steps=tg.Variable(str(outer_state.stagnation_steps), requires_grad=False, role_description="current stagnation steps"),
            delta_min=tg.Variable(str(args.delta_min), requires_grad=False, role_description="minimum meaningful validation gain"),
            current_performance=tg.Variable(json.dumps({"perf_summary": pstat, "primary_state": primary_state}, ensure_ascii=False), requires_grad=False, role_description="current performance summary"),
            downstream_analysis_notes_history=tg.Variable(script_notes_history["downstream_analysis.py"], requires_grad=False, role_description="downstream analysis note history"),
            downstream_analysis_current_diffs=tg.Variable(script_current_diffs["downstream_analysis.py"], requires_grad=False, role_description="current downstream raw diffs"),
            cluster_summary=tg.Variable(json.dumps(cluster_summary, ensure_ascii=False), requires_grad=False, role_description="cluster summary"),
            downstream_schema=tg.Variable(json.dumps(config.stage_requirements("downstream_analysis.py"), ensure_ascii=False), requires_grad=False, role_description="downstream requirements"),
            chat_history=_graph_text_var(json.dumps(evaluator_conversation, ensure_ascii=False), evaluator_message_vars, "current step evaluator chat history"),
        )
        print(f"biology_evaluator_output_step_{step}:\n{biology_eval_out.value}")
        biology_payload: Dict[str, Any] | None = None
        try:
            biology_payload = parse_evaluator_message(biology_eval_out.value, "biology")
            evaluator_conversation.append(biology_payload)
            evaluator_message_vars.append(biology_eval_out)
        except Exception as exc:
            evaluator_errors["biology"] = str(exc)

        critic_out = critic_evaluator.loss_fn(
            step=step,
            suggestion=tg.Variable(suggestion, requires_grad=False, role_description="current consultant suggestion"),
            raw_data_summary=tg.Variable(config.feat_stats, requires_grad=False, role_description="raw data summary"),
            prior_resource_summary=tg.Variable(config.prior_resource_summary, requires_grad=False, role_description="prior resource summary"),
            current_performance=tg.Variable(json.dumps({"perf_summary": pstat, "primary_state": primary_state}, ensure_ascii=False), requires_grad=False, role_description="current performance summary"),
            training_logs=tg.Variable(json.dumps(training_logs, ensure_ascii=False), requires_grad=False, role_description="training logs"),
            pipeline_summary=tg.Variable(json.dumps(pipeline_summary, ensure_ascii=False), requires_grad=False, role_description="pipeline summary"),
            prior_construction_notes_history=tg.Variable(script_notes_history["prior_construction.py"], requires_grad=False, role_description="prior construction note history"),
            data_preprocess_notes_history=tg.Variable(script_notes_history["data_preprocess.py"], requires_grad=False, role_description="data preprocessing note history"),
            model_training_notes_history=tg.Variable(script_notes_history["model_training.py"], requires_grad=False, role_description="model training note history"),
            downstream_analysis_notes_history=tg.Variable(script_notes_history["downstream_analysis.py"], requires_grad=False, role_description="downstream analysis note history"),
            script_summaries=_graph_text_var(StageScriptGenerator.summarize_bundle(code_bundle), list(code_bundle.values()), "current script summaries"),
            chat_history=_graph_text_var(json.dumps(evaluator_conversation, ensure_ascii=False), evaluator_message_vars, "current step evaluator chat history"),
        )
        print(f"critic_output_step_{step}:\n{critic_out.value}")
        critic_payload = parse_critic_output(critic_out.value)
        action = "reconsult" if outer_state.stagnation_steps >= args.stagnation_steps_limit else "exploit"
        critic_plan = critic_plan_from_payload(critic_payload)
        feedback_by_target = {
            filename: {"feedback": str(target_payload.get("feedback", "")).strip()}
            for filename, target_payload in critic_plan.get("targets", {}).items()
            if _feedback_has_signal(str(target_payload.get("feedback", "")).strip())
        }
        optimize_targets = _dedupe_preserve_order(list(feedback_by_target.keys())) if action == "exploit" else []
        exploit_applied = False
        exploit_summary = {
            filename: str((feedback_by_target.get(filename) or {}).get("feedback", "")).strip()
            for filename in optimize_targets
        }
        exploit_change_types = {
            filename: "structural" if exploit_summary.get(filename) else "tuning"
            for filename in optimize_targets
        }

        if action == "exploit" and optimize_targets:
            for optimizer in optimizers.values():
                optimizer.zero_grad()
            critic_out.backward()
            for filename in optimize_targets:
                optimizers[filename].step()
            exploit_applied = True

        open_issues = build_open_issues(run_result=run_result, primary_state=primary_state, critic_payload=critic_payload)
        attempts_used = attempt
        architecture_fingerprint, design_summary = infer_design_identity(bundle_text=bundle_text_map(code_bundle), payload=critic_payload, cluster_summary=cluster_summary)
        failure_phase, failure_fingerprint, root_cause = classify_run_failure(run_result)
        decision_rationale = str(critic_payload.get("global_rationale") or "").strip() or "No explicit rationale provided"
        prev_exploit_context = previous_exploit_context(global_note_records)
        reconsult_reason = f"Automatic reconsult after reaching stagnation limit ({outer_state.stagnation_steps}/{args.stagnation_steps_limit})."

        note_record = HistoryNoteRecord(
            step=step,
            action=action,
            context_mode="full",
            attempts_used=attempts_used,
            run_success=bool(run_result.get("success", False)),
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
            evaluator_diagnosis=str(critic_payload.get("global_rationale", "")).strip(),
            script_plan=critic_plan,
            open_issues=open_issues,
            exploit_applied=exploit_applied,
            optimized_scripts=optimize_targets,
            exploit_change_types=exploit_change_types,
            exploit_summary=exploit_summary,
            previous_exploit_context=prev_exploit_context,
            do_not_repeat=bool(action == "reconsult"),
            do_not_repeat_reason=reconsult_reason if action == "reconsult" else "",
        )
        append_history_note(note_record, outer_notes=outer_state.note_records, global_notes=global_note_records, note_text_path=note_path, note_jsonl_path=history_notes_path, mirror_jsonl_path=history_notes_result_path)
        append_decision_record(
            DecisionLedgerRecord(
                step=step,
                architecture_fingerprint=architecture_fingerprint,
                design_summary=design_summary,
                decision_rationale=decision_rationale,
                primary_metric="ari",
                metric_value=current_metric_value,
                metric_gain=primary_gain,
                result=classify_decision_result(run_success=bool(run_result.get("success", False)), primary_gain=primary_gain, metric_value=current_metric_value),
                action=action,
                failure_fingerprint=failure_fingerprint,
                do_not_repeat=bool(action == "reconsult"),
                do_not_repeat_reason=reconsult_reason if action == "reconsult" else "",
                exploit_applied=exploit_applied,
                optimized_scripts=optimize_targets,
                exploit_change_types=exploit_change_types,
                exploit_summary=exploit_summary,
                rejected_design_labels=[],
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
            executed_script_dir=script_dir,
            best_script_dir=os.path.join(config.code_dir, "code_best_ari"),
            final_out_dir=config.final_out_dir,
        )

        for filename in STAGE_FILENAMES:
            append_script_note_record(
                ScriptNoteRecord(
                    step=step,
                    script=filename,
                    optimization_text=applied_change_contexts.get(filename, "not optimized this step"),
                    current_vs_prev_diff=script_prev_diffs.get(filename, "N/A"),
                    current_vs_best_diff=script_best_diffs.get(filename, "N/A"),
                    note_text=script_note_texts.get(filename, ""),
                    metric_value=current_metric_value,
                    gain=primary_gain,
                ),
                records=script_note_records[filename],
                note_jsonl_path=script_note_paths[filename],
                mirror_jsonl_path=script_note_result_paths[filename],
            )

        previous_step_bundle_texts = current_bundle_texts
        next_applied_change_contexts = {filename: "not optimized this step" for filename in STAGE_FILENAMES}
        if action == "exploit":
            for filename in optimize_targets:
                next_applied_change_contexts[filename] = exploit_summary.get(filename) or str((feedback_by_target.get(filename) or {}).get("feedback", "")).strip() or "optimized this step"
        elif action == "reconsult":
            next_applied_change_contexts = {filename: "reconsult regeneration" for filename in STAGE_FILENAMES}
        applied_change_contexts = next_applied_change_contexts

        step_log = {
            "step": step,
            "action": action,
            "critic_payload": critic_payload,
            "critic_plan": critic_plan,
            "prior_evaluator_payload": prior_payload,
            "data_science_evaluator_payload": data_science_payload,
            "model_evaluator_payload": model_payload,
            "biology_evaluator_payload": biology_payload,
            "evaluator_conversation": evaluator_conversation,
            "evaluator_errors": evaluator_errors,
            "feedback_by_target": feedback_by_target,
            "run_success": run_result.get("success", False),
            "performance": perf,
            "cluster_metrics": cluster_metrics,
            "cluster_summary": cluster_summary,
            "training_logs": training_logs,
            "pipeline_summary": pipeline_summary,
            "script_notes_history": script_notes_history,
            "script_current_diffs": script_current_diffs,
            "script_note_texts": script_note_texts,
            "script_dir": script_dir,
            "optimized_targets": optimize_targets,
        }
        with open(f"{config.result_dir}/feedback/evaluator_conversation_step_{step}.json", "w", encoding="utf-8") as f:
            json.dump({"step": step, "chat_history": evaluator_conversation, "errors": evaluator_errors}, f, indent=2, ensure_ascii=False)
        with open(f"{config.result_dir}/feedback/critic_output_step_{step}.json", "w", encoding="utf-8") as f:
            json.dump(critic_payload, f, indent=2, ensure_ascii=False)
        with open(f"{config.result_dir}/feedback/single_feedback_step_{step}.json", "w", encoding="utf-8") as f:
            json.dump(step_log, f, indent=2, ensure_ascii=False)

        if action == "reconsult":
            current_attempt = {
                "critic_plan": critic_plan,
                "instruction_text": build_instruction_text(critic_plan.get("targets", {})),
                "cluster_metrics": cluster_metrics,
                "cluster_summary": cluster_summary,
                "training_logs": training_logs,
                "pipeline_summary": pipeline_summary,
            }
            why_current_fails = {
                "critic_payload": critic_payload,
                "open_issues": open_issues,
                "failure_fingerprint": failure_fingerprint,
                "history_digest": notes_text,
            }
            historical_failures = "\n".join(open_issues[-10:]) if open_issues else "<none>"
            consultant_history_context = build_consultant_history_context(consultant_records)
            hard_constraints = []
            for filename in STAGE_FILENAMES:
                hard_constraints.extend(_build_optimizer_constraints_for_file(filename, generator.path_prompt_fields, stage_schemas.get(filename, {}), config))
            reconsult_query = build_reconsult_query(
                task_description=task_summary["task_description"],
                background=consultant_background,
                current_suggestion=suggestion,
                current_prior_plan=prior_suggestion,
                current_prior_schema=config.current_prior_schema,
                current_attempt=current_attempt,
                why_current_fails=why_current_fails,
                historical_failures=historical_failures,
                hard_constraints=hard_constraints,
                history_digest=notes_text,
                consultant_history_context=consultant_history_context,
            )
            reconsult_output = consultant.generate(prompt=reconsult_query)
            print(f"consultant_output_step_{step}:\n{reconsult_output}")
            task_summary = TextGradConsultant.parse_main_summary_tags(reconsult_output)
            suggestion = task_summary["suggestion"]
            record_consultant_plan(
                consultant_records=consultant_records,
                path=consultant_history_path,
                record=ConsultantPlanRecord(
                    step=step,
                    source="reconsult",
                    task_description=task_summary["task_description"],
                    suggestion=task_summary["suggestion"],
                    prior_schema_json={},
                    raw_output=reconsult_output,
                    plan_fingerprint=plan_fingerprint(task_summary["task_description"], task_summary["suggestion"], {}),
                ),
            )
            prior_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="prior")
            model_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="model")
            data_science_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="data_science")
            biology_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="biology")
            critic_evaluator = TextGradEvaluator(config=config, engine_name=args.engine, task_decrp=task_summary["task_description"], background=background, eval_type="critic")
            script_notebook = ScriptNotebook(engine_name=args.engine, task_description=task_summary["task_description"])
            code_bundle = None
            optimizers = {}
            outer_state.reset()

        elapsed = time.perf_counter() - step_start
        print(f"Step {step} elapsed: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
