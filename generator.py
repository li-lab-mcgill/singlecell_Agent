"""Code generator for the multi-stage single-cell pipeline."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import textgrad as tg
from dotenv import load_dotenv

from config import Config
from generator_prompts import (
    ANALYSIS_FIX_SYSTEM_PROMPT,
    ANALYSIS_SYSTEM_PROMPT,
    DATA_FIX_SYSTEM_PROMPT,
    DATA_SYSTEM_PROMPT,
    FIX_QUERY,
    MODEL_FIX_SYSTEM_PROMPT,
    MODEL_SYSTEM_PROMPT,
    PRIOR_FIX_SYSTEM_PROMPT,
    PRIOR_SYSTEM_PROMPT,
    STAGE_QUERY,
)
from multieval_types import STAGE_FILES, STAGE_FILENAMES, STAGE_TAG_BY_FILE

load_dotenv()


class BundleFormatError(ValueError):
    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


class StageScriptGenerator:
    def __init__(self, config: Config, engine_name: str):
        self.config = config
        self.engine = tg.get_engine(engine_name, max_tokens=12000)
        self.path_prompt_fields = self._build_path_prompt_fields(config.current_step_layout)

    @staticmethod
    def _clean_code(raw_code: str) -> str:
        match = re.search(r"```(?:python)?\n?(.*?)```", raw_code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_code.strip()

    def _build_path_prompt_fields(self, artifact_layout: Dict[str, Any]) -> Dict[str, str]:
        runtime_inputs = artifact_layout.get("runtime_inputs", {}) if isinstance(artifact_layout, dict) else {}
        generated_outputs = artifact_layout.get("generated_outputs", {}) if isinstance(artifact_layout, dict) else {}
        return {
            "input_mod1_path": str(runtime_inputs.get("mod1", "")),
            "input_mod2_path": str(runtime_inputs.get("mod2", "")),
            "preprocess_metadata_path": str(generated_outputs.get("preprocess_metadata", "")),
            "preprocess_train_mod1_path": str(generated_outputs.get("preprocess_train_mod1", "")),
            "preprocess_val_mod1_path": str(generated_outputs.get("preprocess_val_mod1", "")),
            "preprocess_test_mod1_path": str(generated_outputs.get("preprocess_test_mod1", "")),
            "prior_output_dir_path": str(artifact_layout.get("prior_output_dir", "")),
            "model_performance_path": str(generated_outputs.get("model_performance", "")),
            "best_model_path": str(generated_outputs.get("best_model", "")),
            "embedding_path": str(generated_outputs.get("embedding", "")),
            "embedding_metadata_path": str(generated_outputs.get("embedding_metadata", "")),
            "training_logs_path": str(generated_outputs.get("training_logs", "")),
            "pipeline_summary_path": str(generated_outputs.get("pipeline_summary", "")),
            "cluster_assignments_path": str(generated_outputs.get("cluster_assignments", "")),
            "cluster_metrics_path": str(generated_outputs.get("cluster_metrics", "")),
            "cluster_summary_path": str(generated_outputs.get("cluster_summary", "")),
        }

    @staticmethod
    def _path_label(key: str) -> str:
        labels = {
            "input_mod1_path": "Input modality 1 dataset file",
            "input_mod2_path": "Input modality 2 dataset file",
            "preprocess_metadata_path": "Preprocessing metadata JSON",
            "preprocess_train_mod1_path": "Input training split h5ad",
            "preprocess_val_mod1_path": "Input validation split h5ad",
            "preprocess_test_mod1_path": "Input test split h5ad",
            "prior_output_dir_path": "Prior artifact directory",
            "model_performance_path": "Output model performance JSON",
            "best_model_path": "Output best-model checkpoint file",
            "embedding_path": "Output embedding NPY file",
            "embedding_metadata_path": "Output embedding metadata CSV",
            "training_logs_path": "Output training logs JSON",
            "pipeline_summary_path": "Output pipeline summary JSON",
            "cluster_assignments_path": "Output cluster assignments CSV",
            "cluster_metrics_path": "Output cluster metrics JSON",
            "cluster_summary_path": "Output cluster summary JSON",
        }
        return labels.get(key, key)

    def _primary_metric(self) -> str:
        metrics = self.config.metrics
        if isinstance(metrics, list):
            return str(metrics[0]).strip() if metrics else "ARI"
        return str(metrics).split(",")[0].strip() if metrics is not None else "ARI"

    def _stage_requirements_json(self, filename: str) -> str:
        return json.dumps(self.config.stage_requirements(filename), ensure_ascii=False)

    def _prior_schema_context(self, filename: str) -> str:
        if filename not in {"prior_construction.py", "data_preprocess.py", "model_training.py"}:
            return "<none>"
        return json.dumps(self.config.current_prior_schema, ensure_ascii=False)

    def _prior_resource_lines(self) -> List[str]:
        dataset_dir = getattr(self.config, "dataset_dir", "") or ""
        if not dataset_dir:
            return []
        resources = [
            "MsigDB.csv",
            "NeST.tsv",
            "GO_terms.csv",
            "Cell_marker_Human.xlsx",
            "meta_info.csv",
        ]
        return [f"{name}: {os.path.join(dataset_dir, name)}" for name in resources]

    def _resolved_prior_files(self) -> List[Dict[str, Any]]:
        return self.config.resolved_prior_files()

    def _prior_file_lines(self) -> List[str]:
        lines: List[str] = []
        for item in self._resolved_prior_files():
            artifact_key = str(item.get("artifact_key") or "").strip()
            path = str(item.get("path") or "").strip()
            fmt = str(item.get("format") or "").strip()
            role = str(item.get("description") or item.get("role") or "").strip()
            if not role and fmt == "csv":
                cols = item.get("required_columns", [])
                if isinstance(cols, list) and cols:
                    role = f"CSV with required columns: {', '.join(str(col) for col in cols)}"
            if not role and fmt == "json":
                keys = item.get("required_keys", [])
                if isinstance(keys, list) and keys:
                    role = f"JSON with required keys: {', '.join(str(key) for key in keys)}"
            base = f"Prior artifact {artifact_key}: path={path}; format={fmt}"
            lines.append(f"{base}; description={role}" if role else base)
        return lines

    def _stage_context(self, filename: str) -> str:
        fields = self.path_prompt_fields
        lines: List[str] = []
        if filename == "prior_construction.py":
            lines.extend([
                f"{self._path_label('input_mod1_path')}: {fields['input_mod1_path']}",
                f"{self._path_label('input_mod2_path')}: {fields['input_mod2_path']}",
                f"{self._path_label('prior_output_dir_path')}: {fields['prior_output_dir_path']}",
                "This script must only construct the prior bundle and write the fixed prior artifacts declared in the prior consultant schema.",
            ])
            lines.extend(self._prior_file_lines())
            lines.extend(f"Dataset resource path: {path}" for path in self._prior_resource_lines())
        elif filename == "data_preprocess.py":
            lines.extend([
                f"{self._path_label('input_mod1_path')}: {fields['input_mod1_path']}",
                f"{self._path_label('input_mod2_path')}: {fields['input_mod2_path']}",
                f"{self._path_label('preprocess_metadata_path')}: {fields['preprocess_metadata_path']}",
                f"Output training split h5ad: {fields['preprocess_train_mod1_path']}",
                f"Output validation split h5ad: {fields['preprocess_val_mod1_path']}",
                f"Output test split h5ad: {fields['preprocess_test_mod1_path']}",
                f"{self._path_label('prior_output_dir_path')}: {fields['prior_output_dir_path']}",
                "This script must perform preprocessing and consume the fixed prior bundle already written by prior_construction.py.",
                "Do not rebuild raw prior artifacts from the resource tables in this stage.",
            ])
            lines.extend(self._prior_file_lines())
        elif filename == "model_training.py":
            lines.extend([
                f"{self._path_label('preprocess_metadata_path')}: {fields['preprocess_metadata_path']}",
                f"{self._path_label('preprocess_train_mod1_path')}: {fields['preprocess_train_mod1_path']}",
                f"{self._path_label('preprocess_val_mod1_path')}: {fields['preprocess_val_mod1_path']}",
                f"{self._path_label('preprocess_test_mod1_path')}: {fields['preprocess_test_mod1_path']}",
                f"{self._path_label('prior_output_dir_path')}: {fields['prior_output_dir_path']}",
                f"{self._path_label('model_performance_path')}: {fields['model_performance_path']}",
                f"{self._path_label('best_model_path')}: {fields['best_model_path']}",
                f"{self._path_label('embedding_path')}: {fields['embedding_path']}",
                f"{self._path_label('embedding_metadata_path')}: {fields['embedding_metadata_path']}",
                f"{self._path_label('training_logs_path')}: {fields['training_logs_path']}",
                f"{self._path_label('pipeline_summary_path')}: {fields['pipeline_summary_path']}",
            ])
            lines.extend(self._prior_file_lines())
        elif filename == "downstream_analysis.py":
            lines.extend([
                f"{self._path_label('input_mod1_path')}: {fields['input_mod1_path']}",
                f"{self._path_label('input_mod2_path')}: {fields['input_mod2_path']}",
                f"{self._path_label('preprocess_metadata_path')}: {fields['preprocess_metadata_path']}",
                f"{self._path_label('preprocess_train_mod1_path')}: {fields['preprocess_train_mod1_path']}",
                f"{self._path_label('preprocess_val_mod1_path')}: {fields['preprocess_val_mod1_path']}",
                f"{self._path_label('preprocess_test_mod1_path')}: {fields['preprocess_test_mod1_path']}",
                f"Input embedding NPY file: {fields['embedding_path']}",
                f"Input embedding metadata CSV: {fields['embedding_metadata_path']}",
                f"Input model performance JSON: {fields['model_performance_path']}",
                f"Input pipeline summary JSON: {fields['pipeline_summary_path']}",
                f"{self._path_label('cluster_assignments_path')}: {fields['cluster_assignments_path']}",
                f"{self._path_label('cluster_metrics_path')}: {fields['cluster_metrics_path']}",
                f"{self._path_label('cluster_summary_path')}: {fields['cluster_summary_path']}",
            ])
        return "\n".join(line for line in lines if line.strip()) or "<none>"

    def _stage_query(self, *, filename: str, task_description: str, background: str, main_plan: str, prior_plan: str, data_summary: str, prior_resource_summary: str, script_summaries: str, existing_code: str, mcp_tools_text: str, api_dir: str | None, dataset_dir: str | None) -> str:
        prompt_fields = {
            "target_file": filename,
            "target_tag": STAGE_TAG_BY_FILE[filename],
            "task_description": task_description,
            "background": background,
            "main_plan": main_plan if filename != "prior_construction.py" else "<none>",
            "prior_plan": prior_plan if filename in {"prior_construction.py", "data_preprocess.py", "model_training.py"} else "<none>",
            "prior_schema_json": self._prior_schema_context(filename),
            "stage_requirements_json": self._stage_requirements_json(filename),
            "stage_context": self._stage_context(filename),
            "api_dir": api_dir or "<not provided>",
            "dataset_dir": dataset_dir or "<not provided>",
            "mcp_tools": mcp_tools_text,
            "data_summary": data_summary,
            "prior_resource_summary": prior_resource_summary if filename == "prior_construction.py" else "<none>",
            "primary_metric": self._primary_metric(),
            "metrics": ", ".join(self.config.metrics) if isinstance(self.config.metrics, list) else str(self.config.metrics),
            "time_budget": self.config.timeout,
            "script_summaries": script_summaries,
            "existing_code": existing_code or "<none>",
        }
        return STAGE_QUERY.format(**prompt_fields)

    def _extract_single_tag(self, response: str, tag: str) -> str:
        match = re.fullmatch(rf"\s*<{tag}>(.*?)</{tag}>\s*", response or "", flags=re.DOTALL | re.IGNORECASE)
        if not match:
            raise BundleFormatError(f"Generator output must contain exactly one {tag} block and no extra text", raw_response=response)
        return self._clean_code(match.group(1))

    def _stage_system_prompt(self, filename: str) -> str:
        fields = self.path_prompt_fields
        if filename == "prior_construction.py":
            return PRIOR_SYSTEM_PROMPT
        if filename == "data_preprocess.py":
            return DATA_SYSTEM_PROMPT.format(
                raw_mod1_path=fields.get("input_mod1_path", ""),
                raw_mod2_path=fields.get("input_mod2_path", ""),
                prep_train_out_path=fields.get("preprocess_train_mod1_path", ""),
                prep_val_out_path=fields.get("preprocess_val_mod1_path", ""),
                prep_test_out_path=fields.get("preprocess_test_mod1_path", ""),
                stats_json_path=fields.get("preprocess_metadata_path", ""),
            )
        if filename == "model_training.py":
            return MODEL_SYSTEM_PROMPT.format(
                prep_train_out_path=fields.get("preprocess_train_mod1_path", ""),
                prep_val_out_path=fields.get("preprocess_val_mod1_path", ""),
                prep_test_out_path=fields.get("preprocess_test_mod1_path", ""),
                best_model_out_path=fields.get("best_model_path", ""),
                embedding_out_path=fields.get("embedding_path", ""),
                embedding_metadata_out_path=fields.get("embedding_metadata_path", ""),
                performance_out_path=fields.get("model_performance_path", ""),
                training_logs_out_path=fields.get("training_logs_path", ""),
                pipeline_summary_out_path=fields.get("pipeline_summary_path", ""),
            )
        if filename == "downstream_analysis.py":
            return ANALYSIS_SYSTEM_PROMPT.format(
                cluster_assignments_out_path=fields.get("cluster_assignments_path", ""),
                cluster_metrics_out_path=fields.get("cluster_metrics_path", ""),
                cluster_summary_out_path=fields.get("cluster_summary_path", ""),
            )
        return MODEL_SYSTEM_PROMPT.format(
            prep_train_out_path=fields.get("preprocess_train_mod1_path", ""),
            prep_val_out_path=fields.get("preprocess_val_mod1_path", ""),
            prep_test_out_path=fields.get("preprocess_test_mod1_path", ""),
            best_model_out_path=fields.get("best_model_path", ""),
            embedding_out_path=fields.get("embedding_path", ""),
            embedding_metadata_out_path=fields.get("embedding_metadata_path", ""),
            performance_out_path=fields.get("model_performance_path", ""),
            training_logs_out_path=fields.get("training_logs_path", ""),
            pipeline_summary_out_path=fields.get("pipeline_summary_path", ""),
        )

    @staticmethod
    def _fix_system_prompt(filename: str) -> str:
        if filename == "prior_construction.py":
            return PRIOR_FIX_SYSTEM_PROMPT
        if filename == "data_preprocess.py":
            return DATA_FIX_SYSTEM_PROMPT
        if filename == "model_training.py":
            return MODEL_FIX_SYSTEM_PROMPT
        if filename == "downstream_analysis.py":
            return ANALYSIS_FIX_SYSTEM_PROMPT
        return MODEL_FIX_SYSTEM_PROMPT

    def generate_bundle(self, *, task_description: str, background: str, main_plan: str, prior_plan: str, data_summary: str, prior_resource_summary: str, script_summaries: str, mcp_tools_text: str, api_dir: str | None, dataset_dir: str | None, existing_bundle: Dict[str, tg.Variable] | None = None) -> Dict[str, tg.Variable]:
        bundle: Dict[str, tg.Variable] = {}
        for item in STAGE_FILES:
            filename = item["filename"]
            existing_code = existing_bundle[filename].value if existing_bundle and filename in existing_bundle else ""
            prompt = self._stage_query(
                filename=filename,
                task_description=task_description,
                background=background,
                main_plan=main_plan,
                prior_plan=prior_plan,
                data_summary=data_summary,
                prior_resource_summary=prior_resource_summary,
                script_summaries=script_summaries,
                existing_code=existing_code,
                mcp_tools_text=mcp_tools_text,
                api_dir=api_dir,
                dataset_dir=dataset_dir,
            )
            system_prompt = self._stage_system_prompt(filename)
            response = self.engine.generate(content=prompt, system_prompt=system_prompt, temperature=0.2)
            code = self._extract_single_tag(str(response), item["tag"])
            prompt_var = tg.Variable(prompt, requires_grad=False, role_description=f"generation prompt for {filename}")
            system_prompt_var = tg.Variable(
                system_prompt,
                requires_grad=False,
                role_description=f"system prompt for {filename}",
            )
            bundle[filename] = tg.Variable(
                code,
                requires_grad=True,
                role_description=f"generated code for {filename}",
                predecessors=[system_prompt_var, prompt_var],
            )
        return bundle

    def fix_target(
        self,
        *,
        code_bundle: Dict[str, tg.Variable],
        target: str,
        error: str,
        task_description: str,
        main_plan: str,
        prior_plan: str,
        max_fix_step: int = 1,
    ) -> bool:
        filename = target if target in STAGE_TAG_BY_FILE else STAGE_FILENAMES[0]
        target_var = code_bundle[filename]
        prompt_fields = {
            "target_file": filename,
            "target_tag": STAGE_TAG_BY_FILE[filename],
            "task_description": task_description,
            "main_plan": main_plan if filename != "prior_construction.py" else "<none>",
            "prior_plan": prior_plan if filename in {"prior_construction.py", "data_preprocess.py", "model_training.py"} else "<none>",
            "prior_schema_json": self._prior_schema_context(filename),
            "stage_requirements_json": self._stage_requirements_json(filename),
            "stage_context": self._stage_context(filename),
            "script_summaries": self.summarize_bundle(code_bundle),
            "target_code": target_var.value,
            "error": error,
        }
        prompt = FIX_QUERY.format(**prompt_fields)
        fix_system_prompt = self._fix_system_prompt(filename)
        for _ in range(max_fix_step):
            response = self.engine.generate(content=prompt, system_prompt=fix_system_prompt, temperature=0.2)
            target_var.set_value(self._extract_single_tag(str(response), STAGE_TAG_BY_FILE[filename]))
        return True

    def save_bundle(self, code_bundle: Dict[str, tg.Variable], step_tag: str) -> str:
        step_dir = os.path.join(self.config.code_dir, f"code_{step_tag}")
        os.makedirs(step_dir, exist_ok=True)
        for item in STAGE_FILES:
            with open(os.path.join(step_dir, item["filename"]), "w", encoding="utf-8") as f:
                f.write(code_bundle[item["filename"]].value)
        return step_dir

    @staticmethod
    def summarize_bundle(code_bundle: Dict[str, tg.Variable] | None, max_chars_per_file: int = 500) -> str:
        if not code_bundle:
            return "<none>"
        payload = {}
        for item in STAGE_FILES:
            text = code_bundle[item["filename"]].value if item["filename"] in code_bundle else ""
            payload[item["filename"]] = {"lines": len(text.splitlines()), "head": text[:max_chars_per_file]}
        return json.dumps(payload, ensure_ascii=False)
