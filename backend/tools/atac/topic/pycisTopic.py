"""LDA topic modeling on peak-barcode count matrix via pycisTopic.

Fits a Latent Dirichlet Allocation (LDA) model to the ATAC peak matrix using
pycisTopic's collapsed Gibbs sampler. Produces cell × topic and peak × topic
weight matrices used as input to the SCENIC+ pipeline.

When n_topics is a list, all models are evaluated and evaluation plots are saved
to output_dir/topic_model_selection.pdf. A ValueError is then raised so the user
can inspect the plots and re-run with a single chosen n_topics value.

Serializes the full CistopicObject to disk — required by multi_grn_scenicplus.
"""

from __future__ import annotations

import logging
import pickle
import warnings
from pathlib import Path

logger = logging.getLogger(__name__)


def _align_first_axis(arr, target_len: int, name: str):
    """Orient a 2D array so its first axis has length ``target_len``.

    pycisTopic's ``CistopicLDAModel.cell_topic``/``topic_region`` orientation
    is not guaranteed to be stable across versions (some return
    cells/regions x topics, others topics x cells/regions). pycisTopic is not
    importable in this environment, so the true orientation cannot be probed
    directly — instead of assuming a fixed transpose, align by shape against
    the known AnnData axis length.
    """
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2D, got shape {arr.shape}")
    rows, cols = arr.shape
    if rows == target_len and cols == target_len:
        # Ambiguous square case (e.g. n_obs/n_vars == n_topics): shape alone
        # can't disambiguate orientation. Assume pycisTopic's native
        # orientation and leave the array untouched.
        return arr
    if rows == target_len:
        return arr
    if cols == target_len:
        return arr.T
    raise ValueError(
        f"{name} has shape {arr.shape}; neither dimension matches the "
        f"expected length {target_len}. Cannot determine orientation."
    )


def run(
    adata,
    *,
    n_topics: int | list[int] = 40,
    n_iter: int = 500,
    random_state: int = 555,
    alpha: float = 50.0,
    eta: float = 0.1,
    n_cpu: int = 4,
    force: bool = False,
    tmp_path: Path | None = None,
    output_dir: Path | None = None,
) -> object:
    """Fit LDA topic model(s) on the ATAC peak-barcode count matrix.

    Args:
        adata: AnnData with raw (non-normalized) peak counts in adata.X.
               Peak names in adata.var_names must be 'chr:start-end' format.
        n_topics: Number of topics. Pass a single int to fit one model and
                  proceed. Pass a list of ints to evaluate multiple models —
                  this saves a selection PDF and raises ValueError (human
                  inspection required before re-running).
        n_iter: Number of Gibbs sampling iterations (default 500).
        random_state: Random seed for reproducibility (default 555).
        alpha: Dirichlet prior on per-document topic distribution (default 50.0).
        eta: Dirichlet prior on per-topic word distribution (default 0.1).
        n_cpu: Number of parallel workers for multi-model fitting (default 4).
        force: If True, bypass the hard memory guard at 2e9 matrix entries.
        tmp_path: Directory for Gibbs sampler temporary files. Defaults to
                  output_dir/tmp if output_dir is set, else /tmp.
        output_dir: Directory for output artifacts (CistopicObject, model files,
                    evaluation plots).

    Returns:
        adata augmented in place with:
          - adata.obsm["X_topic"]: cell × topic matrix
          - adata.varm["topic_peak_weights"]: peak × topic weight matrix
          - adata.uns["topic_region_sets"]: {topic_id: [peak_names]}
          - adata.uns["cistopic_object_path"]: path to pickled CistopicObject
          - adata.uns["pycisTopic_model_path"]: path to pickled best LDA model
    """
    return _run_pycisTopic(
        adata,
        n_topics=n_topics,
        n_iter=n_iter,
        random_state=random_state,
        alpha=alpha,
        eta=eta,
        n_cpu=n_cpu,
        force=force,
        tmp_path=Path(tmp_path) if tmp_path else None,
        output_dir=Path(output_dir) if output_dir else None,
    )


def _run_pycisTopic(
    adata,
    *,
    n_topics,
    n_iter,
    random_state,
    alpha,
    eta,
    n_cpu,
    force,
    tmp_path,
    output_dir,
):
    import numpy as np
    import scipy.sparse as sp
    from pycisTopic.cistopic_class import create_cistopic_object, run_cgs_models

    # --- Resolve paths ---
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    if tmp_path is None:
        tmp_path = output_dir / "tmp" if output_dir else Path("/tmp")
    tmp_path.mkdir(parents=True, exist_ok=True)

    # --- Validate input ---
    assert all(":" in v and "-" in v for v in list(adata.var_names)[:5]), (
        "Peak names must be in 'chr:start-end' format for pycisTopic. "
        "Example: 'chr1:10000-10500'. Re-run peak calling with the correct format."
    )

    n_entries = adata.n_obs * adata.n_vars
    if n_entries > 2e9 and not force:
        raise MemoryError(
            f"Peak × cell matrix has {n_entries:.2e} entries "
            f"({adata.n_obs} cells × {adata.n_vars} peaks). "
            "This exceeds the 2e9 safety limit. Pass force=True to override, "
            "or subset to highly variable peaks first."
        )
    if n_entries > 5e8:
        warnings.warn(
            f"Peak × cell matrix has {n_entries:.2e} entries. "
            "pycisTopic will load this into memory. Consider subsetting to "
            "highly variable peaks to reduce memory usage.",
            UserWarning,
            stacklevel=2,
        )

    # --- Always use list for run_cgs_models ---
    n_topics_list = [n_topics] if isinstance(n_topics, int) else list(n_topics)
    fit_multiple = len(n_topics_list) > 1

    # --- Construct CistopicObject (regions × cells) ---
    # adata.X is cells × peaks; CistopicObject requires regions × cells
    fragment_matrix = adata.X.T.tocsr() if sp.issparse(adata.X) else adata.X.T

    cisTopic_obj = create_cistopic_object(
        fragment_matrix=fragment_matrix,
        cell_names=list(adata.obs_names),
        region_names=list(adata.var_names),
    )

    # --- Fit models ---
    models_save_path = str(output_dir / "topic_models") if output_dir else str(tmp_path / "topic_models")
    Path(models_save_path).mkdir(parents=True, exist_ok=True)

    logger.info("Fitting %d topic model(s): %s", len(n_topics_list), n_topics_list)
    models = run_cgs_models(
        cisTopic_obj,
        n_topics=n_topics_list,
        n_cpu=n_cpu,
        n_iter=n_iter,
        random_state=random_state,
        alpha=alpha,
        eta=eta,
        save_path=models_save_path,
        _temp_dir=str(tmp_path),
    )

    # --- Multiple models: plot selection metrics and stop ---
    if fit_multiple:
        _save_model_selection_plots(models, output_dir or tmp_path)
        selection_pdf = str((output_dir or tmp_path) / "topic_model_selection.pdf")
        raise ValueError(
            f"Multiple topic models fitted for n_topics={n_topics_list}. "
            f"Inspect the selection plots at:\n  {selection_pdf}\n"
            "Then re-run with a single n_topics=<chosen_value>."
        )

    # --- Single model: extract and store results ---
    model = models[0]
    cisTopic_obj.add_LDA_model(model)

    # cell x topic. model.cell_topic's orientation is not guaranteed stable
    # across pycisTopic versions (cells x topics vs topics x cells), so align
    # by shape against adata.n_obs rather than assuming a fixed transpose.
    cell_topic = model.cell_topic  # DataFrame or ndarray
    if hasattr(cell_topic, "values"):
        cell_topic = cell_topic.values
    cell_topic = _align_first_axis(cell_topic, adata.n_obs, "model.cell_topic")
    adata.obsm["X_topic"] = cell_topic.astype(np.float32)
    assert adata.obsm["X_topic"].shape[0] == adata.n_obs, (
        f"X_topic first dim {adata.obsm['X_topic'].shape[0]} != adata.n_obs "
        f"{adata.n_obs}; model.cell_topic orientation could not be resolved."
    )

    # peak x topic. Same orientation caveat as above, aligned to adata.n_vars.
    topic_region = model.topic_region
    if hasattr(topic_region, "values"):
        topic_region = topic_region.values
    topic_region = _align_first_axis(topic_region, adata.n_vars, "model.topic_region")
    adata.varm["topic_peak_weights"] = topic_region.astype(np.float32)
    assert adata.varm["topic_peak_weights"].shape[0] == adata.n_vars, (
        f"topic_peak_weights first dim {adata.varm['topic_peak_weights'].shape[0]} "
        f"!= adata.n_vars {adata.n_vars}; model.topic_region orientation could "
        "not be resolved."
    )
    n_topics_aligned = topic_region.shape[1]

    # --- Topic region sets: top peaks per topic ---
    import pandas as pd
    n_top_peaks = 500  # standard pycisTopic default for region set construction
    topic_region_df = pd.DataFrame(
        topic_region,
        index=adata.var_names,
        columns=[f"Topic{i+1}" for i in range(n_topics_aligned)],
    )
    topic_region_sets = {}
    for col in topic_region_df.columns:
        top_peaks = topic_region_df[col].nlargest(n_top_peaks).index.tolist()
        topic_region_sets[col] = top_peaks
    adata.uns["topic_region_sets"] = topic_region_sets

    # --- Serialize CistopicObject (required by multi_grn_scenicplus) ---
    if output_dir is not None:
        cistopic_path = output_dir / "cistopic_object.pkl"
        with open(cistopic_path, "wb") as f:
            pickle.dump(cisTopic_obj, f)
        adata.uns["cistopic_object_path"] = str(cistopic_path)
        logger.info("CistopicObject saved to %s", cistopic_path)

        model_path = output_dir / "topic_models" / f"model_{n_topics_list[0]}.pkl"
        adata.uns["pycisTopic_model_path"] = str(model_path)
    else:
        warnings.warn(
            "output_dir not set — CistopicObject not saved to disk. "
            "multi_grn_scenicplus requires adata.uns['cistopic_object_path']. "
            "Re-run with output_dir set.",
            UserWarning,
            stacklevel=2,
        )

    logger.info(
        "pycisTopic complete: %d cells × %d topics, %d topic region sets",
        adata.n_obs,
        n_topics_list[0],
        len(topic_region_sets),
    )
    return adata


def _save_model_selection_plots(models: dict, output_dir: Path) -> None:
    """Save log-likelihood, coherence, and density plots for model selection."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from pycisTopic.lda_models import evaluate_models

        output_dir.mkdir(parents=True, exist_ok=True)
        fig = evaluate_models(
            models,
            select_model=None,
            return_model=False,
            metrics=["Minmo_2011", "loglikelihood", "Arun_2010"],
            plot=True,
        )
        pdf_path = output_dir / "topic_model_selection.pdf"
        fig.savefig(str(pdf_path), bbox_inches="tight")
        plt.close(fig)
        logger.info("Topic model selection plots saved to %s", pdf_path)
    except Exception as e:
        logger.warning("Could not generate model selection plots: %s", e)
