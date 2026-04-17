from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from rag_types import RAGDocument


def _safe_json_load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


class SharedPaperStore:
    def __init__(self, *, rag_agent: Any, config: Any, prepared_contexts: Dict[str, Any]):
        self.rag_agent = rag_agent
        self.config = config
        self.prepared_contexts = prepared_contexts
        self._documents_by_id: Dict[str, RAGDocument] = {}
        self._doc_channel: Dict[str, str] = {}
        self._paper_summaries: Dict[str, Dict[str, str]] = {}

        for channel_name, payload in prepared_contexts.items():
            if not isinstance(payload, dict):
                continue
            session_key = str(payload.get("session_key", "")).strip()
            if session_key:
                summary_cache = _safe_json_load(rag_agent._summaries_path(session_key, channel_name))
                for doc_id, summary in summary_cache.items():
                    if isinstance(summary, dict):
                        self._paper_summaries[doc_id] = {
                            "objective": str(summary.get("objective", "")).strip(),
                            "key_methods": str(summary.get("key_methods", "")).strip(),
                            "main_findings": str(summary.get("main_findings", "")).strip(),
                            "limitations": str(summary.get("limitations", "")).strip(),
                        }
            for document in payload.get("documents", []):
                if isinstance(document, RAGDocument):
                    self._documents_by_id[document.doc_id] = document
                    self._doc_channel[document.doc_id] = channel_name

    def read_dataset_summary(self) -> Dict[str, Any]:
        return {
            "dataset_summary": str(getattr(self.config, "feat_stats", "") or "").strip(),
            "label_column": str(getattr(self.config, "label_column", "") or "").strip(),
        }

    def read_label_distribution(self, label_key: str) -> Dict[str, Any]:
        key = str(label_key or "").strip()
        if not key:
            raise ValueError("label_key must be non-empty")
        ds = self.config._load_any(self.config.data_mod1_path)
        if ds.get("type") != "h5ad":
            raise ValueError("label distribution is only supported for h5ad inputs")
        adata = ds["obj"]
        if key not in adata.obs.columns:
            raise ValueError(f"{key} not found in dataset obs columns")
        values = pd.Series(adata.obs[key]).astype(str)
        counts = Counter(v for v in values.tolist() if v and v.lower() != "nan")
        total = sum(counts.values())
        distribution = [
            {
                "label": label,
                "count": int(count),
                "fraction": float(count / total) if total else 0.0,
            }
            for label, count in counts.most_common()
        ]
        return {"label_key": key, "total": int(total), "distribution": distribution}

    def read_prior_resource_summary(self) -> Dict[str, Any]:
        try:
            payload = json.loads(str(getattr(self.config, "prior_resource_summary", "") or ""))
        except json.JSONDecodeError:
            payload = {}
        return payload if isinstance(payload, dict) else {}

    def check_prior_coverage(self, resource_name: str) -> Dict[str, Any]:
        resource = str(resource_name or "").strip().lower()
        summary = self.read_prior_resource_summary()
        resources = summary.get("prior_resources", [])
        resource_entry = None
        for item in resources:
            if not isinstance(item, dict):
                continue
            file_path = str(item.get("file_path", "")).lower()
            if resource and resource in file_path:
                resource_entry = item
                break

        if resource == "gene_embedding":
            gene_dir = Path(getattr(self.config, "dataset_dir", "")) / "gene_embedding"
            gene_names_path = gene_dir / "gene_names.txt"
            dataset = self.config._load_any(self.config.data_mod1_path)
            if dataset.get("type") == "h5ad" and gene_names_path.exists():
                adata = dataset["obj"]
                var_names = adata.var_names.tolist() if hasattr(adata.var_names, "tolist") else list(adata.var_names)
                dataset_genes = {str(g).strip().upper() for g in var_names}
                with open(gene_names_path, "r", encoding="utf-8") as f:
                    embedded_genes = {line.strip().upper() for line in f if line.strip()}
                overlap = dataset_genes & embedded_genes
                return {
                    "resource_name": "gene_embedding",
                    "dataset_gene_count": int(len(dataset_genes)),
                    "resource_gene_count": int(len(embedded_genes)),
                    "matched_gene_count": int(len(overlap)),
                    "coverage_fraction": float(len(overlap) / len(dataset_genes)) if dataset_genes else 0.0,
                }

        return {
            "resource_name": resource_name,
            "summary": resource_entry or {},
        }

    def search_index(self, query: str, channel: str, top_k: int = 5) -> Dict[str, Any]:
        channel_name = str(channel or "").strip()
        if channel_name not in self.prepared_contexts:
            raise ValueError(f"Unsupported channel: {channel_name}")
        collection_name = str(self.prepared_contexts[channel_name].get("collection_name", "")).strip()
        hits = self.rag_agent.store.search_runtime(collection_name, str(query or "").strip(), n_results=max(1, int(top_k)))
        results: List[Dict[str, Any]] = []
        for hit in hits[: max(1, int(top_k))]:
            results.append(
                {
                    "paper_id": hit.doc_id,
                    "title": hit.title,
                    "score": float(hit.score),
                    "section_type": hit.section_type or "",
                    "snippet": hit.snippet,
                    "url": hit.url,
                }
            )
        return {"channel": channel_name, "query": query, "results": results}

    def read_paper_summary(self, paper_id: str) -> Dict[str, Any]:
        doc_id = str(paper_id or "").strip()
        document = self._documents_by_id.get(doc_id)
        if document is None:
            raise ValueError(f"Unknown paper_id: {doc_id}")
        summary = self._paper_summaries.get(doc_id)
        if summary is None:
            channel_name = self._doc_channel.get(doc_id, "dataset")
            session_key = str(self.prepared_contexts.get(channel_name, {}).get("session_key", "")).strip()
            summary = self.rag_agent._generate_paper_summary(document=document, session_key=session_key, channel_name=channel_name)
            self._paper_summaries[doc_id] = summary
        return {
            "paper_id": doc_id,
            "title": document.title,
            "channel": self._doc_channel.get(doc_id, ""),
            "summary": summary,
        }

    def fetch_paper_section(self, paper_id: str, section_type: str, top_n_chunks: int = 3) -> Dict[str, Any]:
        payload = self.rag_agent.fetch_paper_section(paper_id, section_type)
        chunks = payload.get("chunks")
        if isinstance(chunks, list):
            payload["chunks"] = chunks[: max(1, int(top_n_chunks))]
        return payload

    def query_marker_database(self, tissue: str, species: str) -> Dict[str, Any]:
        species_text = str(species or "").strip().lower()
        tissue_text = str(tissue or "").strip().lower()
        marker_path = Path(getattr(self.config, "dataset_dir", "")) / "Cell_marker_Human.xlsx"
        if not marker_path.exists():
            raise ValueError("Cell_marker_Human.xlsx not found")
        df = pd.read_excel(marker_path, sheet_name=0)
        filtered = df.copy()
        species_cols = [col for col in filtered.columns if "species" in str(col).lower()]
        tissue_cols = [col for col in filtered.columns if any(tok in str(col).lower() for tok in ["tissue", "organ", "source"])]
        cell_cols = [col for col in filtered.columns if "cell" in str(col).lower() and "marker" not in str(col).lower()]
        gene_cols = [col for col in filtered.columns if any(tok in str(col).lower() for tok in ["gene", "marker"])]

        if species_text and species_cols:
            mask = filtered[species_cols[0]].astype(str).str.lower().str.contains(species_text, na=False)
            filtered = filtered.loc[mask]
        if tissue_text and tissue_cols:
            mask = filtered[tissue_cols[0]].astype(str).str.lower().str.contains(tissue_text, na=False)
            if mask.any():
                filtered = filtered.loc[mask]

        cell_col = cell_cols[0] if cell_cols else None
        gene_col = gene_cols[-1] if gene_cols else None
        if cell_col is None or gene_col is None:
            return {"species": species, "tissue": tissue, "markers_by_cell_type": {}}

        markers_by_cell_type: Dict[str, List[str]] = {}
        for _, row in filtered.iterrows():
            cell_type = str(row.get(cell_col, "")).strip()
            if not cell_type:
                continue
            raw_genes = str(row.get(gene_col, "") or "")
            genes = [item.strip() for item in raw_genes.replace(";", ",").split(",") if item.strip()]
            if not genes:
                continue
            current = markers_by_cell_type.setdefault(cell_type, [])
            for gene in genes:
                if gene not in current:
                    current.append(gene)
        top_items = dict(list(markers_by_cell_type.items())[:20])
        return {"species": species, "tissue": tissue, "markers_by_cell_type": top_items}

    def query_pathway_database(self, database: str, gene: str) -> Dict[str, Any]:
        gene_name = str(gene or "").strip().upper()
        db_name = str(database or "").strip().lower()
        dataset_dir = Path(getattr(self.config, "dataset_dir", ""))
        if db_name == "msigdb":
            path = dataset_dir / "MsigDB.csv"
        elif db_name == "go":
            path = dataset_dir / "GO_terms.csv"
        else:
            raise ValueError(f"Unsupported pathway database: {database}")
        if not path.exists():
            raise ValueError(f"Database file not found: {path}")

        df = pd.read_csv(path)
        matches: List[str] = []
        for _, row in df.iterrows():
            values = [str(value) for value in row.tolist()]
            haystack = ",".join(values).upper()
            if gene_name and gene_name in haystack:
                label = ""
                for key in ["gs_name", "term_name", "term", "set_name", "go_id"]:
                    if key in df.columns:
                        label = str(row.get(key, "")).strip()
                        if label:
                            break
                if not label:
                    label = values[0]
                if label and label not in matches:
                    matches.append(label)
            if len(matches) >= 20:
                break
        return {"database": database, "gene": gene, "matches": matches}
