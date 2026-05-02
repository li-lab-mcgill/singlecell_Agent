"""Dry-run-first cleanup utility for manifest-managed artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def collect_cleanup_candidates(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    candidates: list[dict[str, Any]] = []
    for manifest_path in root.rglob("artifact_manifest.json"):
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in payload.get("artifacts", []):
            if not isinstance(item, dict):
                continue
            if item.get("protected") or item.get("tier") in {"metadata", "best", "result"}:
                continue
            path = Path(str(item.get("path", "")))
            if not path.is_file():
                continue
            candidates.append(
                {
                    "path": str(path),
                    "tier": item.get("tier"),
                    "kind": item.get("kind"),
                    "size_bytes": path.stat().st_size,
                    "manifest": str(manifest_path),
                }
            )
    return {
        "root": str(root),
        "candidate_count": len(candidates),
        "reclaimable_bytes": sum(int(item["size_bytes"]) for item in candidates),
        "candidates": candidates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean manifest-managed single-cell artifacts.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args(argv)

    report = collect_cleanup_candidates(args.root)
    print(json.dumps(report, indent=2))
    if args.dry_run:
        return 0
    for item in report["candidates"]:
        Path(item["path"]).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
