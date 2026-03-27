import os
import json
import hashlib
import re
import sys
from dotenv import load_dotenv
import textgrad as tg
from config import Config
import pandas as pd
from typing import Any, List, Union, Optional, Tuple, Dict, Set
import math
import numpy as np
from multieval_types import ConsultantPlanRecord

from consultant_prompts import (
    MAIN_INPUT_QUERY_SUPERVISED,
    MAIN_INPUT_QUERY_UNSUPERVISED,
    MAIN_INPUT_QUERY_UNSUPERVISED_LABEL,
    MAIN_SYSTEM_PROMPT,
    PRIOR_SYSTEM_PROMPT,
    INPUT_QUERY_SUPERVISED,
    INPUT_QUERY_UNSUPERVISED,
    INPUT_QUERY_UNSUPERVISED_LABEL,
)

load_dotenv()


def _short(text: str, max_chars: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."


def _extract_exact_tag_payloads(text: str, tags: List[str]) -> Dict[str, str]:
    pattern = "".join(fr"\s*<{tag}>(.*?)</{tag}>" for tag in tags)
    match = re.fullmatch(pattern, (text or "").strip(), flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"Consultant output must contain exactly these tags in order: {tags}")
    payloads: Dict[str, str] = {}
    for tag, value in zip(tags, match.groups()):
        payloads[tag] = value.strip()
    return payloads


def plan_fingerprint(task_description: str, suggestion: str, prior_schema: Dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "task_description": task_description or "",
            "suggestion": suggestion or "",
            "prior_schema": prior_schema if isinstance(prior_schema, dict) else {},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def record_consultant_plan(
    *,
    consultant_records: List[ConsultantPlanRecord],
    path: str,
    record: ConsultantPlanRecord,
) -> None:
    consultant_records.append(record)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def build_consultant_history_context(
    consultant_records: List[ConsultantPlanRecord],
    full_k: int = 3,
) -> str:
    if not consultant_records:
        return "<none>"
    older = consultant_records[:-full_k] if len(consultant_records) > full_k else []
    recent = consultant_records[-full_k:]
    lines = ["[CONSULTANT_HISTORY]"]
    if older:
        older_fps = {}
        for rec in older:
            older_fps[rec.plan_fingerprint] = older_fps.get(rec.plan_fingerprint, 0) + 1
        lines.append(f"older_summary_count={len(older)}")
        lines.append(f"older_fingerprint_counts={older_fps}")
    else:
        lines.append("older_summary_count=0")
    lines.append("[RECENT_FULL_PLANS]")
    for rec in recent:
        lines.extend(
            [
                f"step={rec.step} source={rec.source} fingerprint={rec.plan_fingerprint}",
                f"task={_short(rec.task_description, 300)}",
                f"suggestion={_short(rec.suggestion, 1200)}",
                f"prior_schema={json.dumps(rec.prior_schema_json, ensure_ascii=False)[:1200]}",
            ]
        )
    return "\n".join(lines)


def build_reconsult_query(
    *,
    task_description: str,
    background: str,
    current_suggestion: str,
    current_prior_plan: str,
    current_prior_schema: Dict[str, Any],
    current_attempt: Dict[str, Any],
    why_current_fails: Dict[str, Any],
    historical_failures: str,
    hard_constraints: List[str],
    history_digest: str,
    consultant_history_context: str,
) -> str:
    return (
        "You are reconsulted to produce a new improved plan for the same task.\n\n"
        "[TASK_BLOCK]\n"
        f"TASK_DESCRIPTION={task_description}\n"
        f"BACKGROUND={background}\n"
        "[/TASK_BLOCK]\n\n"
        "[CURRENT_PLAN_BLOCK]\n"
        f"SUGGESTION={current_suggestion}\n"
        f"PRIOR_PLAN={current_prior_plan}\n"
        f"PRIOR_SCHEMA_JSON={json.dumps(current_prior_schema, ensure_ascii=False)}\n"
        "[/CURRENT_PLAN_BLOCK]\n\n"
        "[CURRENT_ATTEMPT_BLOCK]\n"
        f"{json.dumps(current_attempt, ensure_ascii=False, indent=2)}\n"
        "[/CURRENT_ATTEMPT_BLOCK]\n\n"
        "[WHY_CURRENT_FAILS_BLOCK]\n"
        f"{json.dumps(why_current_fails, ensure_ascii=False, indent=2)}\n"
        "[/WHY_CURRENT_FAILS_BLOCK]\n\n"
        "[HISTORICAL_FAILURES_BLOCK]\n"
        f"{historical_failures}\n\n"
        f"{history_digest}\n\n"
        f"{consultant_history_context}\n"
        "[/HISTORICAL_FAILURES_BLOCK]\n\n"
        "[HARD_CONSTRAINTS_BLOCK]\n"
        + "\n".join(f"- {c}" for c in hard_constraints)
        + "\n[/HARD_CONSTRAINTS_BLOCK]\n\n"
        "Instructions:\n"
        "1) Propose ONE concrete new plan that addresses why the current attempt fails.\n"
        "2) Do not repeat historically failed strategies unless you explicitly state what changed and why it should work now.\n"
        "3) Keep the plan implementation-ready for three downstream executable stage scripts named data_preprocess.py, model_training.py, and downstream_analysis.py.\n"
        "4) Treat the current prior schema as fixed input and do not redesign it here.\n\n"
        "Return ONLY:\n"
        "<TASK_DESCRIPTION>...</TASK_DESCRIPTION>\n"
        "<SUGGESTION>...</SUGGESTION>\n"
    )


def _validate_prior_schema(prior_schema: Dict[str, Any]) -> None:
    if not isinstance(prior_schema, dict):
        raise ValueError("Consultant PRIOR_SCHEMA_JSON must decode to a JSON object")
    placeholder_pattern = re.compile(r"^(column_[a-z0-9]+|col\d+|field[_-]?\d+|artifact[_-]?\d+|file\d+\.[a-z0-9]+)$", re.IGNORECASE)
    output_files = prior_schema.get("output_files")
    if output_files is None:
        output_files = prior_schema.get("required_files")
    if output_files is None:
        output_files = [prior_schema]
    if not isinstance(output_files, list) or not output_files:
        raise ValueError("Consultant PRIOR_SCHEMA_JSON must include a non-empty output_files list or a single file object")

    for item in output_files:
        if not isinstance(item, dict):
            raise ValueError("Each PRIOR_SCHEMA_JSON output_files entry must be an object")
        file_name = str(item.get("file_name") or "").strip()
        description = str(item.get("description") or "").strip()
        dtype = str(item.get("dtype") or "").strip()
        if not file_name or not description or not dtype:
            raise ValueError("Each PRIOR_SCHEMA_JSON file entry must include non-empty file_name, description, and dtype")
        if placeholder_pattern.match(file_name):
            raise ValueError(f"Consultant PRIOR_SCHEMA_JSON uses placeholder file name: {file_name}")
        shape = item.get("shape")
        if shape is not None:
            if not isinstance(shape, list) or not shape or not all(isinstance(dim, str) and dim.strip() for dim in shape):
                raise ValueError("Consultant PRIOR_SCHEMA_JSON shape must be a non-empty list of symbolic dimension strings when provided")

def _validate_main_plan_text(suggestion: Any) -> None:
    if not str(suggestion or "").strip():
        raise ValueError("Consultant SUGGESTION must be a non-empty string")


class TextGradConsultant:
    def __init__(self, config: Config, engine_name: str, consultant_type: str = "main"):
        self.config = config
        self.engine_name = engine_name
        self.consultant_type = consultant_type
        # self.engine = tg.get_engine(engine_name, max_completion_tokens=10000)
        self.engine = tg.get_engine(engine_name, max_tokens=5000)
        default_api_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apis")
        api_dir = getattr(self.config, "api_dir", default_api_dir)
        default_dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Datasets")
        dataset_dir = getattr(self.config, "dataset_dir", default_dataset_dir)
        api_examples_text = self._get_api_samples_text(api_dir=api_dir)
        prompt_template = PRIOR_SYSTEM_PROMPT if consultant_type == "prior" else MAIN_SYSTEM_PROMPT
        system_prompt_text = (
            prompt_template.replace("{example_api_results}", api_examples_text)
            .replace("{api_dir}", str(api_dir))
            .replace("{dataset_dir}", str(dataset_dir))
        )

        self.system_prompt = tg.Variable(
            system_prompt_text,
            requires_grad=False,
            role_description=f"system prompt for data analyzer for a {config.learning_type} {config.task_type} task"
        )

    def create_query(
        self,
        samples: Union[str, pd.DataFrame, None],
        id_col: str,
        background="Not available",
        label_col=None,
        api_dir: Optional[str] = None,
        dataset_dir: Optional[str] = None,
        include_feat_stats: bool = True,
        background_only: bool = False,
        include_samples: bool = True,
        max_samples: int = 10,
        max_cols: int = 200,
        random_seed: Optional[int] = 42,
        mcp_tools_text: str = "(unavailable)",
        prior_plan: str = "<omitted>",
        prior_output_summary: str = "<omitted>",
    ):
        api_dir_text = api_dir or "<not provided>"
        dataset_dir_text = dataset_dir or "<not provided>"
        prior_resource_paths = ", ".join(
            os.path.join(dataset_dir_text, name)
            for name in ["MsigDB.csv", "NeST.tsv", "GO_terms.csv", "Cell_marker_Human.xlsx", "meta_info.csv"]
        ) if dataset_dir_text and dataset_dir_text != "<not provided>" else "<omitted>"

        if not include_samples or samples is None:
            samples = "(omitted; see background/file path)"
        elif not isinstance(samples, str):
            samples = self._df_to_text(
                self._sample_df_for_prompt(samples, id_col, label_col, max_samples, max_cols, random_seed),
                id_col,
                label_col,
            )
        if background_only:
            return (
                "Background of the dataset:\n"
                f"{background}\n"
                "Please provide:\n"
                "<TASK_DESCRIPTION>...</TASK_DESCRIPTION>\n"
                "<SUGGESTION>...</SUGGESTION>\n"
            )

        if self.config.learning_type.lower() == 'unsupervised'.lower():
            if label_col != None:
                template = INPUT_QUERY_UNSUPERVISED_LABEL if self.consultant_type == "prior" else MAIN_INPUT_QUERY_UNSUPERVISED_LABEL
                query = template.format(task_type=self.config.task_type, learning_type=self.config.learning_type,
                                        feat_stats=self.config.feat_stats if include_feat_stats else "<omitted>", label_col=label_col, id_col=id_col,
                                        api_dir=api_dir_text, dataset_dir=dataset_dir_text,
                                        prior_resource_summary=getattr(self.config, "prior_resource_summary", "<omitted>"),
                                        prior_resource_paths=prior_resource_paths,
                                        prior_plan=prior_plan,
                                        prior_output_summary=prior_output_summary,
                                        mcp_tools=mcp_tools_text,
                                        metrics=self.config.metrics, samples=samples, background=background)
            else:
                template = INPUT_QUERY_UNSUPERVISED if self.consultant_type == "prior" else MAIN_INPUT_QUERY_UNSUPERVISED
                query = template.format(task_type=self.config.task_type, learning_type=self.config.learning_type,
                    feat_stats=self.config.feat_stats if include_feat_stats else "<omitted>", id_col=id_col, metrics=self.config.metrics,
                    api_dir=api_dir_text, dataset_dir=dataset_dir_text,
                    prior_resource_summary=getattr(self.config, "prior_resource_summary", "<omitted>"),
                    prior_resource_paths=prior_resource_paths,
                    prior_plan=prior_plan,
                    prior_output_summary=prior_output_summary,
                    mcp_tools=mcp_tools_text,
                    samples=samples, background=background)

        else:
            template = INPUT_QUERY_SUPERVISED if self.consultant_type == "prior" else MAIN_INPUT_QUERY_SUPERVISED
            query = template.format(task_type=self.config.task_type, learning_type=self.config.learning_type,
                feat_stats=self.config.feat_stats if include_feat_stats else "<omitted>", label_col=label_col, metrics=self.config.metrics,
                api_dir=api_dir_text, dataset_dir=dataset_dir_text,
                prior_resource_summary=getattr(self.config, "prior_resource_summary", "<omitted>"),
                prior_resource_paths=prior_resource_paths,
                prior_plan=prior_plan,
                prior_output_summary=prior_output_summary,
                mcp_tools=mcp_tools_text,
                id_col=id_col, samples=samples, background=background)

        return query

    def generate(self, prompt: str) -> str:
        response = self.engine.generate(
            content=prompt,  
            system_prompt=self.system_prompt.value, 
            temperature=0.2
        )
        return response

    def __call__(self, prompt: str):
        return self.generate(prompt)

    @staticmethod
    def parse_prior_summary_tags(text: str) -> dict:
        payloads = _extract_exact_tag_payloads(text, ["TASK_DESCRIPTION", "SUGGESTION", "PRIOR_SCHEMA_JSON"])
        prior_schema_raw = payloads["PRIOR_SCHEMA_JSON"]
        try:
            prior_schema = json.loads(prior_schema_raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Consultant PRIOR_SCHEMA_JSON is invalid JSON: {exc}") from exc
        _validate_prior_schema(prior_schema)
        return {
            "task_description": payloads["TASK_DESCRIPTION"],
            "suggestion": payloads["SUGGESTION"],
            "prior_schema": prior_schema,
        }

    @staticmethod
    def parse_main_summary_tags(text: str) -> dict:
        payloads = _extract_exact_tag_payloads(text, ["TASK_DESCRIPTION", "SUGGESTION"])
        _validate_main_plan_text(payloads["SUGGESTION"])
        return {
            "task_description": payloads["TASK_DESCRIPTION"],
            "suggestion": payloads["SUGGESTION"],
        }

    @staticmethod
    def parse_summary_tags(text: str) -> dict:
        return TextGradConsultant.parse_prior_summary_tags(text)

    @staticmethod
    def _get_api_samples_text(api_dir: Optional[str] = None, max_chars: int = 12000) -> str:
        api_sample_text = "(unavailable)"
        try:
            apis_dir = api_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "apis")
            if apis_dir not in sys.path:
                sys.path.append(apis_dir)
            from test_apis import get_sample_from_all_apis

            sample_output = get_sample_from_all_apis(execute=False)
            api_sample_text = json.dumps(sample_output, ensure_ascii=True)
            if len(api_sample_text) > max_chars:
                api_sample_text = api_sample_text[: max_chars - 3] + "..."
        except Exception as exc:
            api_sample_text = f"(unavailable: {exc})"

        return api_sample_text
    
    @staticmethod
    def _df_to_text(df: pd.DataFrame, id_col: str, label_col=None) -> str:
        if id_col not in df.columns:
            raise ValueError(f"'{id_col}' not found in DataFrame columns.")
        if label_col is not None and label_col not in df.columns:
            raise ValueError(f"'{label_col}' not found in DataFrame columns.")

        df_filled = df.copy()
        df_filled = df_filled.astype(object).where(pd.notna(df_filled), "Empty Spot")

        lines = []
        for _, row in df_filled.iterrows():
            parts = [f"Sample ID: {row[id_col]}"]

            feature_cols = [c for c in df_filled.columns if c not in [id_col, label_col]]
            if feature_cols:
                feat_text = ", ".join(f"{col}: {row[col]}" for col in feature_cols)
                parts.append(feat_text)

            if label_col is not None:
                parts.append(f"{label_col} (GroundTruth): {row[label_col]}")

            lines.append(", ".join(parts))

        return "\n".join(lines)

    @staticmethod
    def _sample_df_for_prompt(
        df: pd.DataFrame,
        id_col: str,
        label_col=None,
        max_samples: int = 10,
        max_cols: int = 200,
        random_seed: Optional[int] = 42,
    ) -> pd.DataFrame:
        if max_samples is not None and len(df) > max_samples:
            df = df.sample(n=max_samples, random_state=random_seed)
        if max_cols is not None:
            keep = [c for c in [id_col, label_col] if c is not None and c in df.columns]
            feature_cols = [c for c in df.columns if c not in set(keep)]
            if len(feature_cols) > max_cols:
                feature_cols = feature_cols[:max_cols]
            df = df[keep + feature_cols]
        return df
