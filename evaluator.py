import json
from typing import Any, Dict, List, Tuple

import textgrad as tg
from dotenv import load_dotenv

from consultant import _short
from config import Config
from evaluator_prompts import (
    BIOLOGY_EVALUATOR_SYSTEM_PROMPT,
    BIOLOGY_FORMAT_STRING,
    CRITIC_FORMAT_STRING,
    CRITIC_SYSTEM_PROMPT,
    DATA_SCIENCE_EVALUATOR_SYSTEM_PROMPT,
    DATA_SCIENCE_FORMAT_STRING,
    MODEL_EVALUATOR_SYSTEM_PROMPT,
    MODEL_FORMAT_STRING,
)
from multieval_types import STAGE_FILENAMES

load_dotenv()

EVALUATOR_ROLES = {"data_science", "model", "biology"}
CRITIC_TARGETS = {"data_prior.py", "model_training.py", "downstream_analysis.py"}


def _parse_json_object(text: str, label: str) -> Dict[str, Any]:
    stripped = (text or "").strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        raise ValueError(f"{label} output must be a single JSON object with no wrapper tags or extra text")
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} output must decode to a JSON object")
    return payload


def _validate_feedback_text(feedback: Any, label: str) -> str:
    text = str(feedback or "").strip()
    if not text:
        raise ValueError(f"{label} feedback must be a non-empty string")
    return text


def parse_evaluator_message(text: str, expected_role: str) -> Dict[str, Any]:
    if expected_role not in EVALUATOR_ROLES:
        raise ValueError(f"Unsupported evaluator role: {expected_role}")
    payload = _parse_json_object(text, f"{expected_role} evaluator")
    required = ["role", "feedback"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"{expected_role} evaluator payload missing required keys: {missing}")
    role = str(payload.get("role") or "").strip()
    if role != expected_role:
        raise ValueError(f"{expected_role} evaluator role must be '{expected_role}', got: {role}")
    payload["feedback"] = _validate_feedback_text(payload.get("feedback"), f"{expected_role} evaluator")
    return payload


def parse_critic_output(text: str) -> Dict[str, Any]:
    payload = _parse_json_object(text, "critic")
    required = ["step", "global_rationale", "targets"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"critic payload missing required keys: {missing}")
    payload["global_rationale"] = _validate_feedback_text(payload.get("global_rationale"), "critic")
    targets = payload.get("targets")
    if not isinstance(targets, dict):
        raise ValueError("critic targets must be a JSON object")
    normalized_targets: Dict[str, Dict[str, str]] = {}
    for target, target_payload in targets.items():
        if target not in CRITIC_TARGETS:
            raise ValueError(f"critic target must be one of {sorted(CRITIC_TARGETS)}, got: {target}")
        if not isinstance(target_payload, dict):
            raise ValueError(f"critic target payload for {target} must be a JSON object")
        if "feedback" not in target_payload:
            raise ValueError(f"critic target payload for {target} missing required key: feedback")
        feedback = _validate_feedback_text(target_payload.get("feedback"), f"critic target {target}")
        normalized_targets[target] = {"feedback": feedback}
    payload["targets"] = normalized_targets
    return payload


def critic_plan_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {"global_rationale": "", "targets": {}}
    targets = payload.get("targets", {})
    if not isinstance(targets, dict):
        targets = {}
    return {
        "global_rationale": str(payload.get("global_rationale", "")).strip(),
        "targets": {
            str(target): {"feedback": str((target_payload or {}).get("feedback", "")).strip()}
            for target, target_payload in targets.items()
            if str(target).strip()
        },
    }


def to_float(x: Any) -> float | None:
    try:
        return float(x) if x is not None else None
    except Exception:
        return None


def build_open_issues(*, run_result: Dict[str, Any], primary_state: Dict[str, Any], critic_payload: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if not run_result.get("success", False):
        target = str(run_result.get("failed_script") or STAGE_FILENAMES[0])
        issues.append(f"run_failed:{target}")
    gain = to_float(primary_state.get("primary_metric_gain"))
    if gain is None or gain <= 0:
        issues.append("no_meaningful_primary_gain")
    rationale = str(critic_payload.get("global_rationale") or "").strip()
    if rationale:
        issues.append(f"critic:{_short(rationale, 180)}")
    seen = set()
    out: List[str] = []
    for issue in issues:
        if issue not in seen:
            seen.add(issue)
            out.append(issue)
    return out


def build_instruction_text(critic_targets: Dict[str, Dict[str, str]]) -> str:
    if not isinstance(critic_targets, dict) or not critic_targets:
        return "<none>"
    lines: List[str] = []
    for target, payload in critic_targets.items():
        feedback = str((payload or {}).get("feedback", "")).strip()
        lines.append(f"[{target}]")
        lines.append(feedback or "<none>")
        lines.append("")
    return "\n".join(lines).strip()


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
    previous_best_ari = best_ari
    previous_best_sil = best_sil
    if cur_ari is not None:
        best_ari = cur_ari if best_ari is None else max(best_ari, cur_ari)
    if cur_sil is not None:
        best_sil = cur_sil if best_sil is None else max(best_sil, cur_sil)
    return best_ari, best_sil, stagnation_steps, {
        "current_ari": cur_ari,
        "current_silhouette": cur_sil,
        "current_nmi": cur_nmi,
        "previous_best_ari": previous_best_ari,
        "previous_best_silhouette": previous_best_sil,
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
                suggestion="{suggestion}",
                training_history="{training_history}",
                stagnation_steps="{stagnation_steps}",
                delta_min="{delta_min}",
                current_performance="{current_performance}",
                model_training_notes_history="{model_training_notes_history}",
                model_training_current_diffs="{model_training_current_diffs}",
                data_prior_code="{data_prior_code}",
                model_training_code="{model_training_code}",
                paths="{paths}",
                model_schema="{model_schema}",
                training_logs="{training_logs}",
                pipeline_summary="{pipeline_summary}",
                chat_history="{chat_history}",
            )
            self.fields = {
                "step": None,
                "suggestion": None,
                "training_history": None,
                "stagnation_steps": None,
                "delta_min": None,
                "current_performance": None,
                "model_training_notes_history": None,
                "model_training_current_diffs": None,
                "data_prior_code": None,
                "model_training_code": None,
                "paths": None,
                "model_schema": None,
                "training_logs": None,
                "pipeline_summary": None,
                "chat_history": None,
            }
            system_prompt = MODEL_EVALUATOR_SYSTEM_PROMPT
            response_role = "model deliberation message"
            prompt_role = "system prompt for model evaluator"
        elif eval_type == "data_science":
            format_string = DATA_SCIENCE_FORMAT_STRING.format(
                task=task_decrp,
                step="{step}",
                metrics=self.config.metrics,
                time_budget=config.timeout,
                suggestion="{suggestion}",
                training_history="{training_history}",
                stagnation_steps="{stagnation_steps}",
                delta_min="{delta_min}",
                current_performance="{current_performance}",
                data_prior_notes_history="{data_prior_notes_history}",
                data_prior_current_diffs="{data_prior_current_diffs}",
                data_prior_code="{data_prior_code}",
                preprocessing_summary="{preprocessing_summary}",
                prior_resource_summary="{prior_resource_summary}",
                paths="{paths}",
                data_schema="{data_schema}",
                prior_schema="{prior_schema}",
                pipeline_summary="{pipeline_summary}",
                chat_history="{chat_history}",
            )
            self.fields = {
                "step": None,
                "metrics": None,
                "time_budget": None,
                "suggestion": None,
                "training_history": None,
                "stagnation_steps": None,
                "delta_min": None,
                "current_performance": None,
                "data_prior_notes_history": None,
                "data_prior_current_diffs": None,
                "data_prior_code": None,
                "preprocessing_summary": None,
                "prior_resource_summary": None,
                "paths": None,
                "data_schema": None,
                "prior_schema": None,
                "pipeline_summary": None,
                "chat_history": None,
            }
            system_prompt = DATA_SCIENCE_EVALUATOR_SYSTEM_PROMPT
            response_role = "data-science deliberation message"
            prompt_role = "system prompt for data-science evaluator"
        elif eval_type == "biology":
            format_string = BIOLOGY_FORMAT_STRING.format(
                task=task_decrp,
                step="{step}",
                metrics=self.config.metrics,
                time_budget=config.timeout,
                suggestion="{suggestion}",
                training_history="{training_history}",
                stagnation_steps="{stagnation_steps}",
                delta_min="{delta_min}",
                current_performance="{current_performance}",
                downstream_analysis_notes_history="{downstream_analysis_notes_history}",
                downstream_analysis_current_diffs="{downstream_analysis_current_diffs}",
                downstream_analysis_code="{downstream_analysis_code}",
                cluster_summary="{cluster_summary}",
                downstream_schema="{downstream_schema}",
                chat_history="{chat_history}",
            )
            self.fields = {
                "step": None,
                "metrics": None,
                "time_budget": None,
                "suggestion": None,
                "training_history": None,
                "stagnation_steps": None,
                "delta_min": None,
                "current_performance": None,
                "downstream_analysis_notes_history": None,
                "downstream_analysis_current_diffs": None,
                "downstream_analysis_code": None,
                "cluster_summary": None,
                "downstream_schema": None,
                "chat_history": None,
            }
            system_prompt = BIOLOGY_EVALUATOR_SYSTEM_PROMPT
            response_role = "biology deliberation message"
            prompt_role = "system prompt for biology evaluator"
        elif eval_type == "critic":
            format_string = CRITIC_FORMAT_STRING.format(
                task=task_decrp,
                step="{step}",
                suggestion="{suggestion}",
                raw_data_summary="{raw_data_summary}",
                prior_resource_summary="{prior_resource_summary}",
                current_performance="{current_performance}",
                training_logs="{training_logs}",
                pipeline_summary="{pipeline_summary}",
                data_prior_notes_history="{data_prior_notes_history}",
                model_training_notes_history="{model_training_notes_history}",
                downstream_analysis_notes_history="{downstream_analysis_notes_history}",
                script_summaries="{script_summaries}",
                chat_history="{chat_history}",
            )
            self.fields = {
                "step": None,
                "suggestion": None,
                "raw_data_summary": None,
                "prior_resource_summary": None,
                "current_performance": None,
                "training_logs": None,
                "pipeline_summary": None,
                "data_prior_notes_history": None,
                "model_training_notes_history": None,
                "downstream_analysis_notes_history": None,
                "script_summaries": None,
                "chat_history": None,
            }
            system_prompt = CRITIC_SYSTEM_PROMPT
            response_role = "critic optimizer-driving message"
            prompt_role = "system prompt for critic"
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
