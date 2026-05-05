"""Tool registry: scans backend/tools/**/*.py at startup and builds a lookup table.

Tool ID convention: {modality}_{stage}_{toolname}
  e.g.  backend/tools/rna/cluster/leiden.py  →  rna_cluster_leiden
        backend/tools/atac/embed/lsi.py       →  atac_embed_lsi
        backend/tools/eval/ari_nmi.py         →  eval_ari_nmi

Each tool file must expose a single callable named `run`.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from types import ModuleType
from typing import Callable

_TOOLS_DIR = Path(__file__).parent


def _path_to_tool_id(path: Path) -> str:
    """Convert a tool file path to its canonical tool ID.

    backend/tools/rna/cluster/leiden.py  →  rna_cluster_leiden
    backend/tools/eval/ari_nmi.py        →  eval_ari_nmi
    """
    rel = path.relative_to(_TOOLS_DIR)
    parts = list(rel.with_suffix("").parts)
    # Drop single-part paths that aren't real tools (e.g. __init__)
    return "_".join(parts)


def _module_name(path: Path) -> str:
    rel = path.relative_to(_TOOLS_DIR.parent.parent)  # relative to project root
    return str(rel.with_suffix("")).replace("/", ".")


def build_registry() -> dict[str, Callable]:
    """Scan all tool files and return {tool_id: run_fn} mapping."""
    registry: dict[str, Callable] = {}
    for path in sorted(_TOOLS_DIR.rglob("*.py")):
        if path.name.startswith("_") or path.name == "registry.py":
            continue
        parts = path.relative_to(_TOOLS_DIR).with_suffix("").parts
        if not parts:
            continue
        tool_id = "_".join(parts)
        module_dotted = "backend.tools." + ".".join(parts)
        try:
            module: ModuleType = importlib.import_module(module_dotted)
        except Exception as exc:
            # Lazy import errors (missing optional deps) are silenced at scan time.
            # The error surfaces only when the tool is actually called.
            registry[tool_id] = _make_deferred(module_dotted, exc)
            continue
        if not hasattr(module, "run"):
            continue
        registry[tool_id] = module.run
    return registry


def _make_deferred(module_dotted: str, original_exc: Exception) -> Callable:
    """Return a stub that re-raises the import error at call time."""
    def _deferred(*args, **kwargs):
        raise ImportError(
            f"Tool '{module_dotted}' could not be imported at registry build time: {original_exc}"
        ) from original_exc
    _deferred.__name__ = module_dotted
    return _deferred


# Singleton registry — built once on first import.
_registry: dict[str, Callable] | None = None


def get_registry() -> dict[str, Callable]:
    global _registry
    if _registry is None:
        _registry = build_registry()
    return _registry


def get_tool(tool_id: str) -> Callable:
    """Retrieve a tool's run() function by its ID. Raises KeyError if not found."""
    registry = get_registry()
    if tool_id not in registry:
        available = sorted(registry.keys())
        raise KeyError(
            f"Tool '{tool_id}' not found in registry. "
            f"Available tools ({len(available)}): {available[:20]}{'...' if len(available) > 20 else ''}"
        )
    return registry[tool_id]
