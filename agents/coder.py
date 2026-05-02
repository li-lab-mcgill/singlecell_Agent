from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import textgrad as tg

from agents.decision_schema import validate_implementation_plan
from prompts.coder_agent_prompts import (
    CODER_AGENT_IMPLEMENTATION_PROMPT,
    CODER_AGENT_SYSTEM_PROMPT,
    CODER_EVALUATOR_FORMAT_STRING,
    CODER_EVALUATOR_SYSTEM_PROMPT,
    CODER_FIX_PROMPT,
)
from backend.objectives import add_objective_score


class CoderAgent:
    """Plan-driven single-script code pipeline facade."""

    def __init__(
        self,
        *,
        engine_name: str,
        result_dir: str | Path,
        artifact_dir: str | Path | None = None,
        max_attempts: int | None = None,
        max_fix_step: int = 3,
        max_opt_step: int = 3,
    ):
        self.engine_name = engine_name
        self.engine = tg.get_engine(engine_name, max_tokens=12000)
        self.result_dir = Path(artifact_dir) if artifact_dir is not None else Path(result_dir) / "coder_runs"
        self.result_dir.mkdir(parents=True, exist_ok=True)
        if max_attempts is not None:
            max_fix_step = max_attempts
        self.max_fix_step = max(0, int(max_fix_step))
        self.max_opt_step = max(0, int(max_opt_step))

    def run(
        self,
        *,
        implementation_plan: Dict[str, Any],
        session_state: Dict[str, Any] | None = None,
        session_tag: str = "coder",
    ) -> Dict[str, Any]:
        plan, session_state, run_dir, script_path = self._prepare_run(
            implementation_plan=implementation_plan,
            session_state=session_state,
            session_tag=session_tag,
        )
        script = self._generate_initial_script(plan=plan, session_state=session_state)
        execution = self._execute_pipeline(
            plan=plan,
            run_dir=run_dir,
            script_path=script_path,
            script=script,
        )
        return self._build_report(
            initial_plan=plan,
            final_plan=plan,
            plan=plan,
            run_dir=run_dir,
            script_path=script_path,
            execution=execution,
        )

    def _prepare_run(
        self,
        *,
        implementation_plan: Dict[str, Any],
        session_state: Dict[str, Any] | None,
        session_tag: str,
    ) -> tuple[Dict[str, Any], Dict[str, Any], Path, Path]:
        plan = validate_implementation_plan(implementation_plan)
        run_dir = self.result_dir / session_tag
        run_dir.mkdir(parents=True, exist_ok=True)
        script_path = run_dir / Path(plan["script_name"]).name
        return plan, dict(session_state or {}), run_dir, script_path

    def _generate_initial_script(self, *, plan: Dict[str, Any], session_state: Dict[str, Any]) -> str:
        prompt = CODER_AGENT_IMPLEMENTATION_PROMPT.format(
            implementation_plan=json.dumps(plan, indent=2, ensure_ascii=False),
            session_state=json.dumps(session_state, indent=2, ensure_ascii=False),
        )
        response = self.engine.generate(content=prompt, system_prompt=CODER_AGENT_SYSTEM_PROMPT, temperature=0.2)
        return _extract_python(str(response))

    def _execute_pipeline(
        self,
        *,
        plan: Dict[str, Any],
        run_dir: Path,
        script_path: Path,
        script: str,
    ) -> Dict[str, Any]:
        attempts: list[dict[str, Any]] = []
        current_script = script

        execution_result: Dict[str, Any] | None = None
        for fix_attempt in range(self.max_fix_step + 1):
            execution_result = self._execute_attempt(
                script=current_script,
                script_path=script_path,
                run_dir=run_dir,
            )
            attempts.append(
                {
                    "phase": "fix",
                    "attempt": fix_attempt + 1,
                    "execution_result": execution_result,
                }
            )
            if execution_result["returncode"] == 0:
                break
            if fix_attempt >= self.max_fix_step:
                break
            current_script = self._fix_script(
                plan=plan,
                script=current_script,
                error=execution_result.get("stderr") or execution_result.get("stdout") or "Unknown execution error.",
            )

        metrics = _collect_metrics(plan, run_dir)
        if not execution_result or execution_result["returncode"] != 0:
            return {
                "status": "failed",
                "script": current_script,
                "attempts": attempts,
                "metrics": metrics,
                "last_execution_result": execution_result or {},
            }

        if self.max_opt_step <= 0:
            return {
                "status": "completed",
                "script": current_script,
                "attempts": attempts,
                "metrics": metrics,
                "last_execution_result": execution_result,
            }

        optimized = self._optimize_script(
            plan=plan,
            run_dir=run_dir,
            script_path=script_path,
            script=current_script,
            execution_result=execution_result,
            attempts=attempts,
        )
        return optimized

    def _optimize_script(
        self,
        *,
        plan: Dict[str, Any],
        run_dir: Path,
        script_path: Path,
        script: str,
        execution_result: Dict[str, Any],
        attempts: list[dict[str, Any]],
    ) -> Dict[str, Any]:
        if not _textgrad_optimization_available():
            metrics = _collect_metrics(plan, run_dir)
            return {
                "status": "completed",
                "script": script,
                "attempts": attempts,
                "metrics": metrics,
                "last_execution_result": execution_result,
                "optimization_skipped": "TextGrad optimization APIs are unavailable.",
            }

        script_var = tg.Variable(
            script,
            requires_grad=True,
            role_description="Python script that implements the CoderAgent task",
        )
        optimizer = tg.TextualGradientDescent(
            engine=self.engine,
            parameters=[script_var],
            constraints=_build_coder_constraints(plan),
        )
        evaluator = CoderEvaluator(engine_name=self.engine_name)
        last_execution_result = execution_result
        current_script = script
        metrics = _collect_metrics(plan, run_dir)
        evaluator_passed = False

        for opt_step in range(self.max_opt_step):
            loss = evaluator.loss_fn(
                script_code=script_var,
                plan=tg.Variable(
                    json.dumps(plan, indent=2, ensure_ascii=False),
                    requires_grad=False,
                    role_description="implementation plan",
                ),
                success_metric=tg.Variable(
                    plan.get("success_metric", ""),
                    requires_grad=False,
                    role_description="success metric",
                ),
                metrics=tg.Variable(
                    json.dumps(metrics, indent=2, ensure_ascii=False),
                    requires_grad=False,
                    role_description="collected metrics",
                ),
                stdout=tg.Variable(
                    last_execution_result.get("stdout", "")[-4000:],
                    requires_grad=False,
                    role_description="script stdout",
                ),
            )
            eval_payload = _parse_evaluator_response(getattr(loss, "value", str(loss)))
            attempts.append(
                {
                    "phase": "optimize",
                    "attempt": opt_step + 1,
                    "evaluation": eval_payload,
                    "metrics": metrics,
                }
            )
            if eval_payload.get("passed", False):
                evaluator_passed = True
                break

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            current_script = str(script_var.value)

            for fix_attempt in range(self.max_fix_step + 1):
                last_execution_result = self._execute_attempt(
                    script=current_script,
                    script_path=script_path,
                    run_dir=run_dir,
                )
                attempts.append(
                    {
                        "phase": "post_opt_fix",
                        "opt_step": opt_step + 1,
                        "attempt": fix_attempt + 1,
                        "execution_result": last_execution_result,
                    }
                )
                if last_execution_result["returncode"] == 0:
                    break
                if fix_attempt >= self.max_fix_step:
                    break
                current_script = self._fix_script(
                    plan=plan,
                    script=current_script,
                    error=last_execution_result.get("stderr") or last_execution_result.get("stdout") or "Unknown execution error.",
                )
                script_var.set_value(current_script)

            if last_execution_result["returncode"] != 0:
                return {
                    "status": "failed",
                    "script": current_script,
                    "attempts": attempts,
                    "metrics": metrics,
                    "last_execution_result": last_execution_result,
                }

            script_var.set_value(current_script)
            metrics = _collect_metrics(plan, run_dir)

        return {
            "status": "completed" if evaluator_passed else "partial",
            "script": current_script,
            "attempts": attempts,
            "metrics": metrics,
            "last_execution_result": last_execution_result,
        }

    def _execute_attempt(
        self,
        *,
        script: str,
        script_path: Path,
        run_dir: Path,
    ) -> Dict[str, Any]:
        script_path.write_text(script, encoding="utf-8")
        return _run_script(script_path, cwd=run_dir)

    def _fix_script(self, *, plan: Dict[str, Any], script: str, error: str) -> str:
        prompt = CODER_FIX_PROMPT.format(
            implementation_plan=json.dumps(plan, indent=2, ensure_ascii=False),
            script=script,
            error=error,
        )
        revised = self.engine.generate(content=prompt, system_prompt=CODER_AGENT_SYSTEM_PROMPT, temperature=0.2)
        return _extract_python(str(revised))

    def _build_report(
        self,
        *,
        initial_plan: Dict[str, Any],
        final_plan: Dict[str, Any],
        plan: Dict[str, Any],
        run_dir: Path,
        script_path: Path,
        execution: Dict[str, Any],
    ) -> Dict[str, Any]:
        status = str(execution.get("status") or "failed")
        attempts = execution.get("attempts", [])
        final_metrics = execution.get("metrics", {})
        artifacts = _existing_outputs(plan, run_dir)
        images = _collect_images(plan, run_dir, execution)
        report = {
            "status": status,
            "message": self._report_message(status=status, script_path=script_path, attempts=attempts, metrics=final_metrics),
            "script_path": str(script_path),
            "metrics": final_metrics,
            "artifacts": artifacts,
            "images": images,
            "attempts": len(attempts),
            "remaining_gaps": [] if status == "completed" else [_remaining_gap_for_status(status)],
            "attempt_log": attempts,
            "plan_trace": _build_plan_trace(initial=initial_plan, final=final_plan),
        }
        if execution.get("optimization_skipped"):
            report["optimization_skipped"] = execution["optimization_skipped"]
        report_path = run_dir / "coder_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        report["report_path"] = str(report_path)
        return report

    def _report_message(
        self,
        *,
        status: str,
        script_path: Path,
        attempts: list[dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> str:
        parts = [f"Coder pipeline {status}.", f"Script: {script_path}."]
        parts.append(f"Attempts: {len(attempts)}.")
        if metrics:
            parts.append(f"Metrics: {json.dumps(metrics, ensure_ascii=False)}.")
        return " ".join(parts)


class CoderEvaluator:
    """Single TextGrad evaluator for CoderAgent scripts."""

    FIELDS = ["script_code", "plan", "metrics", "stdout", "success_metric"]

    def __init__(self, *, engine_name: str):
        engine = tg.get_engine(engine_name, max_tokens=4000)
        self.system_prompt_var = tg.Variable(
            CODER_EVALUATOR_SYSTEM_PROMPT,
            requires_grad=False,
            role_description="coder evaluator system prompt",
        )
        self.formatted_llm_call = tg.autograd.FormattedLLMCall(
            engine=engine,
            format_string=CODER_EVALUATOR_FORMAT_STRING,
            fields={field: None for field in self.FIELDS},
            system_prompt=self.system_prompt_var,
        )

    def loss_fn(self, **kwargs) -> Any:
        inputs: Dict[str, Any] = {}
        for field in self.FIELDS:
            if field not in kwargs:
                raise ValueError(f"Missing evaluator input field '{field}'")
            inputs[field] = kwargs[field]
        return self.formatted_llm_call(
            inputs=inputs,
            response_role_description="evaluator feedback on script quality",
        )


def _extract_python(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text or "", flags=re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else text).strip()


def _remaining_gap_for_status(status: str) -> str:
    if status == "partial":
        return "Script completed, but evaluator did not confirm that it met the success metric."
    return "Script did not complete successfully within the attempt budget."


def _run_script(script_path: Path, *, cwd: Path) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": str(exc.stdout or "")[-8000:],
            "stderr": (str(exc.stderr or "") + "\nTimed out after 3600 seconds.")[-8000:],
        }
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-8000:],
        "stderr": proc.stderr[-8000:],
    }


def _collect_metrics(plan: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    for path in _candidate_metric_paths(plan, run_dir):
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            if isinstance(payload.get("metrics"), dict):
                metrics.update(payload["metrics"])
            else:
                metrics.update({k: v for k, v in payload.items() if isinstance(v, (int, float))})
    return add_objective_score(metrics, plan.get("success_metric"))


def _parse_evaluator_response(text: str) -> Dict[str, Any]:
    stripped = str(text or "").strip()
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        stripped = match.group(0)
    try:
        payload = json.loads(stripped)
    except Exception:
        return {"passed": False, "feedback": str(text or "").strip() or "Evaluator did not return JSON."}
    if not isinstance(payload, dict):
        return {"passed": False, "feedback": "Evaluator response was not a JSON object."}
    return {
        "passed": bool(payload.get("passed", False)),
        "feedback": str(payload.get("feedback") or "").strip(),
    }


def _build_coder_constraints(plan: Dict[str, Any]) -> list[str]:
    constraints = [
        "Return ONLY valid executable Python code.",
        "Do not use argparse, sys.argv, command-line flags, or environment variables.",
        f"Goal: {plan['goal']}",
    ]
    if plan.get("success_metric"):
        constraints.append(f"Optimize for: {plan['success_metric']}")
    for key, value in plan.get("inputs", {}).items():
        constraints.append(f"Input '{key}' is fixed to: {value}")
    for key, value in plan.get("outputs", {}).items():
        constraints.append(f"Output '{key}' must be written to: {value}")
    constraints.extend(str(item) for item in plan.get("constraints", []))
    return constraints


def _textgrad_optimization_available() -> bool:
    return (
        hasattr(tg, "Variable")
        and hasattr(tg, "TextualGradientDescent")
        and hasattr(tg, "autograd")
        and hasattr(tg.autograd, "FormattedLLMCall")
    )


def _build_plan_trace(*, initial: Dict[str, Any], final: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "initial": initial,
        "final": final,
        "revisions": _diff_dicts(initial, final),
    }


def _diff_dicts(initial: Dict[str, Any], final: Dict[str, Any], prefix: str = "") -> list[Dict[str, Any]]:
    revisions: list[Dict[str, Any]] = []
    keys = sorted(set(initial) | set(final))
    for key in keys:
        field = f"{prefix}.{key}" if prefix else str(key)
        before = initial.get(key)
        after = final.get(key)
        if isinstance(before, dict) and isinstance(after, dict):
            revisions.extend(_diff_dicts(before, after, field))
        elif before != after:
            revisions.append({"field": field, "from": before, "to": after, "reason": "CoderAgent plan revision"})
    return revisions


def _candidate_metric_paths(plan: Dict[str, Any], run_dir: Path) -> list[Path]:
    paths = [run_dir / "metrics.json", run_dir / "cluster_metrics.json"]
    outputs = plan.get("outputs", {})
    if isinstance(outputs, dict):
        for value in outputs.values():
            text = str(value or "").strip()
            if text.endswith(".json"):
                path = Path(text)
                paths.append(path if path.is_absolute() else run_dir / path)
    return paths


def _existing_outputs(plan: Dict[str, Any], run_dir: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    outputs = plan.get("outputs", {})
    if not isinstance(outputs, dict):
        return out
    for key, value in outputs.items():
        for text in _flatten_output_value(value):
            path = Path(text)
            path = path if path.is_absolute() else run_dir / path
            if path.exists():
                out[str(key)] = str(path)
    return out


def _flatten_output_value(value: Any) -> list[str]:
    """Flatten an output value (string or list of strings) into a list of path strings."""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".pdf"}


def _collect_images(plan: Dict[str, Any], run_dir: Path, execution: Dict[str, Any]) -> list[str]:
    """Collect image file paths produced by the coder script.

    Sources:
    1. Declared outputs from the plan that exist on disk.
    2. Image files in the run_dir.
    3. Image files in output directories referenced by the plan.
    4. Image paths extracted from the last successful stdout.
    """
    seen: set[str] = set()
    images: list[str] = []

    def _add(p: Path) -> None:
        resolved = str(p.resolve())
        if resolved not in seen and p.suffix.lower() in _IMAGE_SUFFIXES and p.exists():
            seen.add(resolved)
            images.append(str(p))

    # 1. From plan outputs
    outputs = plan.get("outputs") if isinstance(plan.get("outputs"), dict) else {}
    for value in outputs.values():
        for text in _flatten_output_value(value):
            p = Path(text)
            _add(p if p.is_absolute() else run_dir / p)

    # 2. Scan run_dir for images
    if run_dir.is_dir():
        for child in run_dir.iterdir():
            if child.is_file():
                _add(child)

    # 3. Scan output directories from plan
    for value in outputs.values():
        for text in _flatten_output_value(value):
            p = Path(text) if Path(text).is_absolute() else run_dir / text
            parent = p.parent
            if parent.is_dir() and parent != run_dir:
                for child in parent.iterdir():
                    if child.is_file():
                        _add(child)

    # 4. Extract paths from last successful stdout
    last_exec = execution.get("last_execution_result") if isinstance(execution.get("last_execution_result"), dict) else {}
    stdout = str(last_exec.get("stdout") or "")
    for line in stdout.splitlines():
        for token in line.split():
            token = token.strip().rstrip(".,;:\"')")
            if any(token.lower().endswith(ext) for ext in _IMAGE_SUFFIXES):
                p = Path(token)
                _add(p if p.is_absolute() else run_dir / p)

    return images
