# MultiVelo Backend Tools Code Review

**Reviewed**: 2026-05-14
**Scope**: All 6 MultiVelo tool implementations against `plans/multiVelo_plan.md`
**Files reviewed**:
- `backend/types.py` (dataclasses)
- `backend/tools/rna/velocity/scvelo.py`
- `backend/tools/multi/velocity/aggregate_peaks.py`
- `backend/tools/multi/velocity/knn_smooth.py`
- `backend/tools/multi/velocity/recover_dynamics.py`
- `backend/tools/multi/velocity/downstream.py`
- `backend/tools/multi/velocity/lrt_decoupling.py`

---

## `backend/types.py`

All three dataclasses correctly implemented: `VelocityResult`, `VelocityDownstreamResult`, `LRTResult`. Fields, types, and `to_dict()` methods match the plan spec.

No issues.

---

## Tool 1: `rna/velocity/scvelo.py`

Correct: prerequisites validation (`Mu`/`Ms` layers, embedding key, HVG warning), step order (`filter_and_normalize` → `sc.pp.neighbors` → `scv.pp.moments` → dynamics → velocity → graph → latent time), latent time skip with warning for non-dynamical mode, parquet save, both `adata.uns["scvelo"]` and `adata.uns["velocity"]` written, `VelocityResult` returned.

**[S1] LOW — Double-assignment for `n_velocity_genes`; second block is dead code** (lines 143–145)

```python
n_velocity_genes = int(adata.var.get("velocity_genes", adata.var.index.to_series().apply(lambda _: False)).sum())
if "velocity_genes" in adata.var:
    n_velocity_genes = int(adata.var["velocity_genes"].sum())
```

`DataFrame.get("velocity_genes", fallback)` already returns the column when the key is present. The second `if` block then reassigns the same value. The result is correct but the logic is confusing. The fallback expression is also unnecessarily expensive (`.apply(lambda _: False)`). Simplify to:

```python
n_velocity_genes = int(adata.var["velocity_genes"].sum()) if "velocity_genes" in adata.var else 0
```

**[S2] LOW — `adata.uns["scvelo"]` key name deviates from plan spec** (line 173)

The plan specifies `"n_top_genes": n_velocity_genes` inside `adata.uns["scvelo"]`. The implementation uses `"n_velocity_genes"`. `"n_velocity_genes"` is more descriptive, but anything reading `adata.uns["scvelo"]["n_top_genes"]` (e.g., wiki or downstream tooling) would fail. Align with plan or update plan.

**[S3] MEDIUM — `mode` parameter not validated before use**

`mode` is passed directly to `scv.tl.velocity(adata, mode=mode)` without upfront validation. An invalid mode (e.g. `"dynamic"` typo) produces a cryptic error inside scvelo rather than a clear upfront message. The plan marks three valid values explicitly.

Fix: add validation consistent with other tools in this codebase (e.g., `peak_to_gene.py` validates `species`):
```python
_VALID_MODES = {"dynamical", "stochastic", "deterministic"}
if mode not in _VALID_MODES:
    raise ValueError(
        f"mode='{mode}' is not valid. Choose from {sorted(_VALID_MODES)}."
    )
```

---

## Tool 2: `multi/velocity/aggregate_peaks.py`

Correct: ATAC path resolution with `FileNotFoundError`, input file existence check, `mv.aggregate_peaks_10x()` with correct parameter names, gene overlap validation, `mv.tfidf_norm()`, save back to disk, `adata.uns["velocity_aggregate_peaks"]` written with all plan-specified fields.

No issues.

---

## Tool 3: `multi/velocity/knn_smooth.py`

Correct: `distances` presence check, `_resolve_n_neighbors()` priority order (explicit → `wnn` → `neighbors`), sparse-aware row-by-row extraction using `D.getrow(i)`, `mv.knn_smooth_chrom()`, save back, `adata.uns["velocity_knn_smooth"]` with `source` field.

**[K1] MEDIUM — Phantom neighbor (cell index 0) when a row has fewer than k nonzero entries**

The sparse extraction initializes arrays with zeros:
```python
nn_idx  = np.zeros((n_cells, k), dtype=int)
nn_dist = np.zeros((n_cells, k), dtype=float)
```

If cell `i` has fewer than `k` actual neighbors in the distances matrix (e.g., boundary cells or a dense k-NN graph that isn't perfectly k-uniform), the remaining slots `nn_idx[i, n:]` stay at 0. Cell index 0 is then treated as a phantom neighbor with distance 0, which will be weighted highest by `mv.knn_smooth_chrom` during averaging.

This affects any cell where the WNN distances row has fewer than `k` nonzero entries. In practice most k-NN graphs are exactly k-uniform, so this fires rarely. But when it does, the smoothed chromatin signal for those cells silently incorporates cell 0's accessibility.

Fix: pad with the cell's own index (self-loop has no effect on most smoothers):
```python
nn_idx[i, :n] = nz_idx[order]
nn_idx[i, n:] = i               # self-loop: include self rather than cell 0
nn_dist[i, :n] = nz_dist[order]
nn_dist[i, n:] = 0.0
```

---

## Tool 4: `multi/velocity/recover_dynamics.py`

Correct: prerequisites validation (`Mu`/`Ms`, `connectivities`), ATAC path resolution with `Mc` check, gene overlap validation, all `mv.recover_dynamics_chrom()` parameters correctly threaded, `mv.set_velocity_genes()` call, `n_velocity_genes` / `model_distribution` / `mean_likelihood` extraction, parquet save, both `adata.uns["multivelo"]` and `adata.uns["velocity"]` written, `VelocityResult` returned.

**[R1] LOW — ATAC adata written back after `recover_dynamics_chrom` even if unmodified** (line 233)

```python
adata_atac.write_h5ad(atac_path)
```

The plan specifies this at step 9 ("Save updated ATAC adata back"). However, `mv.recover_dynamics_chrom()` writes all output (velocity layers, `fit_t`, `fit_state`, parameter columns) to the RNA `adata`, not to `adata_atac`. If the function does not modify `adata_atac` in-place, writing it back is unnecessary I/O — for large ATAC files (>5 GB) this can add minutes and risks overwriting a file that another concurrent step is reading.

If `mv.recover_dynamics_chrom` is confirmed not to modify `adata_atac`, remove the write. If it does write to `adata_atac` (e.g., internal time assignment per cell), the write is necessary — add a comment explaining what was written.

---

## Tool 5: `multi/velocity/downstream.py`

Correct: `_resolve_velocity_key()` helper, velocity layer presence check, `mv.velocity_graph(adata, vkey=vkey)`, `mv.latent_time(adata, vkey=vkey)`, `adata.uns["velocity"]["latent_time_key"]` updated via `setdefault`, LRT branch correctly captures all 3 return values (`_, _, lrt_df`), `lrt_df.to_dict()` stored, parquet save, `VelocityDownstreamResult` returned.

**[D1] MEDIUM — `mv.velocity_graph()` and `mv.latent_time()` used for scvelo-originated velocity layers**

The plan describes this tool as working after both `multi_velocity_recover_dynamics` AND `rna_velocity_scvelo`. When scvelo is upstream, `adata.uns["velocity"]["velocity_key"] = "velocity"` (scvelo's layer), not `"velo_s"`. The implementation calls:

```python
mv.velocity_graph(adata, vkey=vkey)   # vkey = "velocity" after scvelo
mv.latent_time(adata, vkey=vkey)
```

MultiVelo's `velocity_graph` and `latent_time` are designed around its own 3-ODE model (chromatin + RNA). Using them with scvelo's 2-ODE `"velocity"` layer is not guaranteed to produce correct results — in particular, `mv.latent_time` may expect chromatin-informed phase diagrams that aren't present after pure scvelo fitting.

Options:
1. Dispatch to `scv.tl.velocity_graph` / `scv.tl.latent_time` when `adata.uns["velocity"]["method"] == "scvelo"`.
2. Document this tool as MultiVelo-only and point scvelo users to a separate step.

Suggested fix:
```python
method = adata.uns.get("velocity", {}).get("method", "multivelo")
if method == "scvelo":
    import scvelo as scv
    scv.tl.velocity_graph(adata)
    if compute_latent_time:
        scv.tl.latent_time(adata)
else:
    mv.velocity_graph(adata, vkey=vkey)
    if compute_latent_time:
        mv.latent_time(adata, vkey=vkey)
```

**[D2] LOW — `mv.velocity_graph()` does not explicitly pass `xkey='Ms'`**

The plan shows: `mv.velocity_graph(adata, vkey='velo_s', xkey='Ms', **kwargs)`. The implementation omits `xkey`. MultiVelo's velocity graph uses the spliced count layer (`Ms`) as the reference expression matrix. If `mv.velocity_graph`'s default `xkey` is `'Ms'`, this is fine. If it defaults to `'spliced'` (scvelo convention), the wrong layer would be used silently.

Fix: pass explicitly for robustness:
```python
mv.velocity_graph(adata, vkey=vkey, xkey="Ms")
```

---

## Tool 6: `multi/velocity/lrt_decoupling.py`

Correct: prerequisites validation (`fit_model`, `fit_likelihood`, `fit_likelihood_c`), ATAC path resolution, 2× cost warning, capture of all 3 return values, `adata.uns["lrt_decoupling"]` written, n_tested / n_decoupled / n_coupled / pct_decoupled computed, parquet save, `LRTResult` returned. Zero-division guard (`if n_tested > 0`) is an improvement over the plan's bare formula.

No issues.

---

## Cross-Cutting

**[X1] LOW — `_resolve_atac_path()` duplicated across 4 files**

An identical helper function (`_resolve_atac_path`) appears in:
- `aggregate_peaks.py` (lines 62–72)
- `knn_smooth.py` (lines 63–73)
- `recover_dynamics.py` (lines 120–130)
- `lrt_decoupling.py` (lines 73–83)

The logic is identical in all four. Any change (e.g., to support a different default key name, or to add a helpful suggestion for a missing file) requires updating 4 files. Consider extracting to `backend/tools/multi/velocity/_utils.py` or a shared `_velocity_utils.py` module, following the same pattern used in SCENIC+ tools.

---

## Summary Table

| ID | Tool | File | Severity | Description |
|----|------|------|----------|-------------|
| D1 | downstream | `downstream.py` | **Medium** | `mv.velocity_graph`/`mv.latent_time` called even after scvelo; wrong functions for scvelo-originated velocity |
| S3 | scvelo | `scvelo.py` | **Medium** | `mode` not validated against allowed values before use |
| K1 | knn_smooth | `knn_smooth.py` | **Medium** | Sparse rows with < k neighbors produce phantom cell-0 neighbor |
| D2 | downstream | `downstream.py` | Low | `velocity_graph()` doesn't pass `xkey='Ms'` explicitly; relies on multivelo default |
| R1 | recover_dynamics | `recover_dynamics.py` | Low | ATAC adata written back after fitting even though it may be unmodified |
| S1 | scvelo | `scvelo.py` | Low | Double-assignment for `n_velocity_genes`; second `if` block is dead code |
| S2 | scvelo | `scvelo.py` | Low | `adata.uns["scvelo"]` key `"n_velocity_genes"` deviates from plan's `"n_top_genes"` |
| X1 | all multi | 4 files | Low | `_resolve_atac_path()` duplicated in all 4 multi/velocity tools |

### Priority fixes

1. **D1** — Dispatch to the correct library (`scv` vs `mv`) based on `adata.uns["velocity"]["method"]` in `downstream.py`. Without this, the scvelo → downstream path uses the wrong velocity graph and latent time functions.
2. **S3** — Add `mode` validation to `scvelo.py` upfront; consistent with how other tools validate enum-like parameters.
3. **K1** — Replace zero-fill with self-loop fill in `_extract_knn_from_sparse()` for cells with fewer than k actual neighbors.
4. **D2** — Pass `xkey="Ms"` explicitly to `mv.velocity_graph()` to avoid silent dependency on multivelo's default.
5. **S1** — Simplify `n_velocity_genes` extraction to a single conditional expression.
