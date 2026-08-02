# Research-Subsystem Prompt Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the research subsystem's prompts from `updated_prompts/*.md` into `prompts/*.py` as the single source of truth, refining the content (dedupe, tighten) without changing agent behavior.

**Architecture:** Create four new `prompts/*.py` modules holding refined versions of the `.md` content, rewire each agent to import constants instead of calling `load_updated_prompt(...)`, migrate the tests that used the loader, then delete the `.md` system and the loader. The panel output schema — currently triplicated across the three role prompts — is extracted to a single `PANEL_OUTPUT_SCHEMA` string constant.

**Tech Stack:** Python, pytest. Prompts are module-level triple-quoted string constants.

## Global Constraints

- Preserve every `.format()` placeholder set exactly (no add/remove/rename). The authoritative sets are in the spec, [docs/superpowers/specs/2026-08-02-research-prompt-consolidation-design.md](docs/superpowers/specs/2026-08-02-research-prompt-consolidation-design.md), and repeated in each relevant task.
- `.format()`-based prompts keep literal JSON braces `{{ }}`-escaped; concat-composed prompts keep braces literal (single).
- Preserve machine-readable contracts unchanged: panelist output-schema keys, mediator output tags (`<MEDIATOR>`, `<MEDIATOR_POST_ANALYSIS>` and accepted aliases), judge JSON keys, paper front-matter keys.
- Source content comes from the named `updated_prompts/*.md` file; refinement edits prose only.
- Do NOT touch legacy-agent prompts (analyst, consultant, evaluator, generator, coder, session_router, tool_consultant).
- Refined constant content ports from the source `.md`; the test in each task locks the contract (placeholder set / required marker tokens) so refinement cannot silently break it.

---

## Batch 1 — panelist + mediator (pilot; user reviews style after)

### Task 1: Create `prompts/mediator_prompts.py`

**Files:**
- Create: `prompts/mediator_prompts.py`
- Source: `updated_prompts/mediator_shared_system.md`, `updated_prompts/mediator_formulation.md`, `updated_prompts/mediator_post_analysis.md`, `updated_prompts/mediator_adversary_revision.md`
- Test: `tests/test_prompt_contracts.py`

**Interfaces:**
- Produces: `MEDIATOR_SHARED_SYSTEM: str`, `MEDIATOR_FORMULATION_PROMPT: str`, `MEDIATOR_POST_ANALYSIS_PROMPT: str`, `MEDIATOR_ADVERSARY_REVISION_PROMPT: str` (all concat-composed; braces literal).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompt_contracts.py
import re

def test_mediator_prompts_contract():
    from prompts import mediator_prompts as m
    for name in ("MEDIATOR_SHARED_SYSTEM", "MEDIATOR_FORMULATION_PROMPT",
                 "MEDIATOR_POST_ANALYSIS_PROMPT", "MEDIATOR_ADVERSARY_REVISION_PROMPT"):
        val = getattr(m, name)
        assert isinstance(val, str) and val.strip(), f"{name} empty"
    # output tag contract used by the parsers must survive refinement
    assert "MEDIATOR_POST_ANALYSIS" in m.MEDIATOR_POST_ANALYSIS_PROMPT
    # post-analysis decision vocabulary the loop switches on
    for token in ("self_revise_plan", "continue_from_node_id"):
        assert token in m.MEDIATOR_POST_ANALYSIS_PROMPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompt_contracts.py::test_mediator_prompts_contract -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prompts.mediator_prompts'`

- [ ] **Step 3: Create the module**

Port each constant from its `.md` source into a triple-quoted string, then refine: remove any lines already stated in `MEDIATOR_SHARED_SYSTEM`, tighten wording. Keep the tag names and the `self_revise_plan`/`continue_from_node_id` vocabulary verbatim. Example skeleton:

```python
# prompts/mediator_prompts.py
"""Prompts for MediatorAgent (research subsystem). Single source of truth."""

MEDIATOR_SHARED_SYSTEM = """\
<ported + refined from updated_prompts/mediator_shared_system.md>
"""

MEDIATOR_FORMULATION_PROMPT = """\
<ported + refined from updated_prompts/mediator_formulation.md>
"""

MEDIATOR_POST_ANALYSIS_PROMPT = """\
<ported + refined from updated_prompts/mediator_post_analysis.md; keep the
<MEDIATOR_POST_ANALYSIS> tag and the self_revise_plan / continue_from_node_id keys>
"""

MEDIATOR_ADVERSARY_REVISION_PROMPT = """\
<ported + refined from updated_prompts/mediator_adversary_revision.md>
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompt_contracts.py::test_mediator_prompts_contract -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add prompts/mediator_prompts.py tests/test_prompt_contracts.py
git commit -m "feat: add prompts/mediator_prompts.py (consolidated from .md)"
```

### Task 2: Create `prompts/panelist_prompts.py` with extracted schema

**Files:**
- Create: `prompts/panelist_prompts.py`
- Source: `updated_prompts/panelist_shared_system.md`, `updated_prompts/{biologist,statistician,bioinformatician}_formulation.md`, `updated_prompts/panelist_callback.md`
- Test: `tests/test_prompt_contracts.py`

**Interfaces:**
- Produces: `PANELIST_SHARED_SYSTEM`, `BIOLOGIST_ROUND1_PROMPT`, `STATISTICIAN_ROUND1_PROMPT`, `BIOINFORMATICIAN_ROUND1_PROMPT`, `PANELIST_CALLBACK_PROMPT`, `PANEL_OUTPUT_SCHEMA` (all `str`, concat-composed, braces literal).

- [ ] **Step 1: Write the failing test**

```python
def test_panelist_prompts_contract():
    from prompts import panelist_prompts as p
    for name in ("PANELIST_SHARED_SYSTEM", "BIOLOGIST_ROUND1_PROMPT",
                 "STATISTICIAN_ROUND1_PROMPT", "BIOINFORMATICIAN_ROUND1_PROMPT",
                 "PANELIST_CALLBACK_PROMPT", "PANEL_OUTPUT_SCHEMA"):
        val = getattr(p, name)
        assert isinstance(val, str) and val.strip(), f"{name} empty"
    # schema keys the panelist-output parser reads must appear once, via the shared constant
    for key in ("intents", "papers_selected", "confidence", "novelty_type"):
        assert key in p.PANEL_OUTPUT_SCHEMA
    # each role prompt must embed the shared schema (composed in, not re-pasted)
    for role_prompt in (p.BIOLOGIST_ROUND1_PROMPT, p.STATISTICIAN_ROUND1_PROMPT,
                        p.BIOINFORMATICIAN_ROUND1_PROMPT):
        assert p.PANEL_OUTPUT_SCHEMA.strip() in role_prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompt_contracts.py::test_panelist_prompts_contract -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create the module**

Extract the ~40-line output-schema block (identical across the three `*_formulation.md` files, also in `scientist_panel_schemas.json`) into `PANEL_OUTPUT_SCHEMA`. Build each role prompt as role-specific text + the shared schema. Refine `PANELIST_SHARED_SYSTEM` to hold the boilerplate common to all roles.

```python
# prompts/panelist_prompts.py
"""Prompts for ScientistPanel panelists (research subsystem)."""

PANEL_OUTPUT_SCHEMA = """\
<the single output-schema block extracted from the three role prompts;
keys intents/papers_selected/confidence/novelty_type preserved verbatim>
"""

PANELIST_SHARED_SYSTEM = """\
<ported + refined from updated_prompts/panelist_shared_system.md>
"""

_BIOLOGIST_BODY = """\
<role-specific text from updated_prompts/biologist_formulation.md, schema removed>
"""
BIOLOGIST_ROUND1_PROMPT = _BIOLOGIST_BODY + "\n\n" + PANEL_OUTPUT_SCHEMA
# ...same pattern for statistician and bioinformatician...

PANELIST_CALLBACK_PROMPT = """\
<ported + refined from updated_prompts/panelist_callback.md>
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompt_contracts.py::test_panelist_prompts_contract -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add prompts/panelist_prompts.py tests/test_prompt_contracts.py
git commit -m "feat: add prompts/panelist_prompts.py with extracted PANEL_OUTPUT_SCHEMA"
```

### Task 3: Rewire `agents/mediator_agent.py`

**Files:**
- Modify: `agents/mediator_agent.py:26-29`

**Interfaces:**
- Consumes: the four constants from `prompts.mediator_prompts` (Task 1).

- [ ] **Step 1: Replace the loader lines**

Replace lines 26-29 (`MEDIATOR_* = load_updated_prompt(...)`) with:

```python
from prompts.mediator_prompts import (
    MEDIATOR_SHARED_SYSTEM,
    MEDIATOR_FORMULATION_PROMPT,
    MEDIATOR_ADVERSARY_REVISION_PROMPT,
    MEDIATOR_POST_ANALYSIS_PROMPT,
)
```

Remove the now-unused `load_updated_prompt` import if nothing else in the file uses it.

- [ ] **Step 2: Verify import resolves**

Run: `python -c "import agents.mediator_agent"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add agents/mediator_agent.py
git commit -m "refactor: mediator_agent imports prompts from mediator_prompts"
```

### Task 4: Rewire `agents/scientist_panel.py`

**Files:**
- Modify: `agents/scientist_panel.py:66-73`

**Interfaces:**
- Consumes: constants from `prompts.panelist_prompts` (Task 2) and `prompts.mediator_prompts` (Task 1).

- [ ] **Step 1: Replace the loader lines**

Replace lines 66-73 with imports:

```python
from prompts.panelist_prompts import (
    PANELIST_SHARED_SYSTEM,
    BIOLOGIST_ROUND1_PROMPT,
    STATISTICIAN_ROUND1_PROMPT,
    BIOINFORMATICIAN_ROUND1_PROMPT,
    PANELIST_CALLBACK_PROMPT,
)
from prompts.mediator_prompts import (
    MEDIATOR_SHARED_SYSTEM,
    MEDIATOR_FORMULATION_PROMPT,
    MEDIATOR_POST_ANALYSIS_PROMPT,
)
```

Remove the `load_updated_prompt` import if unused.

- [ ] **Step 2: Verify import resolves**

Run: `python -c "import agents.scientist_panel"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add agents/scientist_panel.py
git commit -m "refactor: scientist_panel imports prompts from panelist_/mediator_prompts"
```

### Task 5: Migrate Batch-1 tests off the loader

**Files:**
- Modify: `tests/test_mediator_prompt_modes.py:3,7-9`, `tests/test_scientist_panel_callbacks.py:5,8-9`

**Interfaces:**
- Consumes: `prompts.mediator_prompts`, `prompts.panelist_prompts`.

- [ ] **Step 1: Replace loader lines in test_mediator_prompt_modes.py**

```python
from prompts.mediator_prompts import MEDIATOR_FORMULATION_PROMPT, MEDIATOR_SHARED_SYSTEM
from prompts.panelist_prompts import PANELIST_SHARED_SYSTEM
```

- [ ] **Step 2: Replace loader lines in test_scientist_panel_callbacks.py**

```python
from prompts.mediator_prompts import MEDIATOR_FORMULATION_PROMPT
from prompts.panelist_prompts import PANELIST_CALLBACK_PROMPT
```

- [ ] **Step 3: Run both tests**

Run: `pytest tests/test_mediator_prompt_modes.py tests/test_scientist_panel_callbacks.py -v`
Expected: PASS (same assertions, content unchanged in contract).

- [ ] **Step 4: Commit**

```bash
git add tests/test_mediator_prompt_modes.py tests/test_scientist_panel_callbacks.py
git commit -m "test: migrate Batch-1 tests to prompts/*.py imports"
```

### Task 6: Batch-1 verification + style-review checkpoint

- [ ] **Step 1: Run the panelist/mediator-affected suite**

Run: `pytest tests/test_prompt_contracts.py tests/test_mediator_prompt_modes.py tests/test_scientist_panel_callbacks.py tests/test_scientist_panel_formulate.py tests/test_research_loop_phase1.py -v`
Expected: PASS (skip any that need an OpenAI client/network; they must still import cleanly).

- [ ] **Step 2: Confirm no loader references remain in Batch-1 files**

Run: `grep -rn "load_updated_prompt" agents/scientist_panel.py agents/mediator_agent.py tests/test_mediator_prompt_modes.py tests/test_scientist_panel_callbacks.py`
Expected: no output.

- [ ] **Step 3: STOP for user style review**

Present the two new modules for the user to review the refinement style before proceeding to Batch 2.

---

## Batch 2 — paper + literature

### Task 7: Create `prompts/paper_prompts.py`

**Files:**
- Create: `prompts/paper_prompts.py`
- Source: `updated_prompts/paper_judge_system.md`, `paper_judge.md`, `paper_md_writer_system.md`, `paper_md_writer.md`, `paper_md_template.md`
- Test: `tests/test_prompt_contracts.py`

**Interfaces:**
- Produces: `PAPER_JUDGE_SYSTEM`, `PAPER_JUDGE_PROMPT`, `PAPER_MD_WRITER_SYSTEM`, `PAPER_MD_WRITER_PROMPT`, `PAPER_MD_TEMPLATE`. The three non-system constants are `.format()`-based — braces in embedded JSON MUST be `{{ }}`.

- [ ] **Step 1: Write the failing test** (locks the exact placeholder sets)

```python
def test_paper_prompts_format_contract():
    from prompts import paper_prompts as p
    judge_keys = {"role","retrieval_intent","retrieval_goal","base_query","doc_id",
        "source","title","published","url","full_text_status","objective","background",
        "analysis","method_and_dataset","main_findings","benchmark_methods","limitations",
        "figure_captions","abstract"}
    writer_keys = {"doc_id","source","title","published","doi","url","full_text_status",
        "objective","background","analysis","method_and_dataset","main_findings",
        "benchmark_methods","limitations","figure_captions","abstract","retrieval_intent",
        "retrieval_goal","evidence_contribution","covered_evidence_patterns",
        "missing_evidence","source_ids","task_ids","existing_papers_summary"}
    template_keys = {"paper_id","title","doi","url","source_ids_yaml","full_text_status",
        "tasks_yaml","extends_yaml","retrieval_intents_yaml","retrieval_goals_yaml","session",
        "added","objective","background","analysis","method_and_dataset","key_findings",
        "benchmark_methods","limitations","metrics_used","figure_captions","summary"}
    # .format with every key present must not raise (placeholder set preserved, braces escaped)
    p.PAPER_JUDGE_PROMPT.format(**{k: "x" for k in judge_keys})
    p.PAPER_MD_WRITER_PROMPT.format(**{k: "x" for k in writer_keys})
    p.PAPER_MD_TEMPLATE.format(**{k: "x" for k in template_keys})
    assert p.PAPER_JUDGE_SYSTEM.strip() and p.PAPER_MD_WRITER_SYSTEM.strip()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompt_contracts.py::test_paper_prompts_format_contract -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create the module** — port + refine each prompt from its `.md`; double every literal JSON brace to `{{`/`}}`; keep exactly the placeholder names in the test.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompt_contracts.py::test_paper_prompts_format_contract -v`
Expected: PASS (a missing/renamed placeholder raises `KeyError`; an unescaped brace raises `KeyError`/`ValueError`)

- [ ] **Step 5: Commit**

```bash
git add prompts/paper_prompts.py tests/test_prompt_contracts.py
git commit -m "feat: add prompts/paper_prompts.py (consolidated from .md)"
```

### Task 8: Create `prompts/literature_prompts.py`

**Files:**
- Create: `prompts/literature_prompts.py`
- Source: `updated_prompts/literature_paper_summary_system.md`, `literature_paper_summary.md`, `rag_context_paper_summary.md`
- Test: `tests/test_prompt_contracts.py`

**Interfaces:**
- Produces: `LITERATURE_SUMMARY_SYSTEM`, `LITERATURE_SUMMARY_PROMPT`, `RAG_CONTEXT_PAPER_SUMMARY`. Both non-system prompts are `.format()`-based.

- [ ] **Step 1: Write the failing test**

```python
def test_literature_prompts_format_contract():
    from prompts import literature_prompts as p
    keys = {"title","published","abstract","methods","results","discussion","figure_captions"}
    p.LITERATURE_SUMMARY_PROMPT.format(**{k: "x" for k in keys})
    p.RAG_CONTEXT_PAPER_SUMMARY.format(**{k: "x" for k in keys})
    assert p.LITERATURE_SUMMARY_SYSTEM.strip()
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.
- [ ] **Step 3: Create the module** — port + refine; escape literal braces; keep the 7 placeholders.
- [ ] **Step 4: Run test to verify it passes.**
- [ ] **Step 5: Commit**

```bash
git add prompts/literature_prompts.py tests/test_prompt_contracts.py
git commit -m "feat: add prompts/literature_prompts.py (consolidated from .md)"
```

### Task 9: Rewire `agents/paper_judge.py` and `agents/paper_md_writer.py`

**Files:**
- Modify: `agents/paper_judge.py:33-34`, `agents/paper_md_writer.py:33-35`

- [ ] **Step 1: Replace loader lines**

In `paper_judge.py`:
```python
from prompts.paper_prompts import PAPER_JUDGE_SYSTEM as _JUDGE_SYSTEM_PROMPT, PAPER_JUDGE_PROMPT as _JUDGE_PROMPT
```
In `paper_md_writer.py`:
```python
from prompts.paper_prompts import PAPER_MD_WRITER_SYSTEM, PAPER_MD_WRITER_PROMPT, PAPER_MD_TEMPLATE
```
Remove `load_updated_prompt` imports if unused.

- [ ] **Step 2: Verify imports resolve**

Run: `python -c "import agents.paper_judge, agents.paper_md_writer"`
Expected: no error.

- [ ] **Step 3: Run paper tests**

Run: `pytest tests/test_paper_md_writer.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add agents/paper_judge.py agents/paper_md_writer.py
git commit -m "refactor: paper agents import prompts from paper_prompts"
```

### Task 10: Rewire `rag/literature_retriever.py` and `rag/agent.py`

**Files:**
- Modify: `rag/literature_retriever.py:133-134`, `rag/agent.py:111`

- [ ] **Step 1: Replace loader lines**

In `literature_retriever.py`:
```python
from prompts.literature_prompts import LITERATURE_SUMMARY_SYSTEM as _SUMMARY_SYSTEM, LITERATURE_SUMMARY_PROMPT as _SUMMARY_PROMPT
```
In `rag/agent.py`:
```python
from prompts.literature_prompts import RAG_CONTEXT_PAPER_SUMMARY as _PAPER_SUMMARY_PROMPT
```

- [ ] **Step 2: Verify imports resolve**

Run: `python -c "import rag.literature_retriever, rag.agent"`
Expected: no error.

- [ ] **Step 3: Run the rag contract test**

Run: `pytest tests/test_todo2_rag_contract.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add rag/literature_retriever.py rag/agent.py
git commit -m "refactor: rag retriever/agent import prompts from literature_prompts"
```

---

## Batch 3 — analyzer, adversarial, critic (refine kept `.py` modules)

### Task 11: Fold `analyzer.md` into `analyzer_prompts.py` and drop the fallback

**Files:**
- Modify: `prompts/analyzer_prompts.py`, `agents/analyzer_panel.py:64`, `tests/test_analyzer_phase_update.py:8,12-13`
- Source: `updated_prompts/analyzer.md`

- [ ] **Step 1: Fold + refine**

In `analyzer_prompts.py`, set `ANALYZER_MEDIATOR_PROMPT` to the refined content of `analyzer.md` (its production value today, since the loader used `analyzer.md` with the `.py` as fallback).

- [ ] **Step 2: Drop the loader in analyzer_panel.py**

Replace line 64 (`ANALYZER_MEDIATOR_PROMPT = load_updated_prompt("analyzer", fallback=ANALYZER_MEDIATOR_PROMPT)`) — keep only the import from `prompts.analyzer_prompts`; remove the `load_updated_prompt` line and import.

- [ ] **Step 3: Migrate the test**

In `test_analyzer_phase_update.py` replace the loader lines with:
```python
from prompts.analyzer_prompts import ANALYZER_MEDIATOR_PROMPT
from prompts.mediator_prompts import MEDIATOR_POST_ANALYSIS_PROMPT
```

- [ ] **Step 4: Run + commit**

Run: `pytest tests/test_analyzer_phase_update.py -v` → PASS
```bash
git add prompts/analyzer_prompts.py agents/analyzer_panel.py tests/test_analyzer_phase_update.py
git commit -m "refactor: fold analyzer.md into analyzer_prompts, drop loader fallback"
```

### Task 12: Refine `adversarial_prompts.py` in place

**Files:**
- Modify: `prompts/adversarial_prompts.py`

- [ ] **Step 1: Refine** — tighten wording, remove redundant blocks; keep the `role="adversary"` retrieval instructions and any output-tag contract the adversarial parser reads.
- [ ] **Step 2: Verify import + alignment test**

Run: `python -c "import agents.adversarial_panelist" && pytest tests/test_research_loop_tool_alignment.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add prompts/adversarial_prompts.py
git commit -m "refactor: refine adversarial_prompts wording"
```

### Task 13: Refine `critic_prompts.py` in place

**Files:**
- Modify: `prompts/critic_prompts.py`

- [ ] **Step 1: Refine** — keep the doubled `{{ }}` braces (critic prompt is `.format()`-ed) and the `CRITIC_SYSTEM`/`CRITIC_ATTRIBUTION_PROMPT` names.
- [ ] **Step 2: Verify**

Run: `python -c "import agents.attributing_critic"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add prompts/critic_prompts.py
git commit -m "refactor: refine critic_prompts wording"
```

---

## Batch 4 — cleanup + final verification

### Task 14: Delete the `.md` system and the loader

**Files:**
- Delete: all `updated_prompts/*.md`, `updated_prompts/scientist_panel_schemas.json`, `agents/prompt_loader.py`

- [ ] **Step 1: Confirm zero remaining references**

Run: `grep -rn "load_updated_prompt\|load_scientist_panel_schemas\|updated_prompts" --include='*.py' agents/ rag/ tests/`
Expected: no output. (If any appear, rewire them before deleting.)

- [ ] **Step 2: Delete the files**

```bash
git rm -r updated_prompts/ agents/prompt_loader.py
```

- [ ] **Step 3: Verify the subsystem imports**

Run: `python -c "import agents.scientist_panel, agents.mediator_agent, agents.paper_judge, agents.paper_md_writer, agents.analyzer_panel, agents.adversarial_panelist, agents.attributing_critic, rag.literature_retriever, rag.agent"`
Expected: no error.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove updated_prompts/*.md and prompt_loader after consolidation"
```

### Task 15: Full research-subsystem test run

- [ ] **Step 1: Run the full affected suite**

Run: `pytest tests/test_prompt_contracts.py tests/test_mediator_prompt_modes.py tests/test_scientist_panel_callbacks.py tests/test_scientist_panel_formulate.py tests/test_paper_md_writer.py tests/test_panelist_literature_tools.py tests/test_analyzer_phase_update.py tests/test_todo2_rag_contract.py tests/test_research_loop_phase1.py tests/test_research_loop_tool_alignment.py -v`
Expected: PASS (network-dependent tests may skip; all must import cleanly).

- [ ] **Step 2: Final grep gate**

Run: `grep -rn "load_updated_prompt\|updated_prompts\|scientist_panel_schemas" --include='*.py' .`
Expected: no output.

---

## Self-review notes

- **Spec coverage:** every `.md` in the spec's inventory maps to a task (mediator→T1, panelist+schema→T2, paper→T7, literature→T8, analyzer→T11, adversarial→T12, critic→T13); rewiring T3/T4/T9/T10/T11; test migration T5/T11; cleanup T14; verification T6/T15. `scientist_panel_schemas.json` removed in T14 (schema lives in `PANEL_OUTPUT_SCHEMA`, T2).
- **Placeholder preservation** is enforced by executable `.format(**keys)` tests (T7, T8) and the analyzer/critic imports, not by prose.
- **Contract markers** (tags, schema keys, decision vocabulary) asserted in T1/T2 tests.
