---
type: method
id: nmf_programs
label: NMF Gene Program Discovery
---

Non-negative Matrix Factorization (NMF) decomposes the cells × genes expression matrix into a product of two non-negative matrices: a programs × genes matrix (gene loadings) and a cells × programs matrix (cell scores).

Each program is a weighted list of genes that co-vary across cells. The non-negativity constraint produces additive, interpretable programs where each cell is a mixture of programs.

**cNMF** (consensus NMF) runs NMF multiple times with random initialization, then clusters the resulting gene loading vectors to identify stable, consensus programs. This removes unstable solutions from individual runs.

Workflow (cNMF):
1. Choose number of programs K (evaluate using instability and error metrics across K values)
2. Run `cnmf.prepare()`, `cnmf.factorize()`, `cnmf.combine()`, `cnmf.consensus()`
3. Extract usage scores per cell → stored in `adata.obsm["X_cnmf"]`
4. Extract gene scores per program → stored as a programs × genes DataFrame

K selection: run cNMF for K = 5–15; plot instability vs. K and reconstruction error vs. K; choose K at the elbow or below the instability threshold.

Programs are not cell types — a cell can express multiple programs simultaneously. Annotation of programs requires inspecting the top-weighted genes per program.

Edges:
No executable backend tool currently implements NMF gene programs.
