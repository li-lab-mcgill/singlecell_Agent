from __future__ import annotations

import argparse
import time
from pathlib import Path

from rag_sources import (
    BIORXIV_CATEGORIES,
    GITHUB_SEARCH_TOPICS,
    PUBMED_QUERIES,
    fetch_biorxiv_documents,
    fetch_github_documents,
    fetch_pubmed_documents,
    save_manifest,
)
from rag_store import RAGStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the offline general RAG corpus for consultant retrieval.")
    parser.add_argument("--rag-root", default="rag_data")
    parser.add_argument("--pubmed-max-results-per-query", type=int, default=20)
    parser.add_argument("--biorxiv-days", type=int, default=365)
    parser.add_argument("--biorxiv-max-papers", type=int, default=1000)
    parser.add_argument("--github-max-results-per-topic", type=int, default=10)
    parser.add_argument("--embedding-backend", choices=["local", "openai"], default="local")
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    rag_root = Path(args.rag_root)
    if not rag_root.is_absolute():
        rag_root = project_root / rag_root

    started = time.time()
    store = RAGStore(root_dir=rag_root, embedding_backend=args.embedding_backend, embedding_model=args.embedding_model)

    pubmed_docs = fetch_pubmed_documents(PUBMED_QUERIES, max_results_per_query=args.pubmed_max_results_per_query)
    biorxiv_docs = fetch_biorxiv_documents(
        BIORXIV_CATEGORIES,
        days=args.biorxiv_days,
        max_papers=args.biorxiv_max_papers,
    )
    github_docs = fetch_github_documents(GITHUB_SEARCH_TOPICS, max_results_per_topic=args.github_max_results_per_topic)

    all_documents = [*pubmed_docs, *biorxiv_docs, *github_docs]
    deduped_documents = store.deduplicate_documents(all_documents)
    store.save_documents(store.general_corpus_path, deduped_documents)
    chunk_count = store.build_general_index(deduped_documents, rebuild=args.rebuild)

    manifest = {
        "built_at_epoch": started,
        "duration_seconds": round(time.time() - started, 2),
        "embedding_backend": store.embedding_backend,
        "embedding_model": store.embedding_model,
        "rebuild": bool(args.rebuild),
        "counts": {
            "pubmed_raw": len(pubmed_docs),
            "biorxiv_raw": len(biorxiv_docs),
            "github_raw": len(github_docs),
            "general_deduped": len(deduped_documents),
            "general_chunks": chunk_count,
        },
        "paths": {
            "rag_root": str(rag_root),
            "general_corpus": str(store.general_corpus_path),
            "manifest": str(store.manifest_path),
        },
    }
    save_manifest(store.manifest_path, manifest)
    print(f"Built general RAG corpus at {rag_root}")
    print(manifest)


if __name__ == "__main__":
    main()
