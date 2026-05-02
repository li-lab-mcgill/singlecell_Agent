# Execution DAG Architecture Plan

## 1. Problem Statement

A prior implementation had two execution paths for pipeline tasks: a linear sequential tool-call path and an Optuna HPO path over a fixed pipeline. Those paths have been removed.

Both are replaced with a single **execution DAG** system.

## 2. Design Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Path cap | ≤100 | Cartesian product of all variants must not exceed 100 paths. Validated at plan time; rejected if over. LLM keeps it lower by only branching at impactful stages. |
| Intermediate pruning | None | Every path runs to completion. Avoids complexity and risk of cutting the best path. |
| Fixed stages | QC, normalization | Standard defaults; LLM only adds variants if user explicitly asks. |
| Variant selection | LLM reasons per-objective | ToolConsultant reads tool docs and reasons about which stages/params meaningfully affect the target objective. |
| Result format | Best path + comparison table | All paths ranked by objective score with method choices and metrics. |
| Single vs multi path | Unified executor | Same code path regardless of 1 or 100 paths. No special-casing. |
| Decision model | Composable | ToolConsultant decides which components are needed (dag, coder, research). DAG and coder are peer execution subsystems that can run independently or sequentially. |
| Outputs model | consultant-declared + executor-recorded | ToolConsultant declares semantic outputs at plan time (`declared_outputs`); executor resolves refs, executes stages, and records concrete artifact facts (especially `output_h5ad_path`). |
| Ranking | Objective-based for multi-path | 1 path: no ranking needed, no objective required. N paths: `objective_name` required, tie-break by path index. |
| Per-path output | Directory per path | Each path writes to its own folder; tools write all outputs (h5ad, figures, CSVs) to per-stage subdirectories within the path folder. |
| Coder input | Best-ranked path only | Coder receives the best-ranked path's `path_dir` (primary handoff) plus any resolved symbolic keys the consultant already declared (e.g., `cluster_key`, `embedding_key`). |

## 3. Decision Model

The ToolConsultant no longer picks a single execution branch. It decides which components are needed for the request:

| Scenario | dag_plan | implementation_plan | research_brief | Example |
|----------|----------|-------------------|----------------|---------|
| DAG only | present | null | null | "annotate my data and find best ARI" |
| DAG + coder | present | present | null | "cluster my data then zoom into top 3 clusters" |
| Coder only | null | present | null | "write a volcano plot for the DE results" |
| Research | null | null | present | "what's the best method for trajectory inference on my data type?" |

The dispatcher runs components sequentially when more than one is selected:
1. DAG first (if present) — structured pipeline execution
2. Coder second (if present) — consumes a normalized input bundle

`research_brief` is mutually exclusive with `dag_plan` and `implementation_plan`. It runs standalone.

At least one of `dag_plan`, `implementation_plan`, or `research_brief` must be present.

### Execution Component Independence

`DagExecutor` and `CoderAgent` are independent execution subsystems.

- `CoderAgent` must work on its own without any DAG execution.
- When both DAG and coder are selected, DAG runs first and emits a normalized output bundle.
- `CoderAgent` consumes the same resolved-input contract whether its inputs come from:
  - DAG output
  - prior session artifacts
  - direct user-provided dataset/artifacts
- `CoderAgent` must not depend on DAG internals such as:
  - layer arrays
  - variant enumeration
  - `$L{index}.key` references
  - trial registry records

Compatibility is defined through resolved artifacts and resolved metadata, not shared internal plan structures.

### Decision Schema (ToolConsultant output)

**Example — DAG only:**

```json
{
  "task": "cell type annotation with best ARI",
  "reason": "Multiple embedding and clustering choices to explore",
  "objective_name": "cell_type_annotation_default",
  "dag_plan": { ... },
  "implementation_plan": null,
  "research_brief": null
}
```

**Example — DAG + coder:**

```json
{
  "task": "cluster and analyze top clusters",
  "reason": "Pipeline stages for clustering, then custom code for cluster deep-dive",
  "objective_name": null,
  "dag_plan": {
    "layers": [
      {"stage": "rna_quality_control", "variants": [{"method": "basic", "params": {"min_genes": 200}}]},
      {"stage": "rna_normalization", "variants": [{"method": "log1p", "params": {}}]},
      {"stage": "rna_feature_selection", "variants": [{"method": "seurat_v3", "params": {"n_top": 2000}}]},
      {"stage": "rna_dimensionality_reduction", "variants": [{"method": "pca", "params": {"n_pcs": 30}}]},
      {"stage": "rna_clustering", "variants": [{"method": "leiden", "params": {"resolution": 1.0}}]}
    ],
    "evaluation": {"metrics": ["silhouette"], "label_key": "cell_type"},
    "input_h5ad_path": "./data/pbmc_RNA_count.h5ad",
    "output_dir": ""
  },
  "implementation_plan": {
    "goal": "Zoom into top 3 largest clusters, compute marker genes, plot heatmap",
    "depends_on_dag": true,
    "dag_input_source": "best_path",
    "inputs": {
      "path_dir": "dag_output.path_dir",
      "h5ad_path": "dag_output.resolved_outputs.output_h5ad_path",
      "cluster_key": "dag_output.resolved_outputs.cluster_key",
      "embedding_key": "dag_output.resolved_outputs.embedding_key"
    },
    "outputs": {"figures": ["marker_heatmap.png"]},
    "required_steps": [
      "Load the h5ad from inputs.h5ad_path",
      "Read cluster assignments from obs[inputs.cluster_key]",
      "Identify top 3 clusters by cell count",
      "Subset to those clusters",
      "Run rank_genes_groups per cluster",
      "Plot top 10 markers per cluster as heatmap"
    ],
    "success_metric": "Heatmap saved",
    "constraints": []
  },
  "research_brief": null
}
```

## 4. DAG Plan Schema

The DAG plan has ordered **layers**, each containing one or more **variants**. The Cartesian product of all variant lists defines all paths. Must not exceed 100 paths.

Each layer has a unique **layer index** (0, 1, 2...) used for `$ref` resolution. Stage names need not be unique across layers (though uncommon), so `$ref` uses layer index: `$L3.embedding_key` references layer 3's output.

### Outputs model

Each variant can declare outputs in one primary way:

- **`declared_outputs`**: ToolConsultant specifies these at plan time. They are the semantic contract for `$ref` resolution and downstream consumers.

The executor does not need to infer semantic keys independently if the consultant already resolved them. Instead, it:
- resolves `$L{index}.key` references into concrete values before execution
- records executor-known facts such as the most downstream `output_h5ad_path` when a stage produces one
- carries those concrete values forward in `resolved_outputs` for convenience

### Naming conventions vs runtime outputs

Some declared outputs are naming **hints**, not direct tool-return fields:
- `embedding_key` on an embed variant: semantic key the consultant resolved from tool docs
- `suggested_cluster_key` on an embed variant: naming hint for downstream clustering

For v1, both are treated as consultant-declared semantics. The executor trusts them and does not independently rediscover them.

**Example — cell type annotation with multi-path exploration:**

```json
{
  "dag_plan": {
    "input_h5ad_path": "./data/pbmc_RNA_count.h5ad",
    "output_dir": "",
    "objective_name": "cell_type_annotation_default",
    "evaluation": {
      "metrics": ["ari", "nmi", "silhouette"],
      "label_key": "cell_type",
      "embedding_key": "$L3.embedding_key",
      "cluster_key": "$L4.cluster_key"
    },
    "layers": [
      {
        "stage": "rna_quality_control",
        "variants": [
          {"method": "basic", "params": {"min_genes": 200, "max_pct_mito": 20.0, "min_cells": 3}}
        ]
      },
      {
        "stage": "rna_normalization",
        "variants": [
          {"method": "log1p", "params": {"target_sum": 10000}}
        ]
      },
      {
        "stage": "rna_feature_selection",
        "variants": [
          {"method": "seurat_v3", "params": {"n_top": 2000}},
          {"method": "seurat_v3", "params": {"n_top": 3000}}
        ]
      },
      {
        "stage": "rna_dimensionality_reduction",
        "variants": [
          {"method": "pca", "params": {"n_pcs": 30}, "declared_outputs": {"embedding_key": "X_pca", "suggested_cluster_key": "pca_clusters"}},
          {"method": "scvi", "params": {"n_latent": 20}, "declared_outputs": {"embedding_key": "X_scvi", "suggested_cluster_key": "scvi_clusters"}},
          {"method": "scanvi", "params": {"n_latent": 20}, "declared_outputs": {"embedding_key": "X_scanvi", "suggested_cluster_key": "scanvi_clusters"}},
          {"method": "seurat_pca", "params": {}, "declared_outputs": {"embedding_key": "X_seurat_pca", "suggested_cluster_key": "seurat_pca_clusters"}}
        ]
      },
      {
        "stage": "rna_clustering",
        "variants": [
          {"method": "leiden", "params": {"resolution": 0.5, "embedding_key": "$L3.embedding_key"}, "declared_outputs": {"cluster_key": "$L3.suggested_cluster_key"}},
          {"method": "leiden", "params": {"resolution": 0.8, "embedding_key": "$L3.embedding_key"}, "declared_outputs": {"cluster_key": "$L3.suggested_cluster_key"}},
          {"method": "leiden", "params": {"resolution": 1.2, "embedding_key": "$L3.embedding_key"}, "declared_outputs": {"cluster_key": "$L3.suggested_cluster_key"}}
        ]
      },
      {
        "stage": "rna_celltype_annotation",
        "variants": [
          {"method": "celltypist", "params": {"obs_cluster": "$L4.cluster_key"}},
          {"method": "cellmarker", "params": {"obs_cluster": "$L4.cluster_key"}}
        ]
      }
    ]
  }
}
```

**Path count for this example:** 2 n_top x 4 embed x 3 resolution x 2 annotate = **48 paths** (under 100 cap)

**Actual compute with caching:**
| Stage | Unique executions | Why |
|-------|------------------|-----|
| rna_quality_control | 1 | Single variant |
| rna_normalization | 1 | Single variant |
| rna_feature_selection | 2 | 2 n_top values |
| rna_dimensionality_reduction | 8 | 2 features x 4 methods |
| rna_clustering | 24 | 8 embeddings x 3 resolutions |
| rna_celltype_annotation | 48 | 24 clusters x 2 methods |

Expensive steps (scVI, scanvi) run only 2 times each. Everything else is fast.

### Layer Rules

- Each layer has an implicit **layer index** (0, 1, 2...) based on its position in the `layers` array.
- `stage`: tool name from the tool registry (e.g., `rna_clustering`). Stage names need not be unique across layers.
- `variants`: list of variant objects, at least one. Each variant has:
  - `method`: string (required)
  - `params`: dict (optional). May contain `$L{index}.key` references resolved from a prior layer's outputs.
  - `declared_outputs`: dict (optional). LLM-specified naming conventions and expected output keys.
    - Semantic outputs (`embedding_key`, `cluster_key`): values the consultant resolved and downstream stages may reference.
    - Naming hints (`suggested_cluster_key`): conventions for downstream stages.
  - `resolved_outputs`: executor-carried concrete values for downstream convenience. In v1, these are usually the resolved `declared_outputs` plus executor-known artifact facts such as `output_h5ad_path`.
- `$ref` syntax uses layer index: `$L3.embedding_key` references layer 3's output.
- Layers execute in order. Each path picks one variant per layer.
- `objective_name`: required when any layer has >1 variant (multi-path needs ranking). Not required for single-path.
- `evaluation`: specifies metrics and dataset keys; may also use `$L{index}.key` references.
- Path count (Cartesian product of all variant lists) must not exceed **100**.

## 5. Stage Dispatch via Tool Registry

The DAG executor does NOT have its own dispatch table. It reuses the existing `AgentToolRegistry`, which already maps tool names to `run(**kwargs)` functions.

```python
registry = build_tool_executor_registry(backend)
executor = registry.executor()  # {tool_name: tool.run}

# To run a stage:
fn = executor[stage_name]  # e.g. executor["rna_quality_control"]
result = fn(input_path=str(current_input), output_dir=str(stage_dir), **stage_params)
```

Every tool receives two standard arguments:
- `input_path`: the primary input file (typically h5ad, but could be any file type). Stays the same across stages that don't transform data.
- `output_dir`: a per-stage directory where the tool writes all its outputs — h5ad, figures, CSVs, metrics, etc.

Tools do not need to return rich semantic metadata for the DAG architecture to work. The consultant already resolved semantic keys in the plan. The executor only needs to know where stage artifacts were written. If a tool produces a new canonical h5ad snapshot, the executor records its `output_h5ad_path` and uses that as the next stage's `input_path`. If no new h5ad is produced (for example, a figure-only stage), the previous `input_path` carries forward unchanged.

The LLM uses the full tool names directly as stage names (e.g., `"rna_quality_control"`, `"rna_clustering"`, `"rna_2d_projection"`). These match the tool registry keys exactly — no mapping needed.

## 6. Inter-Stage References ($ref with layer index)

Some stages depend on choices made in earlier stages (e.g., cluster needs the embedding_key produced by embed). Instead of hardcoding this logic in the executor, the **LLM specifies it in the plan**.

### How it works

1. Each variant can declare `declared_outputs` — key-value pairs the LLM expects the method to produce.
2. Downstream variants reference them using `$L{index}.key` syntax in `params` or `declared_outputs`.
3. The executor resolves `$ref` values before executing each stage using the concrete values already carried forward from prior layers.

### Reference syntax

`$L{layer_index}.{output_key}` — references a specific layer by its index (0-based).

Why layer index instead of stage name:
- Stage names may not be unique (e.g., two clustering layers with different methods)
- Layer index is unambiguous and positional — easy to validate
- The LLM can see the layer order in the plan and reference by position

### Example — declared_outputs and $ref in a cell type annotation DAG

```json
// Layer 3: rna_dimensionality_reduction
{
  "stage": "rna_dimensionality_reduction",
  "variants": [
    {"method": "pca", "params": {"n_pcs": 30}, "declared_outputs": {"embedding_key": "X_pca", "suggested_cluster_key": "pca_clusters"}},
    {"method": "scvi", "params": {"n_latent": 20}, "declared_outputs": {"embedding_key": "X_scvi", "suggested_cluster_key": "scvi_clusters"}}
  ]
},
// Layer 4: rna_clustering — references layer 3's outputs
{
  "stage": "rna_clustering",
  "variants": [
    {"method": "leiden", "params": {"resolution": 0.8, "embedding_key": "$L3.embedding_key"}, "declared_outputs": {"cluster_key": "$L3.suggested_cluster_key"}}
  ]
},
// Layer 5: rna_celltype_annotation — references layer 4's outputs
{
  "stage": "rna_celltype_annotation",
  "variants": [
    {"method": "celltypist", "params": {"obs_cluster": "$L4.cluster_key"}}
  ]
}
```

The evaluation section also uses `$ref`:

```json
"evaluation": {
  "metrics": ["ari", "nmi", "silhouette"],
  "label_key": "cell_type",
  "embedding_key": "$L3.embedding_key",
  "cluster_key": "$L4.cluster_key"
}
```

### Executor Resolution

The executor resolves `$ref` values before executing each stage. In v1, `resolved_outputs` are mostly the concrete form of prior `declared_outputs`, plus executor-known artifact facts:

```python
def _resolve_refs(params: dict, path_config: list, current_idx: int) -> dict:
    """Replace $L{index}.key references with actual values from prior layers' outputs."""
    resolved = {}
    for key, value in params.items():
        if isinstance(value, str) and value.startswith("$L"):
            # Parse "$L3.output_key"
            ref = value[2:]  # strip "$L"
            layer_idx_str, output_key = ref.split(".", 1)
            layer_idx = int(layer_idx_str)

            if layer_idx >= current_idx:
                raise ValueError(f"Reference {value}: layer {layer_idx} is not before current layer {current_idx}")

            source = path_config[layer_idx]
            outputs = source.get("resolved_outputs") or source.get("declared_outputs", {})
            if output_key not in outputs:
                raise ValueError(f"Reference {value}: output '{output_key}' not found in layer {layer_idx}")

            # Recursively resolve if the value is itself a $ref
            resolved_value = outputs[output_key]
            if isinstance(resolved_value, str) and resolved_value.startswith("$L"):
                resolved_value = _resolve_refs({key: resolved_value}, path_config, layer_idx)[key]
            resolved[key] = resolved_value
        else:
            resolved[key] = value
    return resolved
```

Note: `declared_outputs` can themselves contain `$ref` values (e.g., `"cluster_key": "$L3.suggested_cluster_key"`). The resolver handles this recursively and stores the concrete result on the step.

Same resolution applies to the `evaluation` dict before calling `Evaluator.evaluate()`.

### Runtime output population

Before each stage executes, the executor resolves the step's `declared_outputs` and stores the concrete values on `resolved_outputs`. After execution, it may add executor-known artifact facts such as `output_h5ad_path`:

```python
# Before tool execution
step["resolved_outputs"] = dict(step.get("declared_outputs", {}))

# After tool execution
result = fn(input_path=..., output_dir=..., **stage_params)
if isinstance(result, dict) and result.get("output_h5ad_path"):
    step["resolved_outputs"]["output_h5ad_path"] = result["output_h5ad_path"]
```

This keeps the executor simple:
- semantic keys come from the consultant-authored plan
- the executor only adds mechanical facts learned during execution
- `output_h5ad_path`, when present, is used to chain the data forward to the next stage

### Benefits

- **No hardcoded maps**: no `EMBED_KEY_MAP`, no `_resolve_dynamic_keys()`, no stage-specific logic in the executor
- **LLM specifies all domain knowledge**: it knows from tool docs that PCA writes to X_pca and clustering names its column pca_clusters
- **Consultant owns semantics**: the plan is the source of truth for symbolic keys
- **Generic executor**: works for any new stage or method without code changes
- **Transparent**: the plan is self-contained — you can read it and see exactly what keys each stage produces and consumes
- **Unambiguous references**: `$L3` is positional and unique, no name collisions

## 7. DAG Executor

### Class: DagExecutor

```python
class DagExecutor:
    def __init__(self, *, backend, result_dir):
        self.backend = backend
        self.result_dir = Path(result_dir)
        registry = build_tool_executor_registry(backend)
        self.tool_executor = registry.executor()  # {tool_name: tool.run}

    def execute(self, *, dag_plan, session_tag="dag"):
        plan = validate_dag_plan(dag_plan)
        run_dir = self.result_dir / session_tag
        run_dir.mkdir(parents=True, exist_ok=True)
        if not plan.get("output_dir"):
            plan["output_dir"] = str(run_dir)

        # Enumerate all paths
        paths = self._enumerate_paths(plan["layers"])

        # Create task in registry
        task_id = self.backend.runs.create_task(
            description=f"DAG exploration: {session_tag}",
            objective={"name": plan.get("objective_name")},
            dataset_path=plan["input_h5ad_path"],
        )

        # Execute all paths
        results = []
        for path_idx, path_config in enumerate(paths):
            result = self._execute_path(
                plan=plan,
                path_config=path_config,
                path_idx=path_idx,
                task_id=task_id,
                run_dir=run_dir,
            )
            results.append(result)

        return self._format_result(results, plan, task_id, run_dir)
```

### Path Enumeration

```python
def _enumerate_paths(self, layers):
    """Cartesian product of all variant lists across layers."""
    from itertools import product
    variant_lists = [layer["variants"] for layer in layers]
    stage_names = [layer["stage"] for layer in layers]
    all_combos = list(product(*variant_lists))
    return [
        [{"stage": stage, **variant} for stage, variant in zip(stage_names, combo)]
        for combo in all_combos
    ]
```

### Path Execution

```python
def _execute_path(self, *, plan, path_config, path_idx, task_id, run_dir):
    """Run one path through the DAG with per-path output folder and step caching."""
    import time, shutil
    from backend.cache import sha256_file

    input_path = Path(plan["input_h5ad_path"])
    path_dir = run_dir / f"path_{path_idx:03d}"
    path_dir.mkdir(parents=True, exist_ok=True)

    # Register trial
    trial_id = self.backend.runs.start_trial(
        task_id=task_id,
        config={"path_index": path_idx, "stages": path_config},
    )

    t_start = time.time()
    cache_hits = []

    try:
        current_input = input_path
        input_sha = sha256_file(current_input)

        for i, step in enumerate(path_config):
            stage = step["stage"]
            stage_params = {"method": step["method"], **step.get("params", {})}

            # Resolve $L{index}.key references from prior layers' outputs
            # Also resolve declared_outputs that contain $refs
            stage_params = _resolve_refs(stage_params, path_config, i)
            step["params"] = {k: v for k, v in stage_params.items() if k != "method"}
            if step.get("declared_outputs"):
                step["declared_outputs"] = _resolve_refs(step["declared_outputs"], path_config, i)
                step["resolved_outputs"] = dict(step["declared_outputs"])

            # Per-stage output directory within the path folder
            stage_dir = path_dir / f"{i:02d}_{stage}"
            stage_dir.mkdir(parents=True, exist_ok=True)

            # Check cache
            cache_key = self.backend.cache.key(input_sha, stage, stage_params)

            if self.backend.cache.has(cache_key):
                self.backend.cache.restore_to(cache_key, stage_dir)
                cache_hits.append(stage)
                # Recover executor-recorded outputs from cache metadata
                cached_meta = self.backend.cache.get_meta(cache_key)
                if cached_meta and cached_meta.get("resolved_outputs"):
                    step["resolved_outputs"] = {**step.get("resolved_outputs", {}), **cached_meta["resolved_outputs"]}
            else:
                # Dispatch via tool registry — stage name IS the tool name
                fn = self.tool_executor[stage]
                result = fn(
                    input_path=str(current_input),
                    output_dir=str(stage_dir),
                    **stage_params,
                )
                self.backend.cache.put(
                    cache_key, stage_dir,
                    meta={"stage": stage, "params": stage_params,
                          "resolved_outputs": (
                              {"output_h5ad_path": result["output_h5ad_path"]}
                              if isinstance(result, dict) and result.get("output_h5ad_path")
                              else None
                          )},
                )

                # Record executor-known runtime artifact facts
                if isinstance(result, dict) and result.get("output_h5ad_path"):
                    step.setdefault("resolved_outputs", {})
                    step["resolved_outputs"]["output_h5ad_path"] = result["output_h5ad_path"]

            # Advance input: if the tool produced a new h5ad snapshot, chain it forward.
            outputs = step.get("resolved_outputs", {}) or step.get("declared_outputs", {})
            if "output_h5ad_path" in outputs:
                current_input = Path(outputs["output_h5ad_path"])
                input_sha = sha256_file(current_input)
            # else: current_input and input_sha stay the same (stage didn't transform the data)

        # Evaluate — resolve $refs in evaluation dict using this path's outputs
        evaluation = plan.get("evaluation", {})
        resolved_eval = _resolve_refs(evaluation, path_config, len(path_config))

        # Find the primary h5ad for evaluation: last stage that produced one
        eval_h5ad = _find_primary_h5ad(path_config, default=input_path)

        eval_kwargs = {
            "metrics": resolved_eval.get("metrics", []),
            "embedding_key": resolved_eval.get("embedding_key"),
            "cluster_key": resolved_eval.get("cluster_key"),
            "label_key": resolved_eval.get("label_key"),
            "batch_key": resolved_eval.get("batch_key"),
            "objective_name": plan.get("objective_name"),
        }
        eval_result = self.backend.eval.evaluate(eval_h5ad, **eval_kwargs)

        duration_s = time.time() - t_start

        # Collect all artifacts from all stage dirs
        artifacts = _collect_path_outputs(path_dir)

        self.backend.runs.complete_trial(
            trial_id,
            metrics=eval_result.metrics,
            duration_s=duration_s,
            artifact_paths=artifacts,
        )

        return {
            "path_index": path_idx,
            "status": "completed",
            "config": path_config,
            "metrics": eval_result.metrics,
            "warnings": eval_result.warnings,
            "duration_s": duration_s,
            "path_dir": str(path_dir),
            "artifacts": artifacts,
            "cache_hits": cache_hits,
            "trial_id": trial_id,
        }
    except Exception as exc:
        duration_s = time.time() - t_start
        self.backend.runs.fail_trial(trial_id, str(exc), duration_s)
        return {
            "path_index": path_idx,
            "status": "failed",
            "config": path_config,
            "error": str(exc),
            "duration_s": duration_s,
            "cache_hits": cache_hits,
        }


def _find_primary_h5ad(path_config, default):
    """Walk path config backwards to find the last stage that produced an h5ad."""
    for step in reversed(path_config):
        outputs = step.get("resolved_outputs", {}) or step.get("declared_outputs", {})
        if "output_h5ad_path" in outputs:
            return Path(outputs["output_h5ad_path"])
    return default


def _collect_path_outputs(path_dir):
    """Collect all output files from a path's stage directories into a flat dict."""
    artifacts = {}
    for stage_dir in sorted(path_dir.iterdir()):
        if not stage_dir.is_dir():
            continue
        for f in stage_dir.rglob("*"):
            if f.is_file():
                # Key by relative path from path_dir, e.g. "02_rna_clustering/clusters.csv"
                rel = str(f.relative_to(path_dir))
                artifacts[rel] = str(f)
    return artifacts
```

### Result Formatting

```python
def _format_result(self, results, plan, task_id, run_dir):
    from backend.objectives import score_metrics

    completed = [r for r in results if r["status"] == "completed"]
    failed = [r for r in results if r["status"] == "failed"]

    if not completed:
        return {
            "status": "failed",
            "error": "All paths failed",
            "failed_paths": failed,
            "artifact_dir": str(run_dir),
        }

    objective_name = plan.get("objective_name")

    if objective_name:
        # Multi-path: score, rank, tie-break by path_index (lower = first)
        for r in completed:
            r["objective_score"] = score_metrics(objective_name, r["metrics"])
        completed.sort(key=lambda r: (-r.get("objective_score", -1), r["path_index"]))
    else:
        # Single-path: no ranking needed, metrics are informational
        for r in completed:
            r["objective_score"] = None

    best = completed[0]

    # Extract resolved keys from the best path's stages for the output bundle.
    # Walk the path config and collect the executor-carried concrete values.
    resolved_keys = {}
    for step in best.get("config", []):
        outputs = step.get("resolved_outputs", {}) or step.get("declared_outputs", {})
        resolved_keys.update(outputs)

    # Comparison table only meaningful for multi-path
    comparison_table = self._build_comparison_table(results, plan) if len(results) > 1 else []

    return {
        "status": "completed",
        "best_path": {
            "path_index": best["path_index"],
            "config": best["config"],
            "metrics": best["metrics"],
            "objective_score": best.get("objective_score"),
            "path_dir": best["path_dir"],
            "artifacts": best["artifacts"],
            "resolved_outputs": resolved_keys,
        },
        "comparison_table": comparison_table,
        "paths_completed": len(completed),
        "paths_failed": len(failed),
        "objective_name": objective_name,
        "artifact_dir": str(run_dir),
    }


def _build_comparison_table(self, results, plan):
    """Flat table: one row per path, columns = stage choices + metrics."""
    table = []
    for r in results:
        row = {"path_index": r["path_index"], "status": r["status"]}
        # Extract method/param choices per stage
        for step in r.get("config", []):
            stage = step["stage"]
            row[f"{stage}_method"] = step["method"]
            # Include resolved key params (e.g., resolution, embedding_key, n_top)
            for param_name, param_value in step.get("params", {}).items():
                row[f"{stage}_{param_name}"] = param_value
        # Metrics
        if r.get("metrics"):
            for metric_name, metric_value in r["metrics"].items():
                row[metric_name] = metric_value
        if r.get("objective_score") is not None:
            row["objective_score"] = r["objective_score"]
        if r.get("error"):
            row["error"] = r["error"]
        table.append(row)

    # Sort by objective_score descending
    table.sort(key=lambda row: row.get("objective_score") or -1, reverse=True)
    return table
```

## 8. Session Dispatcher Changes

### Dispatch logic

See Section 12 ("Where it runs") for the full `execute_task()` flow with DAG failure handling, `depends_on_dag`, and input resolution.

### SessionDispatcher.__init__ changes

```python
def __init__(self, *, router, tool_consultant, dag_executor, coder,
             research_executor, result_summarizer, ...):
```

## 9. Decision Schema Validation

### Removed

- `VALID_DECISIONS` (no longer a single-branch enum)
- `validate_optimization_plan()`
- `_validate_tool_plan()`
- `_validate_pipeline_search_space()`

### Added

```python
VALID_STAGES = None  # Not needed — validation checks that stage names exist in the tool registry


def validate_tool_consultant_decision(payload):
    """Validate the ToolConsultant output. At least one plan must be present."""
    dag_plan = payload.get("dag_plan")
    impl_plan = payload.get("implementation_plan")
    research_brief = payload.get("research_brief")

    if not any([dag_plan, impl_plan, research_brief]):
        raise DecisionValidationError(
            "At least one of dag_plan, implementation_plan, or research_brief must be present"
        )

    # research_brief is mutually exclusive with dag_plan and implementation_plan
    if research_brief and (dag_plan or impl_plan):
        raise DecisionValidationError(
            "research_brief is mutually exclusive with dag_plan and implementation_plan"
        )

    out = {
        "task": str(payload.get("task") or "unknown").strip(),
        "reason": str(payload.get("reason") or "").strip(),
        "objective_name": _optional_str(payload, "objective_name"),
        "dag_plan": None,
        "implementation_plan": None,
        "research_brief": None,
    }

    if dag_plan:
        out["dag_plan"] = validate_dag_plan(dag_plan)
    if impl_plan:
        out["implementation_plan"] = validate_implementation_plan(impl_plan)
    if research_brief:
        out["research_brief"] = _dict_or_none(research_brief)

    return out


def validate_dag_plan(payload):
    _required_str(payload, "input_h5ad_path")
    layers = payload.get("layers")
    if not isinstance(layers, list) or not layers:
        raise DecisionValidationError("dag_plan requires non-empty layers list")

    total_paths = 1
    for idx, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise DecisionValidationError(f"layers[{idx}] must be an object")
        stage = _required_str(layer, "stage")
        # Stage name must match a registered tool name
        variants = layer.get("variants")
        if not isinstance(variants, list) or not variants:
            raise DecisionValidationError(
                f"layers[{idx}].variants must be a non-empty list"
            )
        for vi, v in enumerate(variants):
            if not isinstance(v, dict):
                raise DecisionValidationError(
                    f"layers[{idx}].variants[{vi}] must be an object"
                )
            _required_str(v, "method")
        total_paths *= len(variants)

    # Path cap
    if total_paths > 100:
        raise DecisionValidationError(
            f"DAG plan produces {total_paths} paths, exceeding the 100-path cap. "
            "Reduce variants to keep total paths ≤ 100."
        )

    # Multi-path requires an objective for ranking
    if total_paths > 1:
        obj_name = _required_str(payload, "objective_name")
        spec = get_objective(obj_name)
        if spec is None or not spec.available:
            raise DecisionValidationError(
                f"Multi-path DAG requires an available objective, got {obj_name!r}"
            )

    evaluation = _dict_or_none(payload.get("evaluation")) or {}

    return {
        "input_h5ad_path": payload["input_h5ad_path"],
        "output_dir": str(payload.get("output_dir") or ""),
        "objective_name": payload.get("objective_name"),
        "evaluation": evaluation,
        "layers": layers,
    }


def validate_implementation_plan(payload):
    _required_str(payload, "goal")
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        raise DecisionValidationError("implementation_plan requires non-empty inputs dict")

    depends_on_dag = bool(payload.get("depends_on_dag", False))

    # If depends_on_dag, at least one input must reference the DAG output bundle.
    if depends_on_dag:
        has_dag_ref = any(
            isinstance(v, str) and (
                v == "dag_output.path_dir"
                or v == "dag_output.artifacts"
                or v.startswith("dag_output.artifacts.")
                or v.startswith("dag_output.resolved_outputs.")
            )
            for v in inputs.values()
        )
        if not has_dag_ref:
            raise DecisionValidationError(
                "implementation_plan with depends_on_dag=true must have at least one input "
                "referencing dag_output.path_dir, dag_output.artifacts, "
                "dag_output.artifacts.<name>, or "
                "dag_output.resolved_outputs.<name>"
            )

    # No placeholder strings allowed
    for key, value in inputs.items():
        if isinstance(value, str) and value.startswith("<") and value.endswith(">"):
            raise DecisionValidationError(
                f"implementation_plan.inputs['{key}'] contains placeholder '{value}' — "
                "use concrete values or DAG-derived references under dag_output.path_dir, "
                "dag_output.artifacts, dag_output.artifacts.<name>, or "
                "dag_output.resolved_outputs.<name>"
            )

    return {
        "script_name": str(payload.get("script_name") or "solution.py"),
        "goal": payload["goal"],
        "depends_on_dag": depends_on_dag,
        "dag_input_source": str(payload.get("dag_input_source") or "best_path"),
        "inputs": inputs,
        "outputs": _dict_or_none(payload.get("outputs")) or {},
        "required_steps": list(payload.get("required_steps") or []),
        "success_metric": str(payload.get("success_metric") or ""),
        "constraints": list(payload.get("constraints") or []),
    }
```

## 10. ToolConsultant Prompt Changes

### System Prompt

```
Role:
You are ToolConsultant, the first-stage planning agent for a single-cell analysis assistant.

You do not execute tools and you do not write code.
Your job is to decompose the user request and produce an execution plan using one or more of:
- dag_plan: express the workflow as ordered stages with method/parameter variants.
- implementation_plan: custom code needed beyond what tools provide.
- research_brief: full research pipeline for literature-grounded method design.

You may combine dag_plan + implementation_plan when the request mixes tool computation
with custom analysis (e.g., "cluster then zoom into specific clusters").

Use the tool documentation, available objectives, and session state.
Do not invent unavailable tools or objectives.
```

### Decision Prompt Additions

```
DAG plan rules:
- Each layer has a "stage" (matching a tool from the documentation) and a "variants" list.
- Layers are indexed by position (0, 1, 2...). Use layer index for references.
- Each variant has "method", "params", and optionally "declared_outputs".
- "declared_outputs" declares the semantic keys downstream stages will use:
  - Semantic keys (e.g., "embedding_key": "X_pca")
  - Naming hints (e.g., "suggested_cluster_key": "pca_clusters")
    Use "suggested_" prefix for hints that are not consumed directly by the current stage.
- Downstream params reference prior layers using "$L{index}.key" syntax.
  Example: {"embedding_key": "$L3.embedding_key"} resolves to layer 3's embedding_key output.
- "declared_outputs" can also contain "$L{index}.key" references.
  Example: {"cluster_key": "$L3.suggested_cluster_key"} — clustering adopts the embed variant's naming hint.
- The evaluation section can also use "$L{index}.key" references.
- Layers execute in order. The Cartesian product of all variants defines all paths to explore.
- **Path cap: total paths must not exceed 100.** By default, use conservative basic QC
  (`min_genes=200`, `max_pct_mito=20.0`, `min_cells=3`) and fix normalization to standard
  defaults. Then reason about which stages and parameters meaningfully affect the target
  objective — add multiple variants only at those stages. The objective may be user-defined
  or the default for the task. Do not add variants at stages that won't impact the objective
  unless the user explicitly asks.
- objective_name is required when any layer has more than one variant (multi-path needs ranking).
  Not required for single-path plans.
- Only use methods documented as available in the tool docs. Methods marked "Not yet
  implemented" must be excluded.

Resolving keys:
- Keys that refer to dataset columns (label_key, batch_key, group_key, sample_key) must be
  resolved from the session state — specifically from the dataset summary, history, or user
  message. Never use placeholders like "<ground_truth_label_key>".

Implementation plan rules:
- "goal" must be specific and actionable, not vague.
- "depends_on_dag" is true when the coder needs DAG output as input, false otherwise.
- "dag_input_source" defaults to "best_path". This is the only DAG-to-coder source allowed in v1.
- "inputs" must list every key/column/path the script needs — no placeholders.
  - Use these DAG output namespaces when an input comes from the DAG output bundle:
    - `dag_output.path_dir` — selected path directory
    - `dag_output.artifacts` — full artifact map from the selected path
    - `dag_output.artifacts.<name>` — named artifact path from the selected path
    - `dag_output.resolved_outputs.<name>` — resolved stage output such as `cluster_key`
  - Example: `"h5ad_path": "dag_output.resolved_outputs.output_h5ad_path"`
  - Example: `"cluster_key": "dag_output.resolved_outputs.cluster_key"`
  - For coder-only plans, use actual paths from session state.
- "required_steps" should reference the specific keys from "inputs" so the generated script
  uses the correct column names.
- If depends_on_dag is true and the DAG fails, the coder will NOT run.

When to include implementation_plan alongside dag_plan:
- The request mixes pipeline execution with custom analysis/visualization that tools cannot do.
- Example: "cluster my data and plot the top markers for each cluster as a heatmap"
  -> dag_plan handles preprocessing + clustering, implementation_plan handles the custom plot.
```

### Output Schema Prompt

```
Return exactly one <TOOL_DECISION> JSON payload and no extra text.

Schema:
<TOOL_DECISION>
{
  "task": "<short task label>",
  "reason": "<brief reason for the plan>",
  "objective_name": "<from objective registry, or null for single-path>",
  "dag_plan": {
    "input_h5ad_path": "<path>",
    "output_dir": "<directory>",
    "objective_name": "<same as above>",
    "evaluation": {
      "metrics": ["ari", "nmi", "silhouette"],
      "label_key": "<ground truth column from dataset, e.g. cell_type>",
      "batch_key": "<batch column if relevant>"
    },
    "layers": [
      {
        "stage": "<stage name from tool docs>",
        "variants": [
          {"method": "<method name>", "params": {}, "declared_outputs": {"<key>": "<value>"}}
        ]
      }
    ]
  },
  "implementation_plan": {
    "script_name": "solution.py",
    "goal": "<specific goal>",
    "depends_on_dag": true | false,
    "dag_input_source": "best_path",
    "inputs": {
      "path_dir": "dag_output.path_dir | <explicit path>",
      "h5ad_path": "dag_output.resolved_outputs.output_h5ad_path | <explicit path>",
      "cluster_key": "dag_output.resolved_outputs.cluster_key | <explicit value>",
      "<key_name>": "<value or key name the script needs>"
    },
    "outputs": {},
    "required_steps": ["<steps referencing specific keys/columns>"],
    "success_metric": "<objective or metric>",
    "constraints": []
  },
  "research_brief": null
}
</TOOL_DECISION>

Set unused plan fields to null.
At least one of dag_plan, implementation_plan, or research_brief must be present.
implementation_plan.inputs must contain concrete values — no angle-bracket placeholders.
If depends_on_dag is true, at least one input must use `dag_output.path_dir`, `dag_output.artifacts`, `dag_output.artifacts.<name>`, or `dag_output.resolved_outputs.<name>`, and all keys the script needs must be listed.
```

## 11. Caching Detail

The DAG executor reuses the existing `StepCache` from `backend/cache/step_cache.py` unchanged.

### Cache unit

The cache stores a **directory** per stage execution (the stage's `output_dir`), not a single file. `put(key, stage_dir, meta)` archives the entire directory. `restore_to(key, stage_dir)` restores it. `meta` includes executor-recorded `resolved_outputs` so cached stages can provide the same concrete values to downstream `$ref` resolution without re-executing.

### How cache keys chain

```
input_sha = sha256(input.h5ad)
cache_key_0 = sha256("input_sha[:16] | qc | {method: basic, min_genes: 200}")
    -> execute QC, writes to stage_dir, cache stores stage_dir
    -> executor records {"output_h5ad_path": ".../00_rna_quality_control/output.h5ad"}
    -> input_sha updates to sha256 of that output.h5ad
cache_key_1 = sha256("input_sha_1[:16] | normalize | {method: log1p, target_sum: 10000}")
    -> execute normalize, writes to stage_dir, cache stores stage_dir
...
```

If a stage does not produce an h5ad (e.g., projection tool writes only a figure), `input_sha` does not change — the next stage's cache key is based on the same input. This is correct: the data hasn't changed, so subsequent stages that operate on the same data share cache entries.

### How sharing works across paths

Two paths that share the same prefix (same QC + same normalize + same n_top) produce identical cache keys for those stages. The second path hits the cache and skips re-execution.

Example with 48 paths:
- All 48 share the same QC and normalize -> 1 execution each, 47 cache hits each
- Paths split at features (n_top=2000 vs 3000) -> 2 executions, rest are cache hits
- Then split at embed -> 8 executions (2 features x 4 methods)
- And so on

### Cache is content-addressed

The cache key depends on the actual content of the input file (SHA256), not on path index or execution order. This means:
- If two different DAG runs produce the same intermediate h5ad, they share cache entries
- Re-running the same DAG plan after a crash resumes from cached stages

## 12. Result Summarizer

### Problem

The raw results from executors (DAG, coder, research) are structured data — metrics dicts, comparison tables, script stdout, figure paths. The user needs a natural language response that **answers their question** using those results.

Hardcoded formatting can't do this well because:
- The same raw results should be presented differently depending on the user's question
- Combined results (DAG + coder) need unified presentation
- Figures need to be referenced in context

### Solution: ResultSummarizer LLM agent

A lightweight LLM call (no tools) that takes raw results + user query and produces the final response.

```python
class ResultSummarizer:
    """LLM agent that formats raw execution results into a user-facing response."""

    def __init__(self, *, engine_name: str, client=None):
        self.engine_name = engine_name
        self.client = client

    def summarize(self, *, user_query: str, decision: dict, raw_results: dict) -> dict:
        """
        Args:
            user_query: the user's original message
            decision: the ToolConsultant's plan (dag_plan, implementation_plan, etc.)
            raw_results: dict with keys like "dag_result", "coder_result", "research_result"

        Returns:
            {"message": str, "figures": list[str]}
        """
        prompt = RESULT_SUMMARIZER_PROMPT.format(
            user_query=user_query,
            decision_summary=json.dumps(_slim_decision(decision), indent=2),
            raw_results=json.dumps(_slim_results(raw_results), indent=2),
        )

        runner = ToolCallingAgentRunner(
            model=self.engine_name,
            system_prompt=RESULT_SUMMARIZER_SYSTEM_PROMPT,
            tool_specs=[],
            tool_executor={},
            client=self.client,
            max_iterations=2,
            max_tool_calls=0,
        )

        def _handle(text):
            # Extract figures from raw results
            figures = _collect_figures(raw_results)
            return {"done": True, "result": {"message": text.strip(), "figures": figures}}

        return runner.run(initial_user_input=prompt, response_handler=_handle)
```

### Prompt

```
RESULT_SUMMARIZER_SYSTEM_PROMPT = """
You are a result summarizer for a single-cell analysis assistant.
Given the user's original query and raw execution results, produce a clear response
that directly answers the user's question.

Rules:
- Lead with the answer to the user's question
- Include key metrics and the best configuration if a DAG exploration was run
- Present comparison data as a concise table if multiple paths were explored
- Reference any figures by filename so the frontend can render them
- If the coder produced output, summarize what it found
- Be concise — the user can inspect the full results and h5ad files themselves
"""

RESULT_SUMMARIZER_PROMPT = """
User query: {user_query}

Plan executed: {decision_summary}

Raw results: {raw_results}

Write a response that answers the user's question using these results.
"""
```

### Where it runs

In `session_dispatcher.py`, after all components execute:

```python
def execute_task(self, *, user_message, session_state, session_tag):
    decision = self.tool_consultant.decide(...)

    raw_results = {}

    # --- DAG ---
    if decision.get("dag_plan"):
        dag_result = self.dag_executor.execute(
            dag_plan=decision["dag_plan"],
            session_tag=f"{session_tag}_dag",
        )
        raw_results["dag_result"] = dag_result

        # If DAG failed and coder depends on it, stop here
        if dag_result["status"] == "failed" and _coder_depends_on_dag(decision):
            summary = self.result_summarizer.summarize(
                user_query=user_message, decision=decision, raw_results=raw_results,
            )
            return {
                "decision": decision, "raw_results": raw_results,
                "message": summary["message"], "figures": summary["figures"],
                "status": "failed",
            }

    # --- Coder ---
    if decision.get("implementation_plan"):
        impl_plan = decision["implementation_plan"]

        # Resolve DAG output bundle into the coder's inputs.
        # Coder always receives the single best-ranked path only (not top-k) in v1.
        if impl_plan.get("depends_on_dag") and raw_results.get("dag_result"):
            best = raw_results["dag_result"]["best_path"]
            impl_plan = _resolve_dag_inputs(impl_plan, best)

        # Inject resolved inputs into session_state so the coder script can use them
        coder_session = {**session_state}
        for key, value in impl_plan.get("inputs", {}).items():
            coder_session[key] = value

        raw_results["coder_result"] = self.coder.run(
            implementation_plan=impl_plan,
            session_state=coder_session,
            session_tag=f"{session_tag}_coder",
        )

    # --- Research ---
    if decision.get("research_brief"):
        raw_results["research_result"] = self.research_executor.execute(...)

    summary = self.result_summarizer.summarize(
        user_query=user_message, decision=decision, raw_results=raw_results,
    )

    return {
        "decision": decision, "raw_results": raw_results,
        "message": summary["message"], "figures": summary["figures"],
        "status": _overall_status(raw_results),
    }


def _coder_depends_on_dag(decision):
    impl_plan = decision.get("implementation_plan")
    return impl_plan is not None and impl_plan.get("depends_on_dag", False)


def _resolve_dag_inputs(impl_plan, best_path):
    """Replace DAG output bundle references with actual values from the selected best path."""
    resolved = {**impl_plan, "inputs": {**impl_plan.get("inputs", {})}}

    for key, value in resolved["inputs"].items():
        if value == "dag_output.path_dir":
            resolved["inputs"][key] = best_path["path_dir"]
        elif value == "dag_output.artifacts":
            resolved["inputs"][key] = best_path.get("artifacts", {})
        elif isinstance(value, str) and value.startswith("dag_output.artifacts."):
            field = value[len("dag_output.artifacts."):]
            artifacts = best_path.get("artifacts", {})
            if field not in artifacts:
                raise ValueError(
                    f"implementation_plan.inputs['{key}'] references 'dag_output.artifacts.{field}' "
                    f"but best_path.artifacts does not contain '{field}'. "
                    f"Available artifact keys: {list(artifacts.keys())}"
                )
            resolved["inputs"][key] = artifacts[field]
        elif isinstance(value, str) and value.startswith("dag_output.resolved_outputs."):
            field = value[len("dag_output.resolved_outputs."):]
            outputs = best_path.get("resolved_outputs", {})
            if field not in outputs:
                raise ValueError(
                    f"implementation_plan.inputs['{key}'] references 'dag_output.resolved_outputs.{field}' "
                    f"but best_path.resolved_outputs does not contain '{field}'. "
                    f"Available resolved output keys: {list(outputs.keys())}"
                )
            resolved["inputs"][key] = outputs[field]

    return resolved
```

### Figure handling

Figures can come from any execution component:
1. **DAG stages** — tools that produce figures as part of their execution (e.g., a projection tool writing UMAP plots, a future figure tool)
2. **Coder** — matplotlib/seaborn saves to disk, returns paths in `coder_result.artifacts`

`_collect_figures()` walks raw_results and collects all image paths (`.png`, `.jpg`, `.svg`):

```python
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".webp"}

def _collect_figures(raw_results: dict) -> list[str]:
    """Walk raw results and collect all image file paths."""
    figures = []
    _walk_for_images(raw_results, figures)
    return figures

def _walk_for_images(obj, out):
    if isinstance(obj, str):
        if Path(obj).suffix.lower() in IMAGE_SUFFIXES and Path(obj).exists():
            out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk_for_images(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_for_images(v, out)
```

The summarizer LLM sees the figure paths in the raw results and references them by name in its response. The frontend renders them inline.

### What the executor returns (raw, no formatting)

The DAG executor returns raw structured data only — no user-facing text:

```python
# DagExecutor.execute() returns:
{
    "status": "completed",
    "best_path": {
        "path_index": 7,
        "config": [...],
        "metrics": {...},
        "objective_score": 0.734,
        "path_dir": "/artifacts/dag/path_007",
        "artifacts": {
            "00_rna_quality_control/output.h5ad": "/artifacts/dag/path_007/00_rna_quality_control/output.h5ad",
            "03_rna_dimensionality_reduction/output.h5ad": "/artifacts/dag/path_007/03_rna_dimensionality_reduction/output.h5ad",
            "04_rna_clustering/output.h5ad": "/artifacts/dag/path_007/04_rna_clustering/output.h5ad",
            "04_rna_clustering/clusters.csv": "/artifacts/dag/path_007/04_rna_clustering/clusters.csv",
            "05_rna_celltype_annotation/output.h5ad": "/artifacts/dag/path_007/05_rna_celltype_annotation/output.h5ad",
        },
        "resolved_outputs": {
            "output_h5ad_path": "/artifacts/dag/path_007/05_rna_celltype_annotation/output.h5ad",
            "embedding_key": "X_pca",
            "cluster_key": "pca_clusters",
            "suggested_cluster_key": "pca_clusters"
        }
    },
    "comparison_table": [...],
    "paths_completed": 45,
    "paths_failed": 3,
    "objective_name": "cell_type_annotation_default",
    "artifact_dir": "/artifacts/dag/",
}
```

The comparison table, natural language summary, and figure references are all produced by the ResultSummarizer, not the executor.

### Per-path output folder layout

Each path gets its own directory under `run_dir`. Each stage within the path gets its own subdirectory:

```
run_dir/
  path_000/
    00_rna_quality_control/
      output.h5ad
    01_rna_normalization/
      output.h5ad
    02_rna_feature_selection/
      output.h5ad
    03_rna_dimensionality_reduction/
      output.h5ad
    04_rna_clustering/
      output.h5ad
      clusters.csv
    05_rna_celltype_annotation/
      output.h5ad
      annotations.csv
  path_001/
    ...
```

Tools write all their outputs (h5ad, CSVs, figures, metrics) into the `output_dir` they receive. The executor collects all files from the path directory into `artifacts` — a flat dict mapping relative paths to absolute paths.

### Normalized DAG output bundle

The `best_path` payload is the normalized handoff contract for downstream consumers. It contains:
- `path_dir`: the path's output directory (absolute path)
- `artifacts`: dict of all files produced by the path's stages (relative path → absolute path)
- `config`, `metrics`, `objective_score`: standard path metadata
- `resolved_outputs`: concrete semantic values carried forward from the consultant-authored plan, plus executor-known artifact facts such as `output_h5ad_path`

The exact contents of `artifacts` and `resolved_outputs` depend on what tools ran. The stable top-level fields are `path_dir`, `artifacts`, `resolved_outputs`, `config`, `metrics`, and `objective_score`.

**Example — after a preprocessing + clustering + annotation DAG:**

```json
{
  "path_dir": "/artifacts/dag/path_007",
  "artifacts": {
    "04_rna_clustering/output.h5ad": "...",
    "04_rna_clustering/clusters.csv": "...",
    "05_rna_celltype_annotation/output.h5ad": "..."
  },
  "resolved_outputs": {
    "output_h5ad_path": "/artifacts/dag/path_007/05_rna_celltype_annotation/output.h5ad",
    "embedding_key": "X_pca",
    "cluster_key": "pca_clusters"
  },
  "metrics": {"ari": 0.82, "nmi": 0.79}
}
```

`CoderAgent` and other downstream components consume this resolved bundle. The `implementation_plan` can reference any field:
- `"dag_output.path_dir"` — the directory containing all of the path's stage outputs (primary handoff)
- `"dag_output.resolved_outputs.output_h5ad_path"` — the canonical concrete h5ad path when a DAG stage produced one
- `"dag_output.resolved_outputs.cluster_key"` — the cluster column name
- `"dag_output.resolved_outputs.embedding_key"` — the embedding obsm key
- `"dag_output.artifacts"` — dict of all files if the script needs to enumerate them

In v1, `resolved_outputs` are not an independent inference layer. They are mostly the resolved form of `declared_outputs`, with executor-added mechanical facts such as the most downstream `output_h5ad_path`.

## 13. Coder Agent Revision

### Role in the architecture

`CoderAgent` is not a DAG post-processor. It is a plan-driven code pipeline facade that can run:
- standalone
- after DAG

When it runs after DAG, it consumes a normalized DAG output bundle rather than DAG internals.

### Plan lineage

`ToolConsultant` provides the initial `implementation_plan`, but `CoderAgent` may revise that plan during execution when evaluator feedback or runtime reality requires it.

Plan lineage lives under `coder_result.plan_trace` in the coder's return value:

```python
# CoderAgent.run() returns:
{
    "status": "completed",
    "script_path": "...",
    "metrics": {...},
    "artifacts": {...},
    "attempts": 3,
    "plan_trace": {
        "initial": { ... },           # implementation_plan as received
        "final": { ... },             # implementation_plan after any revisions
        "revisions": [                 # list of material changes (may be empty)
            {"field": "inputs.cluster_key", "from": "pca_clusters", "to": "leiden_clusters", "reason": "..."}
        ]
    },
    ...
}
```

Material revisions include changes to:
- inputs
- outputs
- required steps
- DAG dependency fields such as `dag_input_source`

Execution-only code changes inside the script do not need to be logged as plan revisions unless they change the effective execution contract.

`_build_report()` is responsible for constructing `plan_trace` by diffing the initial plan against the final plan state.

### Problem

The current coder has a two-LLM-call fix loop: evaluate (LLM reads stdout/stderr → produces feedback JSON) then revise (LLM rewrites script using feedback). This is unnecessary — the execution error _is_ the feedback. The research branch's `fix_target()` does it in one call.

The current coder also has no optimization loop. Once the script runs without error, it stops. There's no evaluation of output quality or iteration to improve results.

### Revised execution flow

```
Phase 1 — Fix loop (get it running):
  generate → execute → [fix with error] → execute → ... (up to max_fix_step)

Phase 2 — Optimization loop (improve quality):
  evaluate → [optimize with feedback] → execute → ... (up to max_opt_step)
```

### Phase 1: Generate + Fix

```python
def run(self, *, implementation_plan, session_state=None, session_tag="coder"):
    plan, session_state, run_dir, script_path = self._prepare_run(...)

    # --- Generate ---
    script = self._generate_script(plan=plan, session_state=session_state)

    # --- Fix loop ---
    execution_result = None
    for fix_attempt in range(self.max_fix_step + 1):
        script_path.write_text(script, encoding="utf-8")
        execution_result = _run_script(script_path, cwd=run_dir)

        if execution_result["returncode"] == 0:
            break
        if fix_attempt == self.max_fix_step:
            break

        # One LLM call: error + script + plan → fixed script
        script = self._fix_script(
            plan=plan,
            script=script,
            error=execution_result["stderr"],
        )

    if execution_result["returncode"] != 0:
        return self._build_report(plan, run_dir, script_path, status="failed",
                                  execution_result=execution_result, metrics={})

    # --- Phase 2: TextGrad optimization loop ---
    script_var = tg.Variable(script, requires_grad=True,
                             role_description="Python script that implements the task")
    optimizer = tg.TextualGradientDescent(
        engine=self.engine, parameters=[script_var],
        constraints=_build_coder_constraints(plan),
    )
    evaluator = CoderEvaluator(engine_name=self.engine_name)

    for opt_step in range(self.max_opt_step):
        metrics = _collect_metrics(plan, run_dir)

        # Evaluator produces loss tg.Variable via FormattedLLMCall
        loss = evaluator.loss_fn(
            script_code=script_var,                              # requires_grad=True
            plan=tg.Variable(json.dumps(plan, indent=2),
                             requires_grad=False, role_description="implementation plan"),
            success_metric=tg.Variable(plan.get("success_metric", ""),
                                       requires_grad=False, role_description="success metric"),
            metrics=tg.Variable(json.dumps(metrics, indent=2),
                                requires_grad=False, role_description="collected metrics"),
            stdout=tg.Variable(execution_result["stdout"][-4000:],
                               requires_grad=False, role_description="script stdout"),
        )

        eval_payload = _parse_evaluator_response(loss.value)
        if eval_payload["passed"]:
            break

        # TextGrad backward + step
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        script = script_var.value

        # Fix loop on optimized script (optimization may introduce errors)
        for fix_attempt in range(self.max_fix_step + 1):
            script_path.write_text(script, encoding="utf-8")
            execution_result = _run_script(script_path, cwd=run_dir)
            if execution_result["returncode"] == 0:
                break
            if fix_attempt == self.max_fix_step:
                break
            script = self._fix_script(plan=plan, script=script,
                                      error=execution_result["stderr"])
            script_var.set_value(script)

        if execution_result["returncode"] != 0:
            break

    return self._build_report(plan, run_dir, script_path, status="completed",
                              execution_result=execution_result, metrics=metrics)
```

### Phase 2: Evaluate + Optimize (TextGrad)

Same pattern as the research branch. The script is a `tg.Variable`. The evaluator is a `loss_fn` that produces a loss `tg.Variable`. `backward()` computes textual gradients on the script, `TextualGradientDescent.step()` updates it.

#### Optimizer constraints

Same role as the research branch: pin things the optimizer must not change, while the evaluator feedback guides what should change.

```python
def _build_coder_constraints(plan: dict) -> list[str]:
    constraints = [
        "Return ONLY valid executable Python code.",
        "Do not use argparse, sys.argv, command-line flags, or environment variables.",
        f"Goal: {plan['goal']}",
    ]
    if plan.get("success_metric"):
        constraints.append(f"Optimize for: {plan['success_metric']}")
    # Pin input paths/keys — optimizer must not change these
    for key, value in plan.get("inputs", {}).items():
        constraints.append(f"Input '{key}' is fixed to: {value}")
    # Pin output paths — optimizer must not change where outputs are written
    for key, value in plan.get("outputs", {}).items():
        constraints.append(f"Output '{key}' must be written to: {value}")
    # Task-specific constraints from ToolConsultant
    constraints.extend(plan.get("constraints", []))
    return constraints
```

| Research branch | Coder | Why |
|---|---|---|
| Fixed artifact paths per stage | `plan.inputs` + `plan.outputs` | Prevent optimizer from changing I/O |
| No argparse / no env vars | Same | Script must be self-contained |
| Stage requirements JSON | Not needed | No inter-stage contracts |
| Prior schema JSON | Not needed | No prior pipeline |
| Evaluation plan + primary metric | `plan.success_metric` | Same role — tells optimizer what to optimize |
| — | `plan.constraints` | Task-specific constraints from ToolConsultant |

#### CoderEvaluator

The coder has 1 evaluator (vs research branch's 4). Same mechanism: uses `tg.autograd.FormattedLLMCall` so the output `tg.Variable` is part of the computation graph and `backward()` can compute textual gradients on the script.

```python
class CoderEvaluator:
    """Single evaluator for coder scripts. Same pattern as research branch TextGradEvaluator."""

    FIELDS = ["script_code", "plan", "metrics", "stdout", "success_metric"]

    def __init__(self, *, engine_name: str):
        engine = tg.get_engine(engine_name, max_tokens=4000)

        self.system_prompt_var = tg.Variable(
            CODER_EVALUATOR_SYSTEM_PROMPT,
            requires_grad=False,
            role_description="coder evaluator system prompt",
        )
        self.formatted_llm_call = tg.autograd.FormattedLLMCall(
            engine=engine,
            format_string=CODER_EVALUATOR_FORMAT_STRING,
            system_prompt=self.system_prompt_var,
        )

    def loss_fn(self, **kwargs) -> tg.Variable:
        inputs = {}
        for field in self.FIELDS:
            if field not in kwargs:
                raise ValueError(f"Missing evaluator input field '{field}'")
            inputs[field] = kwargs[field]
        return self.formatted_llm_call(
            inputs=inputs,
            response_role_description="evaluator feedback on script quality",
        )
```

`script_code` is passed as `tg.Variable(requires_grad=True)` — this is the optimization target. All other inputs are `requires_grad=False`. When `loss.backward()` runs, TextGrad computes textual gradients only on the script.

#### Optimization loop

```python
# Phase 2 — optimization loop
evaluator = CoderEvaluator(engine_name=self.engine_name)

for opt_step in range(self.max_opt_step):
    metrics = _collect_metrics(plan, run_dir)

    # Evaluator produces loss variable
    loss = evaluator.loss_fn(
        script_code=script_var,
        plan=tg.Variable(json.dumps(plan, indent=2), requires_grad=False,
                         role_description="implementation plan"),
        success_metric=tg.Variable(plan.get("success_metric", ""), requires_grad=False,
                                   role_description="success metric"),
        metrics=tg.Variable(json.dumps(metrics, indent=2), requires_grad=False,
                            role_description="collected metrics"),
        stdout=tg.Variable(execution_result["stdout"][-4000:], requires_grad=False,
                           role_description="script stdout"),
    )

    # Check if evaluator says passed
    eval_payload = _parse_evaluator_response(loss.value)
    if eval_payload["passed"]:
        break

    # TextGrad backward + step — updates script_var.value
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    script = script_var.value

    # Fix loop on optimized script (optimization may introduce errors)
    for fix_attempt in range(self.max_fix_step + 1):
        script_path.write_text(script, encoding="utf-8")
        execution_result = _run_script(script_path, cwd=run_dir)
        if execution_result["returncode"] == 0:
            break
        if fix_attempt == self.max_fix_step:
            break
        script = self._fix_script(plan=plan, script=script,
                                  error=execution_result["stderr"])
        script_var.set_value(script)  # Keep variable in sync

    if execution_result["returncode"] != 0:
        break
```

### Prompts

```python
# --- Generator / Fix ---

CODER_SYSTEM_PROMPT = """
You are CoderAgent. You receive a concrete implementation plan from ToolConsultant.
Write one runnable Python script that satisfies the declared inputs, outputs,
constraints, and success metric. Do not broaden the task.
"""

CODER_FIX_PROMPT = """
Fix this script. Return exactly one fenced Python code block.

Implementation plan:
{implementation_plan}

Current script:
```python
{script}
```

Error:
{error}
"""

# --- Evaluator (TextGrad FormattedLLMCall) ---

CODER_EVALUATOR_SYSTEM_PROMPT = """
You evaluate a single Python script against its implementation plan.
Assess whether the script's output meets the success metric.

Return a JSON object:
{"passed": true/false, "feedback": "<what to improve, or why it passed>"}

If passed is false, feedback must be specific and actionable — describe exactly
what the script should change to improve the output quality or meet the metric.
This feedback will be used as a loss signal to optimize the script.
"""

# FormattedLLMCall format string — {field} placeholders are filled from tg.Variable inputs
CODER_EVALUATOR_FORMAT_STRING = """
|PLAN|: {plan}
|/PLAN|
|SUCCESS METRIC|: {success_metric}
|/SUCCESS METRIC|
|SCRIPT|:
{script_code}
|/SCRIPT|
|METRICS|: {metrics}
|/METRICS|
|STDOUT|: {stdout}
|/STDOUT|

Evaluate the script output against the success metric. Return JSON.
"""
```

Note: no separate `CODER_OPTIMIZE_PROMPT` — TextGrad's `optimizer.step()` handles the revision internally using the gradients from `loss.backward()`. The evaluator format string uses `|TAG|` delimiters (same convention as research branch prompts) to structure the input for the LLM.

### Comparison with research branch

| | Research branch | Coder |
|---|---|---|
| Scripts | 4-stage bundle (`tg.Variable` each) | 1 script (`tg.Variable`) |
| Fix | `fix_target()` per failed stage, resume from failure | `_fix_script()` on whole script, re-run |
| Fix prompt | stage-specific system prompts | single fix prompt |
| Evaluators | 4 (biology, data_science, model, prior) each with `loss_fn` | 1 `CoderEvaluator` with `loss_fn` |
| Optimization | `loss.backward()` → `optimizer.step()` per target | `loss.backward()` → `optimizer.step()` on single script |
| Optimizer | `tg.TextualGradientDescent` per stage file | `tg.TextualGradientDescent` on single script |
| Stagnation | reconsult with consultant for new architecture | not needed (bounded task) |
| Critic | optional second LLM loss signal | none |
| Plan source | ConsultantAgent (research) | ToolConsultant |

### Parameters

```python
class CoderAgent:
    def __init__(self, *, engine_name, result_dir, artifact_dir=None,
                 max_fix_step=3, max_opt_step=3):
```

- `max_fix_step`: max bug-fix attempts per execution (default 3)
- `max_opt_step`: max TextGrad evaluate → backward → step cycles after first success (default 3)

## 14. Implementation Status

### Implemented: `/agents/dag_executor.py`
- `DagExecutor` class (~300 lines)
- `_resolve_refs()` — generic `$L{index}.key` variable substitution with recursive resolution and declared/resolved output precedence
- Uses `AgentToolRegistry` for dispatch — stage names are tool names, no mapping needed
- `_enumerate_paths()` — Cartesian product
- `_execute_path()` — per-stage loop with StepCache, ref resolution, evaluation
- `_format_result()` — best path + comparison table
- `_build_comparison_table()` — flattened per-path summary

### Implemented: `/agents/decision_schema.py`
- Removed branch enum validation, `validate_optimization_plan()`, `_validate_tool_plan()`, and `_validate_pipeline_search_space()`
- Add `validate_dag_plan()` — validates layers, variants, checks stage names exist in tool registry, enforces ≤100 path cap
- Rewrite `validate_tool_consultant_decision()` for composable model (dag + coder + research)

### Implemented: `/agents/result_summarizer.py`
- `ResultSummarizer` class (~60 lines)
- `_slim_decision()`, `_slim_results()` — strip large payloads before sending to LLM
- `_collect_figures()`, `_walk_for_images()` — collect image paths from raw results

### Implemented: `/prompts/result_summarizer_prompts.py`
- `RESULT_SUMMARIZER_SYSTEM_PROMPT` — rules for formatting results as user-facing responses
- `RESULT_SUMMARIZER_PROMPT` — template with user_query, decision_summary, raw_results

### Implemented: `/agents/session_dispatcher.py`
- Replace `tool_executor` and `tool_optimizer` with `dag_executor` and `result_summarizer` in `__init__`
- Replace branch-based dispatch with sequential: dag (if present) -> coder (if present, receives DAG output) -> research (if present)
- Remove `_normalize_result_for_ui()` and `_derive_result_message()` — replaced by `ResultSummarizer`
- Add `result_summarizer.summarize()` call after all executors complete
- Update `_extract_previous_plan()` for dag_plan

### Implemented: `/prompts/tool_consultant_prompts.py`
- Rewrite system prompt for composable decision model
- Replace tool_plan/optimization_plan schema with dag_plan schema
- Add DAG rules and variant selection guidance
- Remove optimization rules and search_space format

### Implemented: `/agents/tool_consultant.py`
- Pass stage interfaces alongside/instead of pipeline interfaces

### Implemented: `/agents/coder.py`
- Rewrite `run()` with two-phase loop: fix loop (phase 1) then optimization loop (phase 2)
- Remove `_evaluate_attempt()` and `_revise_script()` (merged into `_fix_script` and `_optimize_script`)
- Add `_fix_script()` — single LLM call with error + script + plan → fixed script
- Use `CoderEvaluator.loss_fn()` to evaluate output quality against `success_metric`
- Add `_optimize_script()` — TextGrad improves the script from evaluator loss without a separate optimize prompt
- Add `max_opt_step` parameter (default 3)
- Fix loop runs inside optimization loop too (optimization may introduce errors)

### Implemented: `/prompts/coder_agent_prompts.py`
- Replace `CODER_AGENT_EVALUATOR_PROMPT` and `CODER_AGENT_REVISION_PROMPT` with:
  - `CODER_FIX_PROMPT` — error + script + plan → fixed script (1 call)
  - `CODER_EVALUATOR_PROMPT` — plan + metrics + stdout → `{passed, feedback}`
- No `CODER_OPTIMIZE_PROMPT`; optimization is handled by TextGrad using evaluator loss and constraints.
- Keep `CODER_AGENT_IMPLEMENTATION_PROMPT` (initial generation)
- Simplify `CODER_AGENT_SYSTEM_PROMPT`
- Remove `CODER_AGENT_FINAL_REPORT_PROMPT` (report built in code, not by LLM)

### Implemented: `/frontend/server.py`
- Construct `DagExecutor` and `ResultSummarizer` instead of `ToolPlanExecutor` + `ToolOptimizerAgent`
- Pass `dag_executor` and `result_summarizer` to `SessionDispatcher`

### Removed
- Legacy tool-plan executor module — replaced by DagExecutor
- Legacy tool optimizer module — replaced by DagExecutor
- Legacy tool optimizer prompts — no longer needed
- Hardcoded task-result formatting functions in `session_dispatcher.py` — replaced by ResultSummarizer

### Unchanged
- `backend/cache/step_cache.py` — reused directly
- `backend/runs/registry.py` — reused directly
- `backend/eval/` — reused directly
- `backend/objectives.py` — reused directly
- `backend/pipelines/` — kept as-is (DAG executor doesn't use PipelineSpec)
- `research` pipeline — unchanged

## 15. Verification Matrix

| # | Requirement | Code path | Test coverage | Status |
|---|---|---|---|---|
| 1 | Single-path DAG produces output, metrics, null objective score, and trial log | `agents/dag_executor.py` | `tests/test_dag_executor.py::test_single_path_dag_logs_trial_without_objective_score` | Covered |
| 2 | Multi-path DAG ranks by objective and emits comparison table | `DagExecutor._format_result()` | `test_execute_ranks_best_path_and_returns_normalized_bundle` | Covered |
| 3 | Equal objective scores tie-break by lower `path_index` | `DagExecutor._format_result()` | `test_equal_objective_scores_tie_break_to_lower_path_index` | Covered |
| 4 | 48-path annotation-shaped DAG runs and selects best path | `DagExecutor._enumerate_paths()` / `_execute_path()` | `test_full_annotation_dag_shape_can_enumerate_48_paths` | Covered with fake tools |
| 5 | Path cap rejects >100 paths | `validate_dag_plan()` | `test_validate_rejects_path_count_above_cap` | Covered |
| 6 | DAG + coder receives `path_dir`, optional h5ad path, and resolved keys | `SessionDispatcher._resolve_dag_inputs()` | `tests/test_composable_dispatcher.py::test_dag_result_inputs_are_resolved_before_coder_runs` | Covered |
| 7 | DAG failure skips DAG-dependent coder | `SessionDispatcher._execute_composable_task()` | `test_dag_failure_skips_dag_dependent_coder` | Covered |
| 8 | Coder-only task works with no `dag_plan` | `SessionDispatcher._execute_composable_task()` / `CoderAgent.run()` | `tests/test_session_routing.py::test_composable_coder_result_uses_result_summarizer` | Covered |
| 9 | Cache sharing avoids re-executing shared prefixes | `DagExecutor._execute_path()` + `StepCache` directory APIs | `test_execute_restores_shared_prefix_from_directory_cache` | Covered |
| 10 | Failed paths do not block successful paths | `DagExecutor._execute_path()` / `_format_result()` | `test_failed_path_does_not_block_successful_path` | Covered |
| 11 | `$L{idx}.key` resolves by layer/path variant | `_resolve_refs()` | `test_resolve_refs_uses_layer_outputs_and_recursive_declared_outputs` | Covered |
| 12 | Recursive `$ref` through `declared_outputs` works | `_resolve_refs()` | `test_resolve_refs_uses_layer_outputs_and_recursive_declared_outputs` | Covered |
| 13 | Executor-known `output_h5ad_path` is recorded and chained | `_extract_output_h5ad()` / `_find_primary_h5ad()` | `test_execute_ranks_best_path_and_returns_normalized_bundle` | Covered |
| 14 | Declared semantic outputs drive downstream refs | `_resolve_refs()` | `test_resolve_refs_uses_layer_outputs_and_recursive_declared_outputs` | Covered |
| 15 | ResultSummarizer DAG-only prompt contains best config, metrics, comparison table | `ResultSummarizer.summarize()` | `tests/test_result_summarizer.py::test_dag_only_summary_prompt_includes_best_path_and_comparison_table` | Covered |
| 16 | ResultSummarizer DAG+coder prompt contains DAG metrics and coder artifacts | `ResultSummarizer.summarize()` | `test_dag_plus_coder_summary_prompt_includes_metrics_and_coder_artifacts` | Covered |
| 17 | ResultSummarizer coder-only returns user-facing message and figures | `ResultSummarizer.summarize()` | `test_summarize_returns_message_and_figures` | Covered |
| 18 | Figure collection finds nested image artifacts and deduplicates | `_collect_figures()` | `test_collect_figures_walks_nested_results_and_deduplicates` | Covered |
| 19 | Coder fix loop repairs syntax/runtime errors | `CoderAgent._execute_pipeline()` / `_fix_script()` | `tests/test_coder_agent.py::test_coder_fix_loop_repairs_script_and_records_plan_trace` | Covered |
| 20 | Coder TextGrad optimization can run and return partial when evaluator never passes | `CoderAgent._optimize_script()` | `test_coder_optimization_returns_partial_when_evaluator_never_passes` | Covered |
| 21 | Coder inner fix loop recovers from optimization-introduced bug | `CoderAgent._optimize_script()` | `test_coder_inner_fix_loop_recovers_from_broken_optimization_step` | Covered |
| 22 | Coder fix exhaustion fails before optimization | `CoderAgent._execute_pipeline()` | `test_coder_fix_exhaustion_fails_before_optimization` | Covered |
