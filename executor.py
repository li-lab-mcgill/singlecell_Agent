"""Executor for the single-script pipeline."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict

from config import Config
from multieval_types import StepRunContract, ValidationFailure
from validator import SECTION_ORDER, validate_pipeline_outputs


def _read_json_safe(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _infer_failed_stage(stderr: str) -> str:
    text = stderr or ""
    function_to_stage = {
        "run_dataloader": "dataloader",
        "run_prior": "prior",
        "build_model": "model",
        "run_train": "train",
        "run_clustering": "clustering",
    }
    for function_name, stage in function_to_stage.items():
        if re.search(rf"\b{function_name}\b", text):
            return stage
    for stage in SECTION_ORDER:
        if stage in text.lower():
            return stage
    return "pipeline"


class CodeExecutor:
    def __init__(self, config: Config):
        self.config = config

    def _prepare_input_dir(self, contract: StepRunContract) -> str:
        input_dir = os.path.join(contract.run_dir, "input_data")
        os.makedirs(input_dir, exist_ok=True)

        staged_targets = [
            (getattr(self.config, "data_mod1_path", None), os.path.join(input_dir, "adata.h5ad")),
        ]
        mod2_path = getattr(self.config, "data_mod2_path", None)
        if mod2_path:
            staged_targets.append((mod2_path, os.path.join(input_dir, os.path.basename(mod2_path))))

        for source_path, staged_path in staged_targets:
            if not source_path:
                continue
            if not os.path.exists(source_path):
                raise FileNotFoundError(f"Configured input path does not exist: {source_path}")
            if os.path.lexists(staged_path):
                continue
            try:
                os.symlink(source_path, staged_path)
            except OSError:
                shutil.copy2(source_path, staged_path)
        return input_dir

    def _run_script(self, filepath: str, contract: StepRunContract) -> Dict[str, Any]:
        try:
            env = os.environ.copy()
            env.update(contract.build_env())
            input_dir = self._prepare_input_dir(contract)
            env["SCANPY_AGENT_INPUT_DIR"] = input_dir
            env["SCANPY_AGENT_INPUT_MOD1_PATH"] = getattr(self.config, "data_mod1_path", "") or ""
            env["SCANPY_AGENT_INPUT_MOD2_PATH"] = getattr(self.config, "data_mod2_path", "") or ""
            result = subprocess.run(
                ["python", filepath],
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                cwd=os.path.dirname(filepath),
                env=env,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "filepath": filepath,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"Execution timeout ({self.config.timeout}s)",
                "filepath": filepath,
            }
        except Exception as exc:
            return {
                "success": False,
                "output": "",
                "error": str(exc),
                "filepath": filepath,
            }

    @staticmethod
    def _failure_from_validation(failure: ValidationFailure, stage_result: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": False,
            "failed_stage": failure.stage,
            "error": failure.message,
            "stage_results": {"pipeline": stage_result},
            "metrics": metrics,
            "validation_failure": failure.to_dict(),
        }

    def run_bundle(self, script_path: str, contract: StepRunContract) -> Dict[str, Any]:
        stage_result = self._run_script(script_path, contract=contract)
        if not stage_result["success"]:
            return {
                "success": False,
                "failed_stage": _infer_failed_stage(stage_result["error"]),
                "error": stage_result["error"],
                "stage_results": {"pipeline": stage_result},
                "metrics": _read_json_safe(self.config.model_perf_path),
            }

        output_failures = validate_pipeline_outputs(contract)
        if output_failures:
            return self._failure_from_validation(
                output_failures[0],
                stage_result=stage_result,
                metrics=_read_json_safe(self.config.model_perf_path),
            )

        return {
            "success": True,
            "failed_stage": None,
            "error": "",
            "stage_results": {"pipeline": stage_result},
            "metrics": _read_json_safe(self.config.model_perf_path),
            "cluster_metrics": _read_json_safe(self.config.cluster_metrics_path),
            "cluster_summary": _read_json_safe(self.config.cluster_summary_path),
            "training_logs": _read_json_safe(self.config.training_logs_path),
            "pipeline_summary": _read_json_safe(self.config.pipeline_summary_path),
            "prior_manifest": _read_json_safe(self.config.prior_manifest_path),
        }
