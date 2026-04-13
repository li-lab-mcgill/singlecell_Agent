from __future__ import annotations

import json
from typing import Any, Dict, List


ALLOWED_EVALUATOR_ROLES = ["biology", "data_science", "model", "prior", "critic"]
ALLOWED_DOWNSTREAM_OUTPUTS = ["cluster_assignments", "cluster_metrics", "cluster_summary"]
REQUIRED_ASSIGNMENT_COLUMNS = ["cell_id", "predicted_cluster", "split"]
REQUIRED_COMBINED_METRIC_KEY = "combined_score"
REQUIRED_MISSING_VALUE_POLICY = "fail_on_required_skip_optional"
COMBINED_SCORE_TOLERANCE = 1e-6


def _as_non_empty_string(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be a non-empty string")
    return text


def _as_list(value: Any, label: str) -> List[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _normalize_unique_string_list(values: Any, label: str) -> List[str]:
    items = _as_list(values, label)
    normalized: List[str] = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _validate_query_decomposition(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("query_decomposition must be an object")
    return {
        "task_category": _as_non_empty_string(payload.get("task_category"), "query_decomposition.task_category"),
        "primary_question": _as_non_empty_string(payload.get("primary_question"), "query_decomposition.primary_question"),
        "success_hypothesis": _as_non_empty_string(payload.get("success_hypothesis"), "query_decomposition.success_hypothesis"),
        "expected_biological_outcome": _as_non_empty_string(payload.get("expected_biological_outcome"), "query_decomposition.expected_biological_outcome"),
        "benchmark_frame": _as_non_empty_string(payload.get("benchmark_frame"), "query_decomposition.benchmark_frame"),
        "key_risks": _normalize_unique_string_list(payload.get("key_risks"), "query_decomposition.key_risks"),
    }


def _validate_guidance_entries(payload: Any) -> List[Dict[str, str]]:
    entries = _as_list(payload, "guidance_per_evaluator")
    normalized: List[Dict[str, str]] = []
    seen_roles = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("guidance_per_evaluator entries must be objects")
        role = _as_non_empty_string(entry.get("evaluator_role"), "guidance_per_evaluator.evaluator_role")
        if role not in ALLOWED_EVALUATOR_ROLES:
            raise ValueError(f"Unsupported evaluator role: {role}")
        if role in seen_roles:
            raise ValueError(f"Duplicate evaluator guidance for role: {role}")
        seen_roles.add(role)
        normalized.append(
            {
                "evaluator_role": role,
                "what_to_look_for": _as_non_empty_string(entry.get("what_to_look_for"), f"guidance_per_evaluator[{role}].what_to_look_for"),
                "what_good_looks_like": _as_non_empty_string(entry.get("what_good_looks_like"), f"guidance_per_evaluator[{role}].what_good_looks_like"),
            }
        )
    missing_roles = [role for role in ALLOWED_EVALUATOR_ROLES if role not in seen_roles]
    if missing_roles:
        raise ValueError(f"guidance_per_evaluator is missing required roles: {missing_roles}")
    return normalized


def _validate_experiment_plan(payload: Any) -> List[Dict[str, Any]]:
    entries = _as_list(payload, "evaluation_experiments")
    if not entries:
        raise ValueError("evaluation_experiments must contain at least one experiment")
    normalized: List[Dict[str, Any]] = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("evaluation_experiments entries must be objects")
        priority = _as_non_empty_string(entry.get("priority"), f"evaluation_experiments[{idx}].priority")
        if priority not in {"high", "medium", "low"}:
            raise ValueError(f"evaluation_experiments[{idx}].priority must be high, medium, or low")
        normalized.append(
            {
                "name": _as_non_empty_string(entry.get("name"), f"evaluation_experiments[{idx}].name"),
                "purpose": _as_non_empty_string(entry.get("purpose"), f"evaluation_experiments[{idx}].purpose"),
                "required_metrics": _normalize_unique_string_list(entry.get("required_metrics"), f"evaluation_experiments[{idx}].required_metrics"),
                "required_summary_evidence": _normalize_unique_string_list(entry.get("required_summary_evidence"), f"evaluation_experiments[{idx}].required_summary_evidence"),
                "priority": priority,
            }
        )
    return normalized


def _validate_downstream_requirements(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("downstream_requirements must be an object")
    required_outputs = _normalize_unique_string_list(payload.get("required_outputs"), "downstream_requirements.required_outputs")
    if required_outputs != ALLOWED_DOWNSTREAM_OUTPUTS:
        raise ValueError(
            "downstream_requirements.required_outputs must contain exactly "
            f"{ALLOWED_DOWNSTREAM_OUTPUTS}, got {required_outputs}"
        )
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("downstream_requirements.artifacts must be an object")
    unsupported_artifacts = [key for key in artifacts.keys() if key not in ALLOWED_DOWNSTREAM_OUTPUTS]
    if unsupported_artifacts:
        raise ValueError(f"Unsupported downstream artifact keys: {unsupported_artifacts}")

    normalized_artifacts: Dict[str, Dict[str, Any]] = {}

    assignments = artifacts.get("cluster_assignments")
    if not isinstance(assignments, dict):
        raise ValueError("downstream_requirements.artifacts.cluster_assignments must be an object")
    assignment_columns = _normalize_unique_string_list(
        assignments.get("required_columns"),
        "downstream_requirements.artifacts.cluster_assignments.required_columns",
    )
    missing_assignment_cols = [col for col in REQUIRED_ASSIGNMENT_COLUMNS if col not in assignment_columns]
    if missing_assignment_cols:
        raise ValueError(
            "cluster_assignments.required_columns must include "
            f"{REQUIRED_ASSIGNMENT_COLUMNS}; missing {missing_assignment_cols}"
        )
    normalized_artifacts["cluster_assignments"] = {
        "format": "csv",
        "required_columns": assignment_columns,
    }

    metrics = artifacts.get("cluster_metrics")
    if not isinstance(metrics, dict):
        raise ValueError("downstream_requirements.artifacts.cluster_metrics must be an object")
    metric_keys = _normalize_unique_string_list(
        metrics.get("required_keys"),
        "downstream_requirements.artifacts.cluster_metrics.required_keys",
    )
    if REQUIRED_COMBINED_METRIC_KEY not in metric_keys:
        raise ValueError("cluster_metrics.required_keys must include combined_score")
    normalized_artifacts["cluster_metrics"] = {
        "format": "json",
        "required_keys": metric_keys,
    }

    summary = artifacts.get("cluster_summary")
    if not isinstance(summary, dict):
        raise ValueError("downstream_requirements.artifacts.cluster_summary must be an object")
    normalized_artifacts["cluster_summary"] = {
        "format": "json",
        "required_keys": _normalize_unique_string_list(
            summary.get("required_keys", []),
            "downstream_requirements.artifacts.cluster_summary.required_keys",
        ),
    }

    return {
        "required_outputs": required_outputs,
        "artifacts": normalized_artifacts,
    }


def _validate_component(entry: Any, index: int) -> Dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("combined_metric_spec.components entries must be objects")
    key = _as_non_empty_string(entry.get("key"), f"combined_metric_spec.components[{index}].key")
    try:
        weight = float(entry.get("weight"))
    except (TypeError, ValueError):
        raise ValueError(f"combined_metric_spec.components[{index}].weight must be numeric") from None
    if weight <= 0:
        raise ValueError(f"combined_metric_spec.components[{index}].weight must be > 0")
    goal = _as_non_empty_string(entry.get("goal"), f"combined_metric_spec.components[{index}].goal")
    if goal not in {"maximize", "minimize"}:
        raise ValueError(f"combined_metric_spec.components[{index}].goal must be maximize or minimize")
    if not isinstance(entry.get("required"), bool):
        raise ValueError(f"combined_metric_spec.components[{index}].required must be a boolean")
    normalization = entry.get("normalization")
    if not isinstance(normalization, dict):
        raise ValueError(f"combined_metric_spec.components[{index}].normalization must be an object")
    kind = _as_non_empty_string(normalization.get("kind"), f"combined_metric_spec.components[{index}].normalization.kind")
    if kind not in {"clip", "affine"}:
        raise ValueError(f"combined_metric_spec.components[{index}].normalization.kind must be clip or affine")
    try:
        min_value = float(normalization.get("min"))
        max_value = float(normalization.get("max"))
    except (TypeError, ValueError):
        raise ValueError(f"combined_metric_spec.components[{index}].normalization min/max must be numeric") from None
    if max_value <= min_value:
        raise ValueError(f"combined_metric_spec.components[{index}].normalization.max must be > min")
    return {
        "key": key,
        "weight": weight,
        "goal": goal,
        "required": bool(entry.get("required")),
        "normalization": {"kind": kind, "min": min_value, "max": max_value},
        "rationale": _as_non_empty_string(entry.get("rationale"), f"combined_metric_spec.components[{index}].rationale"),
    }


def _validate_combined_metric_spec(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("combined_metric_spec must be an object")
    metric_key = _as_non_empty_string(payload.get("metric_key"), "combined_metric_spec.metric_key")
    if metric_key != REQUIRED_COMBINED_METRIC_KEY:
        raise ValueError("combined_metric_spec.metric_key must be exactly combined_score")
    direction = _as_non_empty_string(payload.get("direction"), "combined_metric_spec.direction")
    if direction != "maximize":
        raise ValueError("combined_metric_spec.direction must be maximize")
    missing_value_policy = _as_non_empty_string(payload.get("missing_value_policy"), "combined_metric_spec.missing_value_policy")
    if missing_value_policy != REQUIRED_MISSING_VALUE_POLICY:
        raise ValueError(
            "combined_metric_spec.missing_value_policy must be "
            f"{REQUIRED_MISSING_VALUE_POLICY}"
        )
    component_entries = _as_list(payload.get("components"), "combined_metric_spec.components")
    if not component_entries:
        raise ValueError("combined_metric_spec.components must be non-empty")
    components = [_validate_component(entry, idx) for idx, entry in enumerate(component_entries)]
    return {
        "metric_key": metric_key,
        "direction": direction,
        "summary": _as_non_empty_string(payload.get("summary"), "combined_metric_spec.summary"),
        "components": components,
        "missing_value_policy": missing_value_policy,
        "formula_text": _as_non_empty_string(payload.get("formula_text"), "combined_metric_spec.formula_text"),
    }


def normalize_evaluation_plan(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Analyst output must decode to a JSON object")
    return {
        "goal": _as_non_empty_string(payload.get("goal"), "goal"),
        "dataset_summary": _as_non_empty_string(payload.get("dataset_summary"), "dataset_summary"),
        "query_decomposition": _validate_query_decomposition(payload.get("query_decomposition")),
        "guidance_per_evaluator": _validate_guidance_entries(payload.get("guidance_per_evaluator")),
        "evaluation_experiments": _validate_experiment_plan(payload.get("evaluation_experiments")),
        "expected_downstream_outputs": _as_non_empty_string(payload.get("expected_downstream_outputs"), "expected_downstream_outputs"),
        "downstream_requirements": _validate_downstream_requirements(payload.get("downstream_requirements")),
        "combined_metric_spec": _validate_combined_metric_spec(payload.get("combined_metric_spec")),
    }


def build_analyst_plan_text(plan: Dict[str, Any]) -> str:
    normalized = normalize_evaluation_plan(plan)
    sections = [
        "Analyst query decomposition:\n" + json.dumps(normalized["query_decomposition"], ensure_ascii=False, indent=2),
        "Analyst evaluation experiments:\n" + json.dumps(normalized["evaluation_experiments"], ensure_ascii=False, indent=2),
        f"Expected downstream outputs:\n{normalized['expected_downstream_outputs']}",
        "Dynamic downstream requirements:\n" + json.dumps(normalized["downstream_requirements"], ensure_ascii=False, indent=2),
        "Combined metric spec:\n" + json.dumps(normalized["combined_metric_spec"], ensure_ascii=False, indent=2),
    ]
    return "\n\n".join(sections)


def _normalize_component_value(value: float, normalization: Dict[str, Any], goal: str) -> float:
    min_value = float(normalization["min"])
    max_value = float(normalization["max"])
    clipped = min(max(value, min_value), max_value)
    normalized = (clipped - min_value) / (max_value - min_value)
    if goal == "minimize":
        normalized = 1.0 - normalized
    return min(max(normalized, 0.0), 1.0)


def compute_combined_score(metrics_payload: Dict[str, Any], combined_metric_spec: Dict[str, Any]) -> float:
    spec = _validate_combined_metric_spec(combined_metric_spec)
    if not isinstance(metrics_payload, dict):
        raise ValueError("metrics_payload must be a JSON object")
    weighted_sum = 0.0
    active_weight_sum = 0.0
    for component in spec["components"]:
        key = component["key"]
        raw_value = metrics_payload.get(key)
        if raw_value is None:
            if component["required"]:
                raise ValueError(f"Required combined-score component '{key}' is missing")
            continue
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            if component["required"]:
                raise ValueError(f"Required combined-score component '{key}' must be numeric") from None
            continue
        normalized_value = _normalize_component_value(
            numeric_value,
            component["normalization"],
            component["goal"],
        )
        weighted_sum += component["weight"] * normalized_value
        active_weight_sum += component["weight"]
    if active_weight_sum <= 0:
        raise ValueError("No combined-score components were available for scoring")
    return weighted_sum / active_weight_sum

