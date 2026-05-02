"""Shared training-device helpers for model-backed methods."""

from __future__ import annotations

from typing import Any


USER_ACCELERATORS = ("auto", "cpu", "cuda", "gpu", "mps")


def build_lightning_train_config(
    *,
    accelerator: str | None = "auto",
    devices: str | int | None = "auto",
    precision: str | int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return PyTorch Lightning train kwargs plus auditable metadata.

    User-facing ``cuda`` is normalized to Lightning's generic ``gpu``
    accelerator. ``auto`` is resolved before calling Trainer so available GPU
    backends, including Apple MPS, are requested explicitly.
    """

    requested = (accelerator or "auto").strip().lower()
    if requested not in USER_ACCELERATORS:
        raise ValueError(
            f"Unsupported accelerator {accelerator!r}. Choose from {USER_ACCELERATORS}."
        )

    resolved = _resolve_accelerator(requested)
    train_kwargs: dict[str, Any] = {
        "accelerator": resolved["trainer_accelerator"],
        "devices": devices if devices is not None else "auto",
    }
    if precision is not None:
        train_kwargs["precision"] = precision

    metadata = {
        "requested_accelerator": requested,
        "accelerator": resolved["metadata_accelerator"],
        "trainer_accelerator": resolved["trainer_accelerator"],
        "devices": train_kwargs["devices"],
    }
    if precision is not None:
        metadata["precision"] = precision
    return train_kwargs, metadata


def _resolve_accelerator(requested: str) -> dict[str, str]:
    if requested == "auto":
        detected = _detect_best_accelerator()
        return _resolve_accelerator(detected)
    if requested == "cuda":
        return {"trainer_accelerator": "gpu", "metadata_accelerator": "cuda"}
    if requested == "gpu":
        return {"trainer_accelerator": "gpu", "metadata_accelerator": "gpu"}
    return {"trainer_accelerator": requested, "metadata_accelerator": requested}


def _detect_best_accelerator() -> str:
    try:
        import torch
    except Exception:
        return "cpu"

    try:
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass

    try:
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            return "mps"
    except Exception:
        pass

    return "cpu"
