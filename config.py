# config.py
"""Configuration for GitHub Models"""
import json
import math
import os
import random
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd
import textgrad as tg

FIXED_DATA_PRIOR_REQUIREMENTS: Dict[str, Any] = {
    "required_outputs": [
        "preprocess_metadata",
        "preprocess_train_mod1",
        "preprocess_val_mod1",
        "preprocess_test_mod1",
    ],
    "artifacts": {},
}

FIXED_MODEL_REQUIREMENTS: Dict[str, Any] = {
    "required_outputs": [
        "model_performance",
        "best_model",
        "embedding",
        "embedding_metadata",
        "training_logs",
        "pipeline_summary",
    ],
    "artifacts": {
        "embedding_metadata": {
            "format": "csv",
            "required_columns": ["cell_id", "split", "row_index", "cell_type", "batch"],
        }
    },
}

FIXED_DOWNSTREAM_REQUIREMENTS: Dict[str, Any] = {
    "required_outputs": [
        "cluster_assignments",
        "cluster_metrics",
        "cluster_summary",
    ],
    "artifacts": {
        "cluster_assignments": {
            "format": "csv",
            "required_columns": ["cell_id", "predicted_cluster", "split"],
        },
        "cluster_metrics": {
            "format": "json",
            "required_keys": ["ari"],
        },
    },
}
    
class Config:
    def __init__(self, code_dir = "saved_code", result_dir = "results", data_dir = "data", file_path = None,
                 mod1_path: str | None = None, mod2_path: str | None = None,
                 opt_step = 3, max_fix_step = 5, timeout = 300, task_type = "classification",
                 learning_type = "supervised", metrics="accuracy", label_column = None, id_column = None,
                 time_column = None, engine_name = "gpt-5",
                 monitor_train_epoch: int = 1, monitor_metric_epoch: int = 5):
        cur_path = os.path.dirname(os.path.abspath(__file__))
        code_dir = f"{cur_path}/{code_dir}"
        result_dir = f"{cur_path}/{result_dir}"
        data_dir = f"{cur_path}/{data_dir}"
        
        self.cur_path = cur_path
        self.intermediate_output_dir = f"{result_dir}/intermediate_output"
        Path(self.intermediate_output_dir).mkdir(parents=True, exist_ok=True)
        self.final_out_dir = f"{result_dir}/final_output"
        self.notes_dir = f"{cur_path}/notes"
        Path(self.final_out_dir).mkdir(parents=True, exist_ok=True)
        Path(self.notes_dir).mkdir(parents=True, exist_ok=True)
        self.data_mod1_path = mod1_path or file_path
        self.data_mod2_path = mod2_path
        self.single_code_dir = f"{code_dir}/singleeval"
        Path(code_dir).mkdir(parents=True, exist_ok=True)
        Path(result_dir).mkdir(parents=True, exist_ok=True)
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.single_code_dir).mkdir(parents=True, exist_ok=True)

        self.code_dir = code_dir
        self.result_dir = result_dir
        self.data_dir = data_dir
        self.artifact_layout_path = os.path.join(cur_path, "artifact_layout.json")
        self.current_step_layout: Dict[str, Any] = {}
        self.current_prior_schema: Dict[str, Any] = {}
        self.current_prior_dir_path: str = ""
        self.task_types = ["Regression", "Classification", "Clustering", "Integration"]
        self.learning_types = ["Supervised", "Unsupervised", "Self-supervised"]
        self.id_column = id_column
        self.time_column = time_column
        self.label_column = label_column
        self.engine_name = engine_name

        self.opt_step = opt_step
        self.max_fix_step = max_fix_step
        self.timeout = timeout
        self.metrics = metrics
        if monitor_train_epoch <= 0:
            raise ValueError("monitor_train_epoch must be a positive integer.")
        if monitor_metric_epoch <= 0:
            raise ValueError("monitor_metric_epoch must be a positive integer.")
        self.monitor_train_epoch = monitor_train_epoch
        self.monitor_metric_epoch = monitor_metric_epoch
        if self.data_mod1_path is None:
            raise ValueError("Error: mod1_path (or file_path) not provided")
        self.file_path = self.data_mod1_path
        if task_type.lower() in (x.lower() for x in self.task_types):
            self.task_type = task_type
        else:
            raise ValueError(f"Error: Task type should be one of: {self.task_types}")
        if learning_type.lower() in (x.lower() for x in self.learning_types):
            self.learning_type = learning_type
        else:
            raise ValueError(f"Error: Learning type should be one of: {self.learning_types}")
        if self.task_type.lower() == 'supervised'.lower():
            if self.label_column == None:
                raise ValueError(f"Error: Need to provide the column name of groundtruth (label_column) for supervised task!")

        self.engine = tg.get_engine(self.engine_name, max_tokens=5000)
        self.feat_stats = self.summarize_dataset_stats(sample_n=1, feature_n=100, random_seed=42)
        if self.label_column is None:
            try:
                parsed = json.loads(self.feat_stats.split("LLM SUMMARY (JSON):", 1)[-1])
                gt = parsed.get("ground_truth_column")
                if isinstance(gt, str) and gt.strip() and gt.strip().lower() != "unknown":
                    self.label_column = gt.strip()
            except Exception:
                pass

    def _load_json_config(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object at {path}")
        return data

    def load_artifact_layout(self) -> Dict[str, Any]:
        return deepcopy(self._load_json_config(self.artifact_layout_path))

    def apply_prior_schema(self, prior_schema: Dict[str, Any]) -> None:
        if not isinstance(prior_schema, dict):
            raise ValueError("prior schema must be a JSON object")
        self.current_prior_schema = deepcopy(prior_schema)

    def stage_requirements(self, filename: str) -> Dict[str, Any]:
        if filename == "data_prior.py":
            return {
                "required_outputs": deepcopy(FIXED_DATA_PRIOR_REQUIREMENTS["required_outputs"]),
                "artifacts": deepcopy(FIXED_DATA_PRIOR_REQUIREMENTS["artifacts"]),
                "prior_output_dir": self.current_prior_dir_path,
                "prior_files": self.resolved_prior_files(),
                "prior_schema": deepcopy(self.current_prior_schema),
            }
        if filename == "model_training.py":
            return deepcopy(FIXED_MODEL_REQUIREMENTS)
        if filename == "downstream_analysis.py":
            return deepcopy(FIXED_DOWNSTREAM_REQUIREMENTS)
        return {"required_outputs": [], "artifacts": {}}

    def downstream_requirements(self) -> Dict[str, Any]:
        return deepcopy(FIXED_DOWNSTREAM_REQUIREMENTS)

    def resolved_prior_files(self) -> List[Dict[str, Any]]:
        prior_schema = self.current_prior_schema if isinstance(self.current_prior_schema, dict) else {}
        required_files = prior_schema.get("required_files", [])
        if not isinstance(required_files, list):
            return []
        resolved: List[Dict[str, Any]] = []
        for item in required_files:
            if not isinstance(item, dict):
                continue
            file_name = str(item.get("file_name") or "").strip()
            if not file_name:
                continue
            payload = deepcopy(item)
            payload["path"] = os.path.join(self.current_prior_dir_path, file_name) if self.current_prior_dir_path else file_name
            resolved.append(payload)
        return resolved

    def _preprocess_split_extension(self) -> str:
        suffix = Path(str(self.data_mod1_path or "")).suffix.lower()
        if suffix == ".h5ad":
            return ".h5ad"
        return ".csv"

    def set_step_output_paths(self, step: int) -> Dict[str, Any]:
        step_dir = os.path.join(self.intermediate_output_dir, f"step_{step}")
        Path(step_dir).mkdir(parents=True, exist_ok=True)
        prior_dir = os.path.join(step_dir, "prior")
        Path(prior_dir).mkdir(parents=True, exist_ok=True)
        artifact_layout = self.load_artifact_layout()

        runtime_inputs = artifact_layout.get("runtime_inputs", {})
        generated_outputs = artifact_layout.get("generated_outputs", {})
        if not isinstance(runtime_inputs, dict) or not isinstance(generated_outputs, dict):
            raise ValueError("artifact_layout.json must contain object keys runtime_inputs and generated_outputs")

        resolved_inputs: Dict[str, str] = {}
        if self.data_mod1_path:
            resolved_inputs["mod1"] = os.path.abspath(self.data_mod1_path)
        if self.data_mod2_path:
            resolved_inputs["mod2"] = os.path.abspath(self.data_mod2_path)
        preprocess_ext = self._preprocess_split_extension()
        output_names = deepcopy(generated_outputs)
        for key in ["preprocess_train_mod1", "preprocess_val_mod1", "preprocess_test_mod1"]:
            value = output_names.get(key)
            if isinstance(value, str) and value:
                stem, _ = os.path.splitext(value)
                output_names[key] = stem + preprocess_ext
        resolved_outputs = {
            key: os.path.join(step_dir, value)
            for key, value in output_names.items()
            if isinstance(value, str) and value
        }

        for path in resolved_outputs.values():
            parent = os.path.dirname(path)
            if parent:
                Path(parent).mkdir(parents=True, exist_ok=True)

        resolved_layout = {
            "step": step,
            "run_dir": step_dir,
            "prior_output_dir": prior_dir,
            "runtime_inputs": resolved_inputs,
            "generated_outputs": resolved_outputs,
        }
        self.current_step_layout = deepcopy(resolved_layout)
        self.current_prior_dir_path = prior_dir
        for key, path in resolved_inputs.items():
            setattr(self, f"current_{key}_path", path)
        setattr(self, "current_prior_dir_path", prior_dir)
        for key, path in resolved_outputs.items():
            setattr(self, f"current_{key}_path", path)
        return resolved_layout

    def generate(self, prompt: str, sys_prompt: str) -> str:
        response = self.engine.generate(
            content=prompt,  
            system_prompt=sys_prompt, 
            temperature=0.2
        )
        
        return response


    def _parse_llm_feature_lists(
        self, llm_text: str, all_columns: List[str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Returns (continuous, categorical, warnings).
        Robust to extra text by extracting the first JSON object found.
        Filters to actual columns; de-duplicates; ensures disjoint lists.
        """
        warnings: List[str] = []
        raw = (llm_text or "").strip()

        # Extract JSON object if model added extra text.
        json_str = None
        # Try direct JSON
        if raw.startswith("{") and raw.endswith("}"):
            json_str = raw
        else:
            m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if m:
                json_str = m.group(0)

        if not json_str:
            warnings.append("LLM output did not contain a JSON object; falling back to empty lists.")
            return [], [], warnings

        try:
            obj = json.loads(json_str)
        except Exception as e:
            warnings.append(f"Failed to parse LLM JSON ({type(e).__name__}: {e}); falling back to empty lists.")
            return [], [], warnings

        cont = obj.get("continuous_features", [])
        cat = obj.get("categorical_features", [])

        if not isinstance(cont, list) or not isinstance(cat, list):
            warnings.append("LLM JSON keys were not lists; falling back to empty lists.")
            return [], [], warnings

        # Normalize to strings + strip
        cont = [str(x).strip() for x in cont if str(x).strip()]
        cat = [str(x).strip() for x in cat if str(x).strip()]

        # Keep only known columns
        col_set = set(all_columns)
        cont_unknown = [c for c in cont if c not in col_set]
        cat_unknown = [c for c in cat if c not in col_set]
        if cont_unknown:
            warnings.append(f"LLM continuous list contained unknown columns (ignored): {cont_unknown[:10]}")
        if cat_unknown:
            warnings.append(f"LLM categorical list contained unknown columns (ignored): {cat_unknown[:10]}")

        cont = [c for c in cont if c in col_set]
        cat = [c for c in cat if c in col_set]

        # De-dup preserve order
        def dedup(xs: List[str]) -> List[str]:
            seen = set()
            out = []
            for x in xs:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        cont = dedup(cont)
        cat = dedup(cat)

        # Ensure disjointness: categorical wins on conflicts (safer)
        overlap = [c for c in cont if c in set(cat)]
        if overlap:
            warnings.append(f"LLM put columns in both lists; treating as categorical: {overlap}")
            cont = [c for c in cont if c not in set(overlap)]

        return cont, cat, warnings


    def _to_py(self, obj: Any) -> Any:
        try:
            if isinstance(obj, np.generic):
                return obj.item()
        except Exception:
            pass
        if hasattr(obj, "tolist") and not isinstance(obj, (str, bytes)):
            try:
                return obj.tolist()
            except Exception:
                return str(obj)
        return obj


    def _load_any(self, path: str) -> Dict[str, Any]:
        ext = os.path.splitext(path.lower())[1]
        if ext == ".h5ad":
            import anndata as ad
            obj = ad.read_h5ad(path)
            return {"type": "h5ad", "obj": obj}
        if ext in [".csv", ".tsv", ".txt"]:
            sep = "\t" if ext in [".tsv", ".txt"] else ","
            df = pd.read_csv(path, sep=sep)
            return {"type": "df", "obj": df}
        if ext == ".parquet":
            df = pd.read_parquet(path)
            return {"type": "df", "obj": df}
        if ext == ".npy":
            arr = np.load(path)
            return {"type": "npy", "obj": arr}
        raise ValueError(f"Unsupported file extension: {ext}")


    def _extract_metadata_and_example(
        self, ds: Dict[str, Any], sample_n: int, feature_n: int
    ) -> Dict[str, Any]:
        if ds["type"] == "h5ad":
            adata = ds["obj"]
            num_samples = int(adata.n_obs)
            num_features = int(adata.n_vars)
            field_names = [str(x) for x in list(adata.obs.columns)]
            n_feat_sel = min(feature_n, num_features)
            n_samp_sel = min(sample_n, num_samples)
            example_dict: Dict[str, Any] = {}
            feature_names = []
            obs_example: Dict[str, Any] = {}
            if num_samples > 0 and n_feat_sel > 0 and n_samp_sel > 0:
                feature_names = [str(x) for x in list(adata.var_names)]
                sel_feat_names = feature_names[:n_feat_sel]
                feat_idx = [int(adata.var_names.get_loc(nm)) for nm in sel_feat_names]
                row_idx = 0
                try:
                    try:
                        from scipy.sparse import issparse
                    except Exception:
                        def issparse(x):
                            return hasattr(x, "toarray")
                    if issparse(adata.X):
                        row = adata.X[row_idx, :]
                        row_dense = np.asarray(row.toarray()).ravel()
                        vals = row_dense[feat_idx]
                    else:
                        vals = np.asarray(adata.X[row_idx, feat_idx]).ravel()
                except Exception:
                    row = adata.X[row_idx, :]
                    row_dense = np.asarray(getattr(row, "toarray", lambda: row)()).ravel()
                    vals = row_dense[feat_idx]
                example_dict = {sel_feat_names[i]: self._to_py(vals[i]) for i in range(len(sel_feat_names))}
                try:
                    obs_row = adata.obs.iloc[row_idx]
                    obs_example = {str(k): self._to_py(obs_row[k]) for k in obs_row.index}
                except Exception:
                    obs_example = {}
            example_key = f"example_{sample_n}_sample_{feature_n}_features_all_fields"
            example_all = {"obs": obs_example, "features": example_dict}
            return {
                "num_samples": num_samples,
                "num_features": num_features,
                "field_names": field_names,
                "feature_names": feature_names[:n_feat_sel],
                "example_key": example_key,
                example_key: example_all,
            }
        if ds["type"] == "df":
            df = ds["obj"]
            num_samples = int(df.shape[0])
            num_features = int(df.shape[1])
            field_names = [str(c) for c in list(df.columns)]
            n_feat_sel = min(feature_n, num_features)
            n_samp_sel = min(sample_n, num_samples)
            example_dict: Dict[str, Any] = {}
            if num_samples > 0 and n_feat_sel > 0 and n_samp_sel > 0:
                sel_feat_names = field_names[:n_feat_sel]
                row = df.iloc[0]
                example_dict = {nm: self._to_py(row[nm]) for nm in sel_feat_names}
            example_key = f"example_{sample_n}_sample_{feature_n}_features"
            return {
                "num_samples": num_samples,
                "num_features": num_features,
                "field_names": field_names,
                "example_key": example_key,
                example_key: example_dict,
            }
        if ds["type"] == "npy":
            arr = ds["obj"]
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            num_samples = int(arr.shape[0])
            num_features = int(arr.shape[1])
            field_names = [f"x{i}" for i in range(num_features)]
            n_feat_sel = min(feature_n, num_features)
            n_samp_sel = min(sample_n, num_samples)
            example_dict: Dict[str, Any] = {}
            if num_samples > 0 and n_feat_sel > 0 and n_samp_sel > 0:
                sel_feat_names = field_names[:n_feat_sel]
                row = np.asarray(arr[0, :n_feat_sel]).ravel()
                example_dict = {sel_feat_names[i]: self._to_py(row[i]) for i in range(len(sel_feat_names))}
            example_key = f"example_{sample_n}_sample_{feature_n}_features"
            return {
                "num_samples": num_samples,
                "num_features": num_features,
                "field_names": field_names,
                "example_key": example_key,
                example_key: example_dict,
            }
        raise ValueError("Unknown dataset type")


    def summarize_dataset_stats(
        self,
        *,
        sample_n: int = 1000,
        feature_n: int = 100,
        random_seed: Optional[int] = 42,
    ) -> str:
        """
        Two-step workflow:
        1) LLM#1 returns code to extract metadata from modality paths.
        2) Execute code, capture JSON output, feed to LLM#2 for final summary.
        """
        if not getattr(self, "file_path", None):
            raise ValueError("self.file_path is missing or empty.")

        mod1 = getattr(self, "data_mod1_path", None) or "unknown"
        mod2 = getattr(self, "data_mod2_path", None) or "unknown"

        default_example_key = f"example_{sample_n}_sample_{feature_n}_features"
        meta1 = {
            "num_samples": "unknown",
            "num_features": "unknown",
            "field_names": [],
            "example_key": default_example_key,
            default_example_key: "unknown",
            "notes": "direct extraction failed",
        }
        meta2 = {
            "num_samples": "unknown",
            "num_features": "unknown",
            "field_names": [],
            "example_key": default_example_key,
            default_example_key: "unknown",
            "notes": "not provided",
        }

        mod1_ds = None
        mod2_ds = None
        try:
            mod1_ds = self._load_any(mod1)
            meta1 = self._extract_metadata_and_example(mod1_ds, sample_n, feature_n)
            # print(f"[summarize_dataset_stats] Successfully read modality 1: {meta1}")
            meta1["notes"] = "direct extraction"
        except Exception as e:
            print(f"[summarize_dataset_stats] Failed to read modality 1: {mod1}. Error: {e}")

        if mod2 and str(mod2).strip().lower() not in ("unknown", "null", "", "na"):
            try:
                mod2_ds = self._load_any(mod2)
                meta2 = self._extract_metadata_and_example(mod2_ds, sample_n, feature_n)
                # print(f"[summarize_dataset_stats] Successfully read modality 2: {meta2}")
                meta2["notes"] = "direct extraction"
            except Exception as e:
                meta2["notes"] = "direct extraction failed"
                print(f"[summarize_dataset_stats] Failed to read modality 2: {mod2}. Error: {e}")

        alignment_check = {
            "modality_2_provided": bool(mod2_ds is not None),
            "same_num_samples": "unknown",
            "alignment_method": "unknown",
            "alignment_notes": "unknown",
        }

        def _guess_id_col(cols):
            if not cols:
                return None
            preferred = [
                "barcode", "cell_id", "cellid", "cell", "cellname",
                "id", "sample_id", "sampleid", "obs_names"
            ]
            lower_map = {c.lower(): c for c in cols}
            for key in preferred:
                if key in lower_map:
                    return lower_map[key]
            return None

        if mod2_ds is not None and mod1_ds is not None:
            try:
                n1 = int(meta1.get("num_samples", 0)) if str(meta1.get("num_samples")).isdigit() else None
                n2 = int(meta2.get("num_samples", 0)) if str(meta2.get("num_samples")).isdigit() else None
                if n1 is not None and n2 is not None:
                    alignment_check["same_num_samples"] = (n1 == n2)
            except Exception:
                pass

            id_col = self.id_column
            id_strategy = None
            same_order = None

            try:
                if mod1_ds["type"] == "h5ad" and mod2_ds["type"] == "h5ad":
                    ad1 = mod1_ds["obj"]
                    ad2 = mod2_ds["obj"]
                    if id_col and id_col in ad1.obs.columns and id_col in ad2.obs.columns:
                        id_strategy = f"obs[{id_col}]"
                        s1 = ad1.obs[id_col].astype(str).to_numpy()
                        s2 = ad2.obs[id_col].astype(str).to_numpy()
                        same_order = (len(s1) == len(s2)) and np.array_equal(s1, s2)
                    else:
                        id_strategy = "obs_names"
                        s1 = ad1.obs_names.astype(str).to_numpy()
                        s2 = ad2.obs_names.astype(str).to_numpy()
                        if len(s1) == len(s2) and len(s1) <= 200000:
                            same_order = np.array_equal(s1, s2)
                        elif len(s1) == len(s2):
                            same_order = (np.array_equal(s1[:50], s2[:50]) and np.array_equal(s1[-50:], s2[-50:]))
                        else:
                            same_order = False
                elif mod1_ds["type"] == "df" and mod2_ds["type"] == "df":
                    df1 = mod1_ds["obj"]
                    df2 = mod2_ds["obj"]
                    if id_col and id_col in df1.columns and id_col in df2.columns:
                        id_strategy = f"column[{id_col}]"
                        s1 = df1[id_col].astype(str).to_numpy()
                        s2 = df2[id_col].astype(str).to_numpy()
                        same_order = (len(s1) == len(s2)) and np.array_equal(s1, s2)
                    else:
                        c1 = _guess_id_col(list(df1.columns))
                        c2 = _guess_id_col(list(df2.columns))
                        if c1 and c2 and c1 == c2:
                            id_strategy = f"column[{c1}]"
                            s1 = df1[c1].astype(str).to_numpy()
                            s2 = df2[c2].astype(str).to_numpy()
                            same_order = (len(s1) == len(s2)) and np.array_equal(s1, s2)
                        else:
                            id_strategy = "row_order"
                            same_order = (df1.shape[0] == df2.shape[0])
                else:
                    id_strategy = "row_order"
                    same_order = (meta1.get("num_samples") == meta2.get("num_samples"))
            except Exception:
                id_strategy = "unknown"
                same_order = None

            alignment_check["alignment_method"] = id_strategy or "unknown"
            alignment_check["alignment_notes"] = (
                "aligned" if same_order is True else "not_aligned" if same_order is False else "unclear"
            )

        meta = {
            "modality_1": meta1,
            "modality_2": meta2 if mod2_ds is not None else "not provided"
        }

        # LLM #2: decide ground_truth_column + important_fields
        example_key = meta1.get("example_key", default_example_key)
        sys_prompt_2 = (
            "Return ONLY valid JSON (no prose) with keys:\n"
            "{\n"
            '  "num_samples": "string",\n'
            '  "num_features": "string",\n'
            '  "ground_truth_column": "string",\n'
            '  "modality_1_important_fields": ["string", ...],\n'
            '  "modality_2_important_fields": ["string", ...],\n'
            f'  "modality_1_{example_key}": "string",\n'
            f'  "modality_2_{example_key}": "string",\n'
            '  "modality_1_summary": "string",\n'
            '  "modality_2_summary": "string",\n'
            '  "alignment_assessment": "string",\n'
            '  "multiomics_strategy": "string",\n'
            '  "field_explanations": {"field": "one sentence explanation", ...},\n'
            '  "notes": "string"\n'
            "}\n"
            "Use 'unknown' when not inferable. Do NOT fabricate the example row; use the provided example. "
            "Interpret field names and example values to provide a one-sentence explanation for each field "
            "from a computational biology point of view. If modality 2 is provided, summarize both modalities, "
            "assess alignment, and propose a concrete multi-omics strategy (or alignment plan if unclear)."
        )
        prompt_2 = (
            "Summarize dataset based on extracted metadata from all modalities. Decide ground_truth_column and important_fields.\n"
            f"Metadata JSON:\n{json.dumps(meta, ensure_ascii=False)}\n"
            f"Requested sample_n: {sample_n}\n"
            f"Requested feature_n: {feature_n}\n"
        )

        try:
            llm2 = self.generate(prompt=prompt_2, sys_prompt=sys_prompt_2)
            parsed = json.loads((llm2 or "").strip())
        except Exception:
            parsed = {
                "num_samples": "unknown",
                "num_features": "unknown",
                "ground_truth_column": "unknown",
                "modality_1_important_fields": [],
                "modality_2_important_fields": [],
                example_key: "unknown",
                "field_explanations": {},
                "notes": "LLM error",
            }

        lines = []
        lines.append("DATASET SUMMARY (LLM, TWO-STEP):")
        lines.append(f"Modality 1 path: {mod1}")
        lines.append(f"Modality 2 path (optional): {mod2}")
        lines.append("Shape: unknown")
        lines.append("Sampled rows: 0 (not read)")
        lines.append(f"Alignment check: {json.dumps(alignment_check)}")
        lines.append("")
        lines.append("LLM SUMMARY (JSON):")
        lines.append(json.dumps(parsed, indent=2))
        lines.append("")

        return "\n".join(lines)

   
