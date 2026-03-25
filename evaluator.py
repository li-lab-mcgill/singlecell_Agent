import json
from typing import Any, Dict, List, Tuple

import textgrad as tg
from dotenv import load_dotenv

from consultant import _short
from config import Config
from evaluator_prompts import (
    BIOLOGY_EVALUATOR_SYSTEM_PROMPT,
    BIOLOGY_FORMAT_STRING,
    DATA_SCIENCE_EVALUATOR_SYSTEM_PROMPT,
    DATA_SCIENCE_FORMAT_STRING,
    MODEL_EVALUATOR_SYSTEM_PROMPT,
    MODEL_FORMAT_STRING,
)
from multieval_types import STAGE_FILENAMES

load_dotenv()


def _validate_feedback_payload(feedback: Dict[str, Any]) -> None:
    required_feedback_keys = ["diagnosis", "focus_areas", "keep_fixed", "change_next"]
    missing_feedback = [key for key in required_feedback_keys if key not in feedback]
    if missing_feedback:
        raise ValueError(f"Evaluator feedback missing required keys: {missing_feedback}")
    if not isinstance(feedback.get("focus_areas"), list):
        raise ValueError("Evaluator feedback focus_areas must be a list")


def _validate_feedback_only_payload(feedback: Dict[str, Any]) -> None:
    required_feedback_keys = ["diagnosis", "focus_areas", "keep_fixed", "change_next"]
    missing_feedback = [key for key in required_feedback_keys if key not in feedback]
    if missing_feedback:
        raise ValueError(f"Advisory evaluator feedback missing required keys: {missing_feedback}")
    if not isinstance(feedback.get("focus_areas"), list):
        raise ValueError("Advisory evaluator feedback focus_areas must be a list")


def _validate_instruction_list(name: str, items: Any) -> None:
    if not isinstance(items, list):
        raise ValueError(f"Evaluator feedback {name} must be a list")
    for item in items:
        if not str(item or "").strip():
            continue


def _parse_json_object(text: str, label: str) -> Dict[str, Any]:
    stripped = (text or "").strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        raise ValueError(f"{label} output must be a single JSON object with no wrapper tags or extra text")
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} output must decode to a JSON object")
    return payload


def parse_eval_action(text: str) -> tuple[dict, dict]:
    payload = _parse_json_object(text, "Evaluator")
    required_keys = [
        "step",
        "primary_reason",
        "performance",
        "training_health",
        "feedback",
    ]
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError(f"Evaluator payload missing required keys: {missing}")
    feedback = payload.get("feedback", {})
    if not isinstance(feedback, dict):
        raise ValueError("Evaluator feedback must be a JSON object")
    _validate_feedback_payload(feedback)
    _validate_instruction_list("keep_fixed", feedback.get("keep_fixed", []))
    _validate_instruction_list("change_next", feedback.get("change_next", []))
    return payload, feedback


def parse_advisory_eval_action(text: str, eval_type: str) -> tuple[dict, dict]:
    if eval_type not in {"data_science", "biology"}:
        raise ValueError(f"Unsupported advisory evaluator type: {eval_type}")
    payload = _parse_json_object(text, f"{eval_type} evaluator")
    if "optimize_targets" in payload:
        raise ValueError(f"{eval_type} evaluator must not emit optimize_targets")
    required_keys = ["step", "feedback"]
    if eval_type == "biology":
        required_keys.append("biological_assessment")
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise ValueError(f"{eval_type} evaluator payload missing required keys: {missing}")
    feedback = payload.get("feedback", {})
    if not isinstance(feedback, dict):
        raise ValueError(f"{eval_type} evaluator feedback must be a JSON object")
    _validate_feedback_only_payload(feedback)
    _validate_instruction_list("keep_fixed", feedback.get("keep_fixed", []))
    _validate_instruction_list("change_next", feedback.get("change_next", []))
    return payload, feedback


def exploit_plan_from_feedback(feedback: Dict[str, Any]) -> Dict[str, Any]:
    keep_fixed = feedback.get("keep_fixed", []) if isinstance(feedback, dict) else []
    change_next = feedback.get("change_next", []) if isinstance(feedback, dict) else []
    return {
        "diagnosis": str(feedback.get("diagnosis", "")).strip() if isinstance(feedback, dict) else "",
        "focus_areas": [str(item).strip() for item in feedback.get("focus_areas", []) if str(item).strip()] if isinstance(feedback, dict) else [],
        "keep_fixed": [str(item).strip() for item in keep_fixed if str(item).strip()],
        "change_next": [str(item).strip() for item in change_next if str(item).strip()],
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
    keep_fixed = feedback.get("keep_fixed", []) if isinstance(feedback, dict) else []
    change_next = feedback.get("change_next", []) if isinstance(feedback, dict) else []
    lines = ["[Focus Areas]"]
    lines.extend(f"- {item}" for item in focus_areas or ["<none>"])
    lines.append("")
    lines.append("[Keep Fixed]")
    lines.extend(f"- {item}" for item in keep_fixed or ["<none>"])
    lines.append("")
    lines.append("[Change Next]")
    lines.extend(f"- {item}" for item in change_next or ["<none>"])
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
    def __init__(self, config: Config, engine_name: str, task_decrp: str, background: str = "Not available", eval_type: str = "model"):
        self.config = config
        self.engine_name = engine_name
        self.engine = tg.get_engine(engine_name, max_tokens=7000)
        self.eval_type = eval_type
        if eval_type == "model":
            format_string = MODEL_FORMAT_STRING.format(
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
                model_schema="{model_schema}",
                training_logs="{training_logs}",
                pipeline_summary="{pipeline_summary}",
            )
            self.fields = {
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
                "model_schema": None,
                "training_logs": None,
                "pipeline_summary": None,
            }
            system_prompt = MODEL_EVALUATOR_SYSTEM_PROMPT
            response_role = "model evaluation of the three-stage pipeline"
            prompt_role = "system prompt to evaluate model training and architecture"
        elif eval_type == "data_science":
            format_string = DATA_SCIENCE_FORMAT_STRING.format(
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
                preprocessing_summary="{preprocessing_summary}",
                paths="{paths}",
                data_schema="{data_schema}",
                prior_schema="{prior_schema}",
                cluster_metrics="{cluster_metrics}",
                cluster_summary="{cluster_summary}",
                training_logs="{training_logs}",
                pipeline_summary="{pipeline_summary}",
            )
            self.fields = {
                "step": None,
                "metrics": None,
                "time_budget": None,
                "notes": None,
                "suggestion": None,
                "training_history": None,
                "stagnation_steps": None,
                "delta_min": None,
                "current_performance": None,
                "data_prior_code": None,
                "model_training_code": None,
                "downstream_analysis_code": None,
                "preprocessing_summary": None,
                "paths": None,
                "data_schema": None,
                "prior_schema": None,
                "cluster_metrics": None,
                "cluster_summary": None,
                "training_logs": None,
                "pipeline_summary": None,
            }
            system_prompt = DATA_SCIENCE_EVALUATOR_SYSTEM_PROMPT
            response_role = "advisory data-science evaluation of data_prior.py"
            prompt_role = "system prompt for advisory data-science evaluation"
        elif eval_type == "biology":
            format_string = BIOLOGY_FORMAT_STRING.format(
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
                cluster_metrics="{cluster_metrics}",
                cluster_summary="{cluster_summary}",
                downstream_schema="{downstream_schema}",
            )
            self.fields = {
                "step": None,
                "metrics": None,
                "time_budget": None,
                "notes": None,
                "suggestion": None,
                "training_history": None,
                "stagnation_steps": None,
                "delta_min": None,
                "current_performance": None,
                "data_prior_code": None,
                "cluster_metrics": None,
                "cluster_summary": None,
                "downstream_schema": None,
            }
            system_prompt = BIOLOGY_EVALUATOR_SYSTEM_PROMPT
            response_role = "advisory biology evaluation of data_prior.py and downstream_analysis.py"
            prompt_role = "system prompt for advisory biology evaluation"
        else:
            raise ValueError(f"Unsupported evaluator type: {eval_type}")
        self.response_role_description = response_role
        self.system_prompt = tg.Variable(system_prompt, requires_grad=False, role_description=prompt_role)
        self.formatted_llm_call = tg.autograd.FormattedLLMCall(
            engine=self.engine,
            format_string=format_string,
            fields=self.fields,
            system_prompt=self.system_prompt,
        )

    def loss_fn(self, **kwargs):
        inputs = {"step": tg.Variable(kwargs["step"], requires_grad=False, role_description="step counter")}
        for field in self.fields:
            if field == "step":
                continue
            if field not in kwargs:
                raise ValueError(f"Missing evaluator input field '{field}' for eval_type={self.eval_type}")
            inputs[field] = kwargs[field]
        return self.formatted_llm_call(inputs=inputs, response_role_description=self.response_role_description)
