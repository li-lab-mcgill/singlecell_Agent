import os
import json
import hashlib
import re
import sys
import logging
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
logger = logging.getLogger(__name__)


def _short(text: str, max_chars: int) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."


def _extract_exact_tag_payloads(text: str, tags: List[str]) -> Dict[str, str]:
    stripped = (text or "").strip()
    payloads: Dict[str, str] = {}
    cursor = 0

    for i, tag in enumerate(tags):
        start_match = re.search(fr"\s*<{tag}>", stripped[cursor:], flags=re.DOTALL | re.IGNORECASE)
        if not start_match:
            raise ValueError(f"Consultant output must contain exactly these tags in order: {tags}")
        absolute_start = cursor + start_match.start()
        if stripped[cursor:absolute_start].strip():
            raise ValueError(f"Consultant output must contain exactly these tags in order: {tags}")
        content_start = cursor + start_match.end()

        end_match = re.search(fr"</{tag}>", stripped[content_start:], flags=re.DOTALL | re.IGNORECASE)
        if end_match:
            content_end = content_start + end_match.start()
            cursor = content_start + end_match.end()
            payloads[tag] = stripped[content_start:content_end].strip()
            continue

        if i != len(tags) - 1:
            raise ValueError(f"Consultant output must contain exactly these tags in order: {tags}")

        payloads[tag] = stripped[content_start:].strip()
        cursor = len(stripped)

    if stripped[cursor:].strip():
        raise ValueError(f"Consultant output must contain exactly these tags in order: {tags}")
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


def _infer_schema_dtype(file_name: str, raw_dtype: Any) -> str:
    dtype = str(raw_dtype or "").strip()
    if dtype:
        return dtype
    suffix = os.path.splitext(str(file_name or "").strip())[1].lower()
    inferred = {
        ".csv": "csv",
        ".tsv": "tsv",
        ".txt": "txt",
        ".json": "json",
        ".jsonl": "jsonl",
        ".npy": "npy",
        ".npz": "npz",
        ".pt": "pt",
        ".pth": "pt",
        ".pkl": "pkl",
        ".parquet": "parquet",
        ".h5": "h5",
        ".h5ad": "h5ad",
    }.get(suffix)
    return inferred or "binary"


def _normalize_shape(shape: Any) -> Any:
    if shape is None:
        return None
    if isinstance(shape, list):
        normalized = [str(dim).strip() for dim in shape if str(dim).strip()]
        return normalized or None
    if isinstance(shape, str):
        cleaned = shape.strip()
        if not cleaned:
            return None
        cleaned = cleaned.strip("[]()")
        parts = [part.strip() for part in re.split(r"[,\u00d7x]", cleaned) if part.strip()]
        return parts or [shape.strip()]
    return None


def _normalize_prior_file_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(item)
    file_name = str(
        item.get("file_name")
        or item.get("filename")
        or item.get("file")
        or item.get("path")
        or item.get("output_file")
        or item.get("name")
        or ""
    ).strip()
    description = str(
        item.get("description")
        or item.get("purpose")
        or item.get("summary")
        or item.get("contents")
        or item.get("content")
        or item.get("notes")
        or ""
    ).strip()
    dtype = _infer_schema_dtype(
        file_name,
        item.get("dtype") or item.get("type") or item.get("format") or item.get("file_type"),
    )
    shape = _normalize_shape(item.get("shape") or item.get("dimensions") or item.get("dims"))

    normalized["file_name"] = file_name
    normalized["dtype"] = dtype
    if description:
        normalized["description"] = description
    elif file_name:
        normalized["description"] = f"Prior artifact generated at {file_name}"
    if shape is not None:
        normalized["shape"] = shape
    return normalized


def _normalize_prior_schema(prior_schema: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(prior_schema, dict):
        return prior_schema
    output_files = prior_schema.get("output_files")
    if output_files is None:
        output_files = prior_schema.get("required_files")
    if output_files is None:
        output_files = [prior_schema]
    if not isinstance(output_files, list):
        return prior_schema

    normalized_files: List[Dict[str, Any]] = []
    dropped_entries = 0
    for item in output_files:
        if not isinstance(item, dict):
            dropped_entries += 1
            continue
        normalized_item = _normalize_prior_file_entry(item)
        if normalized_item.get("file_name"):
            normalized_files.append(normalized_item)
        else:
            dropped_entries += 1

    normalized_schema = dict(prior_schema)
    normalized_schema["output_files"] = normalized_files
    if dropped_entries:
        logger.warning(
            "Dropped %d malformed PRIOR_SCHEMA_JSON output_files entries during normalization",
            dropped_entries,
        )
    return normalized_schema


def _validate_prior_decision(prior_decision: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(prior_decision, dict):
        raise ValueError("Consultant PRIOR_DECISION_JSON must decode to a JSON object")
    use_priors = prior_decision.get("use_priors")
    if not isinstance(use_priors, bool):
        raise ValueError("Consultant PRIOR_DECISION_JSON use_priors must be a boolean")
    decision_reason = str(prior_decision.get("decision_reason", "")).strip()
    if not decision_reason:
        raise ValueError("Consultant PRIOR_DECISION_JSON decision_reason must be a non-empty string")
    selected_resource_names = prior_decision.get("selected_resource_names", [])
    if not isinstance(selected_resource_names, list):
        raise ValueError("Consultant PRIOR_DECISION_JSON selected_resource_names must be a list")
    return {
        "use_priors": use_priors,
        "decision_reason": decision_reason,
        "selected_resource_names": [str(item).strip() for item in selected_resource_names if str(item).strip()],
    }

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
        prior_decision_summary: str = "<omitted>",
        rag_dataset_context: str = "RAG_DATASET_CONTEXT\n<none>",
        rag_prior_resource_context: str = "RAG_PRIOR_RESOURCE_CONTEXT\n<none>",
        rag_prior_method_context: str = "RAG_PRIOR_METHOD_CONTEXT\n<none>",
        rag_model_design_context: str = "RAG_MODEL_DESIGN_CONTEXT\n<none>",
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
                                        prior_decision_summary=prior_decision_summary,
                                        prior_plan=prior_plan,
                                        prior_output_summary=prior_output_summary,
                                        rag_dataset_context=rag_dataset_context,
                                        rag_prior_resource_context=rag_prior_resource_context,
                                        rag_prior_method_context=rag_prior_method_context,
                                        rag_model_design_context=rag_model_design_context,
                                        mcp_tools=mcp_tools_text,
                                        metrics=self.config.metrics, samples=samples, background=background)
            else:
                template = INPUT_QUERY_UNSUPERVISED if self.consultant_type == "prior" else MAIN_INPUT_QUERY_UNSUPERVISED
                query = template.format(task_type=self.config.task_type, learning_type=self.config.learning_type,
                    feat_stats=self.config.feat_stats if include_feat_stats else "<omitted>", id_col=id_col, metrics=self.config.metrics,
                    api_dir=api_dir_text, dataset_dir=dataset_dir_text,
                    prior_resource_summary=getattr(self.config, "prior_resource_summary", "<omitted>"),
                    prior_resource_paths=prior_resource_paths,
                    prior_decision_summary=prior_decision_summary,
                    prior_plan=prior_plan,
                    prior_output_summary=prior_output_summary,
                    rag_dataset_context=rag_dataset_context,
                    rag_prior_resource_context=rag_prior_resource_context,
                    rag_prior_method_context=rag_prior_method_context,
                    rag_model_design_context=rag_model_design_context,
                    mcp_tools=mcp_tools_text,
                    samples=samples, background=background)

        else:
            template = INPUT_QUERY_SUPERVISED if self.consultant_type == "prior" else MAIN_INPUT_QUERY_SUPERVISED
            query = template.format(task_type=self.config.task_type, learning_type=self.config.learning_type,
                feat_stats=self.config.feat_stats if include_feat_stats else "<omitted>", label_col=label_col, metrics=self.config.metrics,
                api_dir=api_dir_text, dataset_dir=dataset_dir_text,
                prior_resource_summary=getattr(self.config, "prior_resource_summary", "<omitted>"),
                prior_resource_paths=prior_resource_paths,
                prior_decision_summary=prior_decision_summary,
                prior_plan=prior_plan,
                prior_output_summary=prior_output_summary,
                rag_dataset_context=rag_dataset_context,
                rag_prior_resource_context=rag_prior_resource_context,
                rag_prior_method_context=rag_prior_method_context,
                rag_model_design_context=rag_model_design_context,
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
        payloads = _extract_exact_tag_payloads(text, ["TASK_DESCRIPTION", "SUGGESTION", "PRIOR_DECISION_JSON", "PRIOR_SCHEMA_JSON"])
        prior_decision_raw = payloads["PRIOR_DECISION_JSON"]
        try:
            prior_decision = json.loads(prior_decision_raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Consultant PRIOR_DECISION_JSON is invalid JSON: {exc}") from exc
        validated_decision = _validate_prior_decision(prior_decision)
        prior_schema_raw = payloads["PRIOR_SCHEMA_JSON"]
        try:
            prior_schema = json.loads(prior_schema_raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Consultant PRIOR_SCHEMA_JSON is invalid JSON: {exc}") from exc
        prior_schema = _normalize_prior_schema(prior_schema)
        if validated_decision["use_priors"]:
            _validate_prior_schema(prior_schema)
        else:
            output_files = prior_schema.get("output_files") if isinstance(prior_schema, dict) else None
            if not isinstance(prior_schema, dict):
                prior_schema = {"output_files": []}
            elif output_files != []:
                logger.warning(
                    "Consultant returned non-empty PRIOR_SCHEMA_JSON while use_priors=false; clearing schema"
                )
                prior_schema = {"output_files": []}
        return {
            "task_description": payloads["TASK_DESCRIPTION"],
            "suggestion": payloads["SUGGESTION"],
            "prior_decision": validated_decision,
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
