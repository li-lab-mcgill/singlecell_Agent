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
class eGRN:
    """Result of enhancer-driven GRN inference (SCENIC+).

    Fields:
        n_eregulons:    Number of eRegulons inferred.
        n_tfs:          Number of unique TFs.
        n_regions:      Number of unique regulatory regions.
        n_target_genes: Number of unique target genes.
        eregulons_key:  adata.uns key storing the eRegulon metadata DataFrame.
        metadata:       Additional details (thresholds, run params, etc.)
    """

    n_eregulons: int
    n_tfs: int
    n_regions: int
    n_target_genes: int
    eregulons_key: str = "scenicplus_eregulons"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_eregulons": self.n_eregulons,
            "n_tfs": self.n_tfs,
            "n_regions": self.n_regions,
            "n_target_genes": self.n_target_genes,
            "eregulons_key": self.eregulons_key,
            "metadata": self.metadata,
        }


@dataclass
class VelocityResult:
    """Result of RNA or multi-omic velocity fitting.

    Fields:
        method:              "scvelo" or "multivelo"
        n_velocity_genes:    Number of genes used to compute velocity
        velocity_key:        Primary velocity layer in adata (e.g. "velocity" or "velo_s")
        latent_time_key:     adata.obs key for latent time, None if not yet computed
        model_distribution:  {"1": N, "2": M} for multivelo; {} for scvelo
        mean_likelihood:     Mean per-gene fit likelihood
        params_path:         Optional path to saved gene-level parameter table (parquet)
        metadata:            Additional run parameters (max_iter, init_mode, etc.)
    """

    method: str
    n_velocity_genes: int
    velocity_key: str
    latent_time_key: Optional[str] = None
    model_distribution: Dict[str, int] = field(default_factory=dict)
    mean_likelihood: float = 0.0
    params_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "n_velocity_genes": self.n_velocity_genes,
            "velocity_key": self.velocity_key,
            "latent_time_key": self.latent_time_key,
            "model_distribution": self.model_distribution,
            "mean_likelihood": self.mean_likelihood,
            "params_path": _path_to_str(self.params_path),
            "metadata": self.metadata,
        }


@dataclass
class VelocityDownstreamResult:
    """Result of velocity graph + latent time + optional LRT computation.

    Fields:
        velocity_key:            Velocity layer used to build the graph
        n_velocity_genes_graph:  Genes included in velocity graph
        latent_time_key:         adata.obs key for latent time; None if not computed
        lrt_n_decoupled:         Genes with decoupled epigenome-transcriptome dynamics
        lrt_n_coupled:           Genes with coupled dynamics
        metadata:                Additional details
    """

    velocity_key: str
    n_velocity_genes_graph: int
    latent_time_key: Optional[str] = None
    lrt_n_decoupled: Optional[int] = None
    lrt_n_coupled: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "velocity_key": self.velocity_key,
            "n_velocity_genes_graph": self.n_velocity_genes_graph,
            "latent_time_key": self.latent_time_key,
            "lrt_n_decoupled": self.lrt_n_decoupled,
            "lrt_n_coupled": self.lrt_n_coupled,
            "metadata": self.metadata,
        }


@dataclass
class LRTResult:
    """Result of epigenome–transcriptome decoupling LRT (mv.LRT_decoupling).

    Fields:
        n_genes_tested:  Total genes tested
        n_decoupled:     Genes where chromatin opens before transcription (pval_c < threshold)
        n_coupled:       Genes where chromatin and transcription are coupled
        pct_decoupled:   Percentage of tested genes that are decoupled
        lrt_table_path:  Path to saved per-gene LRT statistics parquet
        metadata:        Threshold and run parameters
    """

    n_genes_tested: int
    n_decoupled: int
    n_coupled: int
    pct_decoupled: float
    lrt_table_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_genes_tested": self.n_genes_tested,
            "n_decoupled": self.n_decoupled,
            "n_coupled": self.n_coupled,
            "pct_decoupled": self.pct_decoupled,
            "lrt_table_path": _path_to_str(self.lrt_table_path),
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
