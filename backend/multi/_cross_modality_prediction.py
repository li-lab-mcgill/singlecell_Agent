"""Cross-modality prediction: BABEL, Polarbear, scGLUE."""

from __future__ import annotations

from typing import Any

KNOWN_METHODS = ("babel", "polarbear", "scglue")


def dispatch(input_adata, *, source_modality: str, target_modality: str, method: str, refs=None, **kwargs: Any):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.cross_modality_predict method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement multi.cross_modality_predict(method='{method}', "
        f"source='{source_modality}', target='{target_modality}'). All three are pure Python."
    )
