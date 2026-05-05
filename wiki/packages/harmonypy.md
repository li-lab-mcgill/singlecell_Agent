---
type: package
id: harmonypy
version: ">=0.0.9"
citation: Korsunsky et al. 2019 Nature Methods
---

harmonypy is a Python port of the Harmony batch integration algorithm. It operates on precomputed embeddings (typically PCA) and returns a corrected embedding in the same dimensionality.

Install: `pip install harmonypy`

Harmony is the fastest and most widely used batch correction method. It works directly on PCA embeddings without requiring raw counts, making it easy to add to any pipeline. It does not modify the expression matrix — only the embedding. [Korsunsky et al. 2019]

Key parameter: `theta` controls the diversity penalty (default 2.0). Higher theta enforces stronger batch mixing at the cost of biological signal. For datasets with strong biological differences between batches, reduce theta to 1.0–1.5.

Output stored in `adata.obsm["X_harmony"]`.
