"""Cell-cell communication: CellChat, CellPhoneDB, LIANA."""

from __future__ import annotations

from typing import Any

from ..types import CCCResult

KNOWN_METHODS = ("cellchat", "cellphonedb", "liana")


def dispatch(adata, *, method: str, group_key: str, species: str, refs=None, **kwargs: Any) -> CCCResult:
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown rna.cell_cell_comm method: {method}. Choose from {KNOWN_METHODS}.")
    raise NotImplementedError(
        f"TODO: implement rna.cell_cell_comm(method='{method}'). "
        "LIANA is pure Python; CellChat requires R runner; CellPhoneDB is Python CLI + LR DB (refs.get_lr_db)."
    )
