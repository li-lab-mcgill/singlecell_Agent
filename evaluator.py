"""Evaluator agents — 4 specialists + critic, proper TextGrad FormattedLLMCall."""
import json
import re
from typing import Tuple, Any, Dict, List

import textgrad as tg

from config import Config
from evaluator_prompts import EVALUATOR_CONFIG


def parse_json_output(text: str, label: str) -> Dict[str, Any]:
    """Extract JSON from evaluator output, fallback to raw text."""
    stripped = (text or "").strip()
    m = re.search(r"\{.*\}", stripped, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {"role": label, "feedback": stripped}


class Evaluator:
    """Single evaluator instance using FormattedLLMCall."""

    def __init__(self, config: Config, eval_type: str, task: str):
        cfg = EVALUATOR_CONFIG[eval_type]
        self.eval_type = eval_type
        self.engine = tg.get_engine(config.engine_name, max_tokens=7000)

        # Pre-fill static fields
        fmt = cfg["format_string"].replace("{task}", task).replace("{metrics}", config.metrics)

        self.fields = {f: None for f in cfg["fields"]}
        self.system_prompt = tg.Variable(
            cfg["system_prompt"], requires_grad=False,
            role_description=f"system prompt for {eval_type} evaluator",
        )
        self.call = tg.autograd.FormattedLLMCall(
            engine=self.engine, format_string=fmt,
            fields=self.fields, system_prompt=self.system_prompt,
        )

    def evaluate(self, **kwargs) -> tg.Variable:
        """Run evaluation. kwargs must contain all fields as tg.Variables."""
        inputs = {}
        for field in self.fields:
            if field not in kwargs:
                raise ValueError(f"Missing '{field}' for {self.eval_type}")
            inputs[field] = kwargs[field]
        return self.call(inputs=inputs, response_role_description=f"{self.eval_type} evaluation")


class EvaluatorPanel:
    """Manages the 4 specialist evaluators + critic.

    Key design: specialist evaluators receive code variables as inputs to
    FormattedLLMCall, creating the graph edges needed for backward().
    """

    def __init__(self, config: Config, task: str):
        self.evaluators = {
            role: Evaluator(config, role, task)
            for role in ["prior", "data_science", "model", "biology", "critic"]
        }

    def run_meeting(
        self,
        code_bundle: Dict[str, tg.Variable],
        step: int,
        context: Dict[str, str],
    ) -> Tuple[Dict[str, tg.Variable], Dict[str, Any], tg.Variable]:
        """
        Run specialists → collect chat → run critic.

        Returns:
            eval_outputs: {role: tg.Variable} — for calling backward()
            parsed: {role: dict} — parsed JSON
            critic_out: tg.Variable
        """
        step_var = tg.Variable(str(step), requires_grad=False, role_description="step")
        chat_history: List[Dict] = []
        eval_outputs: Dict[str, tg.Variable] = {}
        parsed: Dict[str, Any] = {}

        # Which code variable goes to which evaluator
        code_inputs = {
            "data_science": {"preprocess_code": code_bundle["data_preprocess.py"]},
            "model":        {"preprocess_code": code_bundle["data_preprocess.py"],
                             "model_code": code_bundle["model_training.py"]},
            "prior":        {"prior_code": code_bundle["prior_construction.py"]},
            "biology":      {"downstream_code": code_bundle["downstream_analysis.py"]},
        }

        for role in ["data_science", "model", "prior", "biology"]:
            kwargs = {"step": step_var}
            # Code variables (creates graph edges for backward)
            for k, v in code_inputs[role].items():
                kwargs[k] = v
            # Context strings as non-grad variables
            for field in self.evaluators[role].fields:
                if field not in kwargs and field != "step":
                    kwargs[field] = tg.Variable(
                        context.get(field, "<none>"),
                        requires_grad=False, role_description=field,
                    )

            out = self.evaluators[role].evaluate(**kwargs)
            eval_outputs[role] = out
            p = parse_json_output(out.value, role)
            parsed[role] = p
            chat_history.append(p)

        # Critic
        critic_kwargs = {"step": step_var}
        for field in self.evaluators["critic"].fields:
            if field == "step":
                continue
            if field == "chat_history":
                critic_kwargs[field] = tg.Variable(
                    json.dumps(chat_history), requires_grad=False,
                    role_description="evaluator chat history",
                )
            else:
                critic_kwargs[field] = tg.Variable(
                    context.get(field, "<none>"),
                    requires_grad=False, role_description=field,
                )
        critic_out = self.evaluators["critic"].evaluate(**critic_kwargs)
        parsed["critic"] = parse_json_output(critic_out.value, "critic")

        return eval_outputs, parsed, critic_out