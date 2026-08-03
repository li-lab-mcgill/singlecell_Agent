# Tool Review Checklist

Run through this before merging any new or modified tool.

---

### Signature
- [ ] `run(adata, *, ...)` — `adata` positional, all other params keyword-only
- [ ] Output key names exposed as params with sensible defaults
- [ ] No executor-managed params in signature (`input_h5ad_path`, `output_h5ad_path`, `output_dir`, `method`)
- [ ] Returns `adata` or a metrics `dict` — never `None`

### Imports
- [ ] Heavy dependencies imported inside `run()`, not at module top level
- [ ] Non-standard dependencies auto-install on `ImportError` before re-importing

### Metadata
- [ ] Writes to the correct `adata.uns` location with `method` and output key field
- [ ] Output key in `adata.uns` matches the param used to write to `adata.obsm` / `adata.obs`

### Array safety
- [ ] Every matrix written to `adata.obsm` has `shape[0] == adata.n_obs`
- [ ] Shape is validated explicitly — not assumed from library output orientation

### Input validation
- [ ] Required `adata.obs` columns checked before use, with descriptive error
- [ ] Required `adata.obsm` keys checked before use, with descriptive error

### Wiki sync
- [ ] `wiki/tools/<tool_id>.md` exists
- [ ] All consultant-facing params are documented; output key params are not
- [ ] No params in wiki that don't exist in `run()`, and vice versa
