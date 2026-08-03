# Single-Cell Agent Architecture Overview

## Purpose

`singlecell_Agent` is an LLM-orchestrated single-cell analysis system. It accepts natural-language requests, classifies the request intent, plans executable analysis, runs single-cell tools or generated code, interprets results, and records session artifacts for follow-up turns.

The current implementation supports two major modes:

- **Operational execution**: run a concrete workflow, such as QC, embedding, clustering, annotation, differential expression, or a custom script.
- **Discovery/research execution**: formulate a scientific plan, stress-test it, execute one or more phases, analyze evidence, and decide whether to conclude, revise, ask the user, or continue.

---

## Top-Level Structure

```text
singlecell_Agent/
  agents/            # Routing, planning, research loop, panels, execution orchestration, state
  backend/           # Single-cell computational tools, runners, refs, cache, evaluation
  frontend/          # Local HTTP chat UI and API endpoints
  prompts/           # Legacy/current Python prompt modules
  updated_prompts/   # Current markdown prompt source used by panel/mediator agents
  rag/               # Literature retrieval, paper storage, vector store contracts
  wiki/              # Tool/task/stage/package/method/paper knowledge base
  docs/              # Architecture and tool documentation
  tests/             # Unit and integration tests
```

---

## Request Flow

```text
Frontend / API
  |
  v
SessionStateStore.begin_turn()
  |
  v
SessionDispatcher.handle()
  |
  v
SessionRouter.route()
  |
  +-- direct_response
  |     |
  |     v
  |   DeterministicResponder
  |     - answers from route response, session state, or artifact lookup
  |
  +-- task + operational intent
  |     |
  |     v
  |   ToolConsultantAgent.decide()
  |     |
  |     +-- DagExecutor.execute()
  |     +-- CoderAgent.run()
  |     +-- SubprocessResearchExecutor.execute() when research_brief is explicitly allowed
  |     |
  |     v
  |   ResultSummarizer.summarize()
  |
  +-- task + discovery intent
        |
        v
      ResearchWorkspace.resolve_research_state() when configured
        |
        v
      ResearchLoop.run()
        |
        +-- ScientistPanel / MediatorAgent / AdversarialPanelist
        +-- ToolConsultantAgent
        +-- optional adversarial alignment review
        +-- DagExecutor or CoderAgent
        +-- AnalyzerPanel
        +-- optional AttributingCritic / ShortTermMemory / ContextManager
        +-- MediatorAgent post-analysis decision
```

`SessionRouter` returns one of two routes (`direct_response`, `task`) plus an intent mode (`operational`, `discovery`, `ambiguous`). Ambiguous tasks are not executed; the dispatcher asks the user to choose operational execution or discovery.

---

## Core Agent Components

### `agents/session_router.py`

Classifies each chat turn with an LLM runner and validates the result against the session-route schema:

- `route`: `direct_response` or `task`
- `intent_mode`: `operational`, `discovery`, or `ambiguous`
- `resolved_intent`: normalized user request
- `requires_artifact_lookup`: whether the direct response should read prior artifacts

### `agents/session_dispatcher.py`

The main frontend orchestration layer. It:

- injects persistent session state into routing and planning context;
- handles direct responses through `DeterministicResponder`;
- routes operational tasks through ToolConsultant plus DAG/Coder execution;
- routes discovery tasks through `ResearchLoop`;
- resolves `dag_output.*` references into best-path artifacts;
- resolves `session_output.*` references from prior turns;
- builds the final frontend payload with status, message, images, raw results, and artifact paths.

### `agents/tool_consultant.py`

Plan-only agent. It uses wiki tools, available objective definitions, prior session context, and optional long-term memory to produce a composable `TOOL_DECISION`.

Supported plan fields:

- `dag_plan`: layered tool workflow for `DagExecutor`
- `implementation_plan`: custom code plan for `CoderAgent`
- `research_brief`: standalone research subprocess path

The agent does not execute tools. `agents/decision_schema.py` validates all returned plans before dispatch.

### `agents/dag_executor.py`

Runs layered single-cell tool workflows by enumerating Cartesian products of layer variants.

Key behavior:

- validates plans against the available backend tool registry;
- creates one run directory per `session_tag`;
- enumerates every variant path;
- auto-wires context keys such as `embedding_key`, `cluster_key`, `projection_key`, and velocity keys from upstream tool outputs;
- caches reusable step directories through `backend.cache.StepCache`;
- records trials in `backend.runs.TrialRegistry`;
- evaluates completed paths with `backend.eval` and `backend.objectives.score_metrics`;
- writes `dag_result.json` and an artifact manifest;
- applies output retention so only selected artifacts are preserved when requested.

### `agents/coder.py`

Executes custom implementation plans. It generates scripts, runs them, repairs failures, optionally optimizes generated code, and collects output figures/files for frontend display.

### `agents/result_summarizer.py`

Summarizes operational raw results into a user-facing message and figure list. If unavailable, the dispatcher falls back to deterministic result text and image collection.

---

## Discovery Research Loop

`agents/research_loop.py` implements the full research cycle:

```text
Formulate plan
  -> ToolConsultant executable plan
  -> Execute DAG/Coder
  -> AnalyzerPanel report
  -> Optional attribution/memory/context updates
  -> Mediator post-analysis decision
  -> conclude, revise, continue, ask user, or abstain
```

The loop runs up to `max_phases`. It terminates when the mediator returns a done-like action (`accept_and_conclude`), an abstain/unanswerable action, an ask-user action, or the phase cap is reached.

### Formulation

For non-`skip_panel` discovery runs:

1. `ScientistPanel.run_initial_panelists()` runs biologist, statistician, and bioinformatician panelists.
2. `MediatorAgent.formulate()` synthesizes a selected research plan, alternatives, evidence state, and trajectory decision.
3. The mediator may request bounded panelist callbacks.
4. `AdversarialPanelist.run()` stress-tests the uncommitted candidate plan.
5. If needed, `MediatorAgent.revise_from_adversary()` revises the candidate before it is committed.
6. `ResearchState.commit_initial_plan()` records the accepted plan into the state graph.

`skip_panel` creates a direct operational research plan without panelist debate.

### Execution Per Phase

For each phase:

1. `ToolConsultantAgent.decide()` converts the selected research plan into executable `dag_plan` and/or `implementation_plan`.
2. An optional alignment reviewer can block or revise plans that do not satisfy the research plan.
3. `_execute()` runs `DagExecutor` or `CoderAgent`.
4. The best produced `.h5ad` becomes the next phase input when available.
5. Results, tool plans, coder reports, and summaries are saved through `SessionRecorder`.

### Analysis and Revision

`AnalyzerPanel.analyze()` runs a structured analysis panel:

- **ResultsInterpreter** reads outputs and figures first.
- **LiteratureGrounder** and **DatabaseValidator** run in parallel using the results interpretation.
- **AnalyzerMediator** synthesizes a final analyzer report.

The mediator then runs post-analysis reasoning and chooses among:

- `accept_and_conclude`
- `continue_with_same_research_plan`
- `self_revise_plan`
- `ask_user`
- `declare_unanswerable`

The decision is applied to the `StateGraphManager`, which can conclude a node, mark it awaiting user input, or create a revised branch.

---

## Research State, Graphs, and Recording

### `agents/research_state.py`

Task-scoped source of truth for discovery runs. It stores:

- original and resolved user questions;
- profiled data summary;
- selected and alternative research plans;
- active evidence state;
- panelist outputs, callbacks, mediator outputs, adversary outputs, tool decisions, analyzer reports;
- context builders for mediator, adversary, and tool consultant prompts.

### `agents/state_graph.py`

Maintains a persistent plan graph in `state_graph.json`.

It tracks:

- active research or operational nodes;
- selected and alternative plans;
- plan, tool, execution, analyzer, and next-decision refs;
- plan revisions and branches;
- terminal statuses such as `concluded`, `unanswerable`, and `awaiting_user`.

### `agents/session_recorder.py`

Creates stable conversation/session storage:

```text
conversations/<conversation_id>/sessions/<session_id>/
  session.json
  progress.jsonl
  state_graph.json
  route/
  nodes/
  traces/
  executions/
  artifacts/files/
  reports/
```

The recorder writes JSON/text artifacts for plans, decisions, executions, analyzer reports, final responses, and progress events.

### `agents/session_state.py`

Frontend-local persistent state across turns. It records:

- message history and current turn;
- last route, decision, result, and error;
- last artifacts;
- active `.h5ad`, embedding key, cluster key, and work type;
- enough prior context for follow-up requests and artifact lookup.

---

## Backend and Tool Registry

The active DAG tool path uses `backend/tools/**/*.py`, not the older `backend/rna`, `backend/atac`, and `backend/multi` object APIs directly.

### `backend/tools/registry.py`

Discovers tool modules and exposes tool IDs.

### `backend/tools/executor.py`

Builds the executor registry used by `DagExecutor`:

- loads input `.h5ad` with AnnData;
- filters plan parameters against each tool's `run()` signature;
- calls the tool;
- persists the output `.h5ad`;
- extracts standard context from `adata.uns`;
- returns tool metadata, metrics, dataclass fields, and output context.

Current tool families include:

- RNA: QC, normalization, feature selection, embedding, batch integration, clustering, projection, annotation, differential expression, GRN, velocity.
- ATAC: QC, feature selection, TF-IDF/LSI embedding, batch integration, clustering, projection, annotation, peak calling, motif enrichment, differential accessibility, peak-to-gene, topics.
- Multi-omic: QC/intersection, joint embeddings, GRN/SCENIC+, velocity-related utilities.
- Evaluation: ARI/NMI, silhouette, iLISI/cLISI, kBET.

Supporting backend modules:

- `backend/cache/`: content-addressed step caching.
- `backend/runs/`: SQLite-backed task/trial registry.
- `backend/eval/`: metric evaluation.
- `backend/objectives.py`: objective definitions and scoring.
- `backend/refs/`: reference-data manifest, loaders, and store.
- `backend/runners/`: R and CLI subprocess helpers.
- `backend/workspace_profiler.py`: profiles input workspaces for research-loop context.

---

## RAG and Wiki Knowledge

### RAG

`rag/literature_retriever.py` coordinates literature retrieval for panelists, analyzers, adversary, and mediator paper tools. Supporting modules include:

- `rag/agent.py`: query/retrieval agent utilities.
- `rag/paper_store.py`: paper storage.
- `rag/store_backend.py`: vector-store contract.
- `rag/sources.py`: source adapters and normalization.
- `rag/types.py`: retrieval and paper datatypes.

### Wiki

`wiki/` is the structured knowledge base used by ToolConsultant and paper tooling:

- `wiki/tasks/`: supported analysis tasks.
- `wiki/stages/`: stage definitions.
- `wiki/tools/`: tool documentation used for planning.
- `wiki/methods/`: method-level background.
- `wiki/packages/`: package notes.
- `wiki/resources/`: resource notes.
- `wiki/papers/`: paper markdown entries written during retrieval.

---

## Frontend

`frontend/server.py` provides a local threaded HTTP server with an embedded chat UI.

Important behavior:

- serves the single-page chat interface;
- accepts chat requests and calls `SessionDispatcher.handle()`;
- stores turn state through `SessionStateStore`;
- serves local images through image URLs;
- exposes session/progress state for the activity panel;
- wires the router, consultant, DAG executor, coder, result summarizer, research loop, workspace resolver, backend, and RAG components.

---

## Prompt Sources

The current panel/mediator workflow primarily loads prompts from `updated_prompts/` through `agents/prompt_loader.py`.

Examples:

- `panelist_shared_system.md`
- `biologist_formulation.md`
- `statistician_formulation.md`
- `bioinformatician_formulation.md`
- `mediator_formulation.md`
- `mediator_adversary_revision.md`
- `mediator_post_analysis.md`
- `adversary.md`
- `analyzer.md`
- `paper_md_writer.md`

Python prompt modules in `prompts/` are still used by router, tool consultant, coder, summarizer, and some analyzer/adversary paths.

---

## Example Flows

### Operational Request

User: "Cluster this PBMC dataset and compare PCA vs scVI."

1. Router returns `task` + `operational`.
2. ToolConsultant emits a `dag_plan` with variant layers.
3. DagExecutor enumerates all paths.
4. Backend tools write path outputs and metrics.
5. ResultSummarizer reports the best path and figures.
6. SessionStateStore records active artifacts for follow-up turns.

### Discovery Request

User: "Which immune cell populations may drive inflammation in this dataset?"

1. Router returns `task` + `discovery`.
2. ResearchLoop profiles the workspace and initializes/continues research state.
3. Scientist panel and mediator formulate a research plan.
4. Adversary critiques the plan; mediator revises if needed.
5. ToolConsultant translates the plan into executable tools/code.
6. Execution runs.
7. AnalyzerPanel interprets results, literature support, and database evidence.
8. Mediator decides to conclude, revise, continue, ask the user, or declare unanswerable.
9. SessionRecorder and StateGraphManager persist the full trace.
