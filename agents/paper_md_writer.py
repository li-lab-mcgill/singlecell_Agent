"""PaperMDWriter — writes structured paper md files to the paper wiki.

Triggered after PaperJudge confirms a paper is relevant. Extracts structured
content from the paper summary via a single LLM call and writes a markdown
file to wiki/papers/. Updates the PaperWikiIndex in memory.

Papers already present in the wiki (same paper_id) are never rewritten.
All writes are thread-safe — concurrent panelists can trigger this safely.

Usage:
    writer = PaperMDWriter(
        engine_name="gpt-4o-mini",
        client=client,
        session_id="S03",
    )
    writer.write_if_new(paper_summary)       # single paper
    writer.write_batch(paper_summaries)      # multiple papers in parallel
"""

from __future__ import annotations

import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any

from agents.prompt_loader import load_updated_prompt
from wiki.paper_index import get_paper_index

PAPER_MD_WRITER_SYSTEM = load_updated_prompt("paper_md_writer_system")
PAPER_MD_WRITER_PROMPT = load_updated_prompt("paper_md_writer")
PAPER_MD_TEMPLATE = load_updated_prompt("paper_md_template")

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_MAX_EXISTING_SUMMARIES = 20   # max existing papers to include in prompt for extends detection
_MAX_WORKERS = 4               # parallel LLM calls for batch writes


# ---------------------------------------------------------------------------
# PaperMDWriter
# ---------------------------------------------------------------------------

class PaperMDWriter:
    """Writes paper markdown files to wiki/papers/ after retrieval.

    Args:
        engine_name: LLM model for extraction (use a fast/cheap model).
        client:      OpenAI-compatible client.
        session_id:  Current session ID, recorded in frontmatter.
        task_ids:    Available task IDs from the tool wiki taxonomy.
                     Used to identify which tasks a paper belongs to.
    """

    def __init__(
        self,
        *,
        engine_name: str,
        client: Any | None = None,
        session_id: str = "unknown",
        task_ids: list[str] | None = None,
    ):
        if client is None and OpenAI is None:
            raise RuntimeError("openai package is required for PaperMDWriter")
        self.client = client or OpenAI()
        self.engine_name = engine_name
        self.session_id = session_id
        self.task_ids = task_ids or []
        self._index = get_paper_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_if_new(self, paper_summary: dict[str, Any]) -> str | None:
        """Write a paper md file if not already in the wiki.

        Args:
            paper_summary: Dict from PaperJudge output — must have at minimum:
                           title, doc_id. Optionally: published, source, url,
                           abstract, objective, background, analysis,
                           main_findings, limitations.

        Returns:
            paper_id if written, None if already existed or failed.
        """
        # Derive a stable paper_id from doc_id to check existence quickly.
        # Also check DOI/title equivalence because preprints and published
        # versions often arrive with different doc_ids and different DOIs.
        candidate_id = _derive_candidate_id(paper_summary)
        if self._index.has_paper(candidate_id) or _find_duplicate_wiki_paper(self._index, paper_summary):
            return None

        try:
            return self._write_one(paper_summary)
        except Exception as exc:
            logger.warning(
                "PaperMDWriter failed for '%s': %s",
                paper_summary.get("title", "unknown"),
                exc,
            )
            return None

    def write_batch(self, paper_summaries: list[dict[str, Any]]) -> list[str]:
        """Write multiple papers in parallel. Returns list of paper_ids written."""
        if not paper_summaries:
            return []
        written: list[str] = []
        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(paper_summaries))) as pool:
            futures = {
                pool.submit(self.write_if_new, p): p
                for p in paper_summaries
            }
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    written.append(result)
        return written

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write_one(self, paper_summary: dict[str, Any]) -> str | None:
        """Extract structured content via LLM and write md file."""
        # Build prompt context
        existing_summaries = self._existing_papers_summary()
        task_ids_str = "\n".join(f"- {tid}" for tid in sorted(self.task_ids)) or "(none available)"

        prompt = PAPER_MD_WRITER_PROMPT.format(
            title=str(paper_summary.get("title") or ""),
            doc_id=str(paper_summary.get("doc_id") or ""),
            published=str(paper_summary.get("published") or "unknown"),
            source=str(paper_summary.get("source") or ""),
            url=str(paper_summary.get("url") or ""),
            doi=str(paper_summary.get("doi") or ""),
            source_ids=json.dumps(paper_summary.get("source_ids") or {}, ensure_ascii=False),
            full_text_status=str(paper_summary.get("full_text_status") or "abstract_only"),
            retrieval_goal=str(paper_summary.get("retrieval_goal") or ""),
            retrieval_intent=str(paper_summary.get("retrieval_intent") or ""),
            abstract=str(paper_summary.get("abstract") or ""),
            objective=str(paper_summary.get("objective") or paper_summary.get("abstract") or ""),
            background=str(paper_summary.get("background") or ""),
            analysis=str(paper_summary.get("analysis") or paper_summary.get("key_methods") or ""),
            benchmark_methods=str(paper_summary.get("benchmark_methods") or ""),
            main_findings=str(paper_summary.get("main_findings") or ""),
            limitations=str(paper_summary.get("limitations") or ""),
            figure_captions=str(paper_summary.get("figure_captions") or ""),
            evidence_contribution=str(paper_summary.get("evidence_contribution") or ""),
            covered_evidence_patterns=json.dumps(paper_summary.get("covered_evidence_patterns") or [], ensure_ascii=False),
            missing_evidence=json.dumps(paper_summary.get("missing_evidence") or [], ensure_ascii=False),
            task_ids=task_ids_str,
            existing_papers_summary=existing_summaries,
        )

        text = self._llm(prompt)
        payload = _extract_json(text)
        if not isinstance(payload, dict):
            return None

        paper_id = _sanitize_paper_id(str(payload.get("paper_id") or ""))
        if not paper_id:
            paper_id = _derive_candidate_id(paper_summary)

        # If still exists (race condition), skip
        if self._index.has_paper(paper_id) or _find_duplicate_wiki_paper(self._index, paper_summary):
            return None

        md_content = _render_md(
            payload=payload,
            paper_id=paper_id,
            title=str(paper_summary.get("title") or ""),
            session=self.session_id,
        )

        added = self._index.add_paper(paper_id=paper_id, md_content=md_content)
        if added:
            logger.info("PaperMDWriter: added '%s' → wiki/papers/%s.md", paper_id, paper_id)
            return paper_id
        return None

    def _existing_papers_summary(self) -> str:
        """Build a compact summary of existing wiki papers for extends detection."""
        index = self._index
        summaries: list[str] = []
        count = 0
        # Iterate over all papers — just need paper_id + title + first line of content
        for pid in sorted(index._papers.keys()):
            node = index._papers.get(pid)
            if node is None:
                continue
            first_line = node.content.split("\n")[0][:120] if node.content else ""
            summaries.append(f"- {pid}: {node.title or first_line}")
            count += 1
            if count >= _MAX_EXISTING_SUMMARIES:
                break
        return "\n".join(summaries) if summaries else "(wiki is empty — no existing papers)"

    def _llm(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.engine_name,
            input=[
                {"role": "system", "content": PAPER_MD_WRITER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        text = str(getattr(response, "output_text", "") or "").strip()
        if not text:
            for item in getattr(response, "output", []):
                content = getattr(item, "content", None)
                if isinstance(content, str):
                    return content.strip()
                elif isinstance(content, list):
                    for part in content:
                        t = getattr(part, "text", None)
                        if isinstance(t, str) and t.strip():
                            return t.strip()
        return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _derive_candidate_id(paper_summary: dict[str, Any]) -> str:
    """Derive a stable candidate paper_id from doc_id or title."""
    doc_id = str(paper_summary.get("doc_id") or "")
    if doc_id:
        # sanitize: replace non-alphanum with _, lowercase, truncate
        clean = re.sub(r"[^a-z0-9]+", "_", doc_id.lower()).strip("_")
        return clean[:60]
    # Fallback: slug from title
    title = str(paper_summary.get("title") or "")
    return _sanitize_paper_id(title[:40])


def _find_duplicate_wiki_paper(index: Any, paper_summary: dict[str, Any]) -> str | None:
    """Return an existing paper_id if the summary matches an indexed paper.

    This intentionally treats exact normalized-title matches as duplicates even
    when DOI/doc_id differ, which catches common preprint vs published records.
    """
    doi = _normalize_doi(paper_summary.get("doi"))
    title = _normalize_title(paper_summary.get("title"))
    source_ids = paper_summary.get("source_ids") if isinstance(paper_summary.get("source_ids"), dict) else {}
    identifiers = {
        str(paper_summary.get("doc_id") or "").strip().lower(),
        str(paper_summary.get("paper_id") or "").strip().lower(),
        str(source_ids.get("doc_id") or "").strip().lower(),
        str(source_ids.get("pmid") or "").strip().lower(),
        str(source_ids.get("pmcid") or "").strip().lower(),
        str(source_ids.get("semantic_scholar_id") or "").strip().lower(),
        str(source_ids.get("openalex_id") or "").strip().lower(),
    }
    identifiers.discard("")
    for node in getattr(index, "_papers", {}).values():
        metadata = getattr(node, "metadata", {}) or {}
        existing_source_ids = metadata.get("source_ids") if isinstance(metadata.get("source_ids"), dict) else {}
        existing_identifiers = {
            str(getattr(node, "paper_id", "") or "").strip().lower(),
            str(existing_source_ids.get("doc_id") or "").strip().lower(),
            str(existing_source_ids.get("pmid") or "").strip().lower(),
            str(existing_source_ids.get("pmcid") or "").strip().lower(),
            str(existing_source_ids.get("semantic_scholar_id") or "").strip().lower(),
            str(existing_source_ids.get("openalex_id") or "").strip().lower(),
        }
        existing_identifiers.discard("")
        if identifiers and identifiers & existing_identifiers:
            return str(getattr(node, "paper_id", "") or "")
        if doi and doi == _normalize_doi(metadata.get("doi")):
            return str(getattr(node, "paper_id", "") or "")
        if title and title == _normalize_title(getattr(node, "title", "")):
            return str(getattr(node, "paper_id", "") or "")
    return None


def _normalize_doi(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.strip()


def _normalize_title(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[\W_]+", " ", text)
    text = re.sub(r"\b(preprint|published|version|revised)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _sanitize_paper_id(raw: str) -> str:
    """Sanitize a string into a valid paper_id (lowercase, underscores, max 60 chars)."""
    clean = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return clean[:60] if clean else "unknown"


def _extract_json(text: str) -> Any:
    cleaned = str(text or "").strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        # Try to find first { ... } block
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except Exception:
                pass
    return {}


def _render_md(
    *,
    payload: dict[str, Any],
    paper_id: str,
    title: str,
    session: str,
) -> str:
    """Render the paper md file from extracted payload."""
    tasks = payload.get("tasks") or []
    extends = payload.get("extends") or []
    source_ids = payload.get("source_ids") or {}
    if not isinstance(source_ids, dict):
        source_ids = {}

    tasks_yaml = _yaml_list(tasks)
    extends_yaml = _yaml_list(extends)
    retrieval_goals_yaml = _yaml_list(payload.get("retrieval_goals") or [])
    retrieval_intents_yaml = _yaml_list(payload.get("retrieval_intents") or [])
    source_ids_yaml = _yaml_dict(source_ids)

    return PAPER_MD_TEMPLATE.format(
        paper_id=paper_id,
        title=(title or payload.get("title") or "").replace('"', '\\"'),
        doi=str(payload.get("doi") or "").replace('"', '\\"'),
        url=str(payload.get("url") or "").replace('"', '\\"'),
        source_ids_yaml=source_ids_yaml,
        full_text_status=str(payload.get("full_text_status") or "abstract_only").replace('"', '\\"'),
        tasks_yaml=tasks_yaml,
        retrieval_goals_yaml=retrieval_goals_yaml,
        retrieval_intents_yaml=retrieval_intents_yaml,
        extends_yaml=extends_yaml,
        added=date.today().isoformat(),
        session=session,
        summary=str(payload.get("summary") or ""),
        background=str(payload.get("background") or ""),
        method_and_dataset=str(payload.get("method_and_dataset") or ""),
        analysis=str(payload.get("analysis") or payload.get("methods_used") or ""),
        benchmark_methods=str(payload.get("benchmark_methods") or ""),
        key_findings=str(payload.get("key_findings") or ""),
        limitations=str(payload.get("limitations") or ""),
        metrics_used=str(payload.get("metrics_used") or ""),
        figure_captions=str(payload.get("figure_captions") or ""),
    )


def _yaml_list(items: list[str]) -> str:
    """Render a list as inline YAML: [a, b, c]."""
    if not items:
        return "[]"
    cleaned = [str(item).replace('"', '\\"') for item in items if str(item).strip()]
    return "[" + ", ".join(f'"{item}"' for item in cleaned) + "]"


def _yaml_dict(items: dict[str, Any]) -> str:
    if not items:
        return "{}"
    parts = []
    for key, value in items.items():
        clean_key = re.sub(r"[^a-zA-Z0-9_]+", "_", str(key)).strip("_") or "id"
        clean_value = str(value or "").replace('"', '\\"')
        parts.append(f'{clean_key}: "{clean_value}"')
    return "{" + ", ".join(parts) + "}"
