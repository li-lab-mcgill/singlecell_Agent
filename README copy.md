# Single-cell agent backend

Implements the design we discussed: tree-structured backend (`backend.rna`,
`backend.atac`, `backend.multi`, `backend.refs`, `backend.runners`),
flat tool surface, named-reference fetch with disk + memory cache, and
parameterized API query tools.

## Layout

```
backend/
├── __init__.py            # SingleCellBackend top-level wiring
├── config.py              # BackendConfig
├── types.py               # DEResult, PeakCallResult, MotifResult, ...
├── runners/
│   ├── r_runner.py        # RRunner (subprocess + JSON I/O)
│   └── cli_runner.py      # CliRunner (MACS3, samtools, ...)
├── refs/
│   ├── manifest.py        # Static catalogue of named references
│   ├── store.py           # ReferenceStore: 3-tier resolution
│   ├── loaders.py         # Per-format parsers
│   └── api_clients.py     # REST clients (Ensembl, JASPAR, CellxGene, ...)
├── rna/                   # 15 method modules; backend.py is the orchestrator
├── atac/                  # 12 method modules
├── multi/                 # 9 method modules
└── r_scripts/
    └── rna/dimreduction_seurat_pca.R   # Working example R script

agent_tool_base.py         # Existing AgentTool / AgentToolRegistry / MultiToolBase
agent_tools.py             # All tool classes with new informative names + registry builders
```

## What's implemented vs scaffolded

**Phase A — fully implemented (RNA core):**

- `rna_quality_control` — `basic` and `scrublet` paths run
- `rna_normalization` — `log1p` runs
- `rna_feature_selection` — all three flavors run
- `rna_dimensionality_reduction` — `pca`, `scvi`, `scanvi`, and `seurat_pca` (via R) run
- `rna_batch_integration` — `harmony`, `scvi`, `bbknn`, `scanorama` run
- `rna_clustering` — Leiden + Louvain run
- `rna_celltype_annotation` — `gpt4`, `cellmarker`, `celltypist` run
- `rna_differential_expression` — `wilcoxon` / `t` / `logreg` run
- `rna_2d_projection` — UMAP / t-SNE / FA all run

**Scaffolded (raises NotImplementedError with TODO marker):**

- All other RNA methods (gene programs, trajectory, velocity, perturbation, imputation, CCC)
- Every ATAC method
- Every multimodal method

The dispatcher + schema + tool wiring are complete for every scaffolded method —
fill in each `_run_<method>(...)` body and remove the `NotImplementedError` to
ship it. No re-architecture needed.

## ReferenceStore behavior

Auto-download with SHA256 verification, disk + LRU memory cache.

- First request for `hg38_genome` downloads from the URL in
  `backend/refs/manifest.py`, gunzips if needed, verifies SHA256, and parses.
- Manifest entries currently use placeholder SHA256 (`"0"*64`). On first
  successful download, ReferenceStore prints the observed hash to stderr —
  paste it back into the manifest to enable integrity checks.
- Cache lives at `~/.sc_agent_cache/refs/<category>/<version>/` by default;
  override via `BackendConfig(cache_dir=...)`.
- Memory cache is LRU-bounded by `BackendConfig.memory_budget_gb` (default 16 GB).
- The model never sees URLs. Tools accept reference names as enums; backend
  methods call `refs.get_genome("hg38")`, `refs.get_motifs("jaspar2024_core_vertebrates")`, etc.

## Runners

`RRunner` and `CliRunner` are real:

- `runners.r.run_script("rna/dimreduction_seurat_pca.R", args={...})` runs an R script as a subprocess, passes args via JSON file, parses the JSON the script prints to stdout.
- `runners.cli.run(["macs3", "callpeak", ...])` is a thin subprocess wrapper.

The included R script (`r_scripts/rna/dimreduction_seurat_pca.R`) is the working template — copy it for every other R-backed method following the
`<operation>_<method>.R` naming convention.

## How tools wire to the backend

```
Model picks tool             → rna_batch_integration (AgentTool subclass)
Tool's run() adapter         → backend.rna.integrate(adata, method="harmony", batch_key="sample")
RnaBackend.integrate()       → delegates to backend/rna/_batch_integration.py :: dispatch(...)
_batch_integration.dispatch  → routes to _run_harmony(...)
_run_harmony()               → calls harmonypy, writes adata.obsm["X_harmony"]
```

Each layer has one job. Adding a new method = (1) a new `_run_<method>` in the
matching module, (2) one branch in the dispatcher, (3) the new value in the
tool's enum.

## Per-agent registries (new and existing)

In `agent_tools.py`:

- `build_analyst_registry(store)` — paper / RAG only (unchanged behavior)
- `build_consultant_registry(store, backend)` — paper + refs + API + all compute
- `build_tool_only_consultant_registry(store, backend)` — curated read-only paper tools + refs + API + all compute
- `build_executor_registry(backend)` — refs + API + all compute (no paper tools)
- `build_tool_registry(store, backend)` — alias for the consultant registry

## Quick smoke test

```python
from backend import SingleCellBackend, BackendConfig
from agent_tools import build_executor_registry

backend = SingleCellBackend(BackendConfig())
registry = build_executor_registry(backend)
print(f"{len(registry.tool_specs())} tools registered")
print([s["name"] for s in registry.tool_specs()][:10])

print(backend.health_check())
```

## Migration notes for the existing agents

Existing call sites in `analyst_agent.py` / `consultant_agent.py`:

```python
# Before
single_cell_backend.preprocess_singlecell(...)
single_cell_backend.run_embedding(...)
single_cell_backend.cluster_and_evaluate(...)
single_cell_backend.celltype_annotation(...)
single_cell_backend.batch_integration(...)
```

After (one-line edits):

```python
backend = SingleCellBackend(BackendConfig())
backend.rna.qc(...) ; backend.rna.normalize(...)
backend.rna.embed(method="scvi", ...)
backend.rna.cluster(...)
backend.rna.annotate(method="gpt4", ...)
backend.rna.integrate(method="harmony", batch_key=..., ...)
```

Tool registration changes from `build_consultant_registry(paper_store, single_cell_backend=backend)` to `build_consultant_registry(paper_store, backend=backend)`.

## What's NOT in this scaffold

- A `download_file(url)` / `curl` tool. Intentionally omitted — the manifest
  pattern is the right way to handle reference fetching.
- Per-method R scripts beyond the example. Add them under `r_scripts/<modality>/`
  following the `<operation>_<method>.R` naming convention.
- Python tests. Add under `tests/` mirroring the `backend/` layout.
- Real SHA256 values. Run once with placeholders, paste observed hashes.
