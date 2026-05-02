from __future__ import annotations

from pathlib import Path
from typing import Any, List


class SingleCellStore:
    def __init__(
        self,
        dataset_dir: str | None = None,
        project_root: str | None = None,
        rscript_path: str = "Rscript",
    ):
        base_dir = Path(__file__).resolve().parent
        self.project_root = Path(project_root) if project_root else base_dir
        self.dataset_dir = Path(dataset_dir) if dataset_dir else (base_dir / "Datasets")
        self.rscript_path = str(rscript_path or "Rscript")

    def _rna_preprocessing(
        self,
        adata: Any,
        *,
        batch_key: str | None = None,
        min_genes: int = 200,
        max_pct_mito: float = 5.0,
        min_cells: int = 3,
        n_top_genes: int = 2000,
        target_sum: float = 1e4,
        n_pcs: int = 50,
    ) -> Any:
        """
        Standard preprocessing for single-cell RNA-seq data.

        Steps: QC filtering -> normalize_total -> log1p -> HVG selection -> scale -> PCA.
        Stores raw counts in adata.layers['counts'] before normalization.
        """
        import scanpy as sc

        # Preserve raw counts before any filtering/normalization.
        adata.layers["counts"] = adata.X.copy()

        sc.pp.filter_cells(adata, min_genes=min_genes)
        sc.pp.filter_genes(adata, min_cells=min_cells)
        adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-"))
        sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None, inplace=True)
        adata = adata[adata.obs["pct_counts_mt"] < max_pct_mito, :].copy()

        sc.pp.normalize_total(adata, target_sum=target_sum)
        sc.pp.log1p(adata)

        hvg_kwargs = {"n_top_genes": n_top_genes}
        if batch_key and batch_key in adata.obs.columns:
            hvg_kwargs["batch_key"] = batch_key
        sc.pp.highly_variable_genes(adata, **hvg_kwargs)
        adata.raw = adata
        adata = adata[:, adata.var["highly_variable"]].copy()

        sc.pp.scale(adata, max_value=10)
        n_comps = int(min(n_pcs, max(1, min(adata.n_obs - 1, adata.n_vars - 1))))
        if n_comps >= 1:
            sc.tl.pca(adata, n_comps=n_comps, svd_solver="arpack")

        return adata

    def _atac_preprocessing(
        self,
        adata: Any,
        *,
        min_features: int = 500,
        max_features: int = 50000,
        min_cells: int = 5,
        n_top_features: int = 30000,
        n_components: int = 50,
    ) -> Any:
        """
        Standard preprocessing for single-cell ATAC-seq data.

        Steps: QC filtering -> TF-IDF normalization -> feature selection -> LSI.
        Stores raw counts in adata.layers['counts'] before normalization.
        Expects adata.X to be a peak-by-cell binary or count matrix.
        """
        import numpy as np
        import scanpy as sc
        import scipy.sparse
        from sklearn.preprocessing import normalize
        from sklearn.utils.extmath import randomized_svd

        adata.layers["counts"] = adata.X.copy()

        sc.pp.calculate_qc_metrics(adata, percent_top=None, inplace=True)
        adata.obs["n_features"] = np.asarray((adata.X > 0).sum(axis=1)).ravel()

        adata = adata[
            (adata.obs["n_features"] >= min_features) & (adata.obs["n_features"] <= max_features),
            :,
        ].copy()
        sc.pp.filter_genes(adata, min_cells=min_cells)

        feature_counts = np.asarray(adata.X.sum(axis=0)).ravel()
        top_n = int(min(n_top_features, adata.n_vars))
        top_idx = np.argsort(feature_counts)[::-1][:top_n]
        top_features = adata.var_names[top_idx]
        adata.raw = adata
        adata = adata[:, top_features].copy()

        X = adata.X
        if scipy.sparse.issparse(X):
            X = X.toarray()
        X = X.astype(np.float64, copy=False)

        tf = X / (X.sum(axis=1, keepdims=True) + 1e-8)
        n_cells = X.shape[0]
        doc_freq = (X > 0).sum(axis=0) + 1
        idf = np.log1p(n_cells / doc_freq)
        tfidf = normalize(tf * idf, norm="l2", axis=1)
        adata.X = scipy.sparse.csr_matrix(tfidf)

        max_rank = max(1, min(adata.n_obs, adata.n_vars) - 1)
        n_svd = int(min(n_components + 1, max_rank))
        if n_svd >= 2:
            U, S, _ = randomized_svd(adata.X, n_components=n_svd, random_state=42)
            lsi = U[:, 1:] * S[1:]
        else:
            lsi = np.zeros((adata.n_obs, 0), dtype=np.float64)
        adata.obsm["X_lsi"] = lsi
        adata.obsm["X_pca"] = lsi

        return adata

    def _run_scvi(
        self,
        adata: Any,
        *,
        batch_key: str | None = None,
        n_latent: int = 30,
        n_layers: int = 2,
        n_epochs: int | None = None,
        random_seed: int = 42,
    ) -> Any:
        import random

        import numpy as np
        import scvi

        adata = adata.copy()
        random.seed(random_seed)
        np.random.seed(random_seed)
        try:
            import torch

            torch.manual_seed(random_seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(random_seed)
        except Exception:
            pass
        settings = getattr(scvi, "settings", None)
        if settings is not None:
            try:
                settings.seed = random_seed
            except Exception:
                pass

        setup_kwargs = {"layer": "counts"}
        if batch_key and batch_key in adata.obs.columns:
            setup_kwargs["batch_key"] = batch_key

        scvi.model.SCVI.setup_anndata(adata, **setup_kwargs)
        model = scvi.model.SCVI(
            adata,
            gene_likelihood="nb",
            n_latent=n_latent,
            n_layers=n_layers,
        )
        model.train(max_epochs=n_epochs)
        adata.obsm["X_scvi"] = model.get_latent_representation()
        return adata

    def _run_seurat(
        self,
        adata: Any,
        *,
        batch_key: str | None = None,
        n_pcs: int = 50,
        random_seed: int = 42,
    ) -> Any:
        import os
        import subprocess

        import pandas as pd

        adata = adata.copy()
        renv_lock = self.project_root / "renv.lock"
        if not renv_lock.exists():
            raise RuntimeError(
                f"Project renv is not initialized at {renv_lock}. "
                "Create a local R environment before using the Seurat tool."
            )

        tmp_dir = "./temp/seurat_pipeline"
        os.makedirs(tmp_dir, exist_ok=True)
        input_path = os.path.join(tmp_dir, "input.h5ad")
        adata.write(input_path)

        r_script = os.path.join(tmp_dir, "run_seurat.R")
        batch_integration_block = ""
        if batch_key:
            escaped_batch_key = str(batch_key).replace("\\", "\\\\").replace("'", "\\'")
            batch_integration_block = f"""
if ('{escaped_batch_key}' %in% colnames(adata@meta.data) && length(unique(adata@meta.data[['{escaped_batch_key}']])) > 1) {{
  adata <- IntegrateLayers(adata, method=RPCAIntegration, orig.reduction='pca', new.reduction='integrated.rpca', verbose=FALSE)
  reduction_use <- 'integrated.rpca'
}}
"""
        with open(r_script, "w") as f:
            f.write(
                f"""
library(Seurat)
library(sceasy)

adata <- sceasy::convertFormat("{input_path}", from="anndata", to="seurat")
DefaultAssay(adata) <- "RNA"
adata <- NormalizeData(adata, verbose=FALSE)
adata <- FindVariableFeatures(adata, selection.method="vst", nfeatures=2000, verbose=FALSE)
adata <- ScaleData(adata, verbose=FALSE)
adata <- RunPCA(adata, npcs={n_pcs}, seed.use={random_seed}, verbose=FALSE)

reduction_use <- "pca"
{batch_integration_block}
write.csv(Embeddings(adata, reduction=reduction_use),
          file.path("{tmp_dir}", "embeddings.csv"))
"""
            )

        source_expr = (
            f"renv::load('{self.project_root.as_posix()}'); "
            f"if (!requireNamespace('Seurat', quietly = TRUE)) stop('Seurat is not installed in the project renv'); "
            f"if (!requireNamespace('sceasy', quietly = TRUE)) stop('sceasy is not installed in the project renv'); "
            f"source('{Path(r_script).resolve().as_posix()}')"
        )
        result = subprocess.run(
            [self.rscript_path, "-e", source_expr],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = str(result.stderr or "").strip()
            stdout = str(result.stdout or "").strip()
            details = "\n".join(part for part in [stderr, stdout] if part)
            if not details:
                details = f"{self.rscript_path} failed with exit status {result.returncode}"
            raise RuntimeError(f"Seurat embedding failed: {details}")

        embeddings = pd.read_csv(os.path.join(tmp_dir, "embeddings.csv"), index_col=0)
        embeddings.index = embeddings.index.astype(str)
        aligned_embeddings = embeddings.reindex(adata.obs_names.astype(str))
        if aligned_embeddings.isnull().any(axis=None):
            raise RuntimeError("Seurat embedding output could not be aligned back to AnnData cell IDs")
        adata.obsm["X_seurat"] = aligned_embeddings.to_numpy()
        return adata

    def preprocess_singlecell(
        self,
        adata: Any,
        *,
        modality: str,
        batch_key: str | None = None,
        min_genes: int = 200,
        max_pct_mito: float = 5.0,
        min_cells: int = 3,
        n_top_genes: int = 2000,
        target_sum: float = 1e4,
        n_pcs: int = 50,
        min_features: int = 500,
        max_features: int = 50000,
        n_top_features: int = 30000,
        n_components: int = 50,
    ) -> Any:
        mode = str(modality or "").strip().lower()
        if mode == "rna":
            return self._rna_preprocessing(
                adata,
                batch_key=batch_key,
                min_genes=min_genes,
                max_pct_mito=max_pct_mito,
                min_cells=min_cells,
                n_top_genes=n_top_genes,
                target_sum=target_sum,
                n_pcs=n_pcs,
            )
        if mode == "atac":
            return self._atac_preprocessing(
                adata,
                min_features=min_features,
                max_features=max_features,
                min_cells=min_cells,
                n_top_features=n_top_features,
                n_components=n_components,
            )
        raise ValueError(f"Unsupported preprocessing modality: {modality}")

    def run_embedding(
        self,
        adata: Any,
        *,
        method: str,
        batch_key: str | None = None,
        n_latent: int = 30,
        n_layers: int = 2,
        n_epochs: int | None = None,
        n_pcs: int = 50,
        random_seed: int = 42,
    ) -> Any:
        selected_method = str(method or "").strip().lower()
        if selected_method == "scvi":
            return self._run_scvi(
                adata,
                batch_key=batch_key,
                n_latent=n_latent,
                n_layers=n_layers,
                n_epochs=n_epochs,
                random_seed=random_seed,
            )
        if selected_method == "seurat":
            return self._run_seurat(
                adata,
                batch_key=batch_key,
                n_pcs=n_pcs,
                random_seed=random_seed,
            )
        raise ValueError(f"Unsupported embedding method: {method}")

    def cluster_and_evaluate(
        self,
        adata: Any,
        *,
        embedding_key: str,
        n_neighbors: int = 15,
        resolution: float = 1.0,
        cluster_key: str | None = None,
        deg_method: str = "wilcoxon",
        label_key: str | None = None,
    ) -> Any:
        import numpy as np
        import scanpy as sc
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score

        if embedding_key not in adata.obsm:
            raise ValueError(f"Embedding key '{embedding_key}' not found in adata.obsm")

        if cluster_key is None:
            cluster_key = f"{embedding_key.replace('X_', '')}_clusters"
        deg_key = f"rank_genes_{cluster_key}"

        sc.pp.neighbors(adata, use_rep=embedding_key, n_neighbors=n_neighbors)
        sc.tl.leiden(adata, resolution=resolution, key_added=cluster_key)
        sc.tl.rank_genes_groups(adata, groupby=cluster_key, method=deg_method, key_added=deg_key)
        sc.tl.umap(adata)

        metrics: dict[str, float | None] = {
            "silhouette": None,
            "nmi": None,
            "ari": None,
        }
        embedding = adata.obsm[embedding_key]
        cluster_labels = np.asarray(adata.obs[cluster_key].astype(str))
        if len(np.unique(cluster_labels)) >= 2 and getattr(embedding, "shape", (0, 0))[0] >= 2:
            try:
                metrics["silhouette"] = float(silhouette_score(embedding, cluster_labels))
            except Exception:
                metrics["silhouette"] = None

        if label_key and label_key in adata.obs.columns:
            truth_labels = np.asarray(adata.obs[label_key].astype(str))
            valid_mask = truth_labels != "nan"
            if valid_mask.any():
                truth = truth_labels[valid_mask]
                pred = cluster_labels[valid_mask]
                if len(np.unique(truth)) >= 2 and len(np.unique(pred)) >= 2:
                    metrics["nmi"] = float(normalized_mutual_info_score(truth, pred))
                    metrics["ari"] = float(adjusted_rand_score(truth, pred))

        adata.uns[f"{cluster_key}_metrics"] = metrics
        return adata

    def batch_integration(
        self,
        *,
        input_h5ad_path: str,
        output_h5ad_path: str,
        batch_key: str,
        method: List[str] | str | None = None,
        methods: List[str] | str | None = None,
    ) -> dict[str, Any]:
        import numpy as np
        import scanpy as sc
        import scipy.sparse

        adata = sc.read_h5ad(input_h5ad_path)
        if batch_key not in adata.obs.columns:
            raise ValueError(f"Batch key '{batch_key}' not found in obs columns")

        def run_harmony() -> None:
            import scanpy.external as sce

            if "X_pca" not in adata.obsm:
                sc.tl.pca(adata, svd_solver="arpack")
            sce.pp.harmony_integrate(adata, key=batch_key)
            adata.obsm["X_harmony"] = adata.obsm["X_pca_harmony"]

        def run_liger() -> None:
            import pyliger

            bdata = adata.copy()
            bdata.obs[batch_key] = bdata.obs[batch_key].astype("category")
            batch_cats = bdata.obs[batch_key].cat.categories
            if isinstance(bdata.X, np.ndarray):
                bdata.X = scipy.sparse.csr_matrix(bdata.X)
            adata_list = [bdata[bdata.obs[batch_key] == b].copy() for b in batch_cats]
            for i, batch_name in enumerate(batch_cats):
                adata_list[i].uns["sample_name"] = batch_name
                adata_list[i].uns["var_gene_idx"] = np.arange(bdata.n_vars)
            liger_data = pyliger.create_liger(adata_list, remove_missing=False, make_sparse=False)
            liger_data.var_genes = bdata.var_names
            pyliger.normalize(liger_data)
            pyliger.scale_not_center(liger_data)
            pyliger.optimize_ALS(liger_data, k=30, max_iters=30)
            pyliger.quantile_norm(liger_data)
            adata.obsm["X_pca_liger"] = np.zeros((adata.shape[0], liger_data.adata_list[0].obsm["H_norm"].shape[1]))
            for i, batch_name in enumerate(batch_cats):
                adata.obsm["X_pca_liger"][adata.obs[batch_key] == batch_name] = liger_data.adata_list[i].obsm["H_norm"]
            adata.obsm["X_liger"] = adata.obsm["X_pca_liger"]

        def run_scvi() -> None:
            import scvi

            if "counts" not in adata.layers:
                if adata.raw is None:
                    raise ValueError("scVI batch integration requires raw counts in adata.raw or adata.layers['counts']")
                raw_index = [int(np.where(adata.raw.var_names == v)[0][0]) for v in adata.var_names]
                adata.layers["counts"] = adata.raw.X[:, raw_index]
            scvi.model.SCVI.setup_anndata(adata, layer="counts", batch_key=batch_key)
            vae = scvi.model.SCVI(adata, gene_likelihood="nb", n_layers=2, n_latent=30)
            vae.train()
            adata.obsm["X_pca_scVI"] = vae.get_latent_representation()
            adata.obsm["X_scVI"] = adata.obsm["X_pca_scVI"]

        requested = methods if methods is not None else method
        if requested is None:
            selected_methods = ["liger"]
        elif isinstance(requested, str):
            selected_methods = [requested]
        else:
            selected_methods = list(requested)
        for method_name in selected_methods:
            method = str(method_name).strip().lower()
            if method == "harmony":
                run_harmony()
            elif method == "liger":
                run_liger()
            elif method == "scvi":
                run_scvi()
            else:
                raise ValueError(f"Unsupported batch integration method: {method_name}")

        adata.write_h5ad(output_h5ad_path)
        return {
            "status": "ok",
            "input_h5ad_path": input_h5ad_path,
            "output_h5ad_path": output_h5ad_path,
            "batch_key": batch_key,
            "methods": selected_methods,
            "available_embeddings": sorted(list(adata.obsm.keys())),
            "n_cells": int(adata.n_obs),
            "n_genes": int(adata.n_vars),
        }

    def celltype_annotation(
        self,
        *,
        input_h5ad_path: str,
        output_h5ad_path: str,
        obs_cluster: str,
        method: List[str] | str = "gpt4",
        species: str = "",
        tissue_type: str = "",
        cancer_type: str = "Normal",
        openai_api_key: str | None = None,
        methods: List[str] | str | None = None,
    ) -> dict[str, Any]:
        import re

        import pandas as pd
        import scanpy as sc

        adata = sc.read_h5ad(input_h5ad_path)
        if obs_cluster not in adata.obs.columns:
            raise ValueError(f"Cluster key '{obs_cluster}' not found in obs columns")

        marker_path = self.dataset_dir / "Cell_marker_Human.xlsx"
        if not marker_path.exists():
            raise FileNotFoundError(f"Cell marker database not found: {marker_path}")

        def ensure_rank_genes() -> None:
            if "rank_genes" not in adata.uns:
                sc.tl.rank_genes_groups(adata, obs_cluster, method="wilcoxon", key_added="rank_genes")

        def _resolve_column(columns: List[str], candidates: List[str], contains: List[str] | None = None) -> str | None:
            lowered = {str(col).lower(): str(col) for col in columns}
            for candidate in candidates:
                if candidate.lower() in lowered:
                    return lowered[candidate.lower()]
            if contains:
                for col in columns:
                    text = str(col).lower()
                    if any(token in text for token in contains):
                        return str(col)
            return None

        def _load_cellmarker_reference() -> dict[str, list[str]]:
            marker = pd.read_excel(marker_path, sheet_name=0)
            columns = [str(col) for col in marker.columns]
            species_col = _resolve_column(columns, ["species"])
            tissue_col = _resolve_column(columns, ["tissue_type"], contains=["tissue"])
            cancer_type_col = _resolve_column(columns, ["cancer_type"], contains=["cancer"])
            cancer_normal_col = _resolve_column(columns, ["cancer_or_normal"], contains=["normal"])
            cell_type_col = _resolve_column(columns, ["cell_type", "cell_name"], contains=["cell_type", "cell"])
            symbol_col = _resolve_column(columns, ["Symbol", "symbol", "gene_symbol"])
            marker_col = _resolve_column(columns, ["marker"], contains=["marker"])

            if cell_type_col is None or (symbol_col is None and marker_col is None):
                raise ValueError("Cell_marker_Human.xlsx is missing required cell-type or gene columns")

            filtered = marker.copy()
            if species and species_col is not None:
                filtered = filtered.loc[
                    filtered[species_col].astype(str).str.strip().str.lower() == str(species).strip().lower()
                ]
            if tissue_type and tissue_col is not None:
                exact = filtered[tissue_col].astype(str).str.strip().str.lower() == str(tissue_type).strip().lower()
                if exact.any():
                    filtered = filtered.loc[exact]
                else:
                    contains = filtered[tissue_col].astype(str).str.lower().str.contains(str(tissue_type).strip().lower(), na=False)
                    if contains.any():
                        filtered = filtered.loc[contains]
            if cancer_type:
                cancer_value = str(cancer_type).strip().lower()
                if cancer_type_col is not None:
                    exact = filtered[cancer_type_col].astype(str).str.strip().str.lower() == cancer_value
                    if exact.any():
                        filtered = filtered.loc[exact]
                    elif cancer_normal_col is not None:
                        contains = filtered[cancer_normal_col].astype(str).str.lower().str.contains(cancer_value, na=False)
                        if contains.any():
                            filtered = filtered.loc[contains]
                elif cancer_normal_col is not None:
                    contains = filtered[cancer_normal_col].astype(str).str.lower().str.contains(cancer_value, na=False)
                    if contains.any():
                        filtered = filtered.loc[contains]

            gene_source_col = symbol_col or marker_col
            reference: dict[str, list[str]] = {}
            for _, row in filtered.iterrows():
                cell_name = str(row.get(cell_type_col, "")).strip()
                if not cell_name:
                    continue
                raw_gene = str(row.get(gene_source_col, "")).strip()
                if not raw_gene or raw_gene.lower() == "nan":
                    continue
                genes = [
                    token.strip().upper()
                    for token in re.split(r"[;,]", raw_gene)
                    if token and token.strip() and token.strip().lower() != "nan"
                ]
                if not genes:
                    continue
                bucket = reference.setdefault(cell_name, [])
                for gene in genes:
                    if gene not in bucket:
                        bucket.append(gene)
            if not reference:
                raise ValueError("No marker references matched the requested species/tissue/cancer filters")
            return reference

        def gpt4_method() -> None:
            import openai

            ensure_rank_genes()
            result = adata.uns["rank_genes"]
            groups = result["names"].dtype.names
            dat = pd.DataFrame({group: result["names"][group] for group in groups})
            df_first_10_rows = dat.head(10)
            rows_as_strings = df_first_10_rows.T.apply(lambda x: ",".join(x.dropna().astype(str)), axis=1)
            gene_list = "\n".join([f"{i + 1}.{row}" for i, row in enumerate(rows_as_strings)])
            parts = []
            if tissue_type:
                parts.append(f"of {tissue_type} cells")
            meta = []
            if species:
                meta.append(f"species: {species}")
            if cancer_type:
                meta.append(f"cancer type: {cancer_type}")
            meta_str = f" ({', '.join(meta)})" if meta else ""
            prompt = (
                f"Markers for each cluster ({obs_cluster}):\n"
                f"{gene_list}\n\n"
                f"Identify each cluster cell types {' '.join(parts)}{meta_str} using these markers separately for each row. "
                "Only return the cell type name.\n"
            )
            client = openai.OpenAI(api_key=openai_api_key) if openai_api_key else openai.OpenAI()
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
            lines = completion.choices[0].message.content.split("\n")
            names = [re.sub(r"^\s*\d+\s*[\.\-:]?\s*", "", line).strip() for line in lines if line.strip()]
            n_cluster = len(groups)
            cell_types = (names + [names[-1]] * n_cluster)[:n_cluster] if names else ["Unknown"] * n_cluster
            cluster2type = dict(zip(groups, cell_types))
            adata.obs["gpt4_predict_type"] = adata.obs[obs_cluster].map(cluster2type).astype("category")

        def cellmarker_method() -> None:
            ensure_rank_genes()
            reference = _load_cellmarker_reference()
            cell_annotation_norm = sc.tl.marker_gene_overlap(
                adata,
                reference,
                key="rank_genes",
                normalize="reference",
                adj_pval_threshold=0.05,
                inplace=False,
            )
            max_indexes = cell_annotation_norm.idxmax()
            adata.obs["CellMarker_predict_type"] = adata.obs[obs_cluster].astype(str).map(max_indexes.to_dict()).astype("category")

        requested = methods if methods is not None else method
        requested_methods = [requested] if isinstance(requested, str) else list(requested)
        completed_methods: list[str] = []
        for method_name in requested_methods:
            method = str(method_name).strip().lower()
            if method == "gpt4":
                gpt4_method()
            elif method == "cellmarker":
                cellmarker_method()
            elif method == "act":
                raise ValueError("ACT annotation is not supported in this repo because ACT.csv is not available")
            else:
                raise ValueError(f"Unsupported cell type annotation method: {method_name}")
            completed_methods.append(method)

        adata.write_h5ad(output_h5ad_path)
        added_obs = [col for col in ["gpt4_predict_type", "CellMarker_predict_type", "ACT_predict_type"] if col in adata.obs.columns]
        return {
            "status": "ok",
            "input_h5ad_path": input_h5ad_path,
            "output_h5ad_path": output_h5ad_path,
            "obs_cluster": obs_cluster,
            "methods": completed_methods,
            "added_obs_columns": added_obs,
            "marker_database_path": str(marker_path),
        }
