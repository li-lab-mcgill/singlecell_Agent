from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import pandas as pd

from pipelines.evaluation_plan import COMBINED_SCORE_TOLERANCE, compute_combined_score
from pipelines.multieval_types import ValidationFailure


def _failure(target: str, error_type: str, message: str, **details: Any) -> ValidationFailure:
    payload = {key: value for key, value in details.items() if value is not None}
    return ValidationFailure(target=target, error_type=error_type, message=message, details=payload)


def _schema_for_output(stage_schema: Dict[str, Any], output_key: str) -> Dict[str, Any]:
    artifacts = stage_schema.get("artifacts", {}) if isinstance(stage_schema, dict) else {}
    return artifacts.get(output_key, {}) if isinstance(artifacts, dict) else {}


def _is_non_empty(path: str) -> bool:
    try:
        return os.path.getsize(path) > 0
    except OSError:
        return False


def _validate_csv_file(path: str, required_columns: List[str], target_file: str, output_key: str) -> List[ValidationFailure]:
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        return [_failure(target_file, "InvalidSchema", f"Failed to read CSV output at {path}: {exc}", output_key=output_key, path=path)]
    if frame.empty:
        return [_failure(target_file, "EmptyArtifact", f"CSV output is empty at {path}", output_key=output_key, path=path)]
    missing = [col for col in required_columns if col not in frame.columns]
    if missing:
        return [_failure(target_file, "InvalidSchema", f"CSV output missing required columns: {missing}", output_key=output_key, path=path)]
    return []


def _validate_json_file(path: str, required_keys: List[str], target_file: str, output_key: str) -> List[ValidationFailure]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        return [_failure(target_file, "InvalidSchema", f"Failed to read JSON output at {path}: {exc}", output_key=output_key, path=path)]
    if required_keys:
        missing = [key for key in required_keys if key not in payload]
        if missing:
            return [_failure(target_file, "InvalidSchema", f"JSON output missing required keys: {missing}", output_key=output_key, path=path)]
    return []


def _validate_combined_score(path: str, stage_schema: Dict[str, Any], target_file: str) -> List[ValidationFailure]:
    combined_metric_spec = stage_schema.get("combined_metric_spec") if isinstance(stage_schema, dict) else None
    if not isinstance(combined_metric_spec, dict) or not combined_metric_spec:
        return [_failure(target_file, "InvalidSchema", "Downstream stage schema is missing combined_metric_spec", output_key="cluster_metrics", path=path)]
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        return [_failure(target_file, "InvalidSchema", f"Failed to read JSON output at {path}: {exc}", output_key="cluster_metrics", path=path)]
    try:
        emitted_score = float(payload.get("combined_score"))
    except (TypeError, ValueError):
        return [_failure(target_file, "InvalidSchema", "cluster_metrics.json must contain numeric combined_score", output_key="cluster_metrics", path=path)]
    try:
        recomputed = compute_combined_score(payload, combined_metric_spec)
    except Exception as exc:
        return [_failure(target_file, "InvalidSchema", f"Unable to recompute combined_score: {exc}", output_key="cluster_metrics", path=path)]
    if abs(emitted_score - recomputed) > COMBINED_SCORE_TOLERANCE:
        return [
            _failure(
                target_file,
                "InvalidSchema",
                f"combined_score does not match recomputed value (emitted={emitted_score}, recomputed={recomputed})",
                output_key="cluster_metrics",
                path=path,
            )
        ]
    return []


def _validate_prior_bundle(stage_schema: Dict[str, Any], target_file: str) -> List[ValidationFailure]:
    prior_files = stage_schema.get("prior_files", []) if isinstance(stage_schema, dict) else []
    if prior_files == []:
        return []
    if not isinstance(prior_files, list):
        return [_failure(target_file, "InvalidSchema", "Prior stage is missing resolved prior file requirements")]
    for item in prior_files:
        if not isinstance(item, dict):
            return [_failure(target_file, "InvalidSchema", "Resolved prior file requirements must be objects")]
        artifact_key = str(item.get("artifact_key") or "").strip() or "prior_artifact"
        artifact_path = str(item.get("path") or "").strip()
        if not artifact_path or not os.path.exists(artifact_path):
            return [_failure(target_file, "MissingArtifact", f"Prior artifact missing at {artifact_path}", output_key=artifact_key, path=artifact_path)]
        if not _is_non_empty(artifact_path):
            return [_failure(target_file, "EmptyArtifact", f"Prior artifact is empty at {artifact_path}", output_key=artifact_key, path=artifact_path)]
        fmt = str(item.get("format") or "").strip().lower()
        if fmt == "csv":
            failures = _validate_csv_file(artifact_path, item.get("required_columns", []), target_file, artifact_key)
            if failures:
                return failures
        elif fmt == "json":
            failures = _validate_json_file(artifact_path, item.get("required_keys", []), target_file, artifact_key)
            if failures:
                return failures
    return []


def validate_stage_outputs(resolved_artifact_layout: Dict[str, Any], stage_schema: Dict[str, Any], target_file: str) -> List[ValidationFailure]:
    if target_file == "prior_construction.py":
        failures = _validate_prior_bundle(stage_schema, target_file)
        if failures:
            return failures
    outputs = resolved_artifact_layout.get("generated_outputs", {})
    if not isinstance(outputs, dict):
        return [_failure(target_file, "InvalidSchema", "Resolved artifact layout missing generated_outputs")]
    required_outputs = stage_schema.get("required_outputs", []) if isinstance(stage_schema, dict) else []
    if not isinstance(required_outputs, list):
        return [_failure(target_file, "InvalidSchema", "Stage schema required_outputs must be a list")]

    for output_key in required_outputs:
        path = outputs.get(output_key, "")
        if not path or not os.path.exists(path):
            return [_failure(target_file, "MissingArtifact", f"Required output missing at {path}", output_key=output_key, path=path)]
        if not _is_non_empty(path):
            return [_failure(target_file, "EmptyArtifact", f"Required output is empty at {path}", output_key=output_key, path=path)]
        schema = _schema_for_output(stage_schema, output_key)
        fmt = str(schema.get("format") or "").strip().lower()
        if fmt == "csv":
            failures = _validate_csv_file(path, schema.get("required_columns", []), target_file, output_key)
            if failures:
                return failures
        elif fmt == "json":
            failures = _validate_json_file(path, schema.get("required_keys", []), target_file, output_key)
            if failures:
                return failures
            if target_file == "downstream_analysis.py" and output_key == "cluster_metrics":
                failures = _validate_combined_score(path, stage_schema, target_file)
                if failures:
                    return failures
    return []


def validate_all_outputs(resolved_artifact_layout: Dict[str, Any], stage_schemas: Dict[str, Dict[str, Any]]) -> List[ValidationFailure]:
    for filename, stage_schema in stage_schemas.items():
        failures = validate_stage_outputs(resolved_artifact_layout, stage_schema, filename)
        if failures:
            return failures
    return []


def write_failure_record(path: str, payload: ValidationFailure | Dict[str, Any]) -> None:
    record = payload.to_dict() if isinstance(payload, ValidationFailure) else payload
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
