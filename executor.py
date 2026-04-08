"""Executor for the multi-stage pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List

from config import Config
from multieval_types import STAGE_FILENAMES, STAGE_ORDER_INDEX
from validator import validate_stage_outputs


def _read_json_safe(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class CodeExecutor:
    def __init__(self, config: Config):
        self.config = config

    def _validate_runtime_inputs(self, resolved_artifact_layout: Dict[str, Any]) -> None:
        runtime_inputs = resolved_artifact_layout.get("runtime_inputs", {})
        if not isinstance(runtime_inputs, dict):
            raise ValueError("Resolved artifact layout missing runtime_inputs")
        mod1_path = runtime_inputs.get("mod1")
        if not mod1_path or not os.path.exists(mod1_path):
            raise FileNotFoundError(f"Configured input path does not exist: {mod1_path}")
        mod2_path = runtime_inputs.get("mod2")
        if mod2_path and not os.path.exists(mod2_path):
            raise FileNotFoundError(f"Configured modality 2 path does not exist: {mod2_path}")

    def _run_script(self, filepath: str) -> Dict[str, Any]:
        result = subprocess.run(
            [sys.executable, filepath],
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            cwd=os.path.dirname(filepath),
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip(),
            "filepath": filepath,
        }

    def run_bundle(self, script_dir: str, resolved_artifact_layout: Dict[str, Any], stage_schemas: Dict[str, Dict[str, Any]], start_from: str | None = None) -> Dict[str, Any]:
        try:
            self._validate_runtime_inputs(resolved_artifact_layout)
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "stage_results": {},
                "failed_script": self.config.active_stage_filenames()[0],
            }

        active_stage_filenames = self.config.active_stage_filenames()
        start_stage = start_from or active_stage_filenames[0]
        if start_stage not in active_stage_filenames:
            start_stage = active_stage_filenames[0]
        start_index = active_stage_filenames.index(start_stage)
        stage_results: Dict[str, Dict[str, Any]] = {}
        for filename in active_stage_filenames[start_index:]:
            filepath = os.path.join(script_dir, filename)
            if not os.path.exists(filepath):
                return {
                    "success": False,
                    "error": f"Missing script: {filename}",
                    "stage_results": stage_results,
                    "failed_script": filename,
                }
            try:
                stage_result = self._run_script(filepath)
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"Execution timeout ({self.config.timeout}s)",
                    "stage_results": stage_results,
                    "failed_script": filename,
                }
            except Exception as exc:
                return {
                    "success": False,
                    "error": str(exc),
                    "stage_results": stage_results,
                    "failed_script": filename,
                }
            stage_results[filename] = stage_result
            if not stage_result["success"]:
                return {
                    "success": False,
                    "error": stage_result["error"],
                    "stage_results": stage_results,
                    "failed_script": filename,
                }

            failures = validate_stage_outputs(resolved_artifact_layout, stage_schemas.get(filename, {}), filename)
            if failures:
                return {
                    "success": False,
                    "error": failures[0].message,
                    "stage_results": stage_results,
                    "failed_script": filename,
                    "validation_failure": failures[0].to_dict(),
                }

        outputs = resolved_artifact_layout.get("generated_outputs", {})
        return {
            "success": True,
            "error": "",
            "stage_results": stage_results,
            "metrics": _read_json_safe(str(outputs.get("model_performance", ""))),
            "cluster_metrics": _read_json_safe(str(outputs.get("cluster_metrics", ""))),
            "cluster_summary": _read_json_safe(str(outputs.get("cluster_summary", ""))),
            "training_logs": _read_json_safe(str(outputs.get("training_logs", ""))),
            "pipeline_summary": _read_json_safe(str(outputs.get("pipeline_summary", ""))),
        }
