from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable

from backend.objectives import get_objective


MAX_DAG_PATHS = 100
DAG_EXECUTOR_MANAGED_PARAM_KEYS = {"input_h5ad_path", "output_h5ad_path", "output_dir", "method"}
VALID_RETENTION_INTENTS = {
    "required_checkpoint",
    "active_branch_output",
    "candidate_until_evaluated",
    "final_output",
    "lightweight_summary",
    "recomputable_intermediate",
    "ephemeral",
}


class DecisionValidationError(ValueError):
    pass


def extract_json_payload(text: str, tag: str | None = None) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if tag:
        match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", raw, flags=re.DOTALL | re.IGNORECASE)
        if not match:
            raise DecisionValidationError(f"Missing <{tag}> payload")
        raw = match.group(1).strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DecisionValidationError(f"Invalid JSON payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise DecisionValidationError("Payload must be a JSON object")
    return payload


def validate_tool_consultant_decision(payload: Dict[str, Any], *, available_stages: Iterable[str] | None = None) -> Dict[str, Any]:
    if "decision" in payload:
        raise DecisionValidationError(
            "Legacy 'decision' payloads are no longer supported; use dag_plan, implementation_plan, or research_brief."
        )
    return validate_composable_tool_decision(payload, available_stages=available_stages)


def validate_composable_tool_decision(payload: Dict[str, Any], *, available_stages: Iterable[str] | None = None) -> Dict[str, Any]:
    dag_plan = _dict_or_none(payload.get("dag_plan"))
    implementation_plan = _dict_or_none(payload.get("implementation_plan"))
    research_brief = _dict_or_none(payload.get("research_brief"))
    if not any([dag_plan, implementation_plan, research_brief]):
        raise DecisionValidationError("At least one of dag_plan, implementation_plan, or research_brief must be present")
    if research_brief and (dag_plan or implementation_plan):
        raise DecisionValidationError("research_brief is mutually exclusive with dag_plan and implementation_plan")
    objective_name = _optional_str(payload, "objective_name")
    if dag_plan and objective_name and not _optional_str(dag_plan, "objective_name"):
        dag_plan = dict(dag_plan)
        dag_plan["objective_name"] = objective_name
    out = {
        "task": str(payload.get("task") or "unknown").strip() or "unknown",
        "reason": str(payload.get("reason") or "").strip(),
        "objective_name": objective_name,
        "dag_plan": validate_dag_plan(dag_plan, available_stages=available_stages) if dag_plan else None,
        "implementation_plan": validate_implementation_plan(implementation_plan) if implementation_plan else None,
        "research_brief": research_brief,
        "output_retention_policy": validate_output_retention_policy(payload.get("output_retention_policy")),
    }
    return out


def validate_dag_plan(payload: Dict[str, Any], *, available_stages: Iterable[str] | None = None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise DecisionValidationError("dag_plan must be an object")
    input_h5ad_path = _required_str(payload, "input_h5ad_path")
    layers = payload.get("layers")
    if not isinstance(layers, list) or not layers:
        raise DecisionValidationError("dag_plan requires non-empty layers list")
    available = set(available_stages or [])
    total_paths = 1
    normalized_layers: list[dict[str, Any]] = []
    for layer_idx, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise DecisionValidationError(f"layers[{layer_idx}] must be an object")
        stage = _required_str(layer, "tool")
        if available and stage not in available:
            raise DecisionValidationError(f"layers[{layer_idx}].tool is not a registered tool: {stage}")
        variants = layer.get("variants")
        if not isinstance(variants, list) or not variants:
            raise DecisionValidationError(f"layers[{layer_idx}].variants must be a non-empty list")
        normalized_variants: list[dict[str, Any]] = []
        for variant_idx, variant in enumerate(variants):
            if not isinstance(variant, dict):
                raise DecisionValidationError(f"layers[{layer_idx}].variants[{variant_idx}] must be an object")
            method = _required_str(variant, "method")
            params = variant.get("params") or {}
            if not isinstance(params, dict):
                raise DecisionValidationError(f"layers[{layer_idx}].variants[{variant_idx}].params must be an object")
            forbidden_params = sorted(set(params) & DAG_EXECUTOR_MANAGED_PARAM_KEYS)
            if forbidden_params:
                joined = ", ".join(forbidden_params)
                raise DecisionValidationError(
                    f"layers[{layer_idx}].variants[{variant_idx}].params contains executor-managed key(s): {joined}. "
                    "ToolConsultant must put method at variant.method and let DagExecutor provide "
                    "input_h5ad_path, output_h5ad_path, and output_dir."
                )
            normalized_variants.append({"method": method, "params": params})
        total_paths *= len(normalized_variants)
        normalized_layers.append({"tool": stage, "variants": normalized_variants})
    if total_paths > MAX_DAG_PATHS:
        raise DecisionValidationError(f"DAG plan produces {total_paths} paths, exceeding the {MAX_DAG_PATHS}-path cap")
    objective_name = _optional_str(payload, "objective_name")
    if total_paths > 1:
        if not objective_name:
            raise DecisionValidationError("Multi-path DAG requires objective_name for ranking")
        spec = get_objective(objective_name)
        if spec is None or not spec.available:
            raise DecisionValidationError(f"Multi-path DAG requires an available objective, got {objective_name!r}")
    evaluation = _dict_or_none(payload.get("evaluation")) or {}
    _validate_evaluation_refs(evaluation, normalized_layers)
    return {
        "input_h5ad_path": input_h5ad_path,
        "output_dir": str(payload.get("output_dir") or "").strip(),
        "objective_name": objective_name,
        "evaluation": evaluation,
        "layers": normalized_layers,
        "output_retention_policy": validate_output_retention_policy(payload.get("output_retention_policy")),
    }


def validate_output_retention_policy(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise DecisionValidationError("output_retention_policy must be a list")
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            raise DecisionValidationError(f"output_retention_policy[{idx}] must be an object")
        output_id = str(item.get("output_id") or "").strip()
        semantic_type = str(item.get("semantic_type") or "unknown").strip() or "unknown"
        retention_intent = str(item.get("retention_intent") or "").strip()
        if not output_id:
            raise DecisionValidationError(f"output_retention_policy[{idx}].output_id is required")
        if retention_intent not in VALID_RETENTION_INTENTS:
            raise DecisionValidationError(
                f"output_retention_policy[{idx}].retention_intent must be one of {sorted(VALID_RETENTION_INTENTS)}"
            )
        normalized.append(
            {
                "output_id": output_id,
                "semantic_type": semantic_type,
                "retention_intent": retention_intent,
                "reason": str(item.get("reason") or "").strip(),
            }
        )
    return normalized


def _validate_evaluation_refs(evaluation: Dict[str, Any], layers: list[dict[str, Any]]) -> None:
    """Reject any $L{n}.key syntax in evaluation — outputs are auto-wired from declared_outputs."""
    for field, value in evaluation.items():
        if isinstance(value, str) and value.strip().startswith("$L"):
            raise DecisionValidationError(
                f"evaluation.{field} = {value!r} uses '$L{{n}}.key' syntax which is no longer "
                "supported. Remove embedding_key and cluster_key from evaluation — they are "
                "forwarded automatically from whichever step declared them."
            )


def validate_implementation_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    goal = _required_str(payload, "goal")
    inputs = _dict_or_none(payload.get("inputs")) or {}
    depends_on_dag = bool(payload.get("depends_on_dag", False))
    if not inputs:
        raise DecisionValidationError("implementation_plan requires non-empty inputs dict")
    if depends_on_dag and not _has_dag_input_reference(inputs.values()):
        raise DecisionValidationError(
            "implementation_plan with depends_on_dag=true must have at least one input "
            "referencing dag_output.path_dir, dag_output.artifacts.<name>, "
            "dag_output.resolved_outputs.<name>, or dag_output.artifacts"
        )
    for key, value in inputs.items():
        if _is_placeholder(value):
            raise DecisionValidationError(
                f"implementation_plan.inputs['{key}'] contains placeholder {value!r}; "
                "use concrete values or DAG-derived references."
            )
    return {
        "script_name": str(payload.get("script_name") or "solution.py").strip() or "solution.py",
        "goal": goal,
        "depends_on_dag": depends_on_dag,
        "dag_input_source": str(payload.get("dag_input_source") or "best_path").strip() or "best_path",
        "inputs": inputs,
        "outputs": _dict_or_none(payload.get("outputs")) or {},
        "required_steps": _list_or_empty(payload.get("required_steps")),
        "success_metric": str(payload.get("success_metric") or "").strip(),
        "constraints": _list_or_empty(payload.get("constraints")),
    }


def _has_dag_input_reference(values: Iterable[Any]) -> bool:
    for value in values:
        if value == "dag_output.path_dir" or value == "dag_output.artifacts":
            return True
        if isinstance(value, str) and (
            value.startswith("dag_output.artifacts.") or value.startswith("dag_output.resolved_outputs.")
        ):
            return True
    return False


def _is_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    return text.startswith("<") and text.endswith(">")


def _required_str(payload: Dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise DecisionValidationError(f"Missing required string field: {key}")
    return value


def _optional_str(payload: Dict[str, Any], key: str) -> str | None:
    value = str(payload.get(key) or "").strip()
    return value or None


def _dict_or_none(value: Any) -> Dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise DecisionValidationError("Expected object or null")
    return value


def _list_or_empty(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise DecisionValidationError("Expected list")
    return value


def summarize_tool_specs(specs: Iterable[Dict[str, Any]], *, max_tools: int = 80) -> str:
    lines: list[str] = []
    for idx, spec in enumerate(specs):
        if idx >= max_tools:
            lines.append(f"... {max_tools}+ tools available; omitted for context size.")
            break
        name = str(spec.get("name") or "").strip()
        desc = " ".join(str(spec.get("description") or "").split())
        params = spec.get("parameters", {})
        required: set[str] = set()
        properties: Dict[str, Any] = {}
        if isinstance(params, dict) and isinstance(params.get("properties"), dict):
            properties = params["properties"]
            raw_required = params.get("required", [])
            if isinstance(raw_required, list):
                required = {str(item) for item in raw_required}
        args = _summarize_schema_properties(properties, required=required)
        lines.append(f"- {name}: {desc} Args: {args if args else '<none>'}")
    return "\n".join(lines)


def _summarize_schema_properties(properties: Dict[str, Any], *, required: set[str]) -> str:
    parts: list[str] = []
    for name in sorted(properties):
        schema = properties.get(name)
        if not isinstance(schema, dict):
            parts.append(f"{name}{'*' if name in required else ''}")
            continue
        parts.append(_summarize_schema_property(name, schema, required=name in required))
    return "; ".join(parts)


def _summarize_schema_property(name: str, schema: Dict[str, Any], *, required: bool) -> str:
    label = f"{name}{'*' if required else ''}"
    details: list[str] = []
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        details.append("|".join(str(item) for item in schema_type))
    elif schema_type:
        details.append(str(schema_type))
    if "enum" in schema and isinstance(schema["enum"], list):
        details.append(f"enum=[{', '.join(_short_literal(item) for item in schema['enum'])}]")
    if "const" in schema:
        details.append(f"const={_short_literal(schema['const'])}")
    bounds = _schema_bounds(schema)
    if bounds:
        details.append(bounds)
    if "default" in schema:
        details.append(f"default={_short_literal(schema['default'])}")
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        item_type = item_schema.get("type")
        if item_type:
            details.append(f"items={item_type}")
        if isinstance(item_schema.get("enum"), list):
            details.append(f"items_enum=[{', '.join(_short_literal(item) for item in item_schema['enum'])}]")
    description = " ".join(str(schema.get("description") or "").split())
    if description:
        details.append(f"desc={_truncate(description, 90)}")
    if not details:
        return label
    return f"{label} ({', '.join(details)})"


def _schema_bounds(schema: Dict[str, Any]) -> str:
    bounds: list[str] = []
    for key, marker in (
        ("minimum", "min"),
        ("exclusiveMinimum", "gt"),
        ("maximum", "max"),
        ("exclusiveMaximum", "lt"),
        ("minLength", "min_len"),
        ("maxLength", "max_len"),
        ("minItems", "min_items"),
        ("maxItems", "max_items"),
    ):
        if key in schema:
            bounds.append(f"{marker}={_short_literal(schema[key])}")
    return " ".join(bounds)


def _short_literal(value: Any) -> str:
    if isinstance(value, str):
        return _truncate(value, 40)
    return _truncate(json.dumps(value, ensure_ascii=False), 40)


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)] + "..."
