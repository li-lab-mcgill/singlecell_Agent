# Single-Cell Analysis Agent — Architecture Overview

## System Purpose

An LLM-powered agent system for automated single-cell genomics analysis. Users describe analysis goals in natural language (e.g., "cluster my PBMC data and annotate cell types with the best ARI") and the system plans, executes, evaluates, and summarizes multi-step bioinformatics pipelines — branching across methods and parameters when beneficial.

---

## Top-Level Directory Structure

```
singlecell_Agent/
  agents/           # Agent orchestration, planning, execution, state
  backend/          # Computational backend (RNA, ATAC, multi-omic tools)
  frontend/         # HTTP server + single-page chat UI
  prompts/          # All LLM prompt templates
  rag/              # Literature retrieval (PubMed, embeddings, RAG store)
  docs/             # Tool documentation, architecture docs
  tests/            # Unit and integration tests
  data/             # Input datasets
```

---

## Agent Pipeline

User messages flow through a chain of specialized agents:

```
User Message
    |
    v
SessionRouter          — Classify: "direct_response" or "task"
    |
    v (if task)
ToolConsultant         — Produce an execution plan (dag_plan / implementation_plan / research_brief)
    |
    v
SessionDispatcher      — Orchestrate execution of plan components
    |
    +-- DagExecutor        — Run ordered tool DAGs with branching variants
    +-- CoderAgent         — Generate and execute custom Python scripts (TextGrad-optimized)
    +-- ResearchExecutor   — Literature-grounded research pipeline
    |
    v
ResultSummarizer       — LLM-generated user-facing summary of results
    |
    v
Frontend (UI)
```

### agents/session_router.py — SessionRouter

Classifies each user message as either:
- **direct_response**: Simple questions answered without tool execution (e.g., "what is UMAP?")
- **task**: Requires planning and execution

### agents/tool_consultant.py — ToolConsultantAgent

First-stage planning agent. Does NOT execute tools or write code. Reads tool documentation and session state to produce one or more plan components:

| Plan Component | When Used |
|---|---|
| `dag_plan` | Pipeline execution with ordered tool stages |
| `implementation_plan` | Custom Python script (standalone or post-DAG) |
| `research_brief` | Literature-grounded method design |

Plans can be composed: `dag_plan` + `implementation_plan` runs the DAG first, then passes output to custom code. `research_brief` is standalone.

### agents/session_dispatcher.py — SessionDispatcher

Central orchestrator. Receives the ToolConsultant's decision and executes components sequentially:

1. **DAG execution** (if `dag_plan` present) via `DagExecutor`
2. **Reference resolution** — resolves `dag_output.*` and `session_output.*` references in the implementation plan to concrete paths
3. **Coder execution** (if `implementation_plan` present) via `CoderAgent`
4. **Research execution** (if `research_brief` present) via `ResearchExecutor`
5. **Result summarization** via `ResultSummarizer`
6. **State recording** — updates `SessionStateStore` with turn results

### agents/dag_executor.py — DagExecutor

Executes ordered tool DAGs with Cartesian-product branching:

- **Layers**: Ordered stages (qc -> normalize -> features -> embed -> cluster -> annotate)
- **Variants**: Each layer can have multiple method/parameter choices
- **Paths**: Every combination runs end-to-end (no pruning)
- **Caching**: `StepCache` shares work across paths with identical prefixes
- **Evaluation**: Each completed path is scored via `Evaluator` + `objectives`
- **Output**: Best path + ranked comparison table of all paths

Single-variant-per-layer degrades gracefully to linear execution (replaces the former one-shot mode).

### agents/coder.py — CoderAgent

Generates and executes Python scripts for custom analysis:

- **TextGrad optimization**: Uses TextGrad to iteratively improve generated code
- **Fix loop**: Automatic error diagnosis and retry (up to `max_fix_step`)
- **Optimization loop**: Iterative quality improvement (up to `max_opt_step`)
- **Image collection**: Discovers output images from plan outputs, run directory, and stdout parsing

### agents/research_executor.py — SubprocessResearchExecutor

Runs the literature research pipeline as a subprocess for deep method design tasks.

### agents/result_summarizer.py — ResultSummarizer

LLM-powered summarization of raw execution results into user-facing messages. Collects images from results for UI display.

### agents/session_state.py — SessionStateStore

JSON-backed persistent state across turns:

- `active_h5ad_path` — final h5ad from last successful turn
- `active_embedding_key` — current embedding key (e.g., `X_pca`)
- `active_cluster_key` — current cluster key (e.g., `leiden_clusters`)
- `last_artifacts` — all artifacts from last turn
- Turn history with per-turn results

Supports `session_output.*` references so follow-up turns can use prior results without re-running pipelines.

### agents/runner.py — ToolCallingAgentRunner

Generic LLM agent execution loop with:
- Tool calling support (function-calling protocol)
- Response handler callback pattern
- Transcript and tool trace logging
- Configurable iteration and tool call limits

### agents/decision_schema.py

Validation logic for all plan types. Validates DAG plans (layer structure, stage names, variant format, `$L` references), implementation plans (input references, dependency flags), and the overall decision envelope.

### agents/tools.py

Tool definitions and registry. Each tool wraps a backend method with:
- Input/output schema
- Parameter validation
- Backend dispatch

Registry builder `build_tool_executor_registry()` creates the mapping from tool names to executor functions used by `DagExecutor`.

---

## Backend

The computational engine. All bioinformatics methods live here.

```
SingleCellBackend
  |- config      : BackendConfig          (paths, R executable, scratch dirs)
  |- runners     : RunnerSuite            (R + CLI subprocess helpers)
  |- refs        : ReferenceStore         (reference data download/cache)
  |- api         : dict                   (Ensembl, JASPAR, CellxGene clients)
  |- rna         : RnaBackend             (QC, normalize, features, embed, cluster, annotate, DE, 2D projection)
  |- atac        : AtacBackend            (ATAC-seq processing)
  |- multi       : MultiBackend           (multi-omic integration)
  |- eval        : Evaluator              (ARI, NMI, silhouette, batch entropy)
  |- runs        : TrialRegistry          (SQLite-backed leaderboard)
  |- cache       : StepCache              (SHA256 content-addressed step caching)
```

### Key Backend Modules

| Module | Purpose |
|---|---|
| `backend/rna/` | RNA-seq: QC (basic, scrublet), normalization (log1p), feature selection (seurat_v3, cellranger, scanpy_hvg), embedding (PCA, scVI, scanVI, Seurat PCA), clustering (Leiden, Louvain), annotation (GPT-4, CellMarker, CellTypist), DE, 2D projection |
| `backend/atac/` | ATAC-seq processing pipeline |
| `backend/multi/` | Multi-omic integration (references parent backend) |
| `backend/eval/` | Metric computation: ARI, NMI, silhouette score, batch entropy |
| `backend/objectives.py` | Named objective functions that combine metrics into scalar scores for path ranking |
| `backend/runs/` | `TrialRegistry` — SQLite leaderboard for tracking/comparing pipeline runs |
| `backend/cache/` | `StepCache` — content-addressed caching keyed by SHA256 of inputs; shares work across DAG paths |
| `backend/refs/` | `ReferenceStore` — download, cache, and serve reference datasets and marker databases |
| `backend/runners/` | `RunnerSuite` — subprocess wrappers for R scripts and CLI tools |
| `backend/r_scripts/` | R scripts called via `RunnerSuite` (e.g., Seurat PCA) |

---

## Frontend

### frontend/server.py

Single-file HTTP server with embedded HTML/CSS/JS chat UI:

- `POST /chat` — accepts user message, dispatches through `SessionDispatcher`, returns response + images
- `GET /state` — returns current session state
- Image serving: converts local file paths to `/image?path=...` URLs for browser display
- Constructs all agent components (`SessionRouter`, `ToolConsultantAgent`, `DagExecutor`, `CoderAgent`, `ResultSummarizer`) and wires them into `SessionDispatcher`

---

## RAG System

Literature retrieval for research-mode tasks:

| File | Purpose |
|---|---|
| `rag/agent.py` | RAG agent: generates search queries, retrieves papers, builds context for method design |
| `rag/paper_store.py` | Paper storage and retrieval |
| `rag/store_backend.py` | `RAGStore` — vector store backend for embedding-based retrieval |
| `rag/sources.py` | PubMed fetching, document normalization |
| `rag/prepare.py` | Document preparation and chunking |
| `rag/types.py` | Data types (`RAGDocument`, `RAGHit`, `PromotedPaper`) |

---

## Prompts

All LLM prompt templates organized by agent:

| File | Agent |
|---|---|
| `session_router_prompts.py` | SessionRouter |
| `tool_consultant_prompts.py` | ToolConsultantAgent |
| `coder_agent_prompts.py` | CoderAgent (generation, evaluation, fix) |
| `result_summarizer_prompts.py` | ResultSummarizer |
| `evaluator_prompts.py` | Evaluation prompts |
| `analyst_prompts.py` | Analyst agent |
| `consultant_prompts.py` | Consultant agent |
| `generator_prompts.py` | Generator prompts |

---

## Data Flow Example

**"Cluster my PBMC data and find the best ARI"**

1. **SessionRouter** classifies as `task`
2. **ToolConsultant** produces a `dag_plan` with:
   - Fixed layers: QC (basic), normalize (log1p)
   - Branching: embed (PCA vs scVI), cluster (resolution 0.5 vs 1.0)
   - Evaluation: ARI against ground truth labels
3. **DagExecutor** enumerates 4 paths (2 embed x 2 resolution):
   - Runs QC once (cached), normalize once (cached)
   - Runs each embed method, then each cluster resolution
   - Evaluates ARI for all 4 paths
4. **ResultSummarizer** formats: best path config + comparison table
5. **SessionStateStore** records `active_h5ad_path`, `active_cluster_key` for follow-up turns

**Follow-up: "Now make a UMAP of the best result"**

1. **ToolConsultant** produces `implementation_plan` with `depends_on_dag: false`, using `session_output.active_h5ad_path`
2. **SessionDispatcher** resolves `session_output.*` references from stored state
3. **CoderAgent** generates and runs a Python script to compute + save UMAP
4. **ResultSummarizer** returns summary + collected UMAP image

---

## Key Design Decisions

- **DAG replaces both one-shot and optimization**: A single execution model handles linear pipelines (1 variant per layer) and multi-path exploration (multiple variants). No separate Optuna/HPO system.
- **LLM-driven variant selection**: The ToolConsultant decides where to branch based on the target objective, keeping the Cartesian product manageable.
- **Content-addressed caching**: Paths sharing early stages (same QC + normalize) automatically share cached results.
- **Composable plans**: `dag_plan` + `implementation_plan` can be combined in a single turn. `session_output.*` references enable multi-turn workflows without re-running pipelines.
- **TextGrad code optimization**: The CoderAgent uses TextGrad for iterative script improvement rather than simple retry loops.
