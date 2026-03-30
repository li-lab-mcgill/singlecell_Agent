from __future__ import annotations
import json
from typing import Any, Dict, List, Tuple

import textgrad as tg
from dotenv import load_dotenv

from consultant import _short
from config import Config
from evaluator_prompts import JOINT_EVALUATOR_SYSTEM_PROMPT, JOINT_FORMAT_STRING

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
    if not isinstance(feedback.get("failed_architectures"), list):
        raise ValueError("Evaluator feedback failed_architectures must be a list")
    if not isinstance(feedback.get("evidence_for_consultant"), list):
        raise ValueError("Evaluator feedback evidence_for_consultant must be a list")
    for key in ["focus_areas", "keep_fixed", "change_next"]:
        value = feedback.get(key)
        if not isinstance(value, list):
            raise ValueError(f"Evaluator feedback {key} must be a list")
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError(f"Evaluator feedback {key} must contain non-empty strings")
    bottleneck_reason = feedback.get("bottleneck_reason")
    if not isinstance(bottleneck_reason, str) or not bottleneck_reason.strip():
        raise ValueError("Evaluator feedback bottleneck_reason must be a non-empty string")
    stop_exploit_if = feedback.get("stop_exploit_if")
    if not isinstance(stop_exploit_if, str) or not stop_exploit_if.strip():
        raise ValueError("Evaluator feedback stop_exploit_if must be a non-empty string")


def parse_eval_action(text: str) -> tuple[str, dict, dict]:
    stripped = (text or "").strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        raise ValueError("Evaluator output must be a single JSON object with no wrapper tags or extra text")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Evaluator output is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Evaluator output must decode to a JSON object")
    required_keys = [
        "step",
        "action",
        "primary_reason",
        "performance",
        "training_health",
        "biological_assessment",
        "architecture",
        "feedback",
    ]
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError(f"Evaluator payload missing required keys: {missing}")
    action = str(payload.get("action", "exploit")).strip().lower()
    if action not in {"exploit", "reconsult"}:
        raise ValueError(f"Unsupported evaluator action: {action}")
    feedback = payload.get("feedback", {})
    if not isinstance(feedback, dict):
        raise ValueError("Evaluator feedback must be a JSON object")
    _validate_feedback_payload(feedback)
    return action, payload, feedback


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
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def build_open_issues(*, run_result: Dict[str, Any], primary_state: Dict[str, Any], payload: Dict[str, Any], feedback: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if not run_result.get("success", False):
        issues.append(f"run_failed:{run_result.get('failed_stage') or 'unknown'}")
    gain = to_float(primary_state.get("primary_metric_gain"))
    if gain is None or gain <= 0:
        issues.append("no_meaningful_primary_gain")
    training_health = payload.get("training_health", {}) if isinstance(payload, dict) else {}
    detected = training_health.get("issues_detected", []) if isinstance(training_health, dict) else []
    if isinstance(detected, list):
        for item in detected:
            if str(item).lower() != "none":
                issues.append(f"training:{item}")
    bio = payload.get("biological_assessment", {}) if isinstance(payload, dict) else {}
    if isinstance(bio, dict):
        bad_clusters = bio.get("clusters_without_identity")
        if isinstance(bad_clusters, int) and bad_clusters > 0:
            issues.append(f"clusters_without_identity:{bad_clusters}")
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
    if focus_areas:
        lines.extend(f"- {item}" for item in focus_areas)
    else:
        lines.append("- <none>")
    if bottleneck_reason:
        lines.append("")
        lines.append(f"[Bottleneck Reason]\n- {bottleneck_reason}")
    lines.append("")
    lines.append("[Keep Fixed]")
    if keep_fixed:
        lines.extend(f"- {item}" for item in keep_fixed)
    else:
        lines.append("- <none>")
    lines.append("")
    lines.append("[Change Next]")
    if change_next:
        lines.extend(f"- {item}" for item in change_next)
    else:
        lines.append("- <none>")
    if stop_exploit_if:
        lines.append("")
        lines.append(f"[Stop Exploit If]\n- {stop_exploit_if}")
    return "\n".join(lines)


def update_primary_metric_state(
    cluster_metrics: Dict[str, Any],
    best_ari: float | None,
    best_sil: float | None,
    delta_min: float,
    stagnation_steps: int,
) -> Tuple[float | None, float | None, int, Dict[str, Any]]:
    cur_ari = None
    if isinstance(cluster_metrics, dict):
        cur_ari = to_float(cluster_metrics.get("ari"))
        if cur_ari is None:
            cur_ari = to_float(cluster_metrics.get("ARI"))
    cur_sil = to_float(cluster_metrics.get("silhouette") if isinstance(cluster_metrics, dict) else None)
    cur_nmi = to_float(cluster_metrics.get("nmi") if isinstance(cluster_metrics, dict) else None)

    primary_name = "ari"
    prev_best = best_ari
    current_primary = cur_ari
    gain = None
    if current_primary is not None and prev_best is not None:
        gain = current_primary - prev_best

    if current_primary is None:
        stagnation_steps += 1
    else:
        if prev_best is None or gain is None or gain > delta_min:
            stagnation_steps = 0
        else:
            stagnation_steps += 1

    if cur_ari is not None:
        best_ari = cur_ari if best_ari is None else max(best_ari, cur_ari)
    if cur_sil is not None:
        best_sil = cur_sil if best_sil is None else max(best_sil, cur_sil)

    state = {
        "primary_metric": primary_name,
        "fallback_to_silhouette": False,
        "current_ari": cur_ari,
        "current_silhouette": cur_sil,
        "current_nmi": cur_nmi,
        "previous_best_ari": prev_best,
        "previous_best_silhouette": best_sil,
        "primary_metric_gain": gain,
        "stagnation_steps": stagnation_steps,
    }
    return best_ari, best_sil, stagnation_steps, state


class TextGradEvaluator:
    def __init__(self, config: Config, engine_name: str, task_decrp: str, background: str = "Not available", eval_type: str = "joint"):
        if eval_type != "joint":
            raise ValueError("scAgentSingleEval only supports the joint evaluator")
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
            pipeline_code="{pipeline_code}",
            interface_contract="{interface_contract}",
            context_mode="{context_mode}",
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
            "pipeline_code": None,
            "interface_contract": None,
            "context_mode": None,
            "cluster_metrics": None,
            "cluster_summary": None,
            "training_logs": None,
            "pipeline_summary": None,
        }
        self.system_prompt = tg.Variable(
            JOINT_EVALUATOR_SYSTEM_PROMPT,
            requires_grad=False,
            role_description="system prompt to evaluate the single pipeline script",
        )
        self.formatted_llm_call = tg.autograd.FormattedLLMCall(
            engine=self.engine,
            format_string=format_string,
            fields=fields,
            system_prompt=self.system_prompt,
        )

    def loss_fn(
        self,
        notes: tg.Variable,
        step,
        pipeline_code: tg.Variable,
        suggestion=None,
        training_history=None,
        stagnation_steps=None,
        delta_min=None,
        current_performance=None,
        interface_contract: tg.Variable | None = None,
        context_mode: tg.Variable | None = None,
        cluster_metrics: tg.Variable | None = None,
        cluster_summary: tg.Variable | None = None,
        training_logs: tg.Variable | None = None,
        pipeline_summary: tg.Variable | None = None,
    ):
        step_var = tg.Variable(step, requires_grad=False, role_description="step counter")
        if suggestion is None:
            suggestion = tg.Variable("<omitted>", requires_grad=False, role_description="consultant suggestion")
        if training_history is None:
            training_history = tg.Variable("[]", requires_grad=False, role_description="training history")
        if stagnation_steps is None:
            stagnation_steps = tg.Variable(3, requires_grad=False, role_description="stagnation steps")
        if delta_min is None:
            delta_min = tg.Variable("0.005", requires_grad=False, role_description="delta min")
        if current_performance is None:
            current_performance = tg.Variable("<omitted>", requires_grad=False, role_description="current performance")
        if interface_contract is None:
            interface_contract = tg.Variable("{}", requires_grad=False, role_description="interface contract")
        if context_mode is None:
            context_mode = tg.Variable("full", requires_grad=False, role_description="context mode")
        if cluster_metrics is None:
            cluster_metrics = tg.Variable("<omitted>", requires_grad=False, role_description="cluster metrics")
        if cluster_summary is None:
            cluster_summary = tg.Variable("<omitted>", requires_grad=False, role_description="cluster summary")
        if training_logs is None:
            training_logs = tg.Variable("<omitted>", requires_grad=False, role_description="training logs")
        if pipeline_summary is None:
            pipeline_summary = tg.Variable("<omitted>", requires_grad=False, role_description="pipeline summary")

        return self.formatted_llm_call(
            inputs={
                "step": step_var,
                "notes": notes,
                "suggestion": suggestion,
                "training_history": training_history,
                "stagnation_steps": stagnation_steps,
                "delta_min": delta_min,
                "current_performance": current_performance,
                "pipeline_code": pipeline_code,
                "interface_contract": interface_contract,
                "context_mode": context_mode,
                "cluster_metrics": cluster_metrics,
                "cluster_summary": cluster_summary,
                "training_logs": training_logs,
                "pipeline_summary": pipeline_summary,
            },
            response_role_description="evaluation of the single pipeline script",
        )
