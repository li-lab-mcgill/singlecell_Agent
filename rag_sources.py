from __future__ import annotations

import json
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET

import requests

from rag_types import CoreFetchResult, RAGDocument


PUBMED_QUERIES = [
    "single-cell RNA-seq AND unsupervised learning AND clustering",
    "scRNA-seq AND dimensionality reduction AND cell type discovery",
    "single-cell AND deep learning AND representation learning AND latent space",
    "single-cell AND variational autoencoder AND generative model",
    "scRNA-seq AND graph neural network AND cell embedding",
    "single-cell AND contrastive learning AND self-supervised",
    "single-cell AND cell type annotation AND automated AND benchmark",
    "scRNA-seq AND de novo cell type AND novel cell type AND discovery",
    "single-cell AND cell type classification AND marker gene AND reference",
    "scRNA-seq AND rare cell type AND detection AND unsupervised",
    "single-cell AND cell state AND continuous trajectory AND pseudotime",
    "scRNA-seq AND cell identity AND transcriptional program AND heterogeneity",
    "single-cell AND prior knowledge AND gene regulatory network AND unsupervised",
    "scRNA-seq AND biological prior AND deep learning AND regularization",
    "single-cell AND pathway activity AND gene set AND latent factor",
    "scRNA-seq AND knowledge graph AND gene ontology AND embedding",
    "single-cell AND informed clustering AND biological constraint AND interpretable",
    "gene regulatory prior AND single-cell AND representation learning AND disentangled",
    "single-cell AND gene regulatory network inference AND transcription factor",
    "scRNA-seq AND GRN AND unsupervised AND cell type specific",
    "single-cell AND regulatory network AND deep learning AND prediction",
    "gene regulatory network AND single-cell AND SCENIC AND regulon",
    "scRNA-seq AND transcription factor activity AND network-based AND clustering",
    "single-cell AND causal gene network AND perturbation AND inference",
    "single-cell AND multiomics AND ATAC-seq AND RNA-seq AND integration",
    "single-cell AND chromatin accessibility AND regulatory element AND cell type",
    "scRNA-seq AND enhancer AND cell-type-specific AND gene regulation",
    "single-cell AND epigenomic prior AND gene expression AND prediction",
    "single-cell multiome AND cis-regulatory AND unsupervised AND joint embedding",
    "single-cell AND peak-to-gene AND regulatory linkage AND multimodal",
    "single-cell AND foundation model AND pre-trained AND gene expression",
    "scRNA-seq AND transfer learning AND cross-dataset AND generalization",
    "single-cell AND large language model AND transformer AND cell representation",
    "scRNA-seq AND zero-shot AND few-shot AND cell type AND annotation",
    "single-cell AND self-supervised pretraining AND masked gene AND prediction",
    "single-cell AND interpretable deep learning AND gene program AND module",
    "scRNA-seq AND latent factor AND biological interpretation AND pathway",
    "single-cell AND disentangled representation AND gene regulatory AND mechanism",
    "scRNA-seq AND attention mechanism AND gene importance AND cell type",
    "single-cell AND explainable AI AND feature attribution AND marker discovery",
    "single-cell AND clustering benchmark AND evaluation metric AND ARI NMI",
    "scRNA-seq AND cell type annotation AND benchmark AND ground truth",
    "single-cell AND batch effect AND integration AND unsupervised AND benchmark",
    "scRNA-seq AND simulation AND synthetic data AND ground truth AND evaluation",
    "single-cell AND spatial transcriptomics AND unsupervised AND domain identification",
    "single-cell AND perturbation prediction AND unsupervised AND causal",
    "scRNA-seq AND disease AND cell type AND prior-guided AND patient stratification",
    "single-cell AND developmental biology AND lineage AND unsupervised AND trajectory",
    "single-cell AND cell communication AND ligand receptor AND network prior",
]

BIORXIV_CATEGORIES = ["bioinformatics", "computational biology", "genomics", "systems biology"]

GITHUB_SEARCH_TOPICS = [
    {"query": "single cell unsupervised learning", "language": "python", "min_stars": 10, "category": "general"},
    {"query": "scRNA-seq clustering", "language": "python", "min_stars": 15, "category": "general"},
    {"query": "single cell deep learning", "language": "python", "min_stars": 20, "category": "general"},
    {"query": "single cell analysis tool", "language": "python", "min_stars": 30, "category": "general"},
    {"query": "cell type annotation", "language": "python", "min_stars": 20, "category": "cell_type"},
    {"query": "automatic cell type", "language": "python", "min_stars": 15, "category": "cell_type"},
    {"query": "cell type classification single cell", "language": "python", "min_stars": 10, "category": "cell_type"},
    {"query": "novel cell type discovery", "language": None, "min_stars": 5, "category": "cell_type"},
    {"query": "rare cell type detection", "language": "python", "min_stars": 10, "category": "cell_type"},
    {"query": "marker gene cell type", "language": "python", "min_stars": 15, "category": "cell_type"},
    {"query": "prior knowledge single cell", "language": "python", "min_stars": 5, "category": "prior_guided"},
    {"query": "biologically informed neural network", "language": "python", "min_stars": 10, "category": "prior_guided"},
    {"query": "pathway informed deep learning", "language": "python", "min_stars": 5, "category": "prior_guided"},
    {"query": "knowledge guided representation learning", "language": "python", "min_stars": 5, "category": "prior_guided"},
    {"query": "gene set activity score single cell", "language": "python", "min_stars": 10, "category": "prior_guided"},
    {"query": "gene ontology embedding", "language": "python", "min_stars": 10, "category": "prior_guided"},
    {"query": "biological constraint deep learning", "language": None, "min_stars": 5, "category": "prior_guided"},
    {"query": "gene regulatory network single cell", "language": "python", "min_stars": 20, "category": "grn"},
    {"query": "GRN inference scRNA", "language": "python", "min_stars": 15, "category": "grn"},
    {"query": "SCENIC regulon", "language": None, "min_stars": 20, "category": "grn"},
    {"query": "transcription factor activity single cell", "language": "python", "min_stars": 15, "category": "grn"},
    {"query": "network-based clustering single cell", "language": "python", "min_stars": 5, "category": "grn"},
    {"query": "causal gene network", "language": "python", "min_stars": 10, "category": "grn"},
    {"query": "variational autoencoder single cell", "language": "python", "min_stars": 20, "category": "dl_autoencoder"},
    {"query": "autoencoder scRNA-seq", "language": "python", "min_stars": 15, "category": "dl_autoencoder"},
    {"query": "deep generative model single cell", "language": "python", "min_stars": 15, "category": "dl_autoencoder"},
    {"query": "conditional VAE single cell", "language": "python", "min_stars": 10, "category": "dl_autoencoder"},
    {"query": "beta-VAE disentangled single cell", "language": "python", "min_stars": 5, "category": "dl_autoencoder"},
    {"query": "adversarial autoencoder single cell", "language": "python", "min_stars": 5, "category": "dl_autoencoder"},
    {"query": "denoising autoencoder scRNA", "language": "python", "min_stars": 10, "category": "dl_autoencoder"},
    {"query": "normalizing flow single cell", "language": "python", "min_stars": 5, "category": "dl_autoencoder"},
    {"query": "diffusion model single cell gene expression", "language": "python", "min_stars": 5, "category": "dl_autoencoder"},
    {"query": "graph neural network single cell", "language": "python", "min_stars": 15, "category": "dl_graph"},
    {"query": "graph attention network scRNA", "language": "python", "min_stars": 10, "category": "dl_graph"},
    {"query": "graph convolutional network cell", "language": "python", "min_stars": 10, "category": "dl_graph"},
    {"query": "cell graph network clustering", "language": "python", "min_stars": 5, "category": "dl_graph"},
    {"query": "gene gene graph neural network", "language": "python", "min_stars": 5, "category": "dl_graph"},
    {"query": "spatial graph neural network cell", "language": "python", "min_stars": 10, "category": "dl_graph"},
    {"query": "heterogeneous graph single cell", "language": "python", "min_stars": 5, "category": "dl_graph"},
    {"query": "graph variational autoencoder single cell", "language": "python", "min_stars": 5, "category": "dl_graph"},
    {"query": "contrastive learning single cell", "language": "python", "min_stars": 10, "category": "dl_contrastive"},
    {"query": "self-supervised single cell", "language": "python", "min_stars": 10, "category": "dl_contrastive"},
    {"query": "SimCLR BYOL single cell", "language": None, "min_stars": 5, "category": "dl_contrastive"},
    {"query": "data augmentation scRNA-seq contrastive", "language": "python", "min_stars": 5, "category": "dl_contrastive"},
    {"query": "masked autoencoder single cell gene", "language": "python", "min_stars": 5, "category": "dl_contrastive"},
    {"query": "multi-view learning single cell", "language": "python", "min_stars": 5, "category": "dl_contrastive"},
    {"query": "transformer single cell RNA", "language": "python", "min_stars": 15, "category": "dl_attention"},
    {"query": "attention mechanism gene expression", "language": "python", "min_stars": 10, "category": "dl_attention"},
    {"query": "self-attention scRNA-seq", "language": "python", "min_stars": 5, "category": "dl_attention"},
    {"query": "cross-attention single cell multimodal", "language": "python", "min_stars": 5, "category": "dl_attention"},
    {"query": "gene transformer embedding", "language": "python", "min_stars": 10, "category": "dl_attention"},
    {"query": "disentangled representation single cell", "language": "python", "min_stars": 5, "category": "dl_interpret"},
    {"query": "interpretable deep learning single cell", "language": "python", "min_stars": 10, "category": "dl_interpret"},
    {"query": "gene program discovery deep learning", "language": "python", "min_stars": 10, "category": "dl_interpret"},
    {"query": "latent factor gene module single cell", "language": "python", "min_stars": 5, "category": "dl_interpret"},
    {"query": "sparse autoencoder gene program", "language": "python", "min_stars": 5, "category": "dl_interpret"},
    {"query": "feature attribution single cell neural network", "language": "python", "min_stars": 5, "category": "dl_interpret"},
    {"query": "neural network explainability scRNA", "language": "python", "min_stars": 5, "category": "dl_interpret"},
    {"query": "GAN single cell generation", "language": "python", "min_stars": 10, "category": "dl_hybrid"},
    {"query": "Wasserstein GAN scRNA-seq", "language": "python", "min_stars": 5, "category": "dl_hybrid"},
    {"query": "VAE GAN single cell", "language": "python", "min_stars": 5, "category": "dl_hybrid"},
    {"query": "neural ODE single cell trajectory", "language": "python", "min_stars": 10, "category": "dl_hybrid"},
    {"query": "optimal transport single cell", "language": "python", "min_stars": 10, "category": "dl_hybrid"},
    {"query": "capsule network single cell", "language": "python", "min_stars": 5, "category": "dl_hybrid"},
    {"query": "single cell multiome", "language": "python", "min_stars": 15, "category": "multiomics"},
    {"query": "scATAC-seq scRNA-seq integration", "language": "python", "min_stars": 15, "category": "multiomics"},
    {"query": "peak to gene linkage", "language": "python", "min_stars": 10, "category": "multiomics"},
    {"query": "chromatin accessibility single cell", "language": "python", "min_stars": 20, "category": "multiomics"},
    {"query": "regulatory element single cell multimodal", "language": None, "min_stars": 5, "category": "multiomics"},
    {"query": "epigenomic prior gene expression", "language": None, "min_stars": 5, "category": "multiomics"},
    {"query": "batch correction single cell", "language": "python", "min_stars": 20, "category": "integration"},
    {"query": "scRNA-seq data integration", "language": "python", "min_stars": 20, "category": "integration"},
    {"query": "harmony scanorama scVI", "language": None, "min_stars": 20, "category": "integration"},
    {"query": "single cell benchmark clustering", "language": "python", "min_stars": 15, "category": "benchmark"},
    {"query": "cell type annotation benchmark", "language": "python", "min_stars": 10, "category": "benchmark"},
    {"query": "scRNA-seq simulation synthetic", "language": "python", "min_stars": 15, "category": "benchmark"},
    {"query": "scvi-tools", "language": "python", "min_stars": 50, "category": "tools"},
    {"query": "scanpy", "language": "python", "min_stars": 50, "category": "tools"},
    {"query": "CellTypist", "language": "python", "min_stars": 20, "category": "tools"},
    {"query": "scANVI annotation", "language": "python", "min_stars": 10, "category": "tools"},
    {"query": "TOSICA", "language": "python", "min_stars": 5, "category": "tools"},
    {"query": "scETM", "language": None, "min_stars": 5, "category": "topic_model"},
]

METHOD_TITLE_RE = re.compile(
    r"(?i)^(?:[0-9IVXLCDM]+[.)]?\s+)?(?:methods?|methodology|materials\s+and\s+methods?|methods\s+and\s+materials|approach|experimental\s+methods?)\s*:?\s*$"
)
SECTION_STOP_RE = re.compile(
    r"(?i)^(?:discussion|results|conclusion|conclusions|references?|data\s+availability|code\s+availability|acknowledg(?:e)?ments?|supplementary|appendix)\s*:?\s*$"
)

_NCBI_SESSION = requests.Session()


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional_env(name: str) -> str:
    return os.getenv(name, "").strip()


def _stable_doc_id(source: str, identifier: str) -> str:
    safe_identifier = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", identifier or "unknown")
    return f"{source}:{safe_identifier}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _chunk_text_blocks(text: str) -> str:
    blocks = [re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n{2,}", text or "")]
    return "\n\n".join(block for block in blocks if block)


def _ncbi_params() -> Dict[str, str]:
    params = {"email": _require_env("NCBI_EMAIL"), "tool": "singlecell_agent_rag"}
    api_key = _optional_env("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def _sleep(delay: float) -> None:
    if delay > 0:
        time.sleep(delay)


def _extract_text_recursive(elem: Optional[ET.Element]) -> str:
    if elem is None:
        return ""
    parts: List[str] = []
    if elem.text and elem.text.strip():
        parts.append(elem.text.strip())
    for child in elem:
        child_text = _extract_text_recursive(child)
        if child_text:
            parts.append(child_text)
        if child.tail and child.tail.strip():
            parts.append(child.tail.strip())
    return " ".join(parts)


def _extract_xml_sections(root: ET.Element) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    for sec in root.findall(".//sec"):
        title_elem = sec.find("./title")
        title = _normalize_text(_extract_text_recursive(title_elem))
        if not title:
            continue
        paragraphs = [_normalize_text(_extract_text_recursive(node)) for node in sec.findall(".//p")]
        content = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
        if content:
            sections[title] = content
    return sections


def _extract_methods_from_sections(sections: Dict[str, str]) -> str:
    if not sections:
        return ""
    selected: List[str] = []
    collecting = False
    for title, text in sections.items():
        if METHOD_TITLE_RE.match(title):
            collecting = True
        elif collecting and SECTION_STOP_RE.match(title):
            break
        if collecting and text:
            selected.append(f"{title}\n{text}")
    return _chunk_text_blocks("\n\n".join(selected))


def _build_general_doc(
    *,
    source: str,
    source_id: str,
    title: str,
    abstract: str,
    url: str,
    authors: str = "",
    published: str = "",
    doi: str = "",
    categories: Optional[List[str]] = None,
    metadata: Optional[Dict[str, object]] = None,
) -> RAGDocument:
    return RAGDocument(
        doc_id=_stable_doc_id(source, source_id),
        source=source,
        source_id=source_id,
        title=_normalize_text(title),
        text=_normalize_text(abstract),
        abstract=_normalize_text(abstract),
        url=url,
        authors=_normalize_text(authors),
        published=_normalize_text(published),
        doi=_normalize_text(doi),
        doc_type="general",
        categories=[str(item) for item in (categories or []) if str(item).strip()],
        metadata=dict(metadata or {}),
    )


def _ncbi_delay() -> float:
    return 0.11 if _optional_env("NCBI_API_KEY") else 0.34


def _ncbi_get(url: str, **params: object) -> requests.Response:
    merged_params = {**_ncbi_params(), **params}
    base_delay = _ncbi_delay()
    last_error: Optional[Exception] = None
    for attempt in range(4):
        try:
            response = _NCBI_SESSION.get(url, params=merged_params, timeout=30)
            if response.status_code in {429, 500, 502, 503, 504}:
                raise requests.HTTPError(
                    f"NCBI request failed with status {response.status_code}",
                    response=response,
                )
            response.raise_for_status()
            _sleep(base_delay)
            return response
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            response = getattr(exc, "response", None)
            status_code = response.status_code if response is not None else None
            retryable = status_code in {None, 429, 500, 502, 503, 504}
            last_error = exc
            if attempt == 3 or not retryable:
                break
            # NCBI occasionally drops keep-alive connections; backoff avoids immediate hammering.
            backoff = max(base_delay, 0.5 * (2**attempt)) + random.uniform(0.0, 0.25)
            _sleep(backoff)
    assert last_error is not None
    raise last_error


def _biorxiv_get(session: requests.Session, url: str) -> requests.Response:
    last_error: Optional[Exception] = None
    for attempt in range(4):
        try:
            response = session.get(url, timeout=60)
            if response.status_code in {429, 500, 502, 503, 504}:
                raise requests.HTTPError(
                    f"bioRxiv request failed with status {response.status_code}",
                    response=response,
                )
            response.raise_for_status()
            _sleep(1.0)
            return response
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            response = getattr(exc, "response", None)
            status_code = response.status_code if response is not None else None
            retryable = status_code in {None, 429, 500, 502, 503, 504}
            last_error = exc
            if attempt == 3 or not retryable:
                break
            backoff = 1.0 * (2**attempt) + random.uniform(0.0, 0.5)
            _sleep(backoff)
    assert last_error is not None
    raise last_error


def _pubmed_article_to_document(article: ET.Element) -> Optional[RAGDocument]:
    medline_citation = article.find("./MedlineCitation")
    pubmed_data = article.find("./PubmedData")
    if medline_citation is None:
        return None
    pmid = _normalize_text(_extract_text_recursive(medline_citation.find("./PMID")))
    title = _normalize_text(_extract_text_recursive(medline_citation.find(".//ArticleTitle")))
    abstract_texts = [
        _normalize_text(_extract_text_recursive(node))
        for node in medline_citation.findall(".//Abstract/AbstractText")
        if _normalize_text(_extract_text_recursive(node))
    ]
    abstract = "\n\n".join(abstract_texts)
    if not pmid or not title or not abstract:
        return None
    author_names = []
    for author in medline_citation.findall(".//AuthorList/Author"):
        last_name = _normalize_text(_extract_text_recursive(author.find("./LastName")))
        initials = _normalize_text(_extract_text_recursive(author.find("./Initials")))
        collective = _normalize_text(_extract_text_recursive(author.find("./CollectiveName")))
        if collective:
            author_names.append(collective)
        elif last_name:
            author_names.append(" ".join(part for part in [last_name, initials] if part))
    doi = ""
    if pubmed_data is not None:
        for article_id in pubmed_data.findall(".//ArticleId"):
            if str(article_id.attrib.get("IdType", "")).lower() == "doi":
                doi = _normalize_text(_extract_text_recursive(article_id))
                break
    published = _normalize_text(
        " ".join(
            part
            for part in [
                _extract_text_recursive(medline_citation.find(".//PubDate/Year")),
                _extract_text_recursive(medline_citation.find(".//PubDate/Month")),
                _extract_text_recursive(medline_citation.find(".//PubDate/Day")),
            ]
            if _normalize_text(part)
        )
    )
    journal = _normalize_text(_extract_text_recursive(medline_citation.find(".//Journal/Title")))
    return _build_general_doc(
        source="pubmed",
        source_id=pmid,
        title=title,
        abstract=abstract,
        authors=", ".join(author_names),
        published=published,
        doi=doi,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        metadata={"journal": journal},
    )


def fetch_pubmed_documents(queries: Optional[Iterable[str]] = None, max_results_per_query: int = 20) -> List[RAGDocument]:
    queries = list(queries or PUBMED_QUERIES)
    pmids: List[str] = []
    for query in queries:
        response = _ncbi_get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            db="pubmed",
            term=query,
            retmax=max_results_per_query,
            sort="relevance",
            retmode="json",
        )
        pmids.extend(response.json().get("esearchresult", {}).get("idlist", []))
    unique_pmids = list(dict.fromkeys(pmid for pmid in pmids if str(pmid).strip()))
    documents: List[RAGDocument] = []
    for idx in range(0, len(unique_pmids), 100):
        batch_ids = unique_pmids[idx : idx + 100]
        response = _ncbi_get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            db="pubmed",
            id=",".join(batch_ids),
            retmode="xml",
        )
        root = ET.fromstring(response.text)
        for article in root.findall("./PubmedArticle"):
            document = _pubmed_article_to_document(article)
            if document is not None:
                documents.append(document)
    return documents


def fetch_biorxiv_documents(categories: Optional[Iterable[str]] = None, days: int = 365, max_papers: int = 1000) -> List[RAGDocument]:
    categories = [str(item) for item in (categories or BIORXIV_CATEGORIES) if str(item).strip()]
    session = requests.Session()
    all_papers: List[Dict[str, object]] = []
    cursor = 0
    start_date = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    end_date = time.strftime("%Y-%m-%d")
    while len(all_papers) < max_papers:
        response = _biorxiv_get(session, f"https://api.biorxiv.org/details/biorxiv/{start_date}/{end_date}/{cursor}")
        payload = response.json()
        collection = payload.get("collection", [])
        if not collection:
            break
        all_papers.extend(collection)
        cursor += len(collection)
    documents: List[RAGDocument] = []
    for paper in all_papers:
        paper_category = str(paper.get("category", "")).strip().lower()
        if categories and not any(category.lower() in paper_category for category in categories):
            continue
        doi = str(paper.get("doi", "")).strip()
        title = str(paper.get("title", "")).strip()
        abstract = str(paper.get("abstract", "")).strip()
        if not doi or not title or not abstract:
            continue
        version = str(paper.get("version", "1")).strip() or "1"
        documents.append(
            _build_general_doc(
                source="biorxiv",
                source_id=doi,
                title=title,
                abstract=abstract,
                authors=str(paper.get("authors", "")).strip(),
                published=str(paper.get("date", "")).strip(),
                doi=doi,
                url=f"https://www.biorxiv.org/content/{doi}v{version}",
                categories=[paper_category] if paper_category else [],
                metadata={
                    "version": version,
                    "server": str(paper.get("server", "biorxiv")).strip(),
                    "jats_xml_path": str(paper.get("jats xml path", "")).strip(),
                },
            )
        )
        if len(documents) >= max_papers:
            break
    return documents


def _github_headers() -> Dict[str, str]:
    token = _require_env("GITHUB_TOKEN")
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _github_request(
    session: requests.Session,
    url: str,
    *,
    params: Optional[Dict[str, object]] = None,
    accept: str = "application/vnd.github+json",
) -> requests.Response:
    response = session.get(url, headers={**_github_headers(), "Accept": accept}, params=params, timeout=30)
    if response.status_code in {403, 429}:
        reset_epoch = int(response.headers.get("X-RateLimit-Reset", "0") or "0")
        wait_seconds = max(1, reset_epoch - int(time.time()) + 1) if reset_epoch else 60
        time.sleep(wait_seconds)
        response = session.get(url, headers={**_github_headers(), "Accept": accept}, params=params, timeout=30)
    response.raise_for_status()
    return response


def _search_github(session: requests.Session, query: str, *, language: Optional[str], min_stars: int, per_page: int) -> List[Dict[str, object]]:
    q = query
    if language:
        q += f" language:{language}"
    if min_stars:
        q += f" stars:>={min_stars}"
    response = _github_request(
        session,
        "https://api.github.com/search/repositories",
        params={"q": q, "sort": "stars", "order": "desc", "per_page": per_page},
    )
    return response.json().get("items", [])


def _fetch_github_readme(session: requests.Session, full_name: str, max_chars: int = 6000) -> str:
    try:
        response = _github_request(
            session,
            f"https://api.github.com/repos/{full_name}/readme",
            accept="application/vnd.github.raw+json",
        )
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return ""
        raise
    text = _chunk_text_blocks(response.text)
    if len(text) <= max_chars:
        return text
    # Keep README context bounded so GitHub repos do not dominate the general corpus.
    return text[:max_chars].rsplit(" ", 1)[0].strip()


def fetch_github_documents(search_topics: Optional[Iterable[Dict[str, object]]] = None, max_results_per_topic: int = 10) -> List[RAGDocument]:
    session = requests.Session()
    topics = list(search_topics or GITHUB_SEARCH_TOPICS)
    repos_by_name: Dict[str, RAGDocument] = {}
    for topic in topics:
        items = _search_github(
            session,
            str(topic.get("query", "")).strip(),
            language=str(topic.get("language", "")).strip() or None,
            min_stars=int(topic.get("min_stars", 0) or 0),
            per_page=max(1, min(100, max_results_per_topic)),
        )
        for repo in items:
            full_name = str(repo.get("full_name", "")).strip()
            if not full_name or full_name in repos_by_name:
                continue
            topics_text = ", ".join(str(item) for item in repo.get("topics", []) if str(item).strip())
            readme_text = _fetch_github_readme(session, full_name)
            summary = "\n".join(
                part
                for part in [
                    str(repo.get("description", "")).strip(),
                    f"Topics: {topics_text}" if topics_text else "",
                    f"Language: {repo.get('language', 'unknown')}",
                    f"Stars: {repo.get('stargazers_count', 0)}",
                    f"README:\n{readme_text}" if readme_text else "",
                ]
                if part
            )
            repos_by_name[full_name] = RAGDocument(
                doc_id=_stable_doc_id("github", full_name),
                source="github",
                source_id=full_name,
                title=full_name,
                text=summary,
                abstract=summary,
                url=str(repo.get("html_url", "")).strip(),
                authors=str(repo.get("owner", {}).get("login", "")).strip() if isinstance(repo.get("owner"), dict) else "",
                published=str(repo.get("updated_at", "")).strip(),
                doc_type="general",
                categories=[str(topic.get("category", "")).strip()] if str(topic.get("category", "")).strip() else [],
                metadata={
                    "language": str(repo.get("language", "")).strip(),
                    "stars": int(repo.get("stargazers_count", 0) or 0),
                    "topics": topics_text,
                    "has_readme": bool(readme_text),
                },
            )
            _sleep(0.25)
        # GitHub search has a tighter bucket than standard REST traffic, so keep a hard gap.
        _sleep(2.2)
    return list(repos_by_name.values())


def resolve_pmcid_for_pubmed(pmid: str) -> str:
    response = requests.get(
        "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/",
        params={
            "ids": pmid,
            "idtype": "pmid",
            "format": "json",
            "email": _require_env("NCBI_EMAIL"),
            "tool": "singlecell_agent_rag",
        },
        timeout=30,
    )
    response.raise_for_status()
    _sleep(_ncbi_delay())
    records = response.json().get("records", [])
    for record in records:
        pmcid = str(record.get("pmcid", "")).strip().replace("PMC", "")
        if pmcid:
            return pmcid
    return ""


def _fetch_pmc_xml(pmcid: str) -> str:
    response = _ncbi_get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        db="pmc",
        id=pmcid,
        retmode="xml",
    )
    return response.text


def fetch_pmc_core_document(document: RAGDocument) -> Optional[CoreFetchResult]:
    pmcid = resolve_pmcid_for_pubmed(document.source_id)
    if not pmcid:
        return None
    xml_text = _fetch_pmc_xml(pmcid)
    root = ET.fromstring(xml_text)
    sections = _extract_xml_sections(root)
    methods_text = _extract_methods_from_sections(sections)
    body_text = _chunk_text_blocks("\n\n".join(f"{title}\n{text}" for title, text in sections.items()))
    enriched_text = methods_text or body_text
    if not enriched_text:
        return None
    enriched_doc = RAGDocument(
        doc_id=_stable_doc_id("pmc", pmcid),
        source="pmc",
        source_id=pmcid,
        title=document.title,
        text=enriched_text,
        abstract=document.abstract,
        url=f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/",
        authors=document.authors,
        published=document.published,
        doi=document.doi,
        doc_type="core_methods" if methods_text else "core_full_text",
        categories=list(document.categories),
        metadata={"pmid": document.source_id, "origin_source": "pubmed", "has_methods": bool(methods_text)},
    )
    return CoreFetchResult(
        document=enriched_doc,
        enrichment_source="pmc",
        has_full_text=True,
        extracted_methods=bool(methods_text),
    )


def fetch_biorxiv_core_document(document: RAGDocument) -> Optional[CoreFetchResult]:
    xml_path = str(document.metadata.get("jats_xml_path", "")).strip()
    if not xml_path:
        return None
    xml_url = xml_path if xml_path.startswith("http") else f"https://www.biorxiv.org{xml_path}"
    response = requests.get(xml_url, timeout=30)
    if response.status_code != 200:
        return None
    root = ET.fromstring(response.text)
    sections = _extract_xml_sections(root)
    methods_text = _extract_methods_from_sections(sections)
    body_text = _chunk_text_blocks("\n\n".join(f"{title}\n{text}" for title, text in sections.items()))
    enriched_text = methods_text or body_text
    if not enriched_text:
        return None
    enriched_doc = RAGDocument(
        doc_id=_stable_doc_id("biorxiv-core", f"{document.source_id}:v{version}"),
        source="biorxiv",
        source_id=document.source_id,
        title=document.title,
        text=enriched_text,
        abstract=document.abstract,
        url=document.url,
        authors=document.authors,
        published=document.published,
        doi=document.doi,
        doc_type="core_methods" if methods_text else "core_full_text",
        categories=list(document.categories),
        metadata={
            "version": str(document.metadata.get("version", "1")).strip() or "1",
            "origin_source": "biorxiv",
            "has_methods": bool(methods_text),
            "jats_xml_path": xml_path,
        },
    )
    return CoreFetchResult(
        document=enriched_doc,
        enrichment_source="biorxiv",
        has_full_text=True,
        extracted_methods=bool(methods_text),
    )


def fetch_core_document(document: RAGDocument) -> Optional[CoreFetchResult]:
    if document.source == "pubmed":
        return fetch_pmc_core_document(document)
    if document.source == "biorxiv":
        return fetch_biorxiv_core_document(document)
    return None


def save_manifest(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
