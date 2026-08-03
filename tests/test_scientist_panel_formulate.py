"""Test 1 — ScientistPanel.formulate() in isolation.

Question: "What major immune cell types are present in this healthy PBMC dataset?"

What this tests:
  - RAGStore connects to the existing chroma DB
  - LiteratureRetriever fetches papers via Semantic Scholar + OpenAlex (no PubMed)
  - PaperJudge filters papers by role-specific relevance
  - All 3 panelists run in parallel and produce <ROUND1> output
  - Reconciler identifies conflicts between panelists
  - Confidence adjustment runs without crashing
  - Mediator produces a valid research plan with steps + required_visualizations
  - All output files are written to results/test_formulate/

No DAG execution, no AnalyzerPanel, no loop — pure panel smoke test.

Run:
    source /Users/vickydong/Documents/scGraphETM/GraphSVX/venv/bin/activate
    cd /Users/vickydong/Documents/singlecell_Agent
    export OPENAI_API_KEY=sk-...
    PYTHONPATH=. python tests/test_scientist_panel_formulate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

INPUT_H5AD   = "data/pbmc_RNA_count.h5ad"
RAG_STORE_DIR = "rag_data"
RESULT_DIR   = "results/test_formulate"
ENGINE       = "gpt-4o"
FAST_ENGINE  = "gpt-4o-mini"

USER_QUESTION = (
    "What major immune cell types are present in this healthy PBMC scRNA-seq dataset, "
    "and do their proportions match what is expected from published human PBMC atlases?"
)

DATA_SUMMARY = {
    "n_cells": 9631,
    "n_genes": 29095,
    "tissue": "PBMC",
    "disease": "healthy donors",
    "modality": "scRNA-seq (10x Genomics multiome — RNA modality only)",
    "metadata_columns": {
        "domain":      "categorical tissue domain",
        "protocol":    "sequencing protocol",
        "dataset":     "batch/dataset identifier",
        "orig.ident":  "sample identifier",
        "percent.mt":  "mitochondrial gene percentage (already in obs)",
    },
    "notes": "No disease condition. No donor_id column — use dataset/orig.ident as batch proxy.",
}

# ── Setup ─────────────────────────────────────────────────────────────────────

def _check(condition: bool, label: str, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f"\n         {detail}" if detail and not condition else ""))
    if not condition:
        sys.exit(1)


def main() -> None:
    from openai import OpenAI
    from rag.store_backend import RAGStore
    from agents.scientist_panel import ScientistPanel

    client = OpenAI()

    print("=" * 60)
    print("TEST 1: ScientistPanel.formulate()")
    print(f"  Question : {USER_QUESTION[:80]}...")
    print(f"  Result dir: {RESULT_DIR}")
    print("=" * 60)

    # ── Init ──────────────────────────────────────────────────────────────────

    print("\n[1/2] Initialising RAGStore and ScientistPanel...")
    store = RAGStore(root_dir=RAG_STORE_DIR)
    panel = ScientistPanel(
        engine_name=ENGINE,
        fast_engine_name=FAST_ENGINE,
        rag_store=store,
        result_dir=RESULT_DIR,
        client=client,
    )
    print("       OK")

    # ── Run formulate() ───────────────────────────────────────────────────────

    print("\n[2/2] Running formulate() — ~3-5 min (parallel RAG + 4 LLM rounds)...")
    result = panel.formulate(
        user_question=USER_QUESTION,
        data_summary=DATA_SUMMARY,
        anchor_papers=[],
    )

    # ── Structural assertions ─────────────────────────────────────────────────

    print("\n── Checking output structure ──────────────────────────────────────")

    _check(isinstance(result, dict),
           "formulate() returns a dict")

    _check("parse_error" not in result,
           "No JSON parse error in mediator output",
           result.get("parse_error", ""))

    _check(bool(result.get("consensus_hypothesis")),
           "consensus_hypothesis is present and non-empty",
           str(result.get("consensus_hypothesis", ""))[:120])

    rp = result.get("research_plan", {})
    _check(isinstance(rp, dict),
           "research_plan is a dict")

    steps = rp.get("steps", [])
    _check(isinstance(steps, list) and len(steps) >= 3,
           f"research_plan.steps has ≥3 entries (got {len(steps)})",
           str(steps[:2]))

    viz = rp.get("required_visualizations", [])
    _check(isinstance(viz, list) and len(viz) >= 1,
           f"research_plan.required_visualizations has ≥1 entry (got {len(viz)})",
           str(viz))

    conf = result.get("panel_confidence")
    _check(isinstance(conf, (int, float)) and 0.0 <= float(conf) <= 1.0,
           f"panel_confidence is a valid float (got {conf})")

    _check(result.get("next_action") == "continue",
           f"next_action == 'continue' (got {result.get('next_action')!r})")

    # ── Check output files were written ───────────────────────────────────────

    print("\n── Checking output files ──────────────────────────────────────────")
    result_path = Path(RESULT_DIR)

    for fname in [
        "formulate_round1.json",
        "formulate_round2_reconciler.json",
        "formulate_round3.json",
        "formulate_round4_mediator.json",
    ]:
        _check((result_path / fname).exists(), f"{fname} written to disk")

    for role in ["biologist", "statistician", "bioinformatician"]:
        transcript = result_path / f"{role}_round1_transcript.jsonl"
        tool_trace = result_path / f"{role}_round1_tool_trace.jsonl"
        _check(transcript.exists(), f"{role} transcript exists")
        _check(tool_trace.exists(),  f"{role} tool trace exists")

        # Check at least one retrieve_literature call succeeded
        papers_found = 0
        with open(tool_trace) as f:
            for line in f:
                call = json.loads(line)
                if call.get("tool_name") == "retrieve_literature":
                    result_val = call.get("result", [])
                    if isinstance(result_val, list):
                        papers_found += len(result_val)
        _check(papers_found > 0,
               f"{role}: retrieve_literature returned ≥1 paper (got {papers_found})")

    # ── Check round1 outputs have expected tags ───────────────────────────────

    print("\n── Checking round1 content ────────────────────────────────────────")
    r1 = json.loads((result_path / "formulate_round1.json").read_text())
    for role in ["biologist", "statistician", "bioinformatician"]:
        text = r1.get(role, "")
        _check("<ROUND1>" in text and "</ROUND1>" in text,
               f"{role} round1 output contains <ROUND1> tag")

    # ── Summary ───────────────────────────────────────────────────────────────

    print("\n── Summary ────────────────────────────────────────────────────────")
    print(f"  Hypothesis  : {result['consensus_hypothesis'][:120]}")
    print(f"  Plan steps  : {len(steps)}")
    print(f"  Vis required: {len(viz)}")
    print(f"  Confidence  : {conf:.2f}")
    print(f"\n  Steps:")
    for i, s in enumerate(steps, 1):
        print(f"    {i}. {s[:100]}")
    print(f"\n  Required visualizations:")
    for v in viz:
        print(f"    - {v[:100]}")
    print(f"\n  Results saved to: {RESULT_DIR}/")
    print("\nALL CHECKS PASSED ✓")


if __name__ == "__main__":
    main()
