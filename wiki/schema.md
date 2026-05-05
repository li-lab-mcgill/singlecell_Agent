# Wiki Knowledge Graph Schema

This document defines the structure of the singlecell_Agent wiki knowledge graph.
The ToolConsultant agent receives this schema at the start of every planning session.

---

## Node Types

| Type | Purpose | Created by |
|------|---------|-----------|
| `task` | End-to-end user goals | Human |
| `stage` | Reusable pipeline steps | Human |
| `method` | Conceptual techniques | Human |
| `tool` | Registered executable callables | Human (reviewed) |
| `package` | Software library reference cards | Human |
| `resource` | Datasets and external data | Human |
| `run` | Immutable execution records | Auto-generated |

---

## Edge Types

| Edge type | Source → Target | Purpose |
|-----------|----------------|---------|
| `rna` | stage → method | RNA-specific methods for this stage |
| `atac` | stage → method | ATAC-specific methods for this stage |
| `multi` | stage → method | Multi-omic methods for this stage |
| `implements` | method → tool | Tools that implement this method |
| `evaluated_by` | task → tool | Eval tools that score this task |
| `package` | tool → package | Library this tool belongs to (metadata) |

Edge syntax in markdown: `- [[type/id]] [edge_type]`

Example:
```
- [[methods/graph_based_clustering]] [rna]
- [[tools/rna_cluster_leiden]] [implements]
- [[tools/eval_ari_nmi]] [evaluated_by]
- [[packages/leidenalg]] [package]
```

---

## Task Node Structure

```yaml
---
type: task
id: <task_id>
modality: rna | atac | multi
canonical_pipeline:
  - stages/<id>     # ordered — defines execution sequence
  - stages/<id>
  - ...
eval_weights:       # optional — if absent, equal weighting
  eval_<tool>: 0.5
  eval_<tool>: 0.5
---
```

Body: user-facing description, when this task applies, branching axes, upstream/downstream tasks.

---

## Stage Node Structure

```yaml
---
type: stage
id: <stage_id>
---
```

Body: what this stage does, inputs/outputs, ordering constraints, which tasks use it.
Edges: modality-tagged links to methods.

---

## Method Node Structure

```yaml
---
type: method
id: <method_id>
---
```

Body: conceptual description, when to pick this method over alternatives, key parameters, known pitfalls, benchmark citations.
Edges: `implements` links to tools.

---

## Tool Node Structure

```yaml
---
type: tool
id: <tool_id>
implements: methods/<id>
package: <package_id>
function: backend.tools.<modality>.<stage>.<name>.run
modality: rna | atac | multi | eval
stage: <stage_id>
---
```

Body: function signature, prerequisites, parameter guidance, common errors.
Edges: `package` link.

---

## Package Node Structure

```yaml
---
type: package
id: <package_id>
version: <version>
citation: <paper or docs URL>
---
```

Body: overview, install, key capabilities relevant to single-cell analysis.

---

## Resource Node Structure

```yaml
---
type: resource
id: <resource_id>
modality: rna | atac | multi
n_cells: <int>
access_path: <path or URL>
---
```

Body: dataset description, properties, usage conventions, observations from runs.

---

## Run Node Structure

```yaml
---
type: run
id: <YYYY-MM-DD-description>
task: tasks/<id>
date: <YYYY-MM-DD>
---
```

Body: what stages/methods/tools were used, parameters, results, observations.
Run nodes are immutable — never edited after creation.

---

## Traversal Protocol for ToolConsultant

1. Identify `modality` and `task_category` from user input
2. Call `graph_query("tasks/<id>")` → read `canonical_pipeline` from frontmatter for stage order
3. For each stage in order, call `graph_query("stages/<id>", edge_type=modality)`
4. For each method returned, call `graph_query("methods/<id>", edge_type="implements")`
5. Read tool content → reason on parameters → emit DAG plan step
6. Call `graph_query("tasks/<id>", edge_type="evaluated_by")` → collect eval tools
7. Apply `eval_weights` from task frontmatter (equal weighting if absent)

Branching: if uncertain between methods or parameter values, plan multiple variants.
The DagExecutor will run all variants and rank by eval score.

---

## Provenance Rules

Every non-trivial claim in a node body must cite a source:
- Paper: `[Author Year]`
- Run: `[[runs/<id>]]`
- Docs: `[package docs]`

Claims without citations are flagged during wiki review.
