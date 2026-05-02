"""Foundation model inference: Geneformer, scGPT, scFoundation."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("geneformer", "scgpt", "scfoundation")
KNOWN_TASKS = ("embed", "predict_celltype", "perturbation_response")


def dispatch(adata, *, model: str, task: str, refs=None, **kwargs: Any):
    if model not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.foundation_model model: {model}. Choose from {KNOWN_METHODS}.")
    if task not in KNOWN_TASKS:
        raise ValueError(f"Unknown foundation-model task: {task}. Choose from {KNOWN_TASKS}.")
    raise NotImplementedError(
        f"TODO: implement multi.foundation_model(model='{model}', task='{task}'). "
        "Loads weights via refs.get_pretrained_model(model). Heavy: cap to one loaded model per session (LRU=1)."
    )
