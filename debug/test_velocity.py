"""Velocity tool tests using scvelo example datasets."""
import sys
sys.path.insert(0, '/Users/vickydong/Documents/singlecell_Agent')

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import scanpy as sc
import scvelo as scv

print("=== rna_velocity_scvelo ===")
adata = scv.datasets.dentategyrus()
np.random.seed(42)
cell_idx = np.random.choice(adata.n_obs, 500, replace=False)
adata_sub = adata[cell_idx, :].copy()
sc.pp.pca(adata_sub)
print(f"Input: {adata_sub.shape}, layers={list(adata_sub.layers.keys())}")

from backend.tools.rna.velocity import scvelo as scvelo_tool
result = scvelo_tool.run(
    adata_sub,
    embedding_key='X_pca',
    mode='stochastic',
    compute_latent_time=False,
    n_neighbors=20,
    n_pcs=20,
)
print(f"scVelo result: method={result.method}, n_velocity_genes={result.n_velocity_genes}, mean_likelihood={result.mean_likelihood:.3f}")
print(f"velocity layer: {adata_sub.layers['velocity'].shape}")
print("SUCCESS rna_velocity_scvelo\n")

# multi_velocity_* tools (knn_smooth, recover_dynamics, downstream, lrt_decoupling, aggregate_peaks)
# NOT TESTED: require real paired RNA+ATAC velocity data (velocyto spliced/unspliced + gene-level Mc).
# See debug/tools_missing_input.md for details.
print("multi_velocity_* tools: SKIPPED — missing real paired velocyto + ATAC input files.")
