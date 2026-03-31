"""Pipeline executor — runs scripts sequentially with output validation."""
import json
import os
import subprocess
import sys
from typing import Optional, Any, Dict, List

import pandas as pd

from config import Config
from multieval_types import STAGE_FILENAMES, STAGE_ORDER_INDEX


def _read_json(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class Executor:
    """Runs pipeline scripts sequentially with validation."""

    def __init__(self, config: Config):
        self.config = config

    def run_bundle(
        self, script_dir: str, artifact_layout: Dict[str, Any],
        start_from: Optional[str] = None,
    ) -> Dict[str, Any]:
        inputs = artifact_layout.get("runtime_inputs", {})
        mod1 = inputs.get("mod1", "")
        if not mod1 or not os.path.exists(mod1):
            return self._fail(STAGE_FILENAMES[0], f"Input not found: {mod1}")

        start = STAGE_ORDER_INDEX.get(start_from or STAGE_FILENAMES[0], 0)
        stage_results = {}

        for filename in STAGE_FILENAMES[start:]:
            filepath = os.path.join(script_dir, filename)
            if not os.path.exists(filepath):
                return self._fail(filename, f"Missing script: {filename}", stage_results)

            try:
                result = subprocess.run(
                    [sys.executable, filepath],
                    capture_output=True, text=True,
                    timeout=self.config.timeout,
                    cwd=os.path.dirname(filepath),
                )
            except subprocess.TimeoutExpired:
                return self._fail(filename, f"Timeout ({self.config.timeout}s)", stage_results)
            except Exception as e:
                return self._fail(filename, str(e), stage_results)

            stage_results[filename] = {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip()[-500:],
                "stderr": result.stderr.strip()[-1000:],
            }

            if result.returncode != 0:
                return self._fail(filename, result.stderr.strip(), stage_results)

            # Validate outputs
            errors = self._validate(artifact_layout, filename)
            if errors:
                return self._fail(filename, errors[0], stage_results,
                                  validation_failure={"target": filename, "message": errors[0]})

        outputs = artifact_layout.get("generated_outputs", {})
        return {
            "success": True, "error": "", "failed_script": None,
            "stage_results": stage_results,
            "cluster_metrics": _read_json(outputs.get("cluster_metrics", "")),
            "cluster_summary": _read_json(outputs.get("cluster_summary", "")),
            "training_logs": _read_json(outputs.get("training_logs", "")),
            "pipeline_summary": _read_json(outputs.get("pipeline_summary", "")),
        }

    # ── Validation ─────────────────────────────────────────────────

    def _validate(self, layout: Dict, filename: str) -> List[str]:
        schema = self.config.stage_requirements(filename)
        outputs = layout.get("generated_outputs", {})
        errors = []

        # Prior bundle validation
        if filename == "prior_construction.py":
            for item in schema.get("prior_files", []):
                path = item.get("path", "")
                if not path or not os.path.exists(path):
                    errors.append(f"Prior artifact missing: {path}")
                elif os.path.getsize(path) == 0:
                    errors.append(f"Prior artifact empty: {path}")

        # Required outputs
        for key in schema.get("required_outputs", []):
            path = outputs.get(key, "")
            if not path or not os.path.exists(path):
                errors.append(f"Missing '{key}': {path}")
            elif os.path.getsize(path) == 0:
                errors.append(f"Empty '{key}': {path}")
            else:
                artifact = schema.get("artifacts", {}).get(key, {})
                fmt = artifact.get("format", "")
                if fmt == "csv":
                    try:
                        df = pd.read_csv(path)
                        missing = [c for c in artifact.get("required_columns", []) if c not in df.columns]
                        if missing:
                            errors.append(f"'{key}' missing columns: {missing}")
                    except Exception as e:
                        errors.append(f"Cannot read CSV '{key}': {e}")
                elif fmt == "json":
                    try:
                        with open(path) as f:
                            data = json.load(f)
                        missing = [k for k in artifact.get("required_keys", []) if k not in data]
                        if missing:
                            errors.append(f"'{key}' missing keys: {missing}")
                    except Exception as e:
                        errors.append(f"Cannot read JSON '{key}': {e}")
        return errors

    @staticmethod
    def _fail(script, error, stage_results=None, validation_failure=None):
        result = {
            "success": False, "error": error, "failed_script": script,
            "stage_results": stage_results or {},
            "cluster_metrics": {}, "cluster_summary": {},
            "training_logs": {}, "pipeline_summary": {},
        }
        if validation_failure:
            result["validation_failure"] = validation_failure
        return result