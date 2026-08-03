"""
AD Multiomics End-to-End Execution Monitor
==========================================
Directly instantiates ResearchLoop components (bypassing textgrad/frontend)
and runs the AD DLPFC multiomics query, writing all outputs.

Usage:
    export OPENAI_API_KEY=sk-...
    cd /Users/vickydong/Documents/singlecell_Agent
    python run_ad_monitor.py 2>&1 | tee results_ad_run/run.log
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# ── configuration ─────────────────────────────────────────────────────────────
RNA_PATH   = "data/AD_RNA_count.h5ad"
ATAC_PATH  = "data/AD_ATAC_count.h5ad"
RESULTS    = "results_ad_run"
RAG_ROOT   = "rag_data"
ENGINE     = "gpt-5"
FAST_ENGINE = "gpt-5"
MAX_PHASES = 5

AD_QUERY = """Alzheimer's disease (AD) is a progressive neurodegenerative disorder characterized by cognitive decline, synaptic dysfunction, neuronal loss, amyloid-β plaque accumulation, tau pathology, and widespread molecular alterations throughout the brain. Increasing evidence suggests that AD pathology involves complex interactions among multiple brain cell populations, including excitatory and inhibitory neurons, microglia, astrocytes, oligodendrocytes, and endothelial cells.

Understanding the relationship between chromatin accessibility, transcription factor activity, and gene expression at cell-type resolution is therefore critical for elucidating the regulatory architecture of Alzheimer's disease. In particular, identifying disease-associated cis-regulatory elements and linking them to transcriptional programs may provide mechanistic insight into how non-coding AD risk variants influence neuronal dysfunction, immune activation, and disease progression across distinct brain cell populations.

Design a single cell multiomics study aimed to characterize cell-type-specific regulatory landscapes, identify AD-associated cis-regulatory elements, infer regulatory interactions between accessible chromatin regions and target genes, and investigate transcription factor programs associated with disease-related cellular states in the human brain."""


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(repo_root))

    # Validate data paths
    log("Checking data files...")
    for label, path in [("RNA", RNA_PATH), ("ATAC", ATAC_PATH)]:
        p = repo_root / path
        if not p.exists():
            log(f"ERROR: {label} file not found: {p}")
            sys.exit(1)
        log(f"  {label}: {p.name}  ({p.stat().st_size // 1024 // 1024} MB)")

    result_dir = repo_root / RESULTS
    result_dir.mkdir(parents=True, exist_ok=True)
    log(f"Results: {result_dir}")

    # ── imports ──────────────────────────────────────────────────────────────
    log("Importing modules...")
    from openai import OpenAI
    from agents.adversarial_panelist import AdversarialPanelist
    from agents.analyzer_panel import AnalyzerPanel
    from agents.coder import CoderAgent
    from agents.dag_executor import DagExecutor
    from agents.research_loop import ResearchLoop
    from agents.scientist_panel import ScientistPanel
    from agents.session_dispatcher import SessionDispatcher
    from agents.session_router import SessionRouter
    from agents.session_state import SessionStateStore
    from agents.short_term_memory import ShortTermMemory
    from agents.tool_consultant import ToolConsultantAgent
    from backend import BackendConfig, SingleCellBackend
    from pipelines.config import Config
    from rag.store_backend import RAGStore

    # ── client + config ───────────────────────────────────────────────────────
    log("Creating OpenAI client...")
    client = OpenAI()  # reads OPENAI_API_KEY from environment

    log("Building Config...")
    config = Config(
        opt_step=1,
        max_fix_step=1,
        timeout=3600,
        mod1_path=str(repo_root / RNA_PATH),
        mod2_path=str(repo_root / ATAC_PATH),
        metrics="combined_score",
        label_column=None,
        id_column=None,
        code_dir=str(result_dir / "code"),
        result_dir=str(result_dir),
        engine_name=ENGINE,
    )
    config.api_dir = str(repo_root / "apis")
    config.dataset_dir = str(repo_root / "Datasets")
    try:
        config.prior_resource_summary = config.summarize_prior_resources()
    except Exception as e:
        log(f"  (prior_resource_summary skipped: {e})")
    Path(config.result_dir, "feedback").mkdir(parents=True, exist_ok=True)

    tool_artifact_dir = result_dir / "tool_artifacts"
    tool_artifact_dir.mkdir(parents=True, exist_ok=True)

    # ── backend ───────────────────────────────────────────────────────────────
    log("Building SingleCellBackend...")
    backend = SingleCellBackend(
        BackendConfig(
            cache_dir=tool_artifact_dir / "backend_cache",
            scratch_dir=result_dir / "backend_scratch",
            log_dir=result_dir / "backend_logs",
            reticulate_python=Path(sys.executable),
        )
    )
    backend.bind_runtime_context(config)

    # ── RAG + agents ──────────────────────────────────────────────────────────
    log("Building RAGStore...")
    rag_store = RAGStore(
        root_dir=str(repo_root / RAG_ROOT),
        embedding_backend="local",
        embedding_model=None,
    )

    log("Building ScientistPanel...")
    scientist_panel = ScientistPanel(
        engine_name=ENGINE,
        fast_engine_name=FAST_ENGINE,
        rag_store=rag_store,
        result_dir=result_dir / "research_loop" / "scientist",
        client=client,
    )

    log("Building AnalyzerPanel...")
    analyzer_panel = AnalyzerPanel(
        engine_name=ENGINE,
        fast_engine_name=FAST_ENGINE,
        rag_store=rag_store,
        result_dir=result_dir / "research_loop" / "analyzer",
        client=client,
    )

    log("Building ToolConsultantAgent...")
    tool_consultant = ToolConsultantAgent(
        engine_name=ENGINE,
        result_dir=str(result_dir),
        backend=backend,
        client=client,
    )

    log("Building DagExecutor...")
    dag_executor = DagExecutor(
        backend=backend,
        result_dir=tool_artifact_dir / "dag",
    )

    log("Building CoderAgent...")
    coder = CoderAgent(
        engine_name=ENGINE,
        result_dir=str(result_dir),
        artifact_dir=tool_artifact_dir / "coder",
    )

    log("Building ShortTermMemory...")
    short_term_memory = ShortTermMemory(
        session_id="ad_run",
        result_dir=result_dir / "research_loop" / "memory",
    )

    log("Building AdversarialPanelist...")
    adversarial_panelist = AdversarialPanelist(
        engine_name=ENGINE,
        fast_engine_name=FAST_ENGINE,
        retriever=scientist_panel.retriever,
        judge=scientist_panel.judge,
        paper_md_writer=scientist_panel.paper_md_writer,
        client=client,
        result_dir=result_dir / "research_loop" / "scientist" / "adversarial",
        max_rounds=3,
    )

    log("Building ResearchLoop...")
    research_loop = ResearchLoop(
        scientist_panel=scientist_panel,
        analyzer_panel=analyzer_panel,
        tool_consultant=tool_consultant,
        dag_executor=dag_executor,
        coder=coder,
        short_term_memory=short_term_memory,
        input_h5ad_path=str(repo_root / RNA_PATH),
        data_paths=[str(repo_root / ATAC_PATH)],
        result_dir=result_dir / "research_loop",
        max_phases=MAX_PHASES,
        adversarial_panelist=adversarial_panelist,
    )

    # ── session router + dispatcher ───────────────────────────────────────────
    log("Building SessionRouter + SessionDispatcher...")
    session_store = SessionStateStore(result_dir / "session_state.json")
    session_store.reset()

    session_router = SessionRouter(
        engine_name=ENGINE,
        result_dir=str(result_dir),
        client=client,
    )

    session_dispatcher = SessionDispatcher(
        router=session_router,
        tool_consultant=tool_consultant,
        coder=coder,
        research_executor=None,
        tool_artifact_dir=str(tool_artifact_dir),
        state_store=session_store,
        result_dir=str(result_dir),
        dag_executor=dag_executor,
        research_loop=research_loop,
    )

    # ── run ───────────────────────────────────────────────────────────────────
    session_tag = "ad_run_001"
    session_state = {
        "input_h5ad_path": str(repo_root / RNA_PATH),
        "input_mod2_path": str(repo_root / ATAC_PATH),
        "tool_artifact_dir": str(tool_artifact_dir),
        "initial_query": AD_QUERY,
        "current_message": AD_QUERY,
        "history": [],
    }

    log("\n" + "="*70)
    log("DISPATCHING AD QUERY")
    log("="*70)

    t0 = time.time()
    try:
        result = session_dispatcher.handle(
            user_message=AD_QUERY,
            session_state=session_state,
            session_tag=session_tag,
        )
    except Exception as exc:
        import traceback
        log(f"\nEXCEPTION: {exc}")
        traceback.print_exc()
        result = {"error": str(exc), "traceback": traceback.format_exc()}

    elapsed = time.time() - t0
    log(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Save result
    out = result_dir / "ad_run_result.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    log(f"Result saved: {out}")

    payload = result.get("result") if isinstance(result.get("result"), dict) else {}
    log(f"\nStatus:  {payload.get('status', result.get('error', 'unknown'))}")
    msg = str(payload.get("message") or "")
    if msg:
        log(f"Message: {msg[:400]}")

    route = result.get("route") if isinstance(result.get("route"), dict) else {}
    log(f"Route:        {route.get('route')}")
    log(f"Intent mode:  {route.get('intent_mode')}")
    ri = str(route.get("resolved_intent", ""))
    if ri:
        log(f"Resolved intent:\n  {ri[:400]}")

    log("\nDone. Check results_ad_run/ for all intermediate outputs.")


if __name__ == "__main__":
    main()
