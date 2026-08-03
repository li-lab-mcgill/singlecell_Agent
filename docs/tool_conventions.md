# Backend Tool Conventions

Rules for writing backend tools. Every tool in `backend/tools/**/*.py` must follow these conventions.

---

## Signature

```python
def run(adata, *, param1=default, param2=default, ...):
```

- `adata` is the first positional argument
- All other parameters are keyword-only (after `*`)
- Output key names are exposed as parameters with sensible defaults (e.g. `embedding_key: str = "X_pca"`)
- Never declare executor-managed params: `input_h5ad_path`, `output_h5ad_path`, `output_dir`, `method`

---

## Return value

- Return the modified `adata` if the tool modifies or produces an AnnData object
- Return a `dict` of scalar metrics if the tool is an evaluation tool
- Never return `None`

---

## Imports

- Heavy dependencies must be imported inside `run()`, not at module top level
- If a dependency may not be installed, attempt auto-install inside `run()` before importing
- Stdlib modules and lightweight project utilities may be imported at module level

---

## Standard metadata (required for auto-wiring)

After writing any named output, write to the corresponding `adata.uns` location so the executor can forward it to downstream steps automatically:

| Tool type         | `adata.uns` key        | Required field       |
|-------------------|------------------------|----------------------|
| Embed             | `"embedding"`          | `"obsm_key"`         |
| Cluster           | `"clustering"`         | `"cluster_key"`      |
| Project           | `"projection"`         | `"obsm_key"`         |
| Batch integration | `"batch_integration"`  | `"obsm_key"`         |

Always include `"method"` alongside the output key field.

---

## Array shape safety

Any matrix assigned to `adata.obsm` must have `shape[0] == adata.n_obs`.

- Do not assume a library returns arrays in a fixed orientation — orientations change across library versions
- Always validate shape before assigning; raise a descriptive error if it does not match

---

## Input validation

- Validate that any required `adata.obs` column (e.g. `batch_key`, `label_key`) exists before use
- Validate that any required `adata.obsm` key (e.g. `embedding_key`) exists before use
- Error messages should name the missing key and indicate what needs to run first

---

## Wiki doc sync

- Every parameter the consultant (planner) sets must be documented in the corresponding `wiki/tools/<tool_id>.md`
- Output key params (e.g. `embedding_key` as output in embed tools) are executor-internal — do not document them
- Input key params (e.g. `embedding_key` consumed by cluster/project tools) are consultant choices — document them
- Wiki params and `run()` params must stay in sync: no phantom params in either direction
