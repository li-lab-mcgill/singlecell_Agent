"""Multimodal GRN inference: SCENIC+, FIGR, CellOracle."""

from __future__ import annotations

from typing import Any

from ..types import GRN

KNOWN_METHODS = ("scenic_plus", "figr", "celloracle")


def dispatch(rna_adata, atac_adata, *, method: str, gene_annotation: str, refs, runners, **kwargs: Any) -> GRN:
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown multi.grn_inference method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement multi.grn_inference(method='{method}'). "
        "All three need refs.get_motifs(...), refs.get_gtf(gene_annotation), refs.get_genome(...). "
        "SCENIC+ + CellOracle are Python; FIGR via R runner."
    )
