# Self-Evolving Agent — Architecture Gaps and Implementation Plan

The system is designed around three self-improvement mechanisms:
- **Self-questioning**: panelists that think like real scientists, challenged by an adversary
- **Self-navigating**: a planner that reads accumulated experience before designing a plan
- **Self-attributing**: a critic that attributes credit per step and writes lessons to memory

Each component below is ordered by dependency. Later phases build on earlier ones.

---

## Current State vs Target

| Module | Current | Gap |
|---|---|---|
| Workspace Profiler | Automated — reads h5ad, csv, tsv, loom | Done |
| Paper Wiki | Nothing | No structured literature graph; retrieval is keyword-only |
| PaperMDWriter | Nothing | No agent to write structured paper md files |
| Self-Questioning (2a, 2b) | Three-aspect reading + breadth→depth | Done |
| Self-Questioning (2c) | Panelists produce overlapping schemas | Complementary schemas not implemented |
| Scientific thinking | Panelists synthesize literature | Do not reason about novelty, falsifiability, causal mechanisms |
| AdversarialPanelist | Nothing | No challenge round; plans never stress-tested |
| Executor | DagExecutor — complete | Done |
| Self-Attributing Critic | AnalyzerPanel gives overall result | No per-step attribution; no lesson extraction |
| Short-term Memory | `session_state` flat dict | No phase trace; scientists only see latest result |
| Long-term Memory | Nothing | No compressed cross-session summaries |
| Self-Navigating Planner | Wiki-only planning | No experience-guided planning |
| Context Manager | `session_state` partial | No layered context, no evidence promotion, no compression |

---

## Gap 1: Workspace Profiler — DONE

`backend/workspace_profiler.py` reads all data files (h5ad, csv, tsv, loom) and extracts
structural facts automatically. User provides only biological context (tissue, disease,
modality, notes). Structural facts always come from the files.

**Interface:**
```python
ResearchLoop(
    input_h5ad_path="data/rna.h5ad",
    data_paths=["data/atac.h5ad", "data/metadata.csv"],
    data_summary={"tissue": "PBMC", "disease": "AD", "modality": "multiome"},
)
```

No changes needed.

---

## Gap 2: Self-Questioning

### 2a: Three-Aspect Literature Reading — DONE

Before drawing any conclusion from a paper, panelists extract:
1. **Background** — what context does the paper establish?
2. **Method/Dataset** — what was introduced, on what data/design?
3. **Analysis** — what research question did the paper actually answer? Does it apply here?

Rule: only recommend a method if the paper's Analysis aspect validates it for a similar
question on similar data.

### 2b: Breadth → Depth Retrieval — DONE

Panelists retrieve in two passes:
1. **Breadth** — broad queries to cover the domain
2. **Self-questioning** — what did retrieved papers leave unresolved?
3. **Depth** — targeted queries to fill the identified gaps

### 2c: Complementary Panelist Schemas + Scientific Thinking — PENDING

**Problem:** All three panelists produce the same fields (hypotheses, research_contributions,
required_visualizations). They synthesize literature rather than reasoning like scientists.
Plans replicate existing work rather than advancing beyond it.

**Root cause of the science problem:** A panelist that reads 10 papers and synthesizes them
produces a plan consistent with existing work — which by definition cannot beat it. A real
scientist works differently:
- Works backwards from a publishable claim
- Argues with papers rather than accepting their conclusions
- Asks what would falsify the hypothesis — not just what supports it
- Seeks the surprising finding, not the expected one
- Reasons about mechanism, not just association
- Asks: would a Nature reviewer find this novel?

**Fix — part 1: Distinct schemas per panelist**

Each panelist covers a non-overlapping domain. The Mediator synthesizes across all three.

**BiologistPanelist** — what to investigate:
```json
{
  "biological_context": "<what is established about this tissue/disease from literature>",
  "expected_biology": [
    {"cell_type_or_state": "...", "marker_evidence": "...", "source_paper": "..."}
  ],
  "hypotheses": [
    {
      "statement": "<specific testable claim>",
      "causal_story": "<if we observe X it implies Y mechanism because Z>",
      "falsification_criterion": "<what result would disprove this>",
      "expected_surprise": "<why this finding would be non-obvious to the field>",
      "supporting_evidence": "<paper or known fact>"
    }
  ],
  "biological_analyses": ["<what should be measured or tested>"],
  "required_visualizations": ["<figures needed to evaluate the hypothesis>"],
  "open_questions": [
    {"question": "...", "why_it_matters": "...", "expected_evidence": "..."}
  ],
  "confidence": 0.0
}
```

**StatisticianPanelist** — what makes results trustworthy:
```json
{
  "data_assessment": "<what this data structure permits and rules out statistically>",
  "required_controls": ["<what must be controlled: batch, donor, cell count imbalance, etc.>"],
  "recommended_tests": [
    {"analysis": "...", "test": "...", "rationale": "...", "minimum_sample_size": "..."}
  ],
  "validity_requirements": ["<minimum conditions for results to be trustworthy>"],
  "technical_flags": ["<concrete warnings derived from the data summary>"],
  "open_questions": [
    {"question": "...", "why_it_matters": "...", "expected_evidence": "..."}
  ],
  "confidence": 0.0
}
```

**BioinformaticianPanelist** — how to compute it:
```json
{
  "recommended_approach": "<abstract computational strategy — no tool names>",
  "method_rationale": "<why this approach fits this question and data scale>",
  "alternative_approaches": [
    {"approach": "...", "when_preferred": "..."}
  ],
  "known_risks": ["<failure modes of the recommended approach on this data type>"],
  "open_questions": [
    {"question": "...", "why_it_matters": "...", "expected_evidence": "..."}
  ],
  "confidence": 0.0
}
```

**Mediator synthesis:** each research plan step integrates all three perspectives:
```json
{
  "step_id": "...",
  "biological_goal": "<from biologist — what question this step answers>",
  "statistical_requirement": "<from statistician — what makes this step's result valid>",
  "computational_approach": "<from bioinformatician — how to execute it>",
  "novelty_statement": "<what existing literature has NOT shown that this step will answer>"
}
```

**Fix — part 2: Scientific thinking enforced in all prompts**

Every panelist prompt enforces:
- Papers must be argued with, not just summarized: each paper reading includes
  "what did this paper fail to control for? What alternative explanation does it leave open?"
- Every hypothesis requires `causal_story` and `falsification_criterion`
- Novelty framing: "What would be the most surprising finding this dataset could produce
  that no existing paper has demonstrated?"
- Publishability check: "Write the one-sentence abstract this analysis would produce.
  Would a senior reviewer find it novel?"

**Changes required:**
- `prompts/panelist_prompts.py` — new schemas for all three panelists, updated Mediator prompt
- `agents/scientist_panel.py` — updated parsing of role-specific schemas in
  `_run_round1_formulate()` and `_run_mediator_formulation()`

---

## Gap 3: Paper Wiki + PaperMDWriter + Hybrid Retrieval

**Problem:** Literature retrieval is purely keyword-based. Each session starts with no
knowledge of papers retrieved in prior sessions. Papers that are relevant but don't match
keywords are never found. There is no structured representation of what the literature
knows about each task.

### 3a: Paper Wiki Infrastructure

**Design:** A persistent graph of papers, parallel to the tool wiki. Both share the same
`task` nodes. The tool wiki answers "how to compute it"; the paper wiki answers "what the
literature knows about it."

```
task node (shared)
  ├── tool wiki:   → stage → method → tool
  └── paper wiki:  → paper → paper (via extends)
```

**Two edge types only:**
- `task → paper` — this paper is relevant to this task
- `paper → paper` (extends) — paper2 builds on the method or finding of paper1

**Directory structure:**
```
wiki/papers/
  _index.json          ← adjacency list, rebuilt at startup
  P001_scvi_lopez2018.md
  P002_harmony_korsunsky2019.md
  ...
```

**`_index.json` structure:**
```json
{
  "task_to_papers": {
    "cell_type_annotation": ["P001", "P004", "P007"],
    "batch_correction": ["P002", "P003", "P007"]
  },
  "paper_extends": {
    "P004": ["P001"],
    "P007": ["P002", "P003"]
  }
}
```

Built at startup by scanning all paper md files. Same pattern as tool wiki startup scan.

**Paper md file format:**
```markdown
---
paper_id: P042
title: "Deep generative modeling for single-cell transcriptomics"
tasks: [cell_type_annotation, batch_correction]
extends: [P015, P031]
added: 2026-05-09
session: S03
---

## Summary
2-3 sentence description of what the paper does and why it matters.

## Hypothesis framed
The specific claim or question this paper sets out to answer, stated as a hypothesis.

## Questions answered
- Does deep generative modeling outperform PCA for scRNA-seq embedding?
- Can variational autoencoders model technical noise across batches?

## Key findings
What the paper concluded, specifically — not what it introduced.

## Method and dataset
What method, on what data type, size, and experimental design.
What assumptions the method makes.

## Boundary conditions
Works when: n_cells > 10k, n_donors > 3, batch effect is present
Fails when: n_cells < 5k (overfits), single donor (no batch variable)
```

**Tasks in paper wiki use the same taxonomy as tool wiki task nodes.** No new task
categories are invented — papers link to existing task nodes.

### 3b: PaperMDWriter Agent

**Purpose:** Writes paper md files when new papers are fetched and judged relevant.
Identifies task links and paper-paper extends relationships. Updates the index.

**New files:**
- `agents/paper_md_writer.py`
- `prompts/paper_md_writer_prompts.py`

**Trigger:** after `PaperJudge` returns `relevant=True`, currently in
`rag/literature_retriever.py`. If a paper already has an md file (same paper_id),
skip — do not rewrite.

**Steps:**
1. Read paper content (abstract + available sections)
2. Identify which task nodes it belongs to — compare against tool wiki task taxonomy
3. Read md files of existing papers in wiki — identify which papers this one extends
   (same method advanced, same finding extended, same dataset reanalyzed)
4. Extract structured content via single LLM call using `PAPER_MD_WRITER_PROMPT`
5. Write md file to `wiki/papers/`
6. Update `_index.json`: add entry to `task_to_papers` for each task; add entry to
   `paper_extends` if extends relationships found

**Prompt output:**
```json
{
  "paper_id": "<first_author_lastname_year>",
  "tasks": ["<task_id_from_wiki>"],
  "extends": ["<paper_id_if_extends>"],
  "summary": "...",
  "hypothesis_framed": "...",
  "questions_answered": ["...", "..."],
  "key_findings": "...",
  "method_and_dataset": "...",
  "boundary_conditions": {
    "works_when": "...",
    "fails_when": "..."
  }
}
```

### 3c: Hybrid Retrieval

**Changes to:** `rag/literature_retriever.py`

Panelists now retrieve through two parallel channels:

```
retrieve(query, task):
  A. Keyword search             → entry point papers (current behavior via ChromaDB)
  B. Task → paper traversal     → all papers wiki already knows for this task
                                   (read from _index.json, load their md files)
  C. Paper → extends traversal  → follow extends edges from papers found in A and B
                                   (lazy — agent reads md file and decides to follow)
  → merge, deduplicate by paper_id, return ranked list
```

For A: existing keyword search over ChromaDB vector store — unchanged.
For B: lookup `_index.json["task_to_papers"][task]`, load md files.
For C: for each paper found, check `extends` field in frontmatter, load those md files.

The panelist reads md file content (not just abstract) at each hop and decides which
branches are relevant — same lazy graph reasoning as tool wiki traversal.

**Why this matters:** a paper that doesn't match keywords but is two hops from a
relevant paper via extends edges will now be found. Over time the graph covers the
relevant literature comprehensively; keyword search becomes the fallback for new territory.

---

## Gap 4: AdversarialPanelist

**Problem:** The ScientistPanel produces a draft plan with no challenge. Plans that
replicate existing work, repeat known agent failures, or contain methodological flaws
are never caught before execution. The adversarial panelist stress-tests the plan before
it is executed.

**Design:** A new panelist inserted into `formulate()` after the Reconciler produces
the draft plan. It runs a multi-round debate — challenging specific claims, triggering
targeted paper retrieval, and issuing verdicts. The debate continues until no
high-severity challenges remain or max rounds are reached.

**New files:**
- `agents/adversarial_panelist.py`
- `prompts/adversarial_prompts.py`

### Updated `formulate()` flow

```
Round 1:  BiologistPanelist + StatisticianPanelist + BioinformaticianPanelist
          (parallel, breadth→depth RAG + paper wiki traversal, new schemas)

Round 2:  Reconciler → draft consensus + draft research plan

[Adversarial loop — max 3 rounds]:

  Round A: AdversarialPanelist
    Input: draft research plan + data summary + task
    Step 1: Query long-term memory
            "Has the agent already established any of these findings?"
    Step 2: Traverse paper wiki from task node
            Read questions_answered in linked papers
            "Does existing literature already answer any of these claims?"
    Step 3: Targeted retrieval against specific claims in the plan
            For each step in plan: generate challenge queries
            e.g. "Treg depletion AD PBMC already published?"
            Retrieve and read papers via PaperMDWriter (new papers added to wiki)
    Step 4: For each claim, issue a challenge or clear it:
            {
              "claim": "<specific claim from plan>",
              "challenge_type": "already_in_agent_memory | already_in_literature |
                                 methodological_flaw | missing_control | not_novel_enough",
              "evidence": "<paper title or memory session ID>",
              "severity": "high | medium | low",
              "specific_concern": "<what exactly is wrong>"
            }
    Step 5: Issue overall verdict:
            "unsalvageable" — core finding already established (in memory or literature)
                              redirect: build on this finding, do not re-derive it
            "needs_revision" — specific claims need strengthening, plan salvageable
            "survives"       — plan advances beyond what is known

  Round B (if verdict is needs_revision):
    Original panelists respond to specific challenges (parallel)
    Each panelist addresses only challenges in their domain
    Can retrieve new papers to counter or concede
    Plan revised by Mediator

  Repeat Round A → Round B until: no high-severity challenges, or max 3 rounds

Round final: Mediator formulates plan that has survived adversarial scrutiny
  Each step includes novelty_statement: what no existing paper or agent memory has shown
```

### What the adversary thinks about

The adversary simulates Reviewer #2 — not just "find a paper that does this" but:
- Is this question actually important, or just technically feasible?
- Is the conclusion already implied by existing work, even if not explicitly shown?
- Is the proposed method chosen because it is best, or because it is familiar?
- What alternative explanation would a skeptic give for the expected result?
- What is the causal story — does the proposed analysis actually test the mechanism?
- What would make this result not generalize?
- Has the agent already established this in a prior session (check long-term memory)?

### Unsalvageable verdict

When the adversary issues `unsalvageable`:
- The plan is not retried — it is redirected
- The redirect output states: what is already known + what the next open question is
- The ScientistPanel reformulates starting from the established finding, not from scratch
- This prevents the agent from re-deriving what it or the field already knows

---

## Gap 5: Executor — DONE

DagExecutor is implemented with automatic output forwarding, auto-wiring, caching,
multi-path execution, and structured execution records per step.

No changes needed for the self-evolving architecture.

---

## Gap 6: Self-Attributing Critic

**Problem:** AnalyzerPanel evaluates the overall result. It cannot say which specific
step was the key contribution vs. wasted effort. Without step-level attribution,
lessons cannot be extracted for memory.

**New file:** `agents/attributing_critic.py`

**Interface:**
```python
class AttributingCritic:
    def attribute(
        self,
        *,
        stage_results: dict,       # from DagExecutor — all step outputs
        research_plan: dict,       # what each step was trying to achieve
        prior_phase_metrics: dict, # metrics from previous phase for comparison
        phase_number: int,
    ) -> dict:
        # returns per-step attributions + lesson candidates
```

**Per-step attribution schema:**
```json
{
  "step_id": "rna_cluster_leiden",
  "judgment": "GOOD | BAD | NEEDS_REVISION",
  "contribution_score": 0.78,
  "reason": "<specific explanation tied to metrics or biological interpretation>",
  "what_changed_from_prior_phase": "<if phase > 1>",
  "effect_of_change": "<quantified improvement or regression>",
  "issues": ["<specific problem if BAD or NEEDS_REVISION>"],
  "lesson_candidate": {
    "when_to_use": "<conditions under which this lesson applies>",
    "content": "<what to do or avoid>",
    "boundary_conditions": "<data characteristics that determine applicability>",
    "confidence": 0.7
  }
}
```

**Contribution score:** computed from metric delta between phases where available
(ARI, bio_lisi, batch_lisi, marker_specificity). For steps with no comparable prior
metric, score is LLM-judged from result quality.

**What changes in `agents/research_loop.py`:**
After `AnalyzerPanel.analyze()`, call `AttributingCritic.attribute()`.
Attributions written to short-term memory (Gap 7).
Lesson candidates passed to long-term memory write path (Gap 8).

**Why this matters:**
Without critic: "The analysis produced 7 clusters."
With critic: "Leiden at resolution 0.5 produced interpretable clusters (GOOD, +0.13 ARI).
             Harmony batch correction (GOOD, +0.24 batch_lisi). scVI embedding overfit
             on this small dataset (BAD — use PCA instead for n_cells < 5k)."

---

## Gap 7: Short-Term Memory

**Problem:** `session_state` is a flat dict that only carries the latest result.
Scientists in `update()` only see the current phase output. They cannot reason about
what failed two phases ago, what each change produced, or what the trajectory of
improvement has been. Plans repeat mistakes that occurred earlier in the same session.

**New file:** `agents/short_term_memory.py`

**Scope:** one session, all phases. Lives for the duration of a session.
At session end, compressed into long-term memory (Gap 8).

**Per-phase record:**
```json
{
  "session_id": "S03",
  "phase": 2,
  "research_plan": { "steps": [...] },
  "what_changed_from_prior_phase": "switched PCA embedding → scVI",
  "dag_result": { "best_path": "...", "stage_results": { ... } },
  "metrics": { "ARI": 0.82, "bio_lisi": 0.71, "batch_lisi": 0.55 },
  "what_improved": "ARI +0.17 — embedding quality improved",
  "what_remained_problematic": "batch_lisi still low — batch not resolved",
  "step_attributions": [ ... ],
  "analyzer_report": "...",
  "open_questions": [
    {"question": "...", "why_it_matters": "...", "expected_evidence": "..."}
  ]
}
```

**What each agent reads from short-term memory:**

| Agent | What it reads | Why |
|---|---|---|
| ScientistPanel update() | Full phase trace — all prior phases | Know what failed, what improved, what's still open |
| AdversarialPanelist | Prior phase plans + results | "We tried this in phase 2, it failed because X" |
| AnalyzerPanel | Prior phase metrics | Compare current result to trajectory, not just latest |
| AttributingCritic | Prior phase metrics per step | Compute contribution score as delta from prior |

**Short-term memory replaces** the current ad-hoc use of `session_state` for within-session
trajectory tracking. `session_state` retains h5ad paths and artifact pointers; short-term
memory handles the scientific reasoning trail.

---

## Gap 8: Long-Term Memory

**Problem:** No memory persists across sessions. Every new session starts from scratch —
the agent cannot build on its own prior discoveries, avoid known failures, or let users
continue prior work.

**New file:** `agents/long_term_memory.py`

**Design:** Long-term memory is a compressed summary of short-term memory. At the end
of each session, an LLM compression pass over the full short-term phase trace extracts
the essential record. Long-term memory grows as a chain of compressed sessions on the
same question.

### Compression step

Triggered at session end. Single LLM call over the full short-term trace.

**Compressed session record:**
```json
{
  "session_id": "S03",
  "question": "What cell types drive inflammation in this IBD PBMC dataset?",
  "task": "cell_type_annotation",
  "data_characteristics": {
    "modality": "multiome", "n_cells": 45000, "n_donors": 6, "tissue": "PBMC"
  },
  "best_finding": "Regulatory T cells specifically depleted in active IBD vs. remission",
  "best_method_path": "scVI embedding → BBKNN batch correction → Leiden 0.3",
  "key_decision_points": [
    {
      "phase": 2,
      "change": "PCA → scVI",
      "effect": "ARI +0.17, embedding structure improved"
    },
    {
      "phase": 3,
      "change": "added BBKNN post-embedding",
      "effect": "batch_lisi +0.24, biological signal preserved"
    }
  ],
  "boundary_conditions": [
    "scVI failed in S07 on n_cells < 5k — fall back to PCA"
  ],
  "open_questions": [
    "Cluster 8 identity unresolved — needs matched protein data to confirm"
  ],
  "lesson_candidates": [
    {
      "when_to_use": "PBMC multiome with >3 donors and visible batch effect",
      "content": "scVI → BBKNN → Leiden 0.3 is the reliable path",
      "confidence": 0.81
    }
  ],
  "confidence": 0.73,
  "continues_from": "S01",
  "date": "2026-05-09"
}
```

**Confidence update across sessions:** when the same finding is confirmed in a later
session, confidence increases. When it fails to replicate, boundary conditions narrow.
Long-term memory is a living belief system, not a static archive.

### Session continuation

User says: "continue from session S03"
- Long-term summary for S03 loaded as starting context for ScientistPanel.formulate()
- Scientists know what is already established → design to advance beyond it
- Adversarial panelist reads the same summary → blocks plans that re-derive S03's findings
- New short-term memory starts fresh for the continuation session
- At end of continuation: short-term compressed into new long-term record linked via
  `continues_from: S03`

### What each agent reads from long-term memory

| Agent | What it reads | Why |
|---|---|---|
| ScientistPanel formulate() | Compressed summaries for similar questions | Know what is established, what remains open |
| AdversarialPanelist | Best findings from prior sessions | "Agent already established this in S03" → unsalvageable |
| ToolConsultant | Best method paths + boundary conditions | Start planning near the known good path |

**Storage:** JSON files in `memory/long_term/`, one file per session record.
Retrieval: keyword match over `question` + `task` + `data_characteristics` fields.
Later: embedding-based semantic retrieval for cross-task generalization.

---

## Gap 9: Self-Navigating Planner

**Problem:** ToolConsultant plans purely from the tool wiki on every run. It has no
memory of what was tried before, what succeeded, what failed, or which strategies work
for which question types. Every plan starts from scratch.

**Changes to:** `agents/tool_consultant.py`, `prompts/tool_consultant_prompts.py`

**Updated planning flow:**
```
Before planning:
  1. Query long-term memory — sessions with similar task + data characteristics
  2. Retrieve: best method path, boundary conditions, lesson candidates
  3. Inject as "prior experience" block into the planning prompt

Planning:
  Vanilla plan  — from tool wiki + research plan (current behavior)
  Experience context — prior method paths and lessons injected
  → Merged plan: ToolConsultant synthesizes both, prefers experience-validated paths
    where data characteristics match, deviates where they don't with explicit justification
```

**Experience context format injected into prompt:**
```
PRIOR EXPERIENCE (from long-term memory):
Session S03 — similar question, PBMC multiome, 6 donors:
  Best path: scVI → BBKNN → Leiden 0.3 (ARI 0.84)
  Key lesson: PCA was insufficient; scVI embedding was the key improvement
  Boundary: scVI works here because n_cells > 10k and n_donors > 3
  Open: cluster 8 unresolved

Session S07 — similar question, PBMC RNA, 2 donors:
  scVI failed (n_cells 3k) — used PCA + Harmony instead (ARI 0.71)
  Lesson: fall back to PCA when n_cells < 5k
```

ToolConsultant reads data characteristics from workspace profile and selects the
experience most applicable to current data before planning.

---

## Gap 10: Context Manager

**Problem:** `session_state` is a flat dict. As sessions grow across phases, key findings
get buried under tool traces. The LLM's effective working memory of prior phases degrades.
There is no distinction between established fact, active hypothesis, and discarded
possibility.

**New file:** `agents/context_manager.py`

**Layered structure:**

| Layer | Content | Managed by | Stability |
|---|---|---|---|
| Workspace | Data files, profiler output, tool inventory | WorkspaceProfiler | Fixed at session start |
| Task | Current question and objective | ResearchLoop | Fixed at session start |
| Evidence | Findings promoted from hypothesis to established fact | AnalyzerPanel | Grows across phases |
| Hypotheses | Active hypotheses and current status | ScientistPanel | Changes each phase |
| Memory | Long-term summaries loaded for this session | LongTermMemory | Fixed at session start |
| Critique | Per-step attributions from prior phase | AttributingCritic | Updated each phase |

**Interface:**
```python
class ContextManager:
    def promote_to_evidence(self, finding: dict, confidence: float): ...
        # moves finding from hypotheses to evidence layer

    def mark_as_warning(self, step_id: str, reason: str): ...
        # flags a step result as a known risk for the next phase

    def compress(self, phase_number: int): ...
        # summarizes old phase details, retains key evidence
        # prevents context from growing unbounded across phases

    def to_prompt_str(self) -> str: ...
        # renders the layered context into a compact string for LLM injection
        # evidence layer always in foreground; old hypotheses compressed
```

**Migration:** `session_state` dict replaced by ContextManager across:
- `agents/research_loop.py`
- `agents/session_dispatcher.py`
- `frontend/server.py`

`session_state` retains h5ad paths and artifact pointers (non-scientific state).
ContextManager handles the scientific reasoning trail.

---

## Self-Improvement Cycle

Once Gaps 6–9 are implemented:

```
Execute
  → AttributingCritic attributes per step        (Gap 6)
    → lessons written to short-term memory        (Gap 7)
      → session ends, compressed to long-term     (Gap 8)
        → ToolConsultant reads long-term          (Gap 9)
          → AdversarialPanelist reads long-term   (Gap 4)
            → better plan designed
              → Execute
```

Each cycle makes the planner start closer to the optimal path, makes the adversary
better at catching re-derivations, and makes the scientists aware of what remains
genuinely open. The agent accumulates a growing scientific knowledge base from its
own experiments — not just from external literature.

---

## Paper Wiki — Literature Knowledge Base

The paper wiki and long-term memory serve distinct but complementary roles:

| | Paper wiki | Long-term memory |
|---|---|---|
| Stores | External literature | Agent's own experimental results |
| Written by | PaperMDWriter (Gap 3b) | Compression of short-term (Gap 8) |
| Read by | Panelists during retrieval | Panelists, adversary, planner |
| Grows | As papers are fetched | As sessions complete |
| Queried by | Task node traversal + keyword | Keyword + data characteristics match |

Together they tell the agent: "here is what the field knows, and here is what we have
discovered ourselves."

---

## Dependency Graph

```
Gap 1  (Workspace Profiler)       — done, no changes
Gap 3a (Paper Wiki infra)         — standalone, build first
Gap 3b (PaperMDWriter)            — needs 3a
Gap 3c (Hybrid Retrieval)         — needs 3a, 3b
Gap 2c (Complementary Schemas)    — needs 3c (panelists use new retrieval)
Gap 4  (AdversarialPanelist)      — needs 3c, 2c, and Gap 8 read path
Gap 6  (AttributingCritic)        — needs 2c (panel produces richer output)
Gap 7  (Short-term Memory)        — needs 6
Gap 8  (Long-term Memory)         — needs 7 (compresses it)
Gap 9  (Self-Navigating Planner)  — needs 8
Gap 10 (Context Manager)          — needs all, do last
```

Self-improvement cycle closes when Gap 8 is complete:
```
Execute → Critic (6) → Short-term (7) → Long-term (8) → Planner (9) + Adversary (4) → Execute
```

---

## Implementation Order

| Phase | Component | New files | Status |
|---|---|---|---|
| — | Gap 1: Workspace Profiler | `backend/workspace_profiler.py` | Done |
| — | Gap 2a, 2b: Three-aspect reading, breadth→depth | `prompts/panelist_prompts.py` | Done |
| 1 | Gap 3a: Paper wiki infrastructure | `wiki/papers/`, `wiki/papers/_index.json` | Pending |
| 2 | Gap 3b: PaperMDWriter agent | `agents/paper_md_writer.py`, `prompts/paper_md_writer_prompts.py` | Pending |
| 3 | Gap 3c: Hybrid retrieval | `rag/literature_retriever.py` (update) | Pending |
| 4 | Gap 2c: Complementary schemas + scientific thinking | `prompts/panelist_prompts.py` (update), `agents/scientist_panel.py` (update) | Pending |
| 5 | Gap 4: AdversarialPanelist | `agents/adversarial_panelist.py`, `prompts/adversarial_prompts.py` | Pending |
| 6 | Gap 6: AttributingCritic | `agents/attributing_critic.py`, `prompts/critic_prompts.py` | Pending |
| 7 | Gap 7: Short-term memory | `agents/short_term_memory.py` | Pending |
| 8 | Gap 8: Long-term memory | `agents/long_term_memory.py` | Pending |
| 9 | Gap 9: Self-Navigating Planner | `agents/tool_consultant.py` (update), `prompts/tool_consultant_prompts.py` (update) | Pending |
| 10 | Gap 10: Context Manager | `agents/context_manager.py` | Pending |
