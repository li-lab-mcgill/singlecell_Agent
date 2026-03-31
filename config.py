"""Configuration and dataset summarization."""
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import textgrad as tg


# ── Fixed output schemas per stage ─────────────────────────────────

STAGE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "prior_construction.py": {"required_outputs": [], "artifacts": {}},
    "data_preprocess.py": {
        "required_outputs": [
            "preprocess_metadata", "preprocess_train_mod1",
            "preprocess_val_mod1", "preprocess_test_mod1",
        ],
        "artifacts": {},
    },
    "model_training.py": {
        "required_outputs": [
            "model_performance", "best_model", "embedding",
            "embedding_metadata", "training_logs", "pipeline_summary",
        ],
        "artifacts": {
            "embedding_metadata": {
                "format": "csv",
                "required_columns": ["cell_id", "split", "row_index", "cell_type", "batch"],
            },
        },
    },
    "downstream_analysis.py": {
        "required_outputs": [
            "cluster_assignments", "cluster_metrics", "cluster_summary",
        ],
        "artifacts": {
            "cluster_assignments": {
                "format": "csv",
                "required_columns": ["cell_id", "predicted_cluster", "split"],
            },
            "cluster_metrics": {"format": "json", "required_keys": ["ari"]},
        },
    },
}


class Config:
    """Central configuration for a single-cell agent run."""

    def __init__(
        self,
        *,
        mod1_path: str,
        mod2_path: Optional[str] = None,
        dataset_dir: Optional[str] = None,
        api_dir: Optional[str] = None,
        engine_name: str = "gpt-5",
        opt_steps: int = 5,
        max_fix_steps: int = 3,
        timeout: int = 3600,
        stagnation_limit: int = 5,
        delta_min: float = 0.005,
    ):
        self.cur_path = os.path.dirname(os.path.abspath(__file__))

        # Data paths
        self.mod1_path = os.path.abspath(mod1_path)
        self.mod2_path = os.path.abspath(mod2_path) if mod2_path else None
        self.dataset_dir = dataset_dir or os.path.join(self.cur_path, "Datasets")
        self.api_dir = api_dir or os.path.join(self.cur_path, "apis")

        # Run parameters
        self.engine_name = engine_name
        self.opt_steps = opt_steps
        self.max_fix_steps = max_fix_steps
        self.timeout = timeout
        self.stagnation_limit = stagnation_limit
        self.delta_min = delta_min
        self.metrics = "ARI"

        # Directory layout
        self.code_dir = os.path.join(self.cur_path, "saved_code", "singleeval")
        self.result_dir = os.path.join(self.cur_path, "results")
        self.intermediate_dir = os.path.join(self.result_dir, "intermediate_output")
        self.final_dir = os.path.join(self.result_dir, "final_output")
        self.notes_dir = os.path.join(self.cur_path, "notes")
        self.feedback_dir = os.path.join(self.result_dir, "feedback")
        for d in [self.code_dir, self.result_dir, self.intermediate_dir,
                  self.final_dir, self.notes_dir, self.feedback_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)

        # Artifact layout
        self.artifact_layout_path = os.path.join(self.cur_path, "artifact_layout.json")

        # Prior schema (set by consultant)
        self.prior_schema: Dict[str, Any] = {}
        self._current_prior_dir: str = ""

        # Engine + dataset summary
        self.engine = tg.get_engine(engine_name, max_tokens=5000)
        self.data_summary = self._summarize_dataset()
        self.prior_resource_summary = self._summarize_prior_resources()

    # ── Artifact path resolution ───────────────────────────────────

    def resolve_step_paths(self, step: int) -> Dict[str, Any]:
        """Create step directory and resolve all artifact paths."""
        step_dir = os.path.join(self.intermediate_dir, f"step_{step}")
        prior_dir = os.path.join(step_dir, "prior")
        Path(step_dir).mkdir(parents=True, exist_ok=True)
        Path(prior_dir).mkdir(parents=True, exist_ok=True)

        layout = self._load_json(self.artifact_layout_path)
        output_names = deepcopy(layout.get("generated_outputs", {}))

        # Fix extensions for h5ad data
        for key in ["preprocess_train_mod1", "preprocess_val_mod1", "preprocess_test_mod1"]:
            if key in output_names:
                stem = os.path.splitext(output_names[key])[0]
                output_names[key] = stem + ".h5ad"

        inputs = {"mod1": self.mod1_path}
        if self.mod2_path:
            inputs["mod2"] = self.mod2_path

        outputs = {k: os.path.join(step_dir, v) for k, v in output_names.items() if v}
        for path in outputs.values():
            Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)

        self._current_prior_dir = prior_dir

        return {
            "step": step,
            "run_dir": step_dir,
            "prior_output_dir": prior_dir,
            "runtime_inputs": inputs,
            "generated_outputs": outputs,
        }

    def stage_requirements(self, filename: str) -> Dict[str, Any]:
        """Return validation schema for a pipeline stage."""
        schema = deepcopy(STAGE_SCHEMAS.get(filename, {"required_outputs": [], "artifacts": {}}))
        if filename == "prior_construction.py":
            schema["prior_output_dir"] = self._current_prior_dir
            schema["prior_files"] = self._resolved_prior_files()
            schema["prior_schema"] = deepcopy(self.prior_schema)
        return schema

    def downstream_requirements(self) -> Dict[str, Any]:
        return deepcopy(STAGE_SCHEMAS["downstream_analysis.py"])

    # ── Prior file resolution ──────────────────────────────────────

    def _resolved_prior_files(self) -> List[Dict[str, Any]]:
        if not self.prior_schema:
            return []
        files = self.prior_schema.get("output_files", [self.prior_schema])
        if not isinstance(files, list):
            return []
        resolved = []
        for item in files:
            if not isinstance(item, dict):
                continue
            name = str(item.get("file_name", "")).strip()
            if not name:
                continue
            entry = deepcopy(item)
            entry.setdefault("artifact_key", Path(name).stem)
            entry.setdefault("format", Path(name).suffix.lstrip(".") or "binary")
            entry["path"] = os.path.join(self._current_prior_dir, name) if self._current_prior_dir else name
            resolved.append(entry)
        return resolved

    # ── Dataset summarization ──────────────────────────────────────

    def _summarize_dataset(self) -> str:
        """Extract metadata from h5ad and get LLM summary."""
        try:
            import anndata as ad
            adata = ad.read_h5ad(self.mod1_path, backed="r")
            obs_cols = list(adata.obs.columns)
            n_obs, n_vars = adata.n_obs, adata.n_vars
            var_sample = list(adata.var_names[:10])

            prompt = (
                f"Summarize this single-cell dataset.\n"
                f"Cells: {n_obs}, Genes: {n_vars}\n"
                f"obs columns: {obs_cols}\n"
                f"Sample genes: {var_sample}\n"
                f"Mod1: {self.mod1_path}\nMod2: {self.mod2_path or 'None'}\n"
            )
            sys = (
                "Return ONLY valid JSON with keys: num_samples, num_features, "
                "ground_truth_column, field_explanations, notes. "
                "Use 'unknown' when not inferable."
            )
            response = self.engine.generate(content=prompt, system_prompt=sys, temperature=0.2)
            return (
                f"DATASET SUMMARY:\n"
                f"Modality 1: {self.mod1_path}\n"
                f"Modality 2: {self.mod2_path or 'None'}\n"
                f"Shape: {n_obs} cells x {n_vars} genes\n"
                f"obs columns: {obs_cols}\n\n"
                f"LLM SUMMARY (JSON):\n{response}"
            )
        except Exception as e:
            return f"Failed to read dataset: {e}"

    def _summarize_prior_resources(self) -> str:
        """Scan dataset dir for known resource files."""
        resources = [
            ("MsigDB.csv", ","), ("NeST.tsv", "\t"), ("GO_terms.csv", ","),
            ("Cell_marker_Human.xlsx", None), ("meta_info.csv", ","),
        ]
        summaries = []
        for name, sep in resources:
            path = os.path.join(self.dataset_dir, name)
            entry: Dict[str, Any] = {"file_path": path, "exists": os.path.exists(path)}
            if os.path.exists(path):
                try:
                    if sep is None:
                        df = pd.read_excel(path, nrows=5)
                    else:
                        df = pd.read_csv(path, sep=sep, nrows=5)
                    entry["columns"] = list(df.columns)
                    entry["n_rows_preview"] = len(df)
                except Exception as e:
                    entry["error"] = str(e)
            summaries.append(entry)

        # Gene embeddings
        emb_dir = os.path.join(self.dataset_dir, "gene_embedding")
        if os.path.isdir(emb_dir):
            emb_path = os.path.join(emb_dir, "gene_embeddings.npy")
            try:
                emb = np.load(emb_path, mmap_mode="r")
                summaries.append({"file_path": emb_dir, "type": "gene_embedding", "shape": list(emb.shape)})
            except Exception:
                pass

        return json.dumps({"prior_resources": summaries}, indent=2)

    # ── Helpers ────────────────────────────────────────────────────

    def _load_json(self, path: str) -> Dict[str, Any]:
        with open(path, "r") as f:
            return json.load(f)

    def generate(self, prompt: str, sys_prompt: str) -> str:
        return self.engine.generate(content=prompt, system_prompt=sys_prompt, temperature=0.2)