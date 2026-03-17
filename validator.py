from __future__ import annotations

import ast
import csv
import json
import os
import re
from typing import Any, Dict, List

from config import Config
from multieval_types import PipelineBundle, StepRunContract, ValidationFailure

SECTION_ORDER = ["dataloader", "prior", "model", "train", "clustering"]
REQUIRED_FUNCTIONS = ["main"]


def _extract_prior_components(prior_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    components = prior_plan.get("prior_data_needed", []) if isinstance(prior_plan, dict) else []
    return components if isinstance(components, list) else []


def build_step_run_contract(config: Config, step: int, prior_plan: Dict[str, Any]) -> StepRunContract:
    run_dir = os.path.join(config.intermediate_output_dir, f"step_{step}")
    artifact_paths = {
        "preprocess_metadata": config.preprocess_metadata_path,
        "preprocess_train_mod1": config.preprocess_train_out_path,
        "preprocess_val_mod1": config.preprocess_val_out_path,
        "preprocess_test_mod1": config.preprocess_test_out_path,
        "model_performance": config.model_perf_path,
        "best_model": config.best_model_path,
        "embedding": config.embedding_path,
        "embedding_metadata": config.embedding_metadata_path,
        "cluster_assignments": config.cluster_assignments_path,
        "cluster_metrics": config.cluster_metrics_path,
        "cluster_summary": config.cluster_summary_path,
        "training_logs": config.training_logs_path,
        "pipeline_summary": config.pipeline_summary_path,
        "prior_manifest": config.prior_manifest_path,
    }
    return StepRunContract(
        step=step,
        run_dir=run_dir,
        contract_path=os.path.join(run_dir, "contract.json"),
        component_contract_path=os.path.join(run_dir, "component_contract.json"),
        artifact_paths=artifact_paths,
        required_script="pipeline.py",
        required_functions=REQUIRED_FUNCTIONS,
        section_order=SECTION_ORDER,
        section_output_contracts={
            "dataloader": [
                config.preprocess_metadata_path,
                config.preprocess_train_out_path,
                config.preprocess_val_out_path,
                config.preprocess_test_out_path,
            ],
            "prior": [config.prior_manifest_path],
            "model": [],
            "train": [
                config.model_perf_path,
                config.best_model_path,
                config.embedding_path,
                config.embedding_metadata_path,
                config.training_logs_path,
                config.pipeline_summary_path,
            ],
            "clustering": [config.cluster_assignments_path, config.cluster_metrics_path, config.cluster_summary_path],
        },
    )


def build_component_contract(config: Config, prior_plan: Dict[str, Any], step_contract: StepRunContract) -> Dict[str, Any]:
    return {
        "runtime": {
            "step": step_contract.step,
            "run_dir_env": "SCANPY_AGENT_RUN_DIR",
            "intermediate_output_path": step_contract.run_dir,
            "input_mod1_env": "SCANPY_AGENT_INPUT_MOD1_PATH",
            "input_mod2_env": "SCANPY_AGENT_INPUT_MOD2_PATH",
            "contract_path": step_contract.component_contract_path or step_contract.contract_path,
            "simple_contract_path": step_contract.contract_path,
            "run_dir": step_contract.run_dir,
            "script_name": step_contract.required_script,
            "section_execution_order": step_contract.section_order,
        },
        "required_functions": step_contract.required_functions,
        "section_outputs": step_contract.section_output_contracts,
        "preprocessing": {
            "metadata_path": config.preprocess_metadata_path,
            "metadata_schema": {
                "required_keys": ["n_obs", "n_vars", "input_adata_path"],
                "optional_keys": ["n_hvg", "split_counts", "seed", "qc_filters", "modality_1"],
            },
        },
        "prior": {
            "output_manifest_path": config.prior_manifest_path,
            "specification": prior_plan,
            "fixed_output_dir": "prior/",
            "required_files": [],
            "required_manifest_schema": {
                "top_level": ["required_files"],
                "required_file_fields": ["file_name", "path"],
            },
        },
        "train": {
            "required_metrics": ["train_performance", "val_performance", "test_performance", "training_history"],
            "model_performance_schema": {
                "required_keys": [
                    "train_performance",
                    "val_performance",
                    "test_performance",
                    "training_history",
                    "best_model",
                    "model_coef",
                    "embedding_dim",
                    "model_architecture",
                ],
            },
            "required_output_artifacts": {
                "best_model": config.best_model_path,
                "embedding": config.embedding_path,
                "embedding_metadata": config.embedding_metadata_path,
                "embedding_metadata_columns": ["cell_id", "split", "row_index"],
            },
            "training_logs_schema": {
                "required_keys": ["epochs_completed", "best_epoch", "early_stopped", "history"],
            },
            "pipeline_summary_schema": {
                "required_keys": ["artifacts", "runtime_seconds", "model_summary", "prior_summary", "clustering_summary"],
            },
        },
        "clustering": {
            "embedding_output_semantics": {
                "source": "in_memory_from_train",
                "saved_embedding_artifact": config.embedding_path,
                "saved_embedding_metadata": config.embedding_metadata_path,
            },
            "cluster_metrics_schema": {
                "required_keys": ["ari", "n_clusters"],
                "optional_keys": ["silhouette", "nmi", "resolution", "method"],
            },
            "cluster_summary_schema": {
                "top_level": ["n_clusters", "method", "resolution", "embedding_source", "clusters"],
                "per_cluster": [
                    "cluster_id",
                    "size",
                    "fraction_of_cells",
                    "top_degs",
                    "marker_overlap",
                    "matched_markers",
                    "candidate_cell_types",
                    "notes",
                ],
            }
        },
    }


def _parse_functions(code: str) -> set[str]:
    module = ast.parse(code)
    return {
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _hardcoded_step_paths(code: str) -> List[str]:
    return re.findall(r"intermediate_output/step_\d+", code)


def validate_bundle_contract(bundle: PipelineBundle, contract: StepRunContract) -> List[ValidationFailure]:
    code = bundle.pipeline_code.value
    failures: List[ValidationFailure] = []
    if not code.strip():
        return [ValidationFailure(stage="pipeline", error_type="InvalidSchema", message="Generated script is empty")]
    if "SCANPY_AGENT_RUN_DIR" not in code:
        failures.append(
            ValidationFailure(
                stage="pipeline",
                error_type="ContractViolation",
                message=(
                    "Generated script must resolve step-local output paths from SCANPY_AGENT_RUN_DIR. "
                    "Use os.environ['SCANPY_AGENT_RUN_DIR'] as the base directory for outputs such as "
                    "model_performance.json, best_model.pt, embedding.npy, embedding_metadata.csv, "
                    "cluster_metrics.json, cluster_summary.json, and prior/prior_manifest.json. "
                    "Do not hardcode intermediate_output/step_* paths or assume a fixed run directory."
                ),
                details={
                    "required_env_var": "SCANPY_AGENT_RUN_DIR",
                    "usage": "base directory for current-step outputs only",
                    "examples": [
                        "os.path.join(run_dir, 'model_performance.json')",
                        "os.path.join(run_dir, 'best_model.pt')",
                        "os.path.join(run_dir, 'prior', 'prior_manifest.json')",
                    ],
                },
            )
        )
    hardcoded = _hardcoded_step_paths(code)
    if hardcoded:
        failures.append(
            ValidationFailure(
                stage="pipeline",
                error_type="ContractViolation",
                message="Generated script hardcodes step-specific output paths",
                details={"paths": hardcoded},
            )
        )
    try:
        functions = _parse_functions(code)
    except SyntaxError as exc:
        return [
            ValidationFailure(
                stage="pipeline",
                error_type="InvalidSchema",
                message=f"Generated script is not valid Python: {exc}",
                details={
                    "lineno": getattr(exc, "lineno", None),
                    "offset": getattr(exc, "offset", None),
                    "text": getattr(exc, "text", None),
                },
            )
        ]
    missing = [name for name in contract.required_functions if name not in functions]
    if missing:
        failures.append(
            ValidationFailure(
                stage="pipeline",
                error_type="ContractViolation",
                message="Generated script is missing required top-level functions",
                details={"missing_functions": missing},
            )
        )
    return failures


def validate_script_path(path: str, contract: StepRunContract) -> List[ValidationFailure]:
    failures: List[ValidationFailure] = []
    if not path:
        return [ValidationFailure(stage="pipeline", error_type="MissingArtifact", message="Missing script path")]
    if os.path.basename(path) != contract.required_script:
        failures.append(
            ValidationFailure(
                stage="pipeline",
                error_type="ContractViolation",
                message="Script filename does not match contract",
                details={"expected": contract.required_script, "actual": os.path.basename(path)},
            )
        )
    if not os.path.exists(path):
        failures.append(
            ValidationFailure(stage="pipeline", error_type="MissingArtifact", message=f"Script file missing at {path}")
        )
    return failures


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON payload must be an object")
    return data


def _count_csv_rows(path: str) -> int:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        _ = next(reader, None)
        return sum(1 for _ in reader)


def _failure(stage: str, error_type: str, message: str, **details: Any) -> ValidationFailure:
    payload = {key: value for key, value in details.items() if value is not None}
    return ValidationFailure(stage=stage, error_type=error_type, message=message, details=payload)


def validate_pipeline_outputs(contract: StepRunContract) -> List[ValidationFailure]:
    failures: List[ValidationFailure] = []
    for stage, paths in contract.section_output_contracts.items():
        for path in paths:
            if not os.path.exists(path):
                failures.append(_failure(stage, "MissingArtifact", f"Required output missing at {path}", path=path))
                return failures
            if path.lower().endswith(".csv") and _count_csv_rows(path) <= 0:
                failures.append(_failure(stage, "InvalidSchema", f"Required CSV is empty at {path}", path=path))
                return failures

    try:
        manifest = _read_json(contract.artifact_paths["prior_manifest"])
    except Exception as exc:
        return [_failure("prior", "InvalidSchema", f"prior_manifest.json invalid: {exc}", path=contract.artifact_paths["prior_manifest"])]
    required_files = manifest.get("required_files")
    if not isinstance(required_files, list):
        return [
            _failure(
                "prior",
                "InvalidSchema",
                "prior_manifest.json missing required_files list",
                present_keys=sorted(manifest.keys()),
                required_files_type=type(required_files).__name__ if required_files is not None else "missing",
            )
        ]
    expected_prior_dir = os.path.abspath(os.path.dirname(contract.artifact_paths["prior_manifest"]))
    for idx, item in enumerate(required_files):
        if not isinstance(item, dict):
            return [
                _failure(
                    "prior",
                    "InvalidSchema",
                    "prior_manifest.json required_files entries must be objects",
                    entry_index=idx,
                    entry_type=type(item).__name__,
                    entry_preview=repr(item)[:300],
                )
            ]
        file_path = item.get("path")
        file_name = item.get("file_name", "<unknown>")
        if not isinstance(file_path, str) or not file_path:
            return [
                _failure(
                    "prior",
                    "InvalidSchema",
                    f"prior_manifest.json entry for {file_name} is missing path",
                    entry_index=idx,
                    file_name=file_name,
                    present_keys=sorted(item.keys()),
                    path_type=type(file_path).__name__ if file_path is not None else "missing",
                )
            ]
        abs_file_path = os.path.abspath(file_path)
        if not abs_file_path.startswith(expected_prior_dir + os.sep):
            return [
                _failure(
                    "prior",
                    "InvalidSchema",
                    f"prior_manifest.json entry for {file_name} points outside the fixed prior/ directory",
                    entry_index=idx,
                    file_name=file_name,
                    path=abs_file_path,
                    expected_prefix=expected_prior_dir,
                )
            ]
        if not os.path.exists(abs_file_path):
            return [_failure("prior", "MissingArtifact", f"Required prior file missing: {file_name} at {file_path}")]

    try:
        perf = _read_json(contract.artifact_paths["model_performance"])
    except Exception as exc:
        return [_failure("train", "InvalidSchema", f"model_performance.json invalid: {exc}")]
    missing_perf = [
        key for key in ["train_performance", "val_performance", "test_performance", "training_history"] if key not in perf
    ]
    if missing_perf:
        return [
            _failure(
                "train",
                "InvalidSchema",
                "model_performance.json missing required keys",
                missing_keys=missing_perf,
                present_keys=sorted(perf.keys()),
            )
        ]

    try:
        embedding_meta_rows = _count_csv_rows(contract.artifact_paths["embedding_metadata"])
    except Exception as exc:
        return [_failure("train", "InvalidSchema", f"embedding_metadata.csv invalid: {exc}")]
    if embedding_meta_rows <= 0:
        return [_failure("train", "InvalidSchema", "embedding_metadata.csv is empty", path=contract.artifact_paths["embedding_metadata"])]

    try:
        summary = _read_json(contract.artifact_paths["cluster_summary"])
    except Exception as exc:
        return [_failure("clustering", "InvalidSchema", f"cluster_summary.json invalid: {exc}")]
    required_top = ["n_clusters", "method", "resolution", "embedding_source", "clusters"]
    missing_top = [key for key in required_top if key not in summary]
    if missing_top:
        return [
            _failure(
                "clustering",
                "InvalidSchema",
                "cluster_summary.json missing top-level keys",
                missing_keys=missing_top,
                present_keys=sorted(summary.keys()),
            )
        ]
    clusters = summary.get("clusters")
    if not isinstance(clusters, list):
        return [
            _failure(
                "clustering",
                "InvalidSchema",
                "cluster_summary.json clusters must be a list",
                clusters_type=type(clusters).__name__ if clusters is not None else "missing",
            )
        ]
    required_cluster_keys = {
        "cluster_id",
        "size",
        "fraction_of_cells",
        "top_degs",
        "marker_overlap",
        "matched_markers",
        "candidate_cell_types",
        "notes",
    }
    for idx, item in enumerate(clusters):
        if not isinstance(item, dict):
            return [
                _failure(
                    "clustering",
                    "InvalidSchema",
                    "cluster_summary.json cluster entries must be objects",
                    entry_index=idx,
                    entry_type=type(item).__name__,
                    entry_preview=repr(item)[:300],
                )
            ]
        missing_cluster = sorted(required_cluster_keys - set(item.keys()))
        if missing_cluster:
            return [
                _failure(
                    "clustering",
                    "InvalidSchema",
                    "cluster_summary.json cluster entry missing required keys",
                    entry_index=idx,
                    missing_keys=missing_cluster,
                    present_keys=sorted(item.keys()),
                )
            ]

    try:
        metrics = _read_json(contract.artifact_paths["cluster_metrics"])
    except Exception as exc:
        return [_failure("clustering", "InvalidSchema", f"cluster_metrics.json invalid: {exc}")]
    if "ari" not in metrics and "ARI" not in metrics:
        return [
            _failure(
                "clustering",
                "InvalidSchema",
                "cluster_metrics.json missing ari",
                present_keys=sorted(metrics.keys()),
            )
        ]
    return failures


def write_failure_record(path: str, payload: ValidationFailure | Dict[str, Any]) -> None:
    record = payload.to_dict() if isinstance(payload, ValidationFailure) else payload
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
