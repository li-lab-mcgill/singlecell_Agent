from __future__ import annotations

import collections
import hashlib
import gzip
import shutil
import threading
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import BackendConfig
from ..types import ResourceMetadata
from .manifest import MANIFEST, ResourceSpec, list_by_category


class ReferenceStore:
    """Single owner of all static reference data.

    Three-tier resolution: in-memory cache → on-disk cache → fetch from URL.
    Downloads are SHA256-verified against the manifest; corrupted files are
    removed and a clear error is raised so the model can pick an alternative.

    The model never sees URLs. It picks reference *names* (manifest keys) via
    enum parameters on tools; sub-backend methods then call ``refs.get_*(name)``
    or ``refs.get(name)`` to materialize the bytes.
    """

    def __init__(self, config: BackendConfig, manifest: Optional[Dict[str, ResourceSpec]] = None):
        self.config = config
        self.manifest = manifest or MANIFEST
        self.disk_dir = config.cache_dir / "refs"
        self.disk_dir.mkdir(parents=True, exist_ok=True)
        self._memory: "collections.OrderedDict[str, Any]" = collections.OrderedDict()
        self._memory_size_mb: Dict[str, float] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public discovery / preload API (used by ReferenceToolkit)
    # ------------------------------------------------------------------
    def list_available(self, category: Optional[str] = None) -> List[ResourceMetadata]:
        specs = list_by_category(category) if category else list(self.manifest.values())
        return [self._metadata(spec) for spec in specs]

    def info(self, name: str) -> ResourceMetadata:
        spec = self._spec(name)
        return self._metadata(spec)

    def ensure_loaded(self, name: str) -> None:
        self._resolve(name)

    def clear(self, name: Optional[str] = None) -> None:
        with self._lock:
            if name is None:
                self._memory.clear()
                self._memory_size_mb.clear()
            elif name in self._memory:
                del self._memory[name]
                self._memory_size_mb.pop(name, None)

    # ------------------------------------------------------------------
    # Typed accessors used by sub-backends
    # ------------------------------------------------------------------
    def get(self, name: str) -> Any:
        return self._resolve(name)

    def get_genome(self, build: str) -> Any:
        return self._resolve(build if build.endswith("_genome") else f"{build}_genome")

    def get_gtf(self, name: str) -> Any:
        return self._resolve(name)

    def get_motifs(self, db: str) -> Any:
        return self._resolve(db)

    def get_atlas(self, name: str) -> Any:
        return self._resolve(name)

    def get_marker_db(self, name: str = "cellmarker_v2") -> Any:
        return self._resolve(name)

    def get_cCRE(self, build: str) -> Any:
        return self._resolve(f"encode_cCRE_{build}")

    def get_blacklist(self, build: str) -> Any:
        return self._resolve(f"{build}_blacklist")

    def get_pathway_db(self, name: str) -> Any:
        return self._resolve(name)

    def get_tf_targets(self, name: str) -> Any:
        return self._resolve(name)

    def get_lr_db(self, name: str = "omnipath_lr_human") -> Any:
        return self._resolve(name)

    def get_pretrained_model(self, name: str) -> Any:
        return self._resolve(name)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _spec(self, name: str) -> ResourceSpec:
        if name not in self.manifest:
            available = sorted(self.manifest.keys())
            raise KeyError(
                f"Unknown reference '{name}'. Available: {available}. "
                "Add a new entry to backend/refs/manifest.py to use a new resource."
            )
        return self.manifest[name]

    def _resolve(self, name: str) -> Any:
        with self._lock:
            if name in self._memory:
                # Touch for LRU.
                self._memory.move_to_end(name)
                return self._memory[name]

        spec = self._spec(name)
        on_disk = self._on_disk_path(spec)
        if not on_disk.exists():
            self._download(spec, on_disk)

        loaded = spec.loader(on_disk)
        with self._lock:
            self._memory[name] = loaded
            self._memory_size_mb[name] = spec.size_mb
            self._evict_if_over_budget()
        return loaded

    def _on_disk_path(self, spec: ResourceSpec) -> Path:
        category_dir = self.disk_dir / spec.category / spec.version
        category_dir.mkdir(parents=True, exist_ok=True)
        if spec.local_filename:
            return category_dir / spec.local_filename
        # Fall back to URL basename.
        basename = spec.url.rsplit("/", 1)[-1].split("?", 1)[0]
        if spec.decompress and basename.endswith(".gz"):
            basename = basename[:-3]
        return category_dir / basename

    def _download(self, spec: ResourceSpec, dest: Path) -> None:
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            self._http_download(spec.url, tmp)
            if spec.decompress and spec.url.endswith(".gz"):
                self._gunzip(tmp, dest)
                tmp.unlink(missing_ok=True)
            else:
                shutil.move(str(tmp), str(dest))
            self._verify_sha256(dest, spec)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def _http_download(self, url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "sc-agent/1.0"})
        with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out, length=1024 * 1024)

    def _gunzip(self, src: Path, dest: Path) -> None:
        with gzip.open(src, "rb") as f_in, open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out, length=1024 * 1024)

    def _verify_sha256(self, path: Path, spec: ResourceSpec) -> None:
        # Allow placeholder hashes during initial setup. After the first
        # successful download, replace the placeholder in the manifest with
        # the observed hash printed below.
        if set(spec.sha256) == {"0"}:
            observed = self._sha256(path)
            print(
                f"[refs] {spec.name}: manifest sha256 is placeholder. "
                f"Observed sha256={observed}. "
                "Paste this into manifest.py to enable integrity checks."
            )
            return
        observed = self._sha256(path)
        if observed.lower() != spec.sha256.lower():
            path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Checksum mismatch for {spec.name}: expected {spec.sha256}, got {observed}. "
                "Downloaded file removed."
            )

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _evict_if_over_budget(self) -> None:
        budget = self.config.memory_budget_gb * 1024.0
        total = sum(self._memory_size_mb.values())
        while total > budget and len(self._memory) > 1:
            name, _ = self._memory.popitem(last=False)
            total -= self._memory_size_mb.pop(name, 0.0)

    def _metadata(self, spec: ResourceSpec) -> ResourceMetadata:
        return ResourceMetadata(
            name=spec.name,
            category=spec.category,
            version=spec.version,
            size_mb=spec.size_mb,
            loaded_in_memory=spec.name in self._memory,
            on_disk=self._on_disk_path(spec).exists(),
            source_url=spec.url,
        )
