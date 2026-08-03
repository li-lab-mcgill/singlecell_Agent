# Analyzer Panel — Design Plan

## Overview

The Analyzer Panel interprets the results of each DAG execution phase. It reads
the quantitative outputs, interprets figures via VLM, contextualizes findings
against the literature, and cross-checks biological claims against external
databases. Its report is passed to the Scientist Panel's `update()` call.

When the Scientist Panel's Mediator signals `"done"`, the last Analyzer report
is the final answer to the user's question.

---

## Role in the Loop

```
Scientist Panel formulate() / update()
        ↓
Planner → DAG → DagExecutor
        ↓  (dag_result.json + figures in stage_dirs)
Analyzer Panel
        ↓  (analyzer_report)
Scientist Panel update()
        ↓  "continue" / "pivot" / "done" / "abstain"
```

---

## Inputs

The Analyzer receives:
- `dag_result`: full DagExecutor output — stage results, metrics, artifact paths
- `figure_paths`: list of figure files saved by the DAG (PNG/SVG per stage_dir)
- `research_plan`: the Scientist Panel's research plan for this phase — including
  the ordered steps and required visualizations, so the Analyzer knows what was
  intended and what to look for
- `working_model`: accumulated hypothesis history from prior phases
- `user_question`: original research question

---

## Panelists

### ResultsInterpreter
- **Perspective**: quantitative — reads numerical and tabular outputs from the DAG,
  evaluates whether the steps in the research plan produced the expected results,
  identifies what passed and what failed
- **Tools**:
  - `retrieve_literature(base_query, background)` — optional; retrieves papers
    to contextualize a numerical result (e.g. "is ARI of 0.6 good for this cell type?")
  - `interpret_figure(figure_path)` — VLM call that reads a figure and returns
    a natural language interpretation; ResultsInterpreter calls this for each
    required visualization specified in the research plan
- **Output**: per-step assessment of what the DAG produced, which steps passed
  their validation criteria, what the key numerical findings are, what the figures
  show (via interpret_figure)

---

### LiteratureGrounder
- **Perspective**: contextual — compares findings to what is known in the field.
  "Is what we found consistent with prior literature, or does it contradict /
  extend what is known?"
- **Tools**:
  - `retrieve_literature(base_query, background)` — primary tool; retrieves papers
    relevant to the specific findings (e.g. "exhaustion signatures in CD8+ T cells
    COVID-19", "TIGIT LAG3 co-expression chronic infection")
  - `fetch_paper_section(paper_id, section_type)` — drills into specific paper
    sections to compare methods or results in detail
- **Output**: how findings relate to prior work — confirmed by literature,
  contradicts literature, novel finding not previously reported, or replication
  of known result

---

### DatabaseValidator
- **Perspective**: biological database cross-check — given specific biological
  claims that emerged from the results (proposed TF-TG connections, cell type
  annotations, pathway enrichments, ligand-receptor interactions), validates
  these against curated biological databases
- **Tools**:
  - `retrieve_literature(base_query, background)` — optional
  - `enrichr_enrichment(gene_list, libraries)` — runs gene set enrichment against
    Enrichr libraries: ChEA3 for TF-target, GO/KEGG/Reactome for pathways,
    CellMarker for cell type validation
  - `omnipath_interactions(source_genes, target_genes, interaction_type)` —
    queries OmniPath for directed TF→target edges, ligand-receptor pairs,
    signaling interactions
  - `string_network(gene_list, species)` — checks whether a gene set forms a
    functionally connected PPI network (validates cluster coherence)
- **Invocation pattern**: DatabaseValidator first reads the ResultsInterpreter
  output to identify specific biological claims worth checking, then decides
  which database tools to call. It does not query databases blindly.
- **Output**: per-claim database evidence — supported / not found / contradicted,
  with source and confidence

---

### AnalyzerMediator (final round — single LLM call, no tools)
- Reads all three panelist outputs
- Synthesizes into the final Analyzer report

**Analyzer report format**:
```
results_summary:
  What was found in this phase — key quantitative results, what the figures
  show, which research plan steps succeeded or produced unexpected results.
  Written as a concise scientific summary.

hypothesis_status:
  Per hypothesis from the Scientist Panel's consensus:
    - supported: evidence consistent with hypothesis
    - refuted: evidence contradicts hypothesis
    - inconclusive: insufficient or contradictory evidence
  Include specific evidence for each status.

literature_context:
  How findings relate to prior work — confirmed, contradicted, or novel.
  Cite specific papers retrieved by LiteratureGrounder.

database_evidence:
  Per biological claim checked by DatabaseValidator:
    - claim: what was asserted
    - verdict: supported / not_found / contradicted
    - source: Enrichr ChEA / OmniPath / STRING
    - detail: specific evidence (e.g. "IRF4→TIGIT edge found in OmniPath
      with 3 supporting references")

future_directions:
  What the next phase should investigate, based on what was found.
  Specific and actionable — informs the Scientist Panel's update() call.

improvements:
  What could be done differently or better in a follow-up analysis.
  Method-level suggestions (e.g. "pseudobulking by donor before DE would
  strengthen the statistical claim").
```

---

## Round Structure

```
Round 1 — independent, parallel
  ResultsInterpreter  ──┐  reads dag_result + calls interpret_figure() per figure
  LiteratureGrounder  ──┤  retrieves literature relevant to findings
  DatabaseValidator   ──┘  reads ResultsInterpreter output, queries databases

Round 2 — AnalyzerMediator (single LLM call, no tools)
  reads all 3 Round 1 outputs
  → analyzer_report
```

No Reconciler. No confidence adjustment. Lighter structure than Scientist Panel
`formulate()`.

Note: DatabaseValidator depends on ResultsInterpreter's output to know what
claims to check. Run ResultsInterpreter first, then LiteratureGrounder and
DatabaseValidator in parallel in a second sub-round, then AnalyzerMediator.

---

## Tool Registry

### ResultsInterpreter tools

| Tool | Description |
|------|-------------|
| `retrieve_literature(base_query, background)` | Optional RAG — same pipeline as Scientist Panel panelists |
| `fetch_paper_section(paper_id, section_type)` | Drill into retrieved paper sections |
| `interpret_figure(figure_path)` | VLM call (GPT-4o vision) — reads a figure file and returns natural language interpretation. Input: absolute path to PNG/SVG. Output: description of what the figure shows, key patterns, notable features. |

### LiteratureGrounder tools

| Tool | Description |
|------|-------------|
| `retrieve_literature(base_query, background)` | Primary tool — retrieves papers relevant to specific findings |
| `fetch_paper_section(paper_id, section_type)` | Drills into paper sections |

### DatabaseValidator tools

| Tool | Description |
|------|-------------|
| `retrieve_literature(base_query, background)` | Optional |
| `enrichr_enrichment(gene_list, libraries)` | POST gene list to Enrichr API; returns top enriched terms from specified libraries. Libraries: `["ChEA_2022", "GO_Biological_Process_2023", "KEGG_2021_Human", "CellMarker_2024"]`. Returns ranked terms with p-value, adjusted p-value, overlap genes. |
| `omnipath_interactions(source_genes, target_genes, interaction_type)` | Query OmniPath REST API for directed interactions. `interaction_type`: `"tf_target"`, `"ligand_receptor"`, `"signaling"`. Returns interactions with supporting references and confidence scores. |
| `string_network(gene_list, species)` | Query STRING API for PPI network enrichment. Returns network enrichment p-value, average node degree, number of edges vs expected. Species: `9606` (human), `10090` (mouse). |

---

## interpret_figure Tool

The `interpret_figure` tool is a VLM call wrapping GPT-4o vision:

```
Input:
  figure_path: absolute path to PNG/SVG figure
  context: what this figure is supposed to show (from research plan
           required_visualizations) — helps the VLM focus

Output:
  {
    "description": "natural language description of what the figure shows",
    "key_patterns": ["list of notable patterns or findings"],
    "quality_flags": ["any concerns about figure quality or interpretability"],
    "supports_hypothesis": "yes | partial | no | unclear"
  }
```

The ResultsInterpreter calls this for each figure listed in
`required_visualizations` from the research plan. It can also call it for
unexpected figures found in the artifact directory.

---

## External Database APIs

### Enrichr
- Endpoint: `https://maayanlab.cloud/Enrichr/`
- Flow: POST gene list → get `userListId` → GET enrichment for each library
- No API key required
- Rate limit: reasonable for sequential calls per analysis
- Best for: TF-target (ChEA3), pathway (GO/KEGG/Reactome), cell type (CellMarker)

### OmniPath
- Endpoint: `https://omnipathdb.org/interactions`
- Parameters: `sources`, `targets`, `datasets` (e.g. `tf_target`, `ligrecextra`)
- No API key required
- Best for: directed TF→target edges with literature support, ligand-receptor pairs

### STRING
- Endpoint: `https://string-db.org/api/json/network`
- Parameters: `identifiers` (gene names), `species` (NCBI taxon ID)
- No API key required
- Best for: PPI network enrichment — validates whether a gene set is more
  connected than expected by chance (cluster coherence)

---

## Files to Build

| File | Description |
|------|-------------|
| `agents/analyzer_panel.py` | `AnalyzerPanel` class with `analyze()` method. Orchestrates 2-round flow. Round 1 runs ResultsInterpreter first, then LiteratureGrounder + DatabaseValidator in parallel. AnalyzerMediator synthesizes. |
| `agents/analyzer_tools.py` | Tool classes: `InterpretFigureTool`, `EnrichrEnrichmentTool`, `OmniPathInteractionsTool`, `StringNetworkTool`. Plus `build_results_interpreter_registry()`, `build_literature_grounder_registry()`, `build_database_validator_registry()`. |
| `prompts/analyzer_prompts.py` | Prompts for ResultsInterpreter, LiteratureGrounder, DatabaseValidator, AnalyzerMediator |
