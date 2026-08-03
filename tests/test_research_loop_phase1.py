"""Test 2 — ResearchLoop end-to-end (max_phases=1).

Question: "What are the major T cell subpopulations in this healthy PBMC dataset,
and how does their clustering stability compare across different Leiden resolutions?"

What this tests:
  - ScientistPanel.formulate() produces a valid research_plan
  - ToolConsultantAgent.decide() produces a dag_plan or implementation_plan
  - DagExecutor.execute() (or CoderAgent.run()) runs without crashing
  - AnalyzerPanel.analyze() produces a report with results_summary + claim_updates
  - Mediator post-analysis decision produces a valid decision
  - All loop-level JSON bookkeeping files are written to results/test_loop/

One phase only — validates the full wiring, not the science.

Run:
    source /Users/vickydong/Documents/scGraphETM/GraphSVX/venv/bin/activate
    cd /Users/vickydong/Documents/singlecell_Agent
    export OPENAI_API_KEY=sk-...
    PYTHONPATH=. python tests/test_research_loop_phase1.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

INPUT_H5AD    = "data/pbmc_RNA_count.h5ad"
RAG_STORE_DIR = "rag_data"
RESULT_DIR    = "results/test_loop"
ENGINE        = "gpt-4o"
FAST_ENGINE   = "gpt-4o-mini"

USER_QUESTION = (
    "What are the major T cell subpopulations in this healthy PBMC dataset, "
    "and how does their clustering stability compare across different Leiden resolutions?"
)

DATA_SUMMARY = {
    "n_cells": 9631,
    "n_genes": 29095,
    "tissue": "PBMC",
    "disease": "healthy donors",
    "modality": "scRNA-seq (10x Genomics multiome — RNA modality only)",
    "metadata_columns": {
        "domain":     "categorical tissue domain",
        "protocol":   "sequencing protocol",
        "dataset":    "batch/dataset identifier",
        "orig.ident": "sample identifier",
        "percent.mt": "mitochondrial gene percentage (already in obs)",
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
    from backend import SingleCellBackend
    from rag.store_backend import RAGStore
    from agents.scientist_panel import ScientistPanel
    from agents.analyzer_panel import AnalyzerPanel
    from agents.tool_consultant import ToolConsultantAgent
    from agents.dag_executor import DagExecutor
    from agents.research_loop import ResearchLoop

    client  = OpenAI()
    backend = SingleCellBackend()

    print("=" * 60)
    print("TEST 2: ResearchLoop — 1 phase end-to-end")
    print(f"  Question : {USER_QUESTION[:80]}...")
    print(f"  Result dir: {RESULT_DIR}")
    print("=" * 60)

    # ── Init ──────────────────────────────────────────────────────────────────

    print("\n[1/2] Initialising all components...")
    store = RAGStore(root_dir=RAG_STORE_DIR)

    scientist_panel = ScientistPanel(
        engine_name=ENGINE,
        fast_engine_name=FAST_ENGINE,
        rag_store=store,
        result_dir=RESULT_DIR + "/scientist",
        client=client,
    )
    analyzer_panel = AnalyzerPanel(
        engine_name=ENGINE,
        fast_engine_name=FAST_ENGINE,
        rag_store=store,
        result_dir=RESULT_DIR + "/analyzer",
        client=client,
    )
    tool_consultant = ToolConsultantAgent(
        engine_name=ENGINE,
        result_dir=RESULT_DIR,
        client=client,
    )
    dag_executor = DagExecutor(
        backend=backend,
        result_dir=RESULT_DIR + "/dag",
    )

    loop = ResearchLoop(
        scientist_panel=scientist_panel,
        analyzer_panel=analyzer_panel,
        tool_consultant=tool_consultant,
        dag_executor=dag_executor,
        input_h5ad_path=INPUT_H5AD,
        data_summary=DATA_SUMMARY,
        result_dir=RESULT_DIR,
        max_phases=1,
    )
    print("       OK")

    # ── Run loop ──────────────────────────────────────────────────────────────

    print("\n[2/2] Running ResearchLoop — ~10-20 min (formulate + consult + execute + analyze + update)...")
    result = loop.run(user_question=USER_QUESTION)

    # ── Structural assertions ─────────────────────────────────────────────────

    print("\n── Checking top-level return value ────────────────────────────────")

    _check(isinstance(result, dict),
           "run() returns a dict")

    _check("status" in result,
           "result has 'status' key",
           str(result.keys()))

    _check(result.get("status") in ("done", "abstain", "max_phases_reached"),
           f"status is valid (got {result.get('status')!r})")

    _check("final_report" in result and isinstance(result["final_report"], dict),
           "final_report is a dict")

    _check(result.get("phases_completed", 0) >= 1,
           f"phases_completed >= 1 (got {result.get('phases_completed')})")

    phase_log = result.get("phase_log", [])
    _check(isinstance(phase_log, list) and len(phase_log) >= 1,
           f"phase_log has >= 1 entry (got {len(phase_log)})")

    # ── Check bookkeeping files ───────────────────────────────────────────────

    print("\n── Checking loop bookkeeping files ────────────────────────────────")
    result_path = Path(RESULT_DIR)

    _check((result_path / "phase0_formulate.json").exists(),
           "phase0_formulate.json written")

    _check((result_path / "phase1_decision.json").exists(),
           "phase1_decision.json written")

    _check((result_path / "phase1_dag_result.json").exists(),
           "phase1_dag_result.json written")

    _check((result_path / "phase1_analyzer_report.json").exists(),
           "phase1_analyzer_report.json written")

    _check((result_path / "phase1_update.json").exists(),
           "phase1_update.json written")

    # ── Check phase0 formulate content ───────────────────────────────────────

    print("\n── Checking phase0 formulate content ──────────────────────────────")
    p0 = json.loads((result_path / "phase0_formulate.json").read_text())

    _check(bool(p0.get("consensus_hypothesis")),
           "phase0: consensus_hypothesis present",
           str(p0.get("consensus_hypothesis", ""))[:120])

    rp = p0.get("research_plan", {})
    _check(isinstance(rp, dict) and isinstance(rp.get("steps"), list) and len(rp.get("steps", [])) >= 2,
           f"phase0: research_plan.steps has >=2 entries (got {len(rp.get('steps', []))})")

    # ── Check phase1 decision content ────────────────────────────────────────

    print("\n── Checking phase1 ToolConsultant decision ─────────────────────────")
    p1_dec = json.loads((result_path / "phase1_decision.json").read_text())

    has_dag  = isinstance(p1_dec.get("dag_plan"), dict)
    has_impl = isinstance(p1_dec.get("implementation_plan"), dict)
    _check(has_dag or has_impl,
           f"phase1 decision has dag_plan or implementation_plan (dag={has_dag}, impl={has_impl})",
           json.dumps(list(p1_dec.keys())))

    if has_dag:
        dag = p1_dec["dag_plan"]
        _check(isinstance(dag.get("layers"), list) and len(dag["layers"]) >= 1,
               f"dag_plan has >=1 layer (got {len(dag.get('layers', []))})")
        print(f"       dag_plan stages: {[l.get('stage') for l in dag.get('layers', [])]}")

    # ── Check phase1 dag result content ──────────────────────────────────────

    print("\n── Checking phase1 execution result ───────────────────────────────")
    p1_dag = json.loads((result_path / "phase1_dag_result.json").read_text())

    _check("status" in p1_dag,
           "phase1 dag_result has 'status' key",
           str(list(p1_dag.keys())[:8]))

    exec_status = p1_dag.get("status", "")
    print(f"       Execution status: {exec_status!r}")
    # We accept completed or failed — the loop should handle both gracefully
    _check(isinstance(exec_status, str) and len(exec_status) > 0,
           f"phase1 dag_result.status is a non-empty string (got {exec_status!r})")

    # ── Check phase1 analyzer report ─────────────────────────────────────────

    print("\n── Checking phase1 AnalyzerPanel report ───────────────────────────")
    p1_rep = json.loads((result_path / "phase1_analyzer_report.json").read_text())

    _check(isinstance(p1_rep, dict),
           "phase1 analyzer_report is a dict")

    _check("parse_error" not in p1_rep,
           "No JSON parse error in analyzer mediator output",
           p1_rep.get("parse_error", ""))

    _check(bool(p1_rep.get("results_summary") or p1_rep.get("raw")),
           "phase1 analyzer_report has results_summary (or raw fallback)",
           str(list(p1_rep.keys())[:8]))

    claim_updates = p1_rep.get("claim_updates", "")
    _check(
        (isinstance(claim_updates, str) and len(claim_updates) > 0)
        or (isinstance(claim_updates, list) and len(claim_updates) > 0)
        or (isinstance(claim_updates, dict) and claim_updates),
        f"phase1 claim_updates is non-empty (got {claim_updates!r})"
    )

    # ── Check phase1 update result ────────────────────────────────────────────

    print("\n── Checking phase1 ScientistPanel update ───────────────────────────")
    p1_upd = json.loads((result_path / "phase1_update.json").read_text())

    _check(isinstance(p1_upd, dict),
           "phase1 update result is a dict")

    _check("parse_error" not in p1_upd,
           "No JSON parse error in update mediator output",
           p1_upd.get("parse_error", ""))

    decision_type = p1_upd.get("decision_type") or p1_upd.get("decision")
    _check(decision_type in ("accept_and_conclude", "call_panelists", "self_revise_plan", "ask_user", "declare_unanswerable"),
           f"phase1 post-analysis decision is valid (got {decision_type!r})")

    # ── Check phase_log entry ─────────────────────────────────────────────────

    print("\n── Checking phase_log entry ────────────────────────────────────────")
    entry = phase_log[0]
    _check(entry.get("phase") == 1,
           f"phase_log[0].phase == 1 (got {entry.get('phase')})")

    _check(isinstance(entry.get("next_action"), str),
           f"phase_log[0].next_action is a string (got {entry.get('next_action')!r})")

    # ── Summary ───────────────────────────────────────────────────────────────

    print("\n── Summary ────────────────────────────────────────────────────────")
    hyp = p0.get("consensus_hypothesis", "")
    steps = rp.get("steps", [])
    print(f"  Hypothesis    : {hyp[:120]}")
    print(f"  Plan steps    : {len(steps)}")
    print(f"  Decision type : {'dag_plan' if has_dag else 'implementation_plan'}")
    print(f"  Exec status   : {exec_status}")
    claim_updates_summary = claim_updates if isinstance(claim_updates, str) else json.dumps(claim_updates)[:120]
    print(f"  Claim updates : {claim_updates_summary}")
    print(f"  Decision      : {decision_type}")
    print(f"  Loop status   : {result.get('status')}")
    print(f"\n  Results saved to: {RESULT_DIR}/")
    print("\nALL CHECKS PASSED ✓")


if __name__ == "__main__":
    main()
