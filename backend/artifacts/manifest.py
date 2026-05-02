"""Artifact manifest helpers for storage-efficient tool runs."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


def file_sha256(path: str | Path, block_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(block_size), b""):
            h.update(chunk)
    return h.hexdigest()


def write_h5ad(adata: Any, path: str | Path, *, compression: bool = True) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if compression:
        try:
            adata.write_h5ad(str(path), compression="gzip")
            return
        except TypeError:
            pass
    adata.write_h5ad(str(path))


class ArtifactManifest:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.items: list[dict[str, Any]] = []

    def record_file(
        self,
        path: str | Path,
        *,
        kind: str,
        tier: str,
        stage: str | None = None,
        path_index: int | None = None,
        protected: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        path = Path(path)
        if not path.exists() or not path.is_file():
            return None
        try:
            rel_path = str(path.relative_to(self.root))
        except ValueError:
            rel_path = str(path)
        item = {
            "path": str(path),
            "relative_path": rel_path,
            "kind": kind,
            "tier": tier,
            "stage": stage,
            "path_index": path_index,
            "size_bytes": path.stat().st_size,
            "sha256": file_sha256(path),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "protected": bool(protected),
        }
        if metadata:
            item["metadata"] = metadata
        self.items.append(item)
        return item

    def write(self, path: str | Path | None = None) -> Path:
        path = Path(path) if path is not None else self.root / "artifact_manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"root": str(self.root), "artifacts": self.items}
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
