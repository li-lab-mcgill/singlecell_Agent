from __future__ import annotations
import json
import re
from typing import Any, Dict, List

from multieval_types import DecisionLedgerRecord, HistoryNoteRecord


def _short(text: str, max_chars: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."


def render_history_note_line(record: HistoryNoteRecord) -> str:
    issues = ";".join(record.open_issues[:3]) if record.open_issues else "none"
    exploit = ",".join(record.optimized_scripts) if record.optimized_scripts else "none"
    return (
        f"step={record.step} action={record.action} context={record.context_mode} "
        f"attempts={record.attempts_used} run_success={record.run_success} "
        f"failed_stage={record.failed_stage} design={record.architecture_fingerprint} "
        f"primary={record.primary_metric} value={record.metric_value} gain={record.gain} "
        f"stagnation={record.stagnation} exploit={exploit} issues={issues} "
        f"diagnosis={_short(record.evaluator_diagnosis, 160)}"
    )


def append_history_note(record: HistoryNoteRecord, *, outer_notes: List[HistoryNoteRecord], global_notes: List[HistoryNoteRecord], note_text_path: str, note_jsonl_path: str, mirror_jsonl_path: str | None = None) -> str:
    outer_notes.append(record)
    global_notes.append(record)
    line = render_history_note_line(record)
    with open(note_text_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    with open(note_jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    if mirror_jsonl_path:
        with open(mirror_jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    return line


def append_decision_record(record: DecisionLedgerRecord, *, decision_records: List[DecisionLedgerRecord], decision_jsonl_path: str, mirror_jsonl_path: str | None = None) -> None:
    decision_records.append(record)
    with open(decision_jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    if mirror_jsonl_path:
        with open(mirror_jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def _slugify(text: str, max_len: int = 32) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (normalized or "unknown")[:max_len]


def _detect_model_family(code: str) -> str:
    text = code.lower()
    if "scvi" in text or "zinb" in text or "negativebinomial" in text:
        return "scvi"
    if "vae" in text or "variational" in text or "kl_" in text:
        return "vae"
    if "autoencoder" in text:
        return "autoencoder"
    if "graph" in text or "gat" in text or "sage" in text:
        return "gnn"
    if "transformer" in text or "attention" in text:
        return "transformer"
    return "mlp"


def infer_design_identity(*, bundle_text: Dict[str, str], payload: Dict[str, Any], cluster_summary: Dict[str, Any]) -> tuple[str, str]:
    code = bundle_text.get("pipeline", "")
    architecture = payload.get("architecture", {}) if isinstance(payload, dict) else {}
    label = str(architecture.get("label", "")).strip() if isinstance(architecture, dict) else ""
    code_lower = code.lower()
    dataloader_block = code_lower
    prior_block = code_lower
    model_block = code_lower
    clustering_block = code_lower

    preprocess_flags: List[str] = []
    if "highly_variable_genes" in dataloader_block or "hvg" in dataloader_block:
        preprocess_flags.append("hvg")
    if "normalize_total" in dataloader_block or "size_factor" in dataloader_block:
        preprocess_flags.append("norm")
    if "log1p" in dataloader_block:
        preprocess_flags.append("log1p")
    if "scale(" in dataloader_block:
        preprocess_flags.append("scale")

    prior_type = "pathway" if "pathway" in prior_block else "graph" if "graph" in prior_block else "none"
    model_family = _detect_model_family(model_block)
    latent_match = re.search(r"(?:latent_dim|embedding_dim|z_dim)\s*[:=]\s*(\d+)", code, flags=re.IGNORECASE)
    latent_dim = latent_match.group(1) if latent_match else None
    clustering_method = str(cluster_summary.get("method", "")).strip().lower() or ("leiden" if "leiden" in clustering_block else "unknown-cluster")
    resolution = cluster_summary.get("resolution")

    fingerprint_parts = [prior_type]
    fingerprint_parts.extend(preprocess_flags or ["basic-prep"])
    fingerprint_parts.append(model_family)
    if latent_dim:
        fingerprint_parts.append(f"z{latent_dim}")
    fingerprint_parts.append(_slugify(clustering_method, 24))
    if resolution not in (None, ""):
        fingerprint_parts.append(f"res{_slugify(str(resolution), 12)}")
    if label:
        fingerprint_parts.append(_slugify(label, 24))
    fingerprint = "_".join(part for part in fingerprint_parts if part)[:160]

    summary_parts = [
        f"prior={prior_type}",
        f"prep={'+'.join(preprocess_flags) if preprocess_flags else 'basic'}",
        f"model={model_family}{f' latent={latent_dim}' if latent_dim else ''}",
        f"cluster={clustering_method}{f' res={resolution}' if resolution not in (None, '') else ''}",
    ]
    if label:
        summary_parts.insert(0, f"label={label}")
    return fingerprint or "unknown_design", "; ".join(summary_parts)


def _history_summary(records: List[HistoryNoteRecord]) -> str:
    if not records:
        return "<none>"
    action_counts: Dict[str, int] = {}
    failed_stage_counts: Dict[str, int] = {}
    issue_counts: Dict[str, int] = {}
    for record in records:
        action_counts[record.action] = action_counts.get(record.action, 0) + 1
        stage_key = str(record.failed_stage or "none")
        failed_stage_counts[stage_key] = failed_stage_counts.get(stage_key, 0) + 1
        for issue in record.open_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    top_issues = sorted(issue_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
    return (
        f"action_counts={action_counts}\n"
        f"failed_stage_counts={failed_stage_counts}\n"
        f"top_open_issues={top_issues}"
    )


def _best_design_lines(records: List[DecisionLedgerRecord], limit: int = 3) -> List[str]:
    scored = [record for record in records if record.metric_value is not None]
    if not scored:
        return ["<none>"]
    ranked = sorted(scored, key=lambda record: (record.metric_value, record.step), reverse=True)
    lines: List[str] = []
    seen = set()
    for record in ranked:
        if record.architecture_fingerprint in seen:
            continue
        seen.add(record.architecture_fingerprint)
        lines.append(f"{record.architecture_fingerprint} | ari={record.metric_value} | {_short(record.design_summary, 120)}")
        if len(lines) >= limit:
            break
    return lines or ["<none>"]


def _rejected_design_lines(records: List[DecisionLedgerRecord], limit: int = 5) -> List[str]:
    lines: List[str] = []
    seen = set()
    for record in reversed(records):
        if record.do_not_repeat and record.architecture_fingerprint not in seen:
            seen.add(record.architecture_fingerprint)
            lines.append(f"{record.architecture_fingerprint} | reason={_short(record.do_not_repeat_reason or record.decision_rationale, 140)}")
        for label in record.rejected_design_labels:
            key = f"label:{label}"
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"{label} | reason=reported_rejected_design")
        if len(lines) >= limit:
            break
    return lines[:limit] or ["<none>"]


def _top_failure_patterns(records: List[HistoryNoteRecord], limit: int = 5) -> List[str]:
    counts: Dict[str, int] = {}
    for record in records:
        if record.failure_fingerprint:
            counts[record.failure_fingerprint] = counts.get(record.failure_fingerprint, 0) + 1
    if not counts:
        return ["<none>"]
    return [f"{name} x{count}" for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _open_issue_lines(records: List[HistoryNoteRecord], limit: int = 5) -> List[str]:
    counts: Dict[str, int] = {}
    for record in records:
        for issue in record.open_issues:
            counts[issue] = counts.get(issue, 0) + 1
    if not counts:
        return ["<none>"]
    return [f"{name} x{count}" for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _recent_exploit_lines(records: List[HistoryNoteRecord], limit: int = 4) -> List[str]:
    lines: List[str] = []
    for record in reversed(records):
        if not record.exploit_applied:
            continue
        optimized = ",".join(record.optimized_scripts) if record.optimized_scripts else "none"
        lines.append(f"step={record.step} targets={optimized} outcome={record.fix_outcome}")
        if len(lines) >= limit:
            break
    return list(reversed(lines)) or ["<none>"]


def _exploit_failure_patterns(records: List[HistoryNoteRecord], limit: int = 5) -> List[str]:
    counts: Dict[str, int] = {}
    for record in records:
        prev = record.previous_exploit_context or {}
        if not prev.get("previous_step_exploit_applied"):
            continue
        targets = prev.get("previous_step_optimized_scripts", [])
        if not targets or record.run_success:
            continue
        key = f"after_exploit:{','.join(targets)}->{record.failed_stage or 'unknown'}"
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return ["<none>"]
    return [f"{name} x{count}" for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def build_history_digest(*, outer_notes: List[HistoryNoteRecord], global_notes: List[HistoryNoteRecord], decision_records: List[DecisionLedgerRecord], keep_last: int = 20) -> str:
    recent = global_notes[-keep_last:] if global_notes else []
    recent_lines = [render_history_note_line(record) for record in recent] or ["<none>"]
    sections = [
        "[Best Designs]",
        *(_best_design_lines(decision_records)),
        "",
        "[Rejected Designs]",
        *(_rejected_design_lines(decision_records)),
        "",
        "[Repeated Failure Patterns]",
        *(_top_failure_patterns(global_notes)),
        "",
        "[Open Issues]",
        *(_open_issue_lines(global_notes)),
        "",
        "[Recent Exploit Targets]",
        *(_recent_exploit_lines(global_notes)),
        "",
        "[Exploit Failure Patterns]",
        *(_exploit_failure_patterns(global_notes)),
        "",
        "[Recent Outcomes]",
        *recent_lines,
        "",
        "[Outer Loop Summary]",
        _history_summary(outer_notes),
    ]
    return "\n".join(sections)
