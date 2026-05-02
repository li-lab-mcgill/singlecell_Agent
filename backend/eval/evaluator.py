"""Evaluator: compute requested metrics on a processed AnnData file."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ._types import EvaluationResult
from . import _clustering_metrics as cm
from . import _batch_metrics as bm
from . import _biology_metrics as bim
from backend.objectives import add_objective_score

KNOWN_METRICS = {
    "silhouette", "ari", "nmi", "batch_lisi", "bio_lisi", "batch_entropy", "kbet", "marker_specificity",
}


class Evaluator:
    """Evaluate metrics on a processed AnnData file.

    Declarative: tell it which metrics you want + which keys in the adata
    they should reference. Missing keys produce warnings, not failures,
    so the agent can request several metrics in one call and see which
    applied.
    """

    def evaluate(
        self,
        input_h5ad_path: str | Path,
        *,
        metrics: List[str],
        embedding_key: Optional[str] = None,
        cluster_key: Optional[str] = None,
        label_key: Optional[str] = None,
        batch_key: Optional[str] = None,
        markers: Optional[Dict[str, List[str]]] = None,
        objective_name: Optional[str] = None,
    ) -> EvaluationResult:
        import scanpy as sc

        adata = sc.read_h5ad(str(input_h5ad_path))
        out: Dict[str, float] = {}
        warnings: List[str] = []

        for m in metrics:
            if m not in KNOWN_METRICS:
                warnings.append(f"{m}: unknown metric (known: {sorted(KNOWN_METRICS)})")
                continue
            try:
                if m == "silhouette":
                    _require(warnings, m, embedding_key=embedding_key)
                    # Silhouette is most meaningful against a label column;
                    # fall back to cluster_key if label_key missing.
                    use_key = label_key or cluster_key
                    if use_key is None:
                        warnings.append(f"{m}: need label_key or cluster_key")
                        continue
                    out[m] = cm.silhouette(adata, embedding_key=embedding_key, label_key=use_key)
                elif m == "ari":
                    if not (cluster_key and label_key):
                        warnings.append(f"{m}: cluster_key and label_key are required")
                        continue
                    out[m] = cm.ari(adata, cluster_key=cluster_key, label_key=label_key)
                elif m == "nmi":
                    if not (cluster_key and label_key):
                        warnings.append(f"{m}: cluster_key and label_key are required")
                        continue
                    out[m] = cm.nmi(adata, cluster_key=cluster_key, label_key=label_key)
                elif m == "batch_entropy":
                    if not (embedding_key and batch_key):
                        warnings.append(f"{m}: embedding_key and batch_key are required")
                        continue
                    out[m] = bm.batch_entropy(adata, embedding_key=embedding_key, batch_key=batch_key)
                elif m == "batch_lisi":
                    if not (embedding_key and batch_key):
                        warnings.append(f"{m}: embedding_key and batch_key are required")
                        continue
                    out[m] = bm.batch_lisi(adata, embedding_key=embedding_key, batch_key=batch_key)
                elif m == "bio_lisi":
                    if not (embedding_key and label_key):
                        warnings.append(f"{m}: embedding_key and label_key are required")
                        continue
                    out[m] = bim.bio_lisi(adata, embedding_key=embedding_key, label_key=label_key)
                elif m == "kbet":
                    if not (embedding_key and batch_key):
                        warnings.append(f"{m}: embedding_key and batch_key are required")
                        continue
                    out[m] = bm.kbet(adata, embedding_key=embedding_key, batch_key=batch_key)
                elif m == "marker_specificity":
                    if not cluster_key or not markers:
                        warnings.append(f"{m}: cluster_key and markers are required")
                        continue
                    out[m] = bim.marker_specificity(adata, cluster_key=cluster_key, markers=markers)
            except NotImplementedError as exc:
                warnings.append(f"{m}: {exc}")
            except Exception as exc:  # pragma: no cover - runtime safety
                warnings.append(f"{m}: failed ({exc})")

        out = add_objective_score(out, objective_name)
        return EvaluationResult(metrics=out, warnings=warnings)


def _require(warnings: List[str], metric: str, **keys: Any) -> None:
    missing = [k for k, v in keys.items() if not v]
    if missing:
        warnings.append(f"{metric}: missing required arg(s) {missing}")
