from __future__ import annotations

import json
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

import requests

from rag.types import CoreFetchResult, RAGDocument, RAGSection

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


def _retry_get(
    session: requests.Session,
    url: str,
    *,
    params: Optional[Dict[str, object]] = None,
    timeout: int = 30,
    base_delay: float = 0.5,
    max_attempts: int = 4,
    **kwargs: object,
) -> requests.Response:
    last_error: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            response = session.get(url, params=params, timeout=timeout, **kwargs)
            if response.status_code in {429, 500, 502, 503, 504}:
                raise requests.HTTPError(
                    f"request failed with status {response.status_code}",
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
            if attempt == max_attempts - 1 or not retryable:
                break
            backoff = max(base_delay, base_delay * (2**attempt)) + random.uniform(0.0, base_delay / 2)
            _sleep(backoff)
    assert last_error is not None
    raise last_error


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


def normalize_section_type(title: str) -> str:
    cleaned = _normalize_text(title).lower()
    if not cleaned:
        return "supplement"
    if any(token in cleaned for token in ["abstract", "summary"]):
        return "abstract"
    if any(token in cleaned for token in ["introduction", "background"]):
        return "introduction"
    if any(token in cleaned for token in ["methods", "methodology", "materials and methods", "methods and materials", "experimental methods", "approach"]):
        return "methods"
    if "results" in cleaned:
        return "results"
    if any(token in cleaned for token in ["discussion", "interpretation"]):
        return "discussion"
    if any(token in cleaned for token in ["conclusion", "conclusions"]):
        return "conclusion"
    return "supplement"


def _extract_xml_sections(root: ET.Element) -> List[RAGSection]:
    sections: List[RAGSection] = []
    for order, sec in enumerate(root.findall(".//sec")):
        title_elem = sec.find("./title")
        title = _normalize_text(_extract_text_recursive(title_elem))
        if not title:
            continue
        paragraphs = [_normalize_text(_extract_text_recursive(node)) for node in sec.findall("./p")]
        if not paragraphs:
            paragraphs = [_normalize_text(_extract_text_recursive(node)) for node in sec.findall(".//p")]
        content = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
        if not content:
            continue
        section_type = normalize_section_type(title)
        section_id = f"{section_type}:{order}"
        sections.append(
            RAGSection(
                section_id=section_id,
                section_type=section_type,
                heading=title,
                text=content,
                order=order,
                metadata={},
            )
        )
    return sections


def _finalize_sections(sections: List[RAGSection]) -> List[RAGSection]:
    finalized: List[RAGSection] = []
    type_counts: Dict[str, int] = {}
    for order, section in enumerate(sections):
        section_type = normalize_section_type(section.section_type or section.heading)
        type_index = type_counts.get(section_type, 0)
        type_counts[section_type] = type_index + 1
        finalized.append(
            RAGSection(
                section_id=f"{section_type}:{type_index}",
                section_type=section_type,
                heading=section.heading,
                text=section.text,
                order=order,
                metadata=dict(section.metadata),
            )
        )
    return finalized


def _extract_methods_from_sections(sections: List[RAGSection]) -> str:
    if not sections:
        return ""
    selected: List[str] = []
    collecting = False
    for section in sections:
        title = section.heading
        text = section.text
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
    return _retry_get(_NCBI_SESSION, url, params=merged_params, timeout=30, base_delay=base_delay, max_attempts=4)


def _biorxiv_get(session: requests.Session, url: str) -> requests.Response:
    return _retry_get(session, url, timeout=60, base_delay=1.0, max_attempts=4)


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
    queries = [str(query).strip() for query in (queries or []) if str(query).strip()]
    if not queries:
        return []
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
    categories = [str(item) for item in (categories or []) if str(item).strip()]
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
    topics = [topic for topic in (search_topics or []) if isinstance(topic, dict) and str(topic.get("query", "")).strip()]
    if not topics:
        return []
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
    try:
        response = _retry_get(
            _NCBI_SESSION,
            "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/",
            params={
                "ids": pmid,
                "idtype": "pmid",
                "format": "json",
                "email": _require_env("NCBI_EMAIL"),
                "tool": "singlecell_agent_rag",
            },
            timeout=30,
            base_delay=_ncbi_delay(),
        )
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
        return ""
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
    if document.abstract:
        sections = [
            RAGSection(
                section_id="abstract:lead",
                section_type="abstract",
                heading="Abstract",
                text=document.abstract,
                order=-1,
                metadata={},
            )
        ] + sections
    sections = _finalize_sections(sections)
    methods_text = _extract_methods_from_sections(sections)
    body_text = _chunk_text_blocks(
        "\n\n".join(
            f"{section.heading}\n{section.text}"
            for section in sections
            if str(section.text).strip()
        )
    )
    enriched_text = body_text
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
        doc_type="core_full_text",
        categories=list(document.categories),
        metadata={"pmid": document.source_id, "origin_source": "pubmed", "has_methods": bool(methods_text)},
        sections=sections,
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
    version = str(document.metadata.get("version", "1")).strip() or "1"
    xml_url = xml_path if xml_path.startswith("http") else f"https://www.biorxiv.org{xml_path}"
    response = requests.get(xml_url, timeout=30)
    if response.status_code != 200:
        return None
    root = ET.fromstring(response.text)
    sections = _extract_xml_sections(root)
    if document.abstract:
        sections = [
            RAGSection(
                section_id="abstract:lead",
                section_type="abstract",
                heading="Abstract",
                text=document.abstract,
                order=-1,
                metadata={},
            )
        ] + sections
    sections = _finalize_sections(sections)
    methods_text = _extract_methods_from_sections(sections)
    body_text = _chunk_text_blocks(
        "\n\n".join(
            f"{section.heading}\n{section.text}"
            for section in sections
            if str(section.text).strip()
        )
    )
    enriched_text = body_text
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
        doc_type="core_full_text",
        categories=list(document.categories),
        metadata={
            "version": str(document.metadata.get("version", "1")).strip() or "1",
            "origin_source": "biorxiv",
            "has_methods": bool(methods_text),
            "jats_xml_path": xml_path,
        },
        sections=sections,
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
