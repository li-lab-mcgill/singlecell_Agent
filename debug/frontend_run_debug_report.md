# Debug Report — singlecell_Agent Frontend Run

**Date reviewed:** 2026-05-12  
**Run output directory:** `results_frontend/`  
**Sessions analysed:** `frontend_consultant_001` through `frontend_consultant_004`

---

## 1. Agent System Flow

```
User Query
    └─► SessionRouter.route()          [classifies intent: task vs direct_response]
            │
            ├─ "task" (operational)
            │       └─► ToolConsultantAgent.decide()   [LLM plans DAG + implementation_plan]
            │               │
            │               ├─► DagExecutor.execute()  [runs tool chain step-by-step]
            │               │       └─► backend/tools/**/*.py run()   [per-step tool adapter]
            │               │
            │               └─► (if DAG succeeds) Coder.run()         [custom implementation script]
            │
            └─ "direct_response"
                    └─► DeterministicResponder          [reads session state / artifacts]

All paths → ResultSummarizer.summarize() → SessionStateStore.update() → response to user
```

Key files:
- Entry point: `run_frontend.py` → `frontend/server.py`
- Dispatch logic: `agents/session_dispatcher.py`
- Routing: `agents/session_router.py`
- Planning: `agents/tool_consultant.py`
- Pipeline execution: `agents/dag_executor.py`
- Tool adapters: `backend/tools/executor.py`
- Per-tool implementations: `backend/tools/rna/`, `backend/tools/atac/`, `backend/tools/multi/`

---

## 2. Session-by-Session Trace

| Session | User intent | Execution path | Outcome |
|---|---|---|---|
| `001` | MultiVelo RNA+ATAC velocity; CD8 naive→memory→effector, monocyte→DC, B-cell maturation; TF motif enrichment | 11-step DAG → Coder | **Failed at DAG step 02** (`rna_qc_scrublet`) |
| `002` | NK trajectory + TF drivers via decoupler/CollecTRI GRN | 1-step DAG → Coder | **Failed at DAG step 00** (`rna_grn_decoupler`) |
| `003` | Generate UMAP plots from existing annotated h5ad | Coder only (no DAG) | Succeeded (2 attempts) |
| `004` | Cluster refinement suggestions to improve ARI | Coder only (no DAG) | Succeeded (2 attempts) |

Sessions 003 and 004 succeeded because they bypassed the DAG entirely and used the Coder directly against pre-existing h5ad artifacts. All failures occurred inside `DagExecutor`.

---

## 3. Error Locations

### Error A — Session 001: `scikit-image` missing

**File:** `backend/tools/rna/qc/scrublet.py`, line 13  
**Error message:** `"threshold is None and thus scrublet requires skimage, but skimage is not installed."`

```python
# scrublet.py line 13 — the failing call
sc.external.pp.scrublet(adata, expected_doublet_rate=expected_doublet_rate)
```

`sc.external.pp.scrublet` internally calls `skimage.filters.threshold_minimum()` to auto-compute the doublet score threshold. When `scikit-image` is absent this raises the error above.

The exception propagates to `agents/dag_executor.py:228` (the `except Exception as exc` block in `_execute_path`), which marks `path_000` as `"failed"` and returns `"All DAG paths failed"`.

Back in `agents/session_dispatcher.py:294`:

```python
if raw_results["dag_result"].get("status") == "failed" and _coder_depends_on_dag(decision):
    return ...   # early return — the Coder and MultiVelo script never run
```

The retention policy then **deletes all 318 MB** of intermediate h5ad files (only 2 `result.json` files are kept). The steps that had already succeeded — RNA QC (9,631 cells, 25,523 genes) and ATAC QC (9,631 cells, 21,022 peaks) — are discarded.

**Steps that never ran as a result:**
- `rna_normalize_log1p`
- `rna_feature_selection_scanpy_hvg`
- `atac_feature_selection_peaks`
- `multi_qc_intersect`
- `multi_embed_multivi`
- `rna_cluster_leiden`
- `rna_project_umap`
- `rna_annotate_celltypist`
- MultiVelo implementation script
- TF motif enrichment

---

### Error B — Session 002: `decoupler` missing

**File:** `backend/tools/rna/grn/decoupler.py` (or equivalent), inside the `rna_grn_decoupler` adapter  
**Error message:** `"No module named 'decoupler'"`

The same pattern: the tool does a top-level `import decoupler` with no try/except. The 1-step DAG fails immediately (duration: 0.53 s). No artifacts are produced.

**Compounding issue — stale artifact path in the plan:**  
Session 002's `tool_consultant` embedded this path as the DAG input:

```
tool_artifacts_frontend/dag/frontend_consultant_001_dag/path_000/06_rna_annotate_celltypist/output.h5ad
```

This file exists — but it came from an *earlier, separate run* of session 001 that used `tool_artifacts_frontend/` as its artifact directory. The `session_state.json` in `results_frontend/` reflects a *later* run of session 001 that only reached step 01 (`atac_qc_basic`) before failing, and whose `active_h5ad_path` points to a different location. The tool_consultant did not verify that the referenced artifact path matched the current session's state or that the prior run had actually completed step 06.

---

## 4. Root Cause Analysis

### Cause 1 — Missing Python packages (immediate trigger)

Both `scikit-image` (needed by Scrublet's auto-threshold) and `decoupler` (needed by the GRN tool) are absent from the Python environment. Neither package is installed:

```
$ python3 -c "import skimage"    # ModuleNotFoundError: No module named 'skimage'
$ python3 -c "import decoupler"  # ModuleNotFoundError: No module named 'decoupler'
$ python3 -c "import scrublet"   # ModuleNotFoundError: No module named 'scrublet'
```

These are optional scientific packages that the tools assume are present but never declare as hard requirements at import time.

---

### Cause 2 — Tool implementations have no dependency fallback

`backend/tools/rna/qc/scrublet.py` calls `sc.external.pp.scrublet()` unconditionally. If `skimage` is absent the call raises and the whole DAG path dies. The tool could instead:

- Pass an explicit `threshold=0.25` (reasonable default for PBMCs) when auto-threshold fails, or
- Catch the exception, log a warning, and skip doublet filtering gracefully.

The same applies to any tool that wraps an optional heavy dependency (`decoupler`, `multivelo`, etc.).

---

### Cause 3 — No dependency pre-flight check in the DAG executor

`agents/dag_executor.py` and `backend/tools/executor.py` build tool adapters eagerly at startup but defer all imports to call time. There is no mechanism to run a lightweight `check_imports()` before the pipeline starts. A missing package is only discovered after the relevant step is reached, wasting any work done by earlier steps.

---

### Cause 4 — Single DAG path with no fallback variants

The tool_consultant generated exactly one variant per layer, so only one path (`path_000`) was enumerated. `DagExecutor._enumerate_paths` supports multiple variants via the `variants` list, but the planner never exploits this. A second variant that skips scrublet (or uses a manual threshold) would have allowed the pipeline to continue on `path_001` even when `path_000` failed.

---

### Cause 5 — Hard stop when DAG fails and coder depends on it

`session_dispatcher.py:294` exits immediately if the DAG failed and `implementation_plan.depends_on_dag = True`. There is no attempt to run the coder with degraded or partial inputs, nor any structured guidance to the user about which specific package to install. The failure message reaches the user only after passing through `ResultSummarizer`, which adds latency and can obscure the root cause.

---

### Cause 6 — Tool-consultant embeds artifact paths without existence checks

When building the next turn's plan, the tool_consultant reads `active_h5ad_path` and prior artifact paths from session state and may embed them directly into `dag_plan.input_h5ad_path`. It does not call `Path(path).exists()`. If the referenced file is missing — because a prior run failed and the retention policy deleted intermediates, or because the session state refers to a different run's directory — the next session silently targets a non-existent file, wasting the new DAG's budget.

---

## 5. Suggested Fixes

### Fix 1 — Install the missing packages (fastest unblock)

```bash
pip install scikit-image decoupler-py
# and if scrublet itself is missing:
pip install scrublet
```

This resolves Errors A and B immediately without any code changes.

---

### Fix 2 — Add a fallback threshold in `scrublet.py`

**File:** `backend/tools/rna/qc/scrublet.py`

```python
def run(adata, *, expected_doublet_rate: float = 0.06):
    import scanpy as sc

    try:
        sc.external.pp.scrublet(adata, expected_doublet_rate=expected_doublet_rate)
    except Exception as exc:
        if "skimage" in str(exc) or "threshold is None" in str(exc):
            # scikit-image absent — fall back to a reasonable explicit threshold
            import warnings
            warnings.warn(
                "scikit-image not installed; using threshold=0.25 for Scrublet. "
                "Install scikit-image for automatic threshold selection.",
                RuntimeWarning,
                stacklevel=2,
            )
            sc.external.pp.scrublet(
                adata, expected_doublet_rate=expected_doublet_rate, threshold=0.25
            )
        else:
            raise

    if "predicted_doublet" in adata.obs:
        adata = adata[~adata.obs["predicted_doublet"].astype(bool), :].copy()
    adata.uns["qc_doublet"] = {
        "method": "scrublet",
        "expected_doublet_rate": expected_doublet_rate,
        "n_cells_after": int(adata.n_obs),
    }
    return adata
```

---

### Fix 3 — Add a dependency pre-flight check to the DAG executor

Add an optional `check_dependencies()` declaration to each tool, and call it in `DagExecutor.execute()` before any path starts:

**In `backend/tools/executor.py`:**
```python
def _make_adapter(tool_id: str, run_fn: Callable) -> Callable:
    ...
    # Attach a dependency checker if the module defines one
    check_fn = getattr(inspect.getmodule(run_fn), "check_dependencies", None)
    adapter._check_dependencies = check_fn
    ...
```

**In `agents/dag_executor.py`, at the top of `execute()`:**
```python
missing = []
for step in all_steps:
    fn = self.tool_executor.get(step["tool"])
    checker = getattr(fn, "_check_dependencies", None)
    if checker:
        result = checker()
        if result:   # returns list of missing package names
            missing.extend(result)
if missing:
    return {
        "status": "failed",
        "error": f"DEPENDENCY_MISSING: {missing}. Run: pip install {' '.join(missing)}",
        ...
    }
```

This surfaces the install command to the user before any computation runs.

---

### Fix 4 — Include a scrublet-free fallback variant in the planner

Update the `tool_consultant` prompt to always generate a second DAG variant that replaces `rna_qc_scrublet` with a no-op or manual-threshold step, so `path_001` can proceed if `path_000` fails at doublet detection.

Example structure the consultant should produce:

```json
{
  "tool": "rna_qc_scrublet",
  "variants": [
    { "method": "doublet_detection", "params": { "expected_doublet_rate": 0.06 } },
    { "method": "doublet_detection", "params": { "expected_doublet_rate": 0.06, "threshold": 0.25 } }
  ]
}
```

With two variants, `DagExecutor._enumerate_paths` will run two paths and the second will succeed even without `scikit-image`.

---

### Fix 5 — Validate artifact paths before embedding them into plans

In `ToolConsultantAgent.decide()` (or in `session_dispatcher._build_task_session_state()`), verify that any path in `active_h5ad_path` / `last_artifacts` actually exists on disk before passing it to the next turn:

```python
# In _build_execution_context or equivalent:
active_h5ad = persistent.get("active_h5ad_path")
if active_h5ad and not Path(active_h5ad).exists():
    # Prior run's artifact was deleted; fall back to the raw input
    active_h5ad = session_state.get("input_h5ad_path")
    context["active_h5ad_path"] = active_h5ad
    context["active_h5ad_path_warning"] = "Prior artifact missing; using raw input."
```

This prevents the tool_consultant from planning a pipeline that starts from a non-existent file.

---

### Fix 6 — Surface structured dependency errors immediately

In `session_dispatcher._build_composable_payload()`, parse the DAG error before passing it to `ResultSummarizer`:

```python
dag_error = (raw_results.get("dag_result") or {}).get("error", "")
if "No module named" in dag_error or "DEPENDENCY_MISSING" in dag_error:
    # Extract package name and prepend a clear install instruction
    import re
    pkg = re.search(r"No module named '([^']+)'", dag_error)
    if pkg:
        install_hint = f"\n\nACTION REQUIRED: `pip install {pkg.group(1)}` then re-run."
        raw_results["dag_result"]["error"] = dag_error + install_hint
```

This ensures the user sees the `pip install` command directly in the chat response without having to dig through JSON traces.

---

## 6. Summary Table

| # | Problem | Affected sessions | Severity | Fix |
|---|---|---|---|---|
| 1 | `scikit-image` not installed | 001 | Critical — blocks entire pipeline | `pip install scikit-image` |
| 2 | `decoupler` not installed | 002 | Critical — blocks GRN/TF step | `pip install decoupler-py` |
| 3 | Scrublet tool has no fallback threshold | 001 | High — single missing dep kills DAG | Fix 2: catch + explicit threshold |
| 4 | No dependency pre-flight check | 001, 002 | High — error discovered late, wastes prior steps | Fix 3: check before execution |
| 5 | Only 1 DAG path, no fallback variant | 001 | Medium — no recovery path when one step fails | Fix 4: multi-variant planning |
| 6 | Artifact paths not validated before re-use | 002 | Medium — tool_consultant plans against missing files | Fix 5: existence check in state builder |
| 7 | Hard stop on DAG failure, no install hint | 001, 002 | Low — UX issue, error is buried | Fix 6: structured error propagation |
