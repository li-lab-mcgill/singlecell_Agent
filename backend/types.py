from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _path_to_str(p: Optional[Path]) -> Optional[str]:
    return str(p) if p is not None else None


@dataclass
class DEResult:
    """Differential expression / accessibility result."""

    method: str
    group_key: str
    n_groups: int
    n_genes: int
    table_path: Optional[Path] = None
    top_per_group: Dict[str, List[str]] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "group_key": self.group_key,
            "n_groups": self.n_groups,
            "n_genes": self.n_genes,
            "table_path": _path_to_str(self.table_path),
            "top_per_group": self.top_per_group,
            "metrics": self.metrics,
        }


@dataclass
class PeakCallResult:
    method: str
    peaks_path: Path
    n_peaks: int
    frip: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "peaks_path": str(self.peaks_path),
            "n_peaks": self.n_peaks,
            "frip": self.frip,
            "metrics": self.metrics,
        }


@dataclass
class MotifResult:
    method: str
    motif_db: str
    n_motifs: int
    table_path: Optional[Path] = None
    enrichment: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "motif_db": self.motif_db,
            "n_motifs": self.n_motifs,
            "table_path": _path_to_str(self.table_path),
            "enrichment": self.enrichment,
        }


@dataclass
class LinkSet:
    method: str
    n_links: int
    links_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "n_links": self.n_links,
            "links_path": _path_to_str(self.links_path),
            "metadata": self.metadata,
        }


@dataclass
class CCCResult:
    method: str
    n_pairs: int
    table_path: Optional[Path] = None
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "n_pairs": self.n_pairs,
            "table_path": _path_to_str(self.table_path),
            "summary": self.summary,
        }


@dataclass
class JointDEResult:
    method: str
    group_key: str
    rna_table_path: Optional[Path] = None
    atac_table_path: Optional[Path] = None
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "group_key": self.group_key,
            "rna_table_path": _path_to_str(self.rna_table_path),
            "atac_table_path": _path_to_str(self.atac_table_path),
            "summary": self.summary,
        }


@dataclass
class GRN:
    method: str
    n_tfs: int
    n_targets: int
    n_edges: int
    edges_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "n_tfs": self.n_tfs,
            "n_targets": self.n_targets,
            "n_edges": self.n_edges,
            "edges_path": _path_to_str(self.edges_path),
            "metadata": self.metadata,
        }


@dataclass
class ResourceMetadata:
    name: str
    category: str
    version: str
    size_mb: float
    loaded_in_memory: bool
    on_disk: bool
    source_url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "size_mb": self.size_mb,
            "loaded_in_memory": self.loaded_in_memory,
            "on_disk": self.on_disk,
            "source_url": self.source_url,
        }
