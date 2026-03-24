import json
from typing import Any, Dict, List, Tuple

import textgrad as tg
from dotenv import load_dotenv

from consultant import _short
from config import Config
from evaluator_prompts import JOINT_EVALUATOR_SYSTEM_PROMPT, JOINT_FORMAT_STRING
from multieval_types import STAGE_FILENAMES

load_dotenv()


def _validate_feedback_payload(feedback: Dict[str, Any]) -> None:
    required_feedback_keys = [
        "diagnosis",
        "strategy",
        "strategy_source",
        "expected_metric_effect",
        "failed_architectures",
        "evidence_for_consultant",
        "focus_areas",
        "bottleneck_reason",
        "keep_fixed",
        "change_next",
        "stop_exploit_if",
    ]
    missing_feedback = [key for key in required_feedback_keys if key not in feedback]
    if missing_feedback:
        raise ValueError(f"Evaluator feedback missing required keys: {missing_feedback}")


def _validate_scoped_instruction_list(name: str, items: Any) -> None:
    if not isinstance(items, list):
        raise ValueError(f"Evaluator feedback {name} must be a list")
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        if not any(text.startswith(f"{filename}:") for filename in STAGE_FILENAMES):
            raise ValueError(
                f"Evaluator feedback {name} entries must be file-scoped like '<filename>.py: ...'; got: {text}"
            )


def parse_eval_action(text: str) -> tuple[dict, dict]:
    stripped = (text or "").strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        raise ValueError("Evaluator output must be a single JSON object with no wrapper tags or extra text")
    payload = json.loads(stripped)
    required_keys = [
        "step",
        "primary_reason",
        "performance",
        "training_health",
        "biological_assessment",
        "architecture",
        "optimize_targets",
        "feedback",
    ]
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError(f"Evaluator payload missing required keys: {missing}")
    targets = []
    for item in payload.get("optimize_targets", []):
        target = str(item).strip()
        if not target:
            continue
        if target not in STAGE_FILENAMES:
            raise ValueError(f"Unsupported optimize target: {target}")
        targets.append(target)
    payload["optimize_targets"] = targets
    feedback = payload.get("feedback", {})
    if not isinstance(feedback, dict):
        raise ValueError("Evaluator feedback must be a JSON object")
    _validate_feedback_payload(feedback)
    _validate_scoped_instruction_list("keep_fixed", feedback.get("keep_fixed", []))
    _validate_scoped_instruction_list("change_next", feedback.get("change_next", []))
    return payload, feedback


def exploit_plan_from_feedback(feedback: Dict[str, Any]) -> Dict[str, Any]:
    keep_fixed = feedback.get("keep_fixed", []) if isinstance(feedback, dict) else []
    change_next = feedback.get("change_next", []) if isinstance(feedback, dict) else []
    return {
        "diagnosis": str(feedback.get("diagnosis", "")).strip() if isinstance(feedback, dict) else "",
        "strategy": str(feedback.get("strategy", "")).strip() if isinstance(feedback, dict) else "",
        "expected_metric_effect": str(feedback.get("expected_metric_effect", "")).strip() if isinstance(feedback, dict) else "",
        "focus_areas": [str(item).strip() for item in feedback.get("focus_areas", []) if str(item).strip()] if isinstance(feedback, dict) else [],
        "bottleneck_reason": str(feedback.get("bottleneck_reason", "")).strip() if isinstance(feedback, dict) else "",
        "keep_fixed": [str(item).strip() for item in keep_fixed if str(item).strip()],
        "change_next": [str(item).strip() for item in change_next if str(item).strip()],
        "stop_exploit_if": str(feedback.get("stop_exploit_if", "")).strip() if isinstance(feedback, dict) else "",
    }


def to_float(x: Any) -> float | None:
    try:
        return float(x) if x is not None else None
    except Exception:
        return None


def build_open_issues(*, run_result: Dict[str, Any], primary_state: Dict[str, Any], payload: Dict[str, Any], feedback: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if not run_result.get("success", False):
        target = str(run_result.get("failed_script") or STAGE_FILENAMES[0])
        issues.append(f"run_failed:{target}")
    gain = to_float(primary_state.get("primary_metric_gain"))
    if gain is None or gain <= 0:
        issues.append("no_meaningful_primary_gain")
    diagnosis = (feedback.get("diagnosis") if isinstance(feedback, dict) else "") or ""
    if diagnosis.strip():
        issues.append(f"diagnosis:{_short(diagnosis, 180)}")
    seen = set()
    out: List[str] = []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            out.append(issue)
    return out


def build_instruction_text(feedback: Dict[str, Any]) -> str:
    focus_areas = feedback.get("focus_areas", []) if isinstance(feedback, dict) else []
    bottleneck_reason = str(feedback.get("bottleneck_reason", "")).strip() if isinstance(feedback, dict) else ""
    keep_fixed = feedback.get("keep_fixed", []) if isinstance(feedback, dict) else []
    change_next = feedback.get("change_next", []) if isinstance(feedback, dict) else []
    stop_exploit_if = str(feedback.get("stop_exploit_if", "")).strip() if isinstance(feedback, dict) else ""
    lines = ["[Focus Areas]"]
    lines.extend(f"- {item}" for item in focus_areas or ["<none>"])
    if bottleneck_reason:
        lines.append("")
        lines.append(f"[Bottleneck Reason]\n- {bottleneck_reason}")
    lines.append("")
    lines.append("[Keep Fixed]")
    lines.extend(f"- {item}" for item in keep_fixed or ["<none>"])
    lines.append("")
    lines.append("[Change Next]")
    lines.extend(f"- {item}" for item in change_next or ["<none>"])
    if stop_exploit_if:
        lines.append("")
        lines.append(f"[Stop Exploit If]\n- {stop_exploit_if}")
    return "\n".join(lines)


def update_primary_metric_state(cluster_metrics: Dict[str, Any], best_ari: float | None, best_sil: float | None, delta_min: float, stagnation_steps: int) -> Tuple[float | None, float | None, int, Dict[str, Any]]:
    cur_ari = to_float(cluster_metrics.get("ari") if isinstance(cluster_metrics, dict) else None)
    cur_sil = to_float(cluster_metrics.get("silhouette") if isinstance(cluster_metrics, dict) else None)
    cur_nmi = to_float(cluster_metrics.get("nmi") if isinstance(cluster_metrics, dict) else None)
    gain = None if cur_ari is None or best_ari is None else cur_ari - best_ari
    if cur_ari is None:
        stagnation_steps += 1
    elif best_ari is None or gain is None or gain > delta_min:
        stagnation_steps = 0
    else:
        stagnation_steps += 1
    if cur_ari is not None:
        best_ari = cur_ari if best_ari is None else max(best_ari, cur_ari)
    if cur_sil is not None:
        best_sil = cur_sil if best_sil is None else max(best_sil, cur_sil)
    return best_ari, best_sil, stagnation_steps, {
        "current_ari": cur_ari,
        "current_silhouette": cur_sil,
        "current_nmi": cur_nmi,
        "previous_best_ari": best_ari,
        "previous_best_silhouette": best_sil,
        "previous_best_nmi": None,
        "primary_metric_gain": gain,
    }


class TextGradEvaluator:
    def __init__(self, config: Config, engine_name: str, task_decrp: str, background: str = "Not available", eval_type: str = "joint"):
        if eval_type != "joint":
            raise ValueError("Only the joint evaluator is supported")
        self.config = config
        self.engine_name = engine_name
        self.engine = tg.get_engine(engine_name, max_tokens=7000)
        format_string = JOINT_FORMAT_STRING.format(
            task=task_decrp,
            step="{step}",
            metrics=self.config.metrics,
            time_budget=config.timeout,
            notes="{notes}",
            suggestion="{suggestion}",
            training_history="{training_history}",
            stagnation_steps="{stagnation_steps}",
            delta_min="{delta_min}",
            current_performance="{current_performance}",
            data_prior_code="{data_prior_code}",
            model_training_code="{model_training_code}",
            downstream_analysis_code="{downstream_analysis_code}",
            paths="{paths}",
            data_schema="{data_schema}",
            prior_schema="{prior_schema}",
            model_schema="{model_schema}",
            downstream_schema="{downstream_schema}",
            cluster_metrics="{cluster_metrics}",
            cluster_summary="{cluster_summary}",
            training_logs="{training_logs}",
            pipeline_summary="{pipeline_summary}",
        )
        fields = {
            "step": None,
            "notes": None,
            "suggestion": None,
            "training_history": None,
            "stagnation_steps": None,
            "delta_min": None,
            "current_performance": None,
            "data_prior_code": None,
            "model_training_code": None,
            "downstream_analysis_code": None,
            "paths": None,
            "data_schema": None,
            "prior_schema": None,
            "model_schema": None,
            "downstream_schema": None,
            "cluster_metrics": None,
            "cluster_summary": None,
            "training_logs": None,
            "pipeline_summary": None,
        }
        self.system_prompt = tg.Variable(JOINT_EVALUATOR_SYSTEM_PROMPT, requires_grad=False, role_description="system prompt to evaluate the three-stage pipeline")
        self.formatted_llm_call = tg.autograd.FormattedLLMCall(engine=self.engine, format_string=format_string, fields=fields, system_prompt=self.system_prompt)

    def loss_fn(self, *, notes: tg.Variable, step, data_prior_code: tg.Variable, model_training_code: tg.Variable, downstream_analysis_code: tg.Variable, suggestion: tg.Variable, training_history: tg.Variable, stagnation_steps: tg.Variable, delta_min: tg.Variable, current_performance: tg.Variable, paths: tg.Variable, data_schema: tg.Variable, prior_schema: tg.Variable, model_schema: tg.Variable, downstream_schema: tg.Variable, cluster_metrics: tg.Variable, cluster_summary: tg.Variable, training_logs: tg.Variable, pipeline_summary: tg.Variable):
        step_var = tg.Variable(step, requires_grad=False, role_description="step counter")
        return self.formatted_llm_call(
            inputs={
                "step": step_var,
                "notes": notes,
                "suggestion": suggestion,
                "training_history": training_history,
                "stagnation_steps": stagnation_steps,
                "delta_min": delta_min,
                "current_performance": current_performance,
                "data_prior_code": data_prior_code,
                "model_training_code": model_training_code,
                "downstream_analysis_code": downstream_analysis_code,
                "paths": paths,
                "data_schema": data_schema,
                "prior_schema": prior_schema,
                "model_schema": model_schema,
                "downstream_schema": downstream_schema,
                "cluster_metrics": cluster_metrics,
                "cluster_summary": cluster_summary,
                "training_logs": training_logs,
                "pipeline_summary": pipeline_summary,
            },
            response_role_description="evaluation of the three-stage pipeline",
        )
