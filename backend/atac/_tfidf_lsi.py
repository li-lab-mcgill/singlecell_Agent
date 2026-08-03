"""ATAC TF-IDF + LSI (normalization + dimensionality reduction combined)."""

from __future__ import annotations

from typing import Any

from ._utils import require_matrix

KNOWN_METHODS = ("tfidf_lsi_v1", "tfidf_lsi_v3", "snapatac2_svd")


def dispatch(
    adata,
    *,
    method: str = "tfidf_lsi_v3",
    n_components: int = 50,
    drop_first: bool = True,
    binarize: bool = True,
    random_seed: int = 0,
    scale_factor: float = 10_000.0,
    embedding_key: str = "X_lsi",
    **kwargs: Any,
):
    if method not in KNOWN_METHODS:
        raise ValueError(f"Unknown atac.tfidf_lsi method: {method}. Choose from {KNOWN_METHODS}.")
    if method in {"tfidf_lsi_v1", "tfidf_lsi_v3"}:
        return _run_tfidf_lsi(
            adata,
            method=method,
            n_components=n_components,
            drop_first=drop_first,
            binarize=binarize,
            random_seed=random_seed,
            scale_factor=scale_factor,
            embedding_key=embedding_key,
        )
    raise NotImplementedError(
        "atac.tfidf_lsi(method='snapatac2_svd') requires snapatac2-specific AnnData handling and is not implemented yet."
    )


def _run_tfidf_lsi(
    adata,
    *,
    method: str,
    n_components: int,
    drop_first: bool,
    binarize: bool,
    random_seed: int,
    scale_factor: float,
    embedding_key: str = "X_lsi",
):
    import numpy as np
    from scipy import sparse
    from sklearn.decomposition import TruncatedSVD

    X = require_matrix(adata)
    X = X.tocsr().astype(float) if sparse.issparse(X) else sparse.csr_matrix(X, dtype=float)
    if binarize:
        X = X.copy()
        X.data[:] = 1.0

    row_sums = np.asarray(X.sum(axis=1)).ravel()
    if np.any(row_sums <= 0):
        raise ValueError("TF-IDF/LSI requires nonzero counts for every cell; run ATAC QC first.")
    feature_nnz = np.asarray(X.getnnz(axis=0)).ravel()
    if np.any(feature_nnz <= 0):
        raise ValueError("TF-IDF/LSI requires nonzero counts for every feature; run ATAC QC first.")

    tf = X.copy()
    tf.data = (tf.data / np.repeat(row_sums, np.diff(tf.indptr))) * float(scale_factor)
    idf = X.shape[0] / feature_nnz
    if method == "tfidf_lsi_v3":
        # Signac method 3: log(TF) * log(IDF). log1p keeps sparse nonzero
        # entries finite for low-depth cells without materializing zeros.
        tf.data = np.log1p(tf.data)
        tfidf = tf.multiply(np.log1p(idf))
    else:
        # Signac method 1/default: log(TF * IDF).
        tfidf = tf.multiply(idf)
        tfidf.data = np.log1p(tfidf.data)

    requested_raw = n_components + (1 if drop_first else 0)
    max_components = max(1, min(tfidf.shape) - 1)
    raw_components = min(requested_raw, max_components)
    if drop_first and raw_components < 2:
        raise ValueError("drop_first=True requires at least two available LSI components.")

    svd = TruncatedSVD(n_components=raw_components, random_state=random_seed)
    lsi_raw = svd.fit_transform(tfidf)
    lsi = lsi_raw[:, 1:] if drop_first else lsi_raw
    if lsi.shape[1] == 0:
        raise ValueError("LSI produced zero retained components; reduce n_components or set drop_first=False.")

    depth = np.log1p(row_sums)
    depth_correlation = []
    for idx in range(lsi_raw.shape[1]):
        component = lsi_raw[:, idx]
        if np.std(component) == 0 or np.std(depth) == 0:
            corr = 0.0
        else:
            corr = float(np.corrcoef(component, depth)[0, 1])
        depth_correlation.append(corr)

    adata.obsm[embedding_key] = lsi
    adata.uns["tfidf_lsi"] = {
        "method": method,
        "n_components": int(n_components),
        "raw_components": int(raw_components),
        "retained_components": int(lsi.shape[1]),
        "drop_first": bool(drop_first),
        "binarize": bool(binarize),
        "random_seed": int(random_seed),
        "scale_factor": float(scale_factor),
        "obsm_key": embedding_key,
        "explained_variance_ratio": [float(x) for x in svd.explained_variance_ratio_],
        "singular_values": [float(x) for x in svd.singular_values_],
        "depth_correlation": depth_correlation,
    }
    adata.uns["embedding"] = {"method": "lsi", "n_components": int(n_components), "obsm_key": embedding_key}
    if adata.obsm[embedding_key].shape != (adata.n_obs, lsi.shape[1]):
        raise RuntimeError(f"TF-IDF/LSI completed but adata.obsm['{embedding_key}'] has an invalid shape.")
    return adata
