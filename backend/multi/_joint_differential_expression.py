"""Joint RNA + ATAC differential expression: limma-voom, scanpy_joint, MAST joint."""

from __future__ import annotations

from typing import Any

from ..types import JointDEResult

KNOWN_METHODS = ("limma_voom", "scanpy_joint", "mast_joint")


def dispatch(rna_adata, atac_adata, *, group_key: str, method: str, runners=None, **kwargs: Any) -> JointDEResult:
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.joint_de method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement multi.joint_de(method='{method}'). "
        "limma-voom + MAST joint via R runner; scanpy_joint runs scanpy DE on both adatas + aligns results."
    )
