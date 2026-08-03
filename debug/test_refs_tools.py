"""Tests for tools unblocked by ReferenceStore (refs).

Runs against:
  - data/pbmc_RNA_count.h5ad
  - data/pbmc_ATAC_count.h5ad

Refs used:
  - cellmarker_v2     (5 MB, markers category)
  - tf_list_hg38      (0.01 MB, tf_list category)
  - cistarget_hg38_10kb_v10_rankings  (297 MB, cistarget_db category)
  - motif_annotations_hgnc_v10        (94 MB, motif_annotations category)

Note: the pyscenic tool applies multiprocessing.set_start_method('fork', force=True)
internally via _patch_pyscenic_dask(). No need to set it here.
"""

import sys
sys.path.insert(0, '/Users/vickydong/Documents/singlecell_Agent')

import warnings
warnings.filterwarnings('ignore')

import scanpy as sc
import anndata as ad
from pathlib import Path

from backend.config import BackendConfig
from backend.refs.store import ReferenceStore

cfg = BackendConfig(cache_dir=Path.home() / '.sc_agent_cache')
refs = ReferenceStore(cfg)

RNA_PATH = Path('/Users/vickydong/Documents/singlecell_Agent/data/pbmc_RNA_count.h5ad')
ATAC_PATH = Path('/Users/vickydong/Documents/singlecell_Agent/data/pbmc_ATAC_count.h5ad')

# ---------------------------------------------------------------------------
# Shared RNA preprocessing (normalize → HVG → PCA → neighbors → leiden)
# ---------------------------------------------------------------------------
print("Loading and preprocessing RNA...")
adata_rna = sc.read_h5ad(RNA_PATH)
sc.pp.normalize_total(adata_rna, target_sum=1e4)
sc.pp.log1p(adata_rna)
sc.pp.highly_variable_genes(adata_rna, n_top_genes=2000)
sc.pp.pca(adata_rna, n_comps=30)
sc.pp.neighbors(adata_rna)
sc.tl.leiden(adata_rna, resolution=0.5)
print(f"RNA ready: {adata_rna.shape}, {adata_rna.obs['leiden'].nunique()} clusters")

# ---------------------------------------------------------------------------
# 1. rna_annotate_cellmarker
# ---------------------------------------------------------------------------
print("\n=== rna_annotate_cellmarker ===")
from backend.tools.rna.annotate import cellmarker as cellmarker_tool
result = cellmarker_tool.run(
    adata_rna,
    refs=refs,
    obs_cluster='leiden',
    species='Human',
    tissue_type='Blood',
)
print(f"Cluster-to-celltype: {result.uns['annotation']['cluster_to_celltype']}")
print("SUCCESS rna_annotate_cellmarker\n")

# ---------------------------------------------------------------------------
# 2. rna_grn_pyscenic (GRNBoost2 + cisTarget)
# ---------------------------------------------------------------------------
print("=== rna_grn_pyscenic ===")
from backend.tools.rna.grn import pyscenic as pyscenic_tool

# Use a small subset for speed (500 cells, 1000 HVGs)
adata_sub = adata_rna[:500, adata_rna.var['highly_variable']].copy()
print(f"Subset for pySCENIC: {adata_sub.shape}")

print("Fetching TF list via refs (small)...")
tf_list_path = refs.get_tf_list("tf_list_hg38")
print(f"TF list path: {tf_list_path}")

print("Fetching cistarget DB via refs (297 MB — may take a few minutes)...")
db_path = refs.get_cistarget_db("cistarget_hg38_10kb_v10_rankings")
print(f"cisTarget DB path: {db_path}")

print("Fetching motif annotations via refs (94 MB)...")
motif_ann_path = refs.get_motif_annotations("motif_annotations_hgnc_v10")
print(f"Motif annotations path: {motif_ann_path}")

result_grn = pyscenic_tool.run(
    adata_sub,
    tf_list_path=tf_list_path,
    cistarget_db_paths=[db_path],
    motif_annotations_path=motif_ann_path,
    n_jobs=2,
)
print(f"pySCENIC result: n_tfs={result_grn.n_tfs}, n_targets={result_grn.n_targets}, "
      f"n_regulons={result_grn.metadata['n_regulons']}")
print("SUCCESS rna_grn_pyscenic\n")

# ---------------------------------------------------------------------------
# 3. rna_grn_pyscenic_aucell (uses regulons from above)
# ---------------------------------------------------------------------------
print("=== rna_grn_pyscenic_aucell ===")
from backend.tools.rna.grn import pyscenic_aucell as aucell_tool
result_auc = aucell_tool.run(adata_sub, n_cpu=2)
print(f"AUCell result: {adata_sub.obsm['X_pyscenic_auc'].shape}, "
      f"n_tfs={result_auc.n_tfs}")
print("SUCCESS rna_grn_pyscenic_aucell\n")

# ---------------------------------------------------------------------------
# 4. atac_motif_enrichment — needs genome FASTA (3 GB)
# ---------------------------------------------------------------------------
print("=== atac_motif_enrichment ===")
print("SKIPPED — requires hg38 genome FASTA (3 GB download via refs.get_genome('hg38')).")
print("snapatac2.tl.motif_enrichment() requires a local FASTA for motif scanning.\n")

# ---------------------------------------------------------------------------
# 5. multi_grn_peak_to_gene — needs scenicplus package
# ---------------------------------------------------------------------------
print("=== multi_grn_peak_to_gene ===")
try:
    import scenicplus
    print("scenicplus installed, running test...")
    # (test would go here)
except ImportError:
    print("BLOCKED — scenicplus not on PyPI. Install from GitHub:")
    print("  pip install git+https://github.com/aertslab/pycisTopic.git")
    print("  pip install git+https://github.com/aertslab/pycistarget.git")
    print("  pip install git+https://github.com/aertslab/scenicplus.git")
    print("Requires Python <= 3.11.8\n")

# ---------------------------------------------------------------------------
# 6. multi_grn_pycistarget / multi_grn_scenicplus / multi_grn_scenicplus_aucell
# ---------------------------------------------------------------------------
print("=== multi_grn_pycistarget / scenicplus / scenicplus_aucell ===")
print("BLOCKED — require atac_topic_pycisTopic (pycistopic, conda-only) as upstream input.")
print("Also requires scenicplus and pycistarget packages.\n")
