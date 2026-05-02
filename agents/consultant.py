from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from typing import Any, Dict, List, Set

from pipelines.multieval_types import ConsultantPlanRecord


logger = logging.getLogger(__name__)


def _short(text: str, max_chars: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."


def plan_fingerprint(task_description: str, suggestion: str, prior_schema: Dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "task_description": task_description or "",
            "suggestion": suggestion or "",
            "prior_schema": prior_schema if isinstance(prior_schema, dict) else {},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def record_consultant_plan(
    *,
    consultant_records: List[ConsultantPlanRecord],
    path: str,
    record: ConsultantPlanRecord,
) -> None:
    consultant_records.append(record)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def build_consultant_history_context(
    consultant_records: List[ConsultantPlanRecord],
    full_k: int = 3,
) -> str:
    if not consultant_records:
        return "<none>"
    older = consultant_records[:-full_k] if len(consultant_records) > full_k else []
    recent = consultant_records[-full_k:]
    lines = ["[CONSULTANT_HISTORY]"]
    if older:
        older_fps = {}
        for rec in older:
            older_fps[rec.plan_fingerprint] = older_fps.get(rec.plan_fingerprint, 0) + 1
        lines.append(f"older_summary_count={len(older)}")
        lines.append(f"older_fingerprint_counts={older_fps}")
    else:
        lines.append("older_summary_count=0")
    lines.append("[RECENT_FULL_PLANS]")
    for rec in recent:
        lines.extend(
            [
                f"step={rec.step} source={rec.source} fingerprint={rec.plan_fingerprint}",
                f"task={_short(rec.task_description, 300)}",
                f"suggestion={_short(rec.suggestion, 1200)}",
                f"prior_schema={json.dumps(rec.prior_schema_json, ensure_ascii=False)[:1200]}",
            ]
        )
    return "\n".join(lines)


def _validate_prior_schema(prior_schema: Dict[str, Any]) -> None:
    if not isinstance(prior_schema, dict):
        raise ValueError("Consultant PRIOR_SCHEMA_JSON must decode to a JSON object")
    placeholder_pattern = re.compile(
        r"^(column_[a-z0-9]+|col\d+|field[_-]?\d+|artifact[_-]?\d+|file\d+\.[a-z0-9]+)$",
        re.IGNORECASE,
    )
    output_files = prior_schema.get("output_files")
    if output_files is None:
        output_files = prior_schema.get("required_files")
    if output_files is None:
        output_files = [prior_schema]
    if not isinstance(output_files, list) or not output_files:
        raise ValueError("Consultant PRIOR_SCHEMA_JSON must include a non-empty output_files list or a single file object")

    for item in output_files:
        if not isinstance(item, dict):
            raise ValueError("Each PRIOR_SCHEMA_JSON output_files entry must be an object")
        file_name = str(item.get("file_name") or "").strip()
        description = str(item.get("description") or "").strip()
        dtype = str(item.get("dtype") or "").strip()
        if not file_name or not description or not dtype:
            raise ValueError("Each PRIOR_SCHEMA_JSON file entry must include non-empty file_name, description, and dtype")
        if placeholder_pattern.match(file_name):
            raise ValueError(f"Consultant PRIOR_SCHEMA_JSON uses placeholder file name: {file_name}")
        shape = item.get("shape")
        if shape is not None:
            if shape == []:
                continue
            if not isinstance(shape, list) or not all(isinstance(dim, str) and dim.strip() for dim in shape):
                raise ValueError("Consultant PRIOR_SCHEMA_JSON shape must be a non-empty list of symbolic dimension strings when provided")


def _infer_schema_dtype(file_name: str, raw_dtype: Any) -> str:
    dtype = str(raw_dtype or "").strip()
    if dtype:
        return dtype
    suffix = os.path.splitext(str(file_name or "").strip())[1].lower()
    inferred = {
        ".csv": "csv",
        ".tsv": "tsv",
        ".txt": "txt",
        ".json": "json",
        ".jsonl": "jsonl",
        ".npy": "npy",
        ".npz": "npz",
        ".pt": "pt",
        ".pth": "pt",
        ".pkl": "pkl",
        ".parquet": "parquet",
        ".h5": "h5",
        ".h5ad": "h5ad",
    }.get(suffix)
    return inferred or "binary"


def _normalize_shape(shape: Any) -> Any:
    if shape is None:
        return None
    if isinstance(shape, list):
        normalized = [str(dim).strip() for dim in shape if str(dim).strip()]
        return normalized or None
    if isinstance(shape, str):
        cleaned = shape.strip()
        if not cleaned:
            return None
        cleaned = cleaned.strip("[]()")
        parts = [part.strip() for part in re.split(r"[,\u00d7x]", cleaned) if part.strip()]
        return parts or [shape.strip()]
    return None


def _normalize_prior_file_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(item)
    file_name = str(
        item.get("file_name")
        or item.get("filename")
        or item.get("file")
        or item.get("path")
        or item.get("output_file")
        or item.get("name")
        or ""
    ).strip()
    description = str(
        item.get("description")
        or item.get("purpose")
        or item.get("summary")
        or item.get("contents")
        or item.get("content")
        or item.get("notes")
        or ""
    ).strip()
    dtype = _infer_schema_dtype(
        file_name,
        item.get("dtype") or item.get("type") or item.get("format") or item.get("file_type"),
    )
    shape = _normalize_shape(item.get("shape") or item.get("dimensions") or item.get("dims"))
    normalized.pop("shape", None)
    normalized.pop("dimensions", None)
    normalized.pop("dims", None)

    normalized["file_name"] = file_name
    normalized["dtype"] = dtype
    if description:
        normalized["description"] = description
    elif file_name:
        normalized["description"] = f"Prior artifact generated at {file_name}"
    if shape is not None:
        normalized["shape"] = shape
    return normalized


def _normalize_prior_schema(prior_schema: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(prior_schema, dict):
        return prior_schema
    output_files = prior_schema.get("output_files")
    if output_files is None:
        output_files = prior_schema.get("required_files")
    if output_files is None:
        output_files = [prior_schema]
    if not isinstance(output_files, list):
        return prior_schema

    normalized_files: List[Dict[str, Any]] = []
    dropped_entries = 0
    for item in output_files:
        if not isinstance(item, dict):
            dropped_entries += 1
            continue
        normalized_item = _normalize_prior_file_entry(item)
        if normalized_item.get("file_name"):
            normalized_files.append(normalized_item)
        else:
            dropped_entries += 1

    normalized_schema = dict(prior_schema)
    normalized_schema["output_files"] = normalized_files
    if dropped_entries:
        logger.warning(
            "Dropped %d malformed PRIOR_SCHEMA_JSON output_files entries during normalization",
            dropped_entries,
        )
    return normalized_schema


def _validate_prior_decision(prior_decision: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(prior_decision, dict):
        raise ValueError("Consultant PRIOR_DECISION_JSON must decode to a JSON object")
    use_priors = prior_decision.get("use_priors")
    if not isinstance(use_priors, bool):
        raise ValueError("Consultant PRIOR_DECISION_JSON use_priors must be a boolean")
    decision_reason = str(prior_decision.get("decision_reason", "")).strip()
    if not decision_reason:
        raise ValueError("Consultant PRIOR_DECISION_JSON decision_reason must be a non-empty string")
    selected_resource_names = prior_decision.get("selected_resource_names", [])
    if not isinstance(selected_resource_names, list):
        raise ValueError("Consultant PRIOR_DECISION_JSON selected_resource_names must be a list")
    return {
        "use_priors": use_priors,
        "decision_reason": decision_reason,
        "selected_resource_names": [str(item).strip() for item in selected_resource_names if str(item).strip()],
    }


def _extract_tag_payload(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", str(text or ""), flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"Missing <{tag}> block")
    return match.group(1).strip()


def validate_candidate_comparison(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("candidate comparison must be a JSON object")
    candidates = payload.get("candidate_approaches")
    if not isinstance(candidates, list) or len(candidates) < 3:
        raise ValueError("candidate comparison must include at least 3 candidate approaches")
    normalized_candidates: List[Dict[str, Any]] = []
    labels: Set[str] = set()
    for idx, item in enumerate(candidates):
        if not isinstance(item, dict):
            raise ValueError(f"candidate_approaches[{idx}] must be an object")
        label = str(item.get("label", "")).strip()
        summary = str(item.get("summary", "")).strip()
        if not label or not summary:
            raise ValueError(f"candidate_approaches[{idx}] must include non-empty label and summary")
        if label in labels:
            raise ValueError(f"Duplicate candidate label: {label}")
        labels.add(label)
        pros = [str(x).strip() for x in item.get("pros", []) if str(x).strip()]
        cons = [str(x).strip() for x in item.get("cons", []) if str(x).strip()]
        normalized_candidates.append({"label": label, "summary": summary, "pros": pros, "cons": cons})
    selected_label = str(payload.get("selected_label", "")).strip()
    if selected_label not in labels:
        raise ValueError("selected_label must match one of the candidate labels")
    selection_reason = str(payload.get("selection_reason", "")).strip()
    if not selection_reason:
        raise ValueError("selection_reason must be non-empty")
    return {
        "candidate_approaches": normalized_candidates,
        "selected_label": selected_label,
        "selection_reason": selection_reason,
    }


def validate_prior_decision_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    decision = _validate_prior_decision(payload)
    prior_schema = _normalize_prior_schema(payload.get("prior_schema", {"output_files": []}))
    if decision["use_priors"]:
        _validate_prior_schema(prior_schema)
    else:
        prior_schema = {"output_files": []}
    return {
        **decision,
        "prior_schema": prior_schema,
    }


def validate_implementation_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("implementation plan must be a JSON object")
    task_summary = str(payload.get("task_summary", "")).strip()
    chosen_approach = str(payload.get("chosen_approach", "")).strip()
    if not task_summary or not chosen_approach:
        raise ValueError("implementation plan must include non-empty task_summary and chosen_approach")
    prior_decision_summary = str(payload.get("prior_decision_summary", "")).strip()
    stage_plan = payload.get("stage_plan")
    if not isinstance(stage_plan, dict):
        raise ValueError("implementation plan stage_plan must be an object")
    normalized_stage_plan = {
        filename: str(stage_plan.get(filename, "")).strip()
        for filename in ["prior_construction.py", "data_preprocess.py", "model_training.py", "downstream_analysis.py"]
    }
    artifact_expectations = payload.get("artifact_expectations", {})
    if not isinstance(artifact_expectations, dict):
        artifact_expectations = {}
    open_risks = [str(x).strip() for x in payload.get("open_risks", []) if str(x).strip()]
    return {
        "task_summary": task_summary,
        "chosen_approach": chosen_approach,
        "prior_decision_summary": prior_decision_summary,
        "stage_plan": normalized_stage_plan,
        "artifact_expectations": artifact_expectations,
        "open_risks": open_risks,
    }


def format_prior_plan_text(prior_decision: Dict[str, Any]) -> str:
    lines = [
        f"Use priors: {bool(prior_decision.get('use_priors', False))}",
        f"Decision reason: {str(prior_decision.get('decision_reason', '')).strip()}",
    ]
    selected = prior_decision.get("selected_resource_names", [])
    if isinstance(selected, list) and selected:
        lines.append("Selected resources: " + ", ".join(str(x).strip() for x in selected if str(x).strip()))
    schema = prior_decision.get("prior_schema", {})
    output_files = schema.get("output_files", []) if isinstance(schema, dict) else []
    if output_files:
        lines.append("Prior artifacts:")
        for item in output_files:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {str(item.get('file_name', '')).strip()} ({str(item.get('dtype', '')).strip()}): "
                f"{str(item.get('description', '')).strip()}"
            )
    return "\n".join(line for line in lines if line.strip())


def format_implementation_plan_text(plan: Dict[str, Any]) -> str:
    lines = [
        f"Task summary: {str(plan.get('task_summary', '')).strip()}",
        f"Chosen approach: {str(plan.get('chosen_approach', '')).strip()}",
    ]
    prior_summary = str(plan.get("prior_decision_summary", "")).strip()
    if prior_summary:
        lines.append(f"Prior decision summary: {prior_summary}")
    stage_plan = plan.get("stage_plan", {})
    if isinstance(stage_plan, dict):
        for filename in ["prior_construction.py", "data_preprocess.py", "model_training.py", "downstream_analysis.py"]:
            value = str(stage_plan.get(filename, "")).strip()
            if value:
                lines.append(f"{filename}: {value}")
    risks = [str(x).strip() for x in plan.get("open_risks", []) if str(x).strip()]
    if risks:
        lines.append("Open risks:")
        lines.extend(f"- {item}" for item in risks)
    return "\n".join(lines)
