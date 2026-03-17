"""Code generator for the single-script scanpy agent."""

from __future__ import annotations

import json
import os
import re

import textgrad as tg
from dotenv import load_dotenv

from config import Config
from generator_prompts import FIX_QUERY, FIX_SYSTEM_PROMPT, JOINT_INPUT_QUERY, JOINT_SYSTEM_PROMPT
from multieval_types import PipelineBundle

load_dotenv()


class BundleFormatError(ValueError):
    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


class SingleScriptGenerator:
    def __init__(self, config: Config, engine_name: str, results_path: str):
        self.config = config
        self.results_path = results_path
        self.engine = tg.get_engine(engine_name, max_tokens=20000)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = getattr(config, "api_dir", f"{base_dir}/apis")
        dataset_dir = getattr(config, "dataset_dir", f"{base_dir}/Datasets")
        system_prompt_text = JOINT_SYSTEM_PROMPT.format(
            raw_mod1_path=config.data_mod1_path,
            raw_mod2_path=config.data_mod2_path,
            prep_train_out_path=config.preprocess_train_out_path,
            prep_val_out_path=config.preprocess_val_out_path,
            prep_test_out_path=config.preprocess_test_out_path,
            stats_json_path=config.preprocess_metadata_path,
            training_stats_json_path=config.model_perf_path,
            training_logs_path=config.training_logs_path,
            pipeline_summary_path=config.pipeline_summary_path,
            cluster_assignments_path=config.cluster_assignments_path,
            cluster_metrics_path=config.cluster_metrics_path,
            cluster_summary_path=config.cluster_summary_path,
            prior_manifest_path=config.prior_manifest_path,
            dataset_dir=dataset_dir,
        )
        self.system_prompt = tg.Variable(
            system_prompt_text,
            requires_grad=False,
            role_description="system prompt for single-script pipeline generation",
        )

    def create_query(
        self,
        task_descrp: str,
        data_summary: str,
        suggestion: str,
        interface_contract: str,
        script_summaries: str,
        background: str = "Not available",
        metadata: str = "<omitted>",
        preprocess_output_summary: str = "<omitted>",
        cluster_metrics: str = "<omitted>",
        cluster_summary: str = "<omitted>",
        mcp_tools_text: str = "(unavailable)",
        api_dir: str | None = None,
        dataset_dir: str | None = None,
    ) -> str:
        api_dir_text = api_dir or "<not provided>"
        dataset_dir_text = dataset_dir or "<not provided>"
        metrics_str = ", ".join(self.config.metrics) if isinstance(self.config.metrics, list) else str(self.config.metrics)
        primary_metric = metrics_str.split(",")[0].strip()
        return JOINT_INPUT_QUERY.format(
            task_descrp=task_descrp,
            background=background,
            api_dir=api_dir_text,
            dataset_dir=dataset_dir_text,
            mcp_tools=mcp_tools_text,
            metrics=metrics_str,
            primary_metric=primary_metric,
            file_path=self.config.file_path,
            data_summary=data_summary,
            suggestion=suggestion,
            time_budget=self.config.timeout,
            metadata=metadata,
            preprocess_output_summary=preprocess_output_summary,
            results_path=self.results_path,
            interface_contract=interface_contract,
            script_summaries=script_summaries,
            cluster_metrics=cluster_metrics,
            cluster_summary=cluster_summary,
        )

    def _generate_response(self, prompt: str) -> str:
        response = self.engine.generate(
            content=prompt,
            system_prompt=self.system_prompt.value,
            temperature=0.2,
        )
        return str(response)

    def generate_bundle(self, prompt: str) -> PipelineBundle:
        response = self._generate_response(prompt)
        return self._parse_bundle_response(response, prompt)

    def regenerate_bundle(self, prompt: str, error: str) -> PipelineBundle:
        retry_prompt = (
            f"{prompt}\n\n"
            "[PREVIOUS_GENERATION_ERROR]\n"
            f"{error}\n"
            "[/PREVIOUS_GENERATION_ERROR]\n"
            "Regenerate the full single-script pipeline. Return only the exact PIPELINE_CODE tag."
        )
        response = self._generate_response(retry_prompt)
        return self._parse_bundle_response(response, retry_prompt)

    @staticmethod
    def _extract_exact_bundle(response: str) -> str:
        match = re.fullmatch(r"\s*<PIPELINE_CODE>(.*?)</PIPELINE_CODE>\s*", response or "", flags=re.DOTALL | re.IGNORECASE)
        if not match:
            raise BundleFormatError(
                "Generator output must contain exactly one PIPELINE_CODE block and no extra text",
                raw_response=response,
            )
        return match.group(1).strip()

    @staticmethod
    def _clean_code(raw_code: str) -> str:
        match = re.search(r"```(?:python)?\n?(.*?)```", raw_code, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_code.strip()

    def _parse_bundle_response(self, response: str, prompt: str) -> PipelineBundle:
        code = self._clean_code(self._extract_exact_bundle(response))
        query = tg.Variable(prompt, requires_grad=False, role_description="single pipeline input query")
        return PipelineBundle(
            pipeline_code=tg.Variable(
                code,
                requires_grad=True,
                role_description="single pipeline script",
                predecessors=[self.system_prompt, query],
            )
        )

    def fix(self, code: tg.Variable, error: str) -> None:
        fix_prompt = FIX_QUERY.format(code=code.value, error=error)
        response = self.engine.generate(
            content=fix_prompt,
            system_prompt=FIX_SYSTEM_PROMPT,
            temperature=0.2,
        )
        code.set_value(self._clean_code(str(response)))

    def fix_stage(self, bundle: PipelineBundle, failed_stage: str, error: str, max_fix_step: int) -> bool:
        scoped_error = f"Target section: {failed_stage}\n{error}"
        for _ in range(max_fix_step):
            self.fix(bundle.pipeline_code, scoped_error)
        return True

    def save_bundle(self, bundle: PipelineBundle, step_tag: str) -> str:
        step_dir = os.path.join(self.config.code_dir, f"code_{step_tag}")
        os.makedirs(step_dir, exist_ok=True)
        path = os.path.join(step_dir, "pipeline.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(bundle.pipeline_code.value)
        return path

    @staticmethod
    def summarize_bundle(bundle: PipelineBundle, max_chars: int = 2400) -> str:
        text = bundle.pipeline_code.value
        payload = {"lines": len(text.splitlines()), "head": text[:max_chars]}
        return json.dumps(payload, ensure_ascii=False)
