from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Literal, Optional

from . import loaders as _L


Category = Literal[
    "genome",
    "annotation",
    "motifs",
    "atlas",
    "markers",
    "intervals",
    "pathways",
    "tf_targets",
    "ligand_receptor",
    "model",
]


@dataclass(frozen=True)
class ResourceSpec:
    """Declarative record for one static reference the backend can materialize.

    URLs and checksums are pinned. The model never sees URLs; it only picks
    resource names from the manifest keys via enum parameters on tools.
    """

    name: str
    url: str
    sha256: str
    version: str
    category: Category
    loader: Callable
    size_mb: float
    local_filename: Optional[str] = None  # defaults to the URL's basename
    decompress: bool = False              # True if the downloaded file should be gunzipped
    extra: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
# NOTE: SHA256 values below are placeholders. Fill them in once after your
# first successful download (ReferenceStore surfaces the observed hash in its
# mismatch error so you can paste it back here).
# ---------------------------------------------------------------------------

_PLACEHOLDER_SHA = "0" * 64


MANIFEST: Dict[str, ResourceSpec] = {
    # -------------------- Genomes --------------------
    "hg38_genome": ResourceSpec(
        name="hg38_genome",
        url="https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz",
        sha256=_PLACEHOLDER_SHA,
        version="hg38",
        category="genome",
        loader=_L.load_genome_fasta,
        size_mb=3000.0,
        local_filename="hg38.fa",
        decompress=True,
    ),
    "mm10_genome": ResourceSpec(
        name="mm10_genome",
        url="https://hgdownload.soe.ucsc.edu/goldenPath/mm10/bigZips/mm10.fa.gz",
        sha256=_PLACEHOLDER_SHA,
        version="mm10",
        category="genome",
        loader=_L.load_genome_fasta,
        size_mb=2600.0,
        local_filename="mm10.fa",
        decompress=True,
    ),

    # -------------------- Gene annotations --------------------
    "gencode_v44_human": ResourceSpec(
        name="gencode_v44_human",
        url="https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_44/gencode.v44.annotation.gtf.gz",
        sha256=_PLACEHOLDER_SHA,
        version="v44",
        category="annotation",
        loader=_L.load_gtf,
        size_mb=1000.0,
        local_filename="gencode.v44.annotation.gtf",
        decompress=True,
    ),
    "gencode_vM33_mouse": ResourceSpec(
        name="gencode_vM33_mouse",
        url="https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_mouse/release_M33/gencode.vM33.annotation.gtf.gz",
        sha256=_PLACEHOLDER_SHA,
        version="vM33",
        category="annotation",
        loader=_L.load_gtf,
        size_mb=800.0,
        local_filename="gencode.vM33.annotation.gtf",
        decompress=True,
    ),

    # -------------------- Intervals --------------------
    "hg38_blacklist": ResourceSpec(
        name="hg38_blacklist",
        url="https://raw.githubusercontent.com/Boyle-Lab/Blacklist/master/lists/hg38-blacklist.v2.bed.gz",
        sha256=_PLACEHOLDER_SHA,
        version="v2",
        category="intervals",
        loader=_L.load_bed,
        size_mb=0.1,
        local_filename="hg38-blacklist.v2.bed",
        decompress=True,
    ),
    "mm10_blacklist": ResourceSpec(
        name="mm10_blacklist",
        url="https://raw.githubusercontent.com/Boyle-Lab/Blacklist/master/lists/mm10-blacklist.v2.bed.gz",
        sha256=_PLACEHOLDER_SHA,
        version="v2",
        category="intervals",
        loader=_L.load_bed,
        size_mb=0.1,
        local_filename="mm10-blacklist.v2.bed",
        decompress=True,
    ),
    "encode_cCRE_hg38": ResourceSpec(
        name="encode_cCRE_hg38",
        url="https://downloads.wenglab.org/Registry-V4/GRCh38-cCREs.bed",
        sha256=_PLACEHOLDER_SHA,
        version="v4",
        category="intervals",
        loader=_L.load_bed,
        size_mb=10.0,
    ),
    "encode_cCRE_mm10": ResourceSpec(
        name="encode_cCRE_mm10",
        url="https://downloads.wenglab.org/Registry-V4/mm10-cCREs.bed",
        sha256=_PLACEHOLDER_SHA,
        version="v4",
        category="intervals",
        loader=_L.load_bed,
        size_mb=10.0,
    ),

    # -------------------- Motif databases --------------------
    "jaspar2024_core_vertebrates": ResourceSpec(
        name="jaspar2024_core_vertebrates",
        url="https://jaspar.genereg.net/download/data/2024/CORE/JASPAR2024_CORE_non-redundant_pfms_meme.txt",
        sha256=_PLACEHOLDER_SHA,
        version="2024",
        category="motifs",
        loader=_L.load_motifs_meme,
        size_mb=30.0,
    ),
    "cisbp_v2_human": ResourceSpec(
        name="cisbp_v2_human",
        url="http://cisbp.ccbr.utoronto.ca/data/2.00/DataFiles/Bulk_downloads/EntireDataset/PWMs.zip",
        sha256=_PLACEHOLDER_SHA,
        version="v2.00",
        category="motifs",
        loader=_L.load_motifs_cisbp,
        size_mb=50.0,
        extra={"species_filter": "Homo_sapiens"},
    ),

    # -------------------- Marker & ligand-receptor DBs --------------------
    "cellmarker_v2": ResourceSpec(
        name="cellmarker_v2",
        url="http://117.50.127.228/CellMarker/CellMarker_download_files/file/Cell_marker_All.xlsx",
        sha256=_PLACEHOLDER_SHA,
        version="v2",
        category="markers",
        loader=_L.load_cellmarker,
        size_mb=5.0,
    ),
    "panglao_db": ResourceSpec(
        name="panglao_db",
        url="https://panglaodb.se/markers/PanglaoDB_markers_27_Mar_2020.tsv.gz",
        sha256=_PLACEHOLDER_SHA,
        version="2020-03-27",
        category="markers",
        loader=_L.load_panglao,
        size_mb=5.0,
        local_filename="panglao_markers.tsv",
        decompress=True,
    ),
    "omnipath_lr_human": ResourceSpec(
        name="omnipath_lr_human",
        url="https://omnipathdb.org/interactions?types=post_translational&sources=CellChatDB,CellPhoneDB,LIGANDS&genesymbols=yes&license=academic",
        sha256=_PLACEHOLDER_SHA,
        version="latest",
        category="ligand_receptor",
        loader=_L.load_lr_tsv,
        size_mb=5.0,
        local_filename="omnipath_lr_human.tsv",
    ),

    # -------------------- Pathway / GO --------------------
    "msigdb_h_v2023": ResourceSpec(
        name="msigdb_h_v2023",
        url="https://data.broadinstitute.org/gsea-msigdb/msigdb/release/2023.2.Hs/h.all.v2023.2.Hs.symbols.gmt",
        sha256=_PLACEHOLDER_SHA,
        version="2023.2.Hs",
        category="pathways",
        loader=_L.load_gmt,
        size_mb=1.0,
    ),
    "reactome_gmt_human": ResourceSpec(
        name="reactome_gmt_human",
        url="https://reactome.org/download/current/ReactomePathways.gmt.zip",
        sha256=_PLACEHOLDER_SHA,
        version="latest",
        category="pathways",
        loader=_L.load_gmt,
        size_mb=10.0,
        local_filename="ReactomePathways.gmt",
    ),

    # -------------------- TF–target regulatory --------------------
    "dorothea_human": ResourceSpec(
        name="dorothea_human",
        url="https://raw.githubusercontent.com/saezlab/dorothea/master/data/entire_database/entire_database.csv",
        sha256=_PLACEHOLDER_SHA,
        version="latest",
        category="tf_targets",
        loader=_L.load_tf_targets_tsv,
        size_mb=10.0,
        extra={"species": "human"},
    ),
    "trrust_human": ResourceSpec(
        name="trrust_human",
        url="https://www.grnpedia.org/trrust/data/trrust_rawdata.human.tsv",
        sha256=_PLACEHOLDER_SHA,
        version="v2",
        category="tf_targets",
        loader=_L.load_tf_targets_tsv,
        size_mb=1.0,
    ),

    # -------------------- Reference atlases --------------------
    "tabula_sapiens_v1": ResourceSpec(
        name="tabula_sapiens_v1",
        url="https://datasets.cellxgene.cziscience.com/TabulaSapiens.h5ad",
        sha256=_PLACEHOLDER_SHA,
        version="v1",
        category="atlas",
        loader=_L.load_atlas_backed,
        size_mb=5000.0,
    ),

    # -------------------- Pretrained models --------------------
    # Model entries typically require download + additional unpacking. Keep
    # entries here and flesh out the loader for each family as you need them.
}


def list_by_category(category: Optional[str] = None) -> list[ResourceSpec]:
    if category is None:
        return list(MANIFEST.values())
    return [r for r in MANIFEST.values() if r.category == category]
