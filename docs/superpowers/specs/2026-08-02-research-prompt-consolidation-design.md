# Research-subsystem prompt consolidation + refinement

Date: 2026-08-02
Status: Design — awaiting user review

## Goal

Collapse the two parallel prompt systems (`prompts/*.py` and `updated_prompts/*.md`) into a
**single source of truth in `prompts/*.py`** for the research-orchestration subsystem, and
**refine the prompt content** while doing so (dedupe repeated blocks, fold in the intent that
currently lives in the `.md` files, tighten wording to cut tokens).

Non-goal: touching the legacy agents' prompts (analyst, consultant, evaluator, generator, coder,
session_router, tool_consultant). Those stay as-is this pass.

## Decisions (from the user)

- Canonical location: **Python** (`prompts/*.py`). The `.md` files are deleted after their
  intent is folded into `.py`.
- Scope: **research subsystem only**.
- Depth: **consolidate + actively refine** the content.
- Shared panel output schema: a **Python string constant** composed into the role prompts
  (not the JSON file).
- Review order: **panelist + mediator first** as a pilot; user reviews the refinement style
  before the pattern is applied to the rest.

## Current state

The research subsystem loads most prompts from `updated_prompts/*.md` via
`agents/prompt_loader.load_updated_prompt(...)`; three modules already use `prompts/*.py`.
`scientist_panel.py` and `mediator_agent.py` each independently load the same four mediator
`.md` files (double-maintained). `scientist_panel_schemas.json` has a loader
(`load_scientist_panel_schemas`) that is never called; the panel output schema is instead
pasted inline into all three role prompts (~40 identical lines each). `adversary.md` and
`workflow.md` are orphaned (never loaded).

### Prompt inventory and how each is consumed

`.format()`-based (placeholder contract MUST be preserved exactly):

| Prompt (`.md`) | Consumed at | Placeholders |
|---|---|---|
| `paper_judge` | paper_judge.py:150 | role, retrieval_intent, retrieval_goal, base_query, doc_id, source, title, published, url, full_text_status, objective, background, analysis, method_and_dataset, main_findings, benchmark_methods, limitations, figure_captions, abstract |
| `paper_md_writer` | paper_md_writer.py:138 | doc_id, source, title, published, doi, url, full_text_status, objective, background, analysis, method_and_dataset, main_findings, benchmark_methods, limitations, figure_captions, abstract, retrieval_intent, retrieval_goal, evidence_contribution, covered_evidence_patterns, missing_evidence, source_ids, task_ids, existing_papers_summary |
| `paper_md_template` | paper_md_writer.py:343 | paper_id, title, doi, url, source_ids_yaml, full_text_status, tasks_yaml, extends_yaml, retrieval_intents_yaml, retrieval_goals_yaml, session, added, objective, background, analysis, method_and_dataset, key_findings, benchmark_methods, limitations, metrics_used, figure_captions, summary |
| `literature_paper_summary` | literature_retriever.py:530 | title, published, abstract, methods, results, discussion, figure_captions |
| `rag_context_paper_summary` | rag/agent.py:679 | title, published, abstract, methods, results, discussion, figure_captions |

Concatenation-based (no `.format()`; embedded JSON is literal text, so **no brace-escaping
needed** once in `.py`): `panelist_shared_system`, `{biologist,statistician,bioinformatician}_formulation`,
`panelist_callback`, `mediator_shared_system`, `mediator_formulation`, `mediator_post_analysis`,
`mediator_adversary_revision`, `analyzer`. System-string constants (`*_system`) are passed as
`system=`.

## Target architecture

New/kept modules under `prompts/`:

| Module | Constants | Source | Importers |
|---|---|---|---|
| `panelist_prompts.py` *(new)* | `PANELIST_SHARED_SYSTEM`, `BIOLOGIST_ROUND1_PROMPT`, `STATISTICIAN_ROUND1_PROMPT`, `BIOINFORMATICIAN_ROUND1_PROMPT`, `PANELIST_CALLBACK_PROMPT`, `PANEL_OUTPUT_SCHEMA` | `panelist_shared_system.md`, 3× `*_formulation.md`, `panelist_callback.md`, extracted schema | scientist_panel |
| `mediator_prompts.py` *(new)* | `MEDIATOR_SHARED_SYSTEM`, `MEDIATOR_FORMULATION_PROMPT`, `MEDIATOR_POST_ANALYSIS_PROMPT`, `MEDIATOR_ADVERSARY_REVISION_PROMPT` | `mediator_*.md` | scientist_panel **and** mediator_agent |
| `paper_prompts.py` *(new)* | `PAPER_JUDGE_SYSTEM`, `PAPER_JUDGE_PROMPT`, `PAPER_MD_WRITER_SYSTEM`, `PAPER_MD_WRITER_PROMPT`, `PAPER_MD_TEMPLATE` | `paper_judge*.md`, `paper_md_writer*.md`, `paper_md_template.md` | paper_judge, paper_md_writer |
| `literature_prompts.py` *(new)* | `LITERATURE_SUMMARY_SYSTEM`, `LITERATURE_SUMMARY_PROMPT`, `RAG_CONTEXT_PAPER_SUMMARY` | `literature_paper_summary*.md`, `rag_context_paper_summary.md` | literature_retriever, rag/agent |
| `analyzer_prompts.py` *(kept)* | fold `analyzer.md` into the existing constant; drop the `fallback=` load | `analyzer.md` + existing | analyzer_panel |
| `adversarial_prompts.py` *(kept)* | refine in place | existing | adversarial_panelist |
| `critic_prompts.py` *(kept)* | refine in place | existing | attributing_critic |

Each importing agent replaces its `load_updated_prompt(...)` lines with a normal
`from prompts.<module> import ...`.

## Refinement rules

1. **Extract the panel output schema once.** The ~40-line JSON schema triplicated across the
   role prompts becomes `PANEL_OUTPUT_SCHEMA` and is concatenated into each role prompt
   (roles are concat-composed, so this is a plain string join). Delete `scientist_panel_schemas.json`.
2. **Single mediator module.** `scientist_panel.py` and `mediator_agent.py` both import from
   `mediator_prompts.py` — the content exists once.
3. **Fold `.md` intent + tighten.** For each prompt, port the `.md` wording into the `.py`
   constant, then cut: restated boilerplate already in the shared-system constant, redundant
   phrasing, filler. Keep the task instruction sharp.

### Hard constraints (must not break)

- Preserve every `.format()` placeholder name in the table above — no additions, removals, or renames.
- For `.format()`-based prompts, keep literal JSON braces `{{ }}`-escaped. For concat-based
  prompts, braces are literal (do not escape).
- Preserve machine-readable output contracts: the panelist output schema keys, the mediator
  output tags (`<MEDIATOR>` / `<MEDIATOR_POST_ANALYSIS>` and the alias set the parsers accept),
  the judge JSON keys, and the paper front-matter keys. Refinement changes prose, not the
  contract the parsers read.

## Test migration

These tests import the `.md` system and must be rewired to the new `prompts/*.py` constants
(same content, so assertions hold):

- `tests/test_mediator_prompt_modes.py` → `mediator_prompts`, `panelist_prompts`
- `tests/test_scientist_panel_callbacks.py` → `mediator_prompts`, `panelist_prompts`
- `tests/test_analyzer_phase_update.py` → `analyzer_prompts`, `mediator_prompts`

## Cleanup (final step)

- Delete `updated_prompts/` research-subsystem `.md` files, `adversary.md`, `workflow.md`,
  `scientist_panel_schemas.json`.
- Remove `agents/prompt_loader.py` (`load_updated_prompt`, `load_scientist_panel_schemas`) once
  no importer remains.
- Grep-verify zero remaining references to `load_updated_prompt` / `updated_prompts` /
  `scientist_panel_schemas`.

## Execution batches

1. **Batch 1 (pilot):** `panelist_prompts.py` + `mediator_prompts.py`, rewire scientist_panel
   and mediator_agent, migrate the two affected tests, schema extraction. **User reviews style.**
2. **Batch 2:** `paper_prompts.py` + `literature_prompts.py`, rewire paper_judge,
   paper_md_writer, literature_retriever, rag/agent.
3. **Batch 3:** refine `analyzer_prompts.py` (fold `analyzer.md`), `adversarial_prompts.py`,
   `critic_prompts.py`; migrate `test_analyzer_phase_update`.
4. **Cleanup + verification.**

## Verification

- After each batch: `python -c "import <module>"` for touched agents resolves; every `.format()`
  call site still receives its full kwarg set (placeholder sets unchanged).
- Run the affected tests: `test_mediator_prompt_modes`, `test_scientist_panel_callbacks`,
  `test_scientist_panel_formulate`, `test_paper_md_writer`, `test_panelist_literature_tools`,
  `test_analyzer_phase_update`, `test_todo2_rag_contract`, `test_research_loop_*`.
- Final: grep shows no `load_updated_prompt` / `updated_prompts` references anywhere.

## Out of scope / deferred

- Legacy-agent prompts (analyst, consultant, evaluator, generator, coder, session_router,
  tool_consultant).
- The separate token-optimization work (fast-engine routing, iteration caps, cross-source
  dedup) discussed earlier — tracked separately.
