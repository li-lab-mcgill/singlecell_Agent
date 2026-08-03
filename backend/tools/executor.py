"""Adapter layer: wraps backend/tools/**/*.py run(adata, ...) functions into the
DagExecutor calling convention.

DagExecutor calls:
    fn(input_h5ad_path=..., output_h5ad_path=..., output_dir=..., method=..., **params)

Each tool's run() expects:
    run(adata, *, param1=default, param2=default, ...)

The adapter:
1. Loads adata from input_h5ad_path
2. Inspects run() signature — passes only params the function declares
3. Calls run(adata, **filtered_params)
4. If result is AnnData  → that adata is written to output_h5ad_path
   Otherwise             → the (in-place modified) input adata is written
5. Returns a metadata dict; if result is a metrics dict, its keys are merged in

This means:
- `method` is always popped (each file IS the method — it is not a run() param)
- `output_dir` is passed only if run() explicitly declares it
- Eval tools (ari_nmi, silhouette, ...) return a metrics dict; their adata
  annotations (adata.uns["eval_..."]) are still persisted to h5ad
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path
from typing import Any, Callable

import anndata as ad

from backend.tools.registry import get_registry


def _make_adapter(tool_id: str, run_fn: Callable) -> Callable:
    """Return a DagExecutor-compatible wrapper around run_fn."""
    sig = inspect.signature(run_fn)
    # Parameters declared by run() — skip 'adata' itself
    declared: set[str] = set(sig.parameters.keys()) - {"adata"}

    def adapter(
        *,
        input_h5ad_path: str,
        output_h5ad_path: str,
        output_dir: str,
        method: str | None = None,   # popped — the file is already the method
        **params: Any,
    ) -> dict[str, Any]:
        # --- 1. Load adata ---
        adata = ad.read_h5ad(input_h5ad_path)

        # --- 2. Filter kwargs to what run() actually declares ---
        filtered: dict[str, Any] = {k: v for k, v in params.items() if k in declared}
        if "output_dir" in declared:
            filtered["output_dir"] = output_dir
        # Some annotation tools declare 'refs' — supply None so they raise a clean
        # NotImplementedError rather than a missing-arg crash.
        if "refs" in declared and "refs" not in filtered:
            filtered["refs"] = None

        # --- 3. Call the tool ---
        result = run_fn(adata, **filtered)

        # --- 4. Determine which adata to persist ---
        if isinstance(result, ad.AnnData):
            # Tool returned a new or explicitly modified AnnData (e.g. after .copy())
            out_adata = result
        else:
            # Tool modified adata in-place (clustering, embedding, eval, etc.)
            out_adata = adata

        out_adata.write_h5ad(output_h5ad_path)

        # --- 5. Extract standard output context keys from adata.uns ---
        # Tools write to well-known adata.uns locations; read them back so the
        # executor can auto-wire outputs to downstream steps without the plan
        # needing explicit declared_outputs.
        output_context: dict[str, Any] = {}
        uns = out_adata.uns
        emb = uns.get("embedding") or {}
        if emb.get("obsm_key"):
            output_context["embedding_key"] = emb["obsm_key"]
        clust = uns.get("clustering") or {}
        if clust.get("cluster_key"):
            output_context["cluster_key"] = clust["cluster_key"]
        proj = uns.get("projection") or {}
        if proj.get("obsm_key"):
            output_context["projection_key"] = proj["obsm_key"]
        bi = uns.get("batch_integration") or {}
        if bi.get("obsm_key"):
            output_context["embedding_key"] = bi["obsm_key"]  # overwrites PCA key
        vel = uns.get("velocity") or {}
        if vel.get("velocity_key"):
            output_context["velocity_key"] = vel["velocity_key"]
        if vel.get("latent_time_key"):
            output_context["latent_time_key"] = vel["latent_time_key"]

        # --- 6. Build return dict ---
        meta: dict[str, Any] = {
            "output_h5ad_path": output_h5ad_path,
            "status": "ok",
            "tool_id": tool_id,
            "n_obs": int(out_adata.n_obs),
            "n_vars": int(out_adata.n_vars),
            "output_context": output_context,
        }
        # Merge metrics/stage results from dict or dataclass returns
        if isinstance(result, dict):
            # Don't let tool return overwrite our bookkeeping keys
            for k, v in result.items():
                if k not in ("output_h5ad_path", "status", "tool_id"):
                    meta[k] = v
        elif dataclasses.is_dataclass(result) and not isinstance(result, type):
            # DE/GRN tools return result dataclasses — convert and merge
            for k, v in dataclasses.asdict(result).items():
                if k not in ("output_h5ad_path", "status", "tool_id"):
                    meta[k] = v

        return meta

    adapter._accepted_params = frozenset(declared)
    adapter.__name__ = f"adapter_{tool_id}"
    adapter.__doc__ = run_fn.__doc__
    return adapter


def build_wiki_executor_registry() -> dict[str, Callable]:
    """Scan backend/tools/**/*.py and return {tool_id: adapter_fn}.

    This is the sole tool registry used by DagExecutor. No backend object
    is required — each tool imports its own dependencies at call time.
    """
    raw = get_registry()
    return {tool_id: _make_adapter(tool_id, run_fn) for tool_id, run_fn in raw.items()}
