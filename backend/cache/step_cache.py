"""Hash-keyed cache for pipeline step outputs.

Key = sha256(input_sha16 | stage | sorted_json(params)). A cache hit means
"the exact same input, exact same stage, exact same params produced this
output before"; we can reuse it without re-running the stage.

Expected hit rate during a TPE sweep: 50-80% on early stages (QC, normalize)
since they stay constant while later stages vary.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional


def sha256_file(path: str | Path, block_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            h.update(chunk)
    return h.hexdigest()


class StepCache:
    def __init__(self, cache_dir: Path, *, max_gb: float | None = None, use_hardlinks: bool = True):
        self.cache_dir = Path(cache_dir) / "trials"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_gb = max_gb
        self.use_hardlinks = use_hardlinks
        self._lock = threading.Lock()

    def key(self, input_sha: str, stage: str, params: Dict[str, Any]) -> str:
        payload = f"{input_sha[:16]}|{stage}|{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _slot(self, key: str) -> Path:
        return self.cache_dir / key[:2] / key

    def has(self, key: str) -> bool:
        return (self._slot(key) / "output.h5ad").exists()

    def has_dir(self, key: str) -> bool:
        slot = self._slot(key)
        return (slot / "meta.json").exists() or (slot / "output.h5ad").exists() or (slot / "stage_dir").is_dir()

    def get(self, key: str) -> Path:
        return self._slot(key) / "output.h5ad"

    def get_meta(self, key: str) -> Dict[str, Any]:
        meta_path = self._slot(key) / "meta.json"
        if not meta_path.exists():
            return {}
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def put(self, key: str, src_path: str | Path, *, meta: Optional[Dict[str, Any]] = None) -> Path:
        slot = self._slot(key)
        slot.mkdir(parents=True, exist_ok=True)
        dest = slot / "output.h5ad"
        with self._lock:
            _copy_or_link(src_path, dest, use_hardlinks=self.use_hardlinks)
            meta_path = slot / "meta.json"
            meta_payload = dict(meta or {})
            meta_payload["managed_cache_version"] = 2
            meta_payload["cached_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            meta_path.write_text(json.dumps(meta_payload, indent=2))
            self._evict_if_needed()
        return dest

    def put_dir(self, key: str, src_dir: str | Path, *, meta: Optional[Dict[str, Any]] = None) -> Path:
        slot = self._slot(key)
        src_dir = Path(src_dir)
        with self._lock:
            slot.mkdir(parents=True, exist_ok=True)
            legacy_stage_dir = slot / "stage_dir"
            if legacy_stage_dir.exists():
                shutil.rmtree(legacy_stage_dir)
            output_h5ad = src_dir / "output.h5ad"
            if output_h5ad.exists():
                _copy_or_link(output_h5ad, slot / "output.h5ad", use_hardlinks=self.use_hardlinks)
            meta_payload = dict(meta or {})
            meta_payload["cached_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            result_path = src_dir / "result.json"
            if result_path.exists() and "stage_result" not in meta_payload:
                try:
                    meta_payload["stage_result"] = json.loads(result_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            meta_payload["managed_cache_version"] = 2
            (slot / "meta.json").write_text(json.dumps(meta_payload, indent=2))
            self._evict_if_needed()
        return slot

    def restore_dir_to(self, key: str, dest_dir: str | Path) -> Path:
        slot = self._slot(key)
        legacy_src = slot / "stage_dir"
        dest = Path(dest_dir)
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if legacy_src.is_dir():
            shutil.copytree(str(legacy_src), str(dest))
            return dest
        dest.mkdir(parents=True, exist_ok=True)
        output = slot / "output.h5ad"
        if output.exists():
            _copy_or_link(output, dest / "output.h5ad", use_hardlinks=self.use_hardlinks)
        meta = self.get_meta(key)
        if meta.get("stage_result") is not None:
            (dest / "result.json").write_text(json.dumps(meta["stage_result"], indent=2), encoding="utf-8")
        return dest

    def copy_to(self, key: str, dest: str | Path) -> Path:
        """Copy a cached output to an arbitrary path."""
        src = self.get(key)
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        _copy_or_link(src, dest, use_hardlinks=self.use_hardlinks)
        return dest

    def clear(self) -> None:
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _evict_if_needed(self) -> None:
        if not self.max_gb or self.max_gb <= 0:
            return
        max_bytes = int(self.max_gb * 1024 * 1024 * 1024)
        files = []
        for path in self.cache_dir.rglob("output.h5ad"):
            if not path.is_file():
                continue
            key = path.parent.name
            meta = self.get_meta(key)
            if meta.get("managed_cache_version") == 2:
                files.append(path)
        total = sum(path.stat().st_size for path in files)
        if total <= max_bytes:
            return
        files.sort(key=lambda path: (path.stat().st_mtime, -path.stat().st_size))
        for path in files:
            if total <= max_bytes:
                break
            meta = self.get_meta(path.parent.name)
            if meta.get("protected"):
                continue
            size = path.stat().st_size
            shutil.rmtree(path.parent, ignore_errors=True)
            total -= size


def _copy_or_link(src: str | Path, dest: str | Path, *, use_hardlinks: bool) -> None:
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    if use_hardlinks:
        try:
            os.link(src, dest)
            return
        except Exception:
            pass
    shutil.copy2(str(src), str(dest))
