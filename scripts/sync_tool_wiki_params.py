"""Sync the parameter documentation in wiki/tools/*.md with the actual run() signatures.

For each registered tool, reads the run() signature and rewrites the
"Key parameters:" section in the corresponding wiki file to match exactly.
Params the consultant should not see (output keys, executor-managed) are excluded.

Usage:
    python scripts/sync_tool_wiki_params.py          # dry-run, shows diffs
    python scripts/sync_tool_wiki_params.py --write  # applies changes

Run this after modifying any tool's run() signature or after writing a new tool.
"""

from __future__ import annotations

import argparse
import inspect
import re
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.tools.registry import get_registry  # noqa: E402

# Params the executor supplies — never documented in wiki
EXECUTOR_PARAMS = {"input_h5ad_path", "output_h5ad_path", "output_dir", "method"}

# Output key params — executor-internal, not documented for consultant
# (these are OUTPUTS, not inputs the consultant sets)
OUTPUT_KEY_PARAMS = {"embedding_key", "cluster_key", "projection_key"}

WIKI_DIR = ROOT / "wiki" / "tools"


def get_consultant_params(tool_id: str, run_fn) -> list[dict]:
    """Return params the consultant should set, with name, default, and annotation."""
    try:
        sig = inspect.signature(run_fn)
    except (ValueError, TypeError):
        return []

    # Detect whether embedding_key is an OUTPUT (embed tools) or INPUT (others)
    # Embed tools: stage is "embed" — embedding_key is output, hide it
    # Cluster/project/batch tools: embedding_key is input, keep it
    stage = tool_id.split("_")[1] if tool_id.count("_") >= 1 else ""
    hide_embedding_key = stage == "embed"
    hide_cluster_key = stage == "cluster"
    hide_projection_key = stage == "project"

    params = []
    for name, param in sig.parameters.items():
        if name == "adata":
            continue
        if name in EXECUTOR_PARAMS:
            continue
        if hide_embedding_key and name == "embedding_key":
            continue
        if hide_cluster_key and name == "cluster_key":
            continue
        if hide_projection_key and name == "projection_key":
            continue

        default = param.default
        annotation = param.annotation

        params.append({
            "name": name,
            "required": default is inspect.Parameter.empty,
            "default": None if default is inspect.Parameter.empty else default,
            "annotation": annotation if annotation is not inspect.Parameter.empty else None,
        })
    return params


def format_param_line(p: dict) -> str:
    name = p["name"]
    if p["required"]:
        return f"- `{name}` (required)"
    default = p["default"]
    if isinstance(default, str):
        default_str = f'"{default}"'
    elif default is None:
        default_str = "None"
    else:
        default_str = str(default)
    return f"- `{name}` (default {default_str})"


def build_params_section(params: list[dict]) -> str:
    if not params:
        return ""
    lines = ["Key parameters:"] + [format_param_line(p) for p in params]
    return "\n".join(lines)


def update_wiki_params(wiki_path: Path, new_params_section: str) -> tuple[str, str] | None:
    """Return (old_content, new_content) or None if no change needed."""
    content = wiki_path.read_text(encoding="utf-8")

    # Find existing "Key parameters:" block (up to next blank line followed by non-bullet)
    pattern = re.compile(
        r"(Key parameters:(?:\n- `[^`]+`[^\n]*)*)(\n)",
        re.MULTILINE,
    )
    match = pattern.search(content)

    if match:
        old_section = match.group(1)
        if old_section.strip() == new_params_section.strip():
            return None  # already in sync
        new_content = content[:match.start(1)] + new_params_section + content[match.end(1):]
    else:
        # No existing section — insert before the first non-frontmatter paragraph
        # Find end of frontmatter
        fm_end = content.find("---", 3)
        if fm_end == -1:
            return None
        insert_pos = fm_end + 3
        # Skip blank lines after frontmatter
        while insert_pos < len(content) and content[insert_pos] in ("\n", "\r"):
            insert_pos += 1
        # Find end of first paragraph
        para_end = content.find("\n\n", insert_pos)
        if para_end == -1:
            para_end = len(content)
        new_content = (
            content[:para_end + 2]
            + new_params_section + "\n\n"
            + content[para_end + 2:]
        )

    return content, new_content


def main():
    parser = argparse.ArgumentParser(description="Sync wiki param docs with run() signatures")
    parser.add_argument("--write", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--tool", help="Only process this tool ID")
    args = parser.parse_args()

    registry = get_registry()
    changed = []
    missing_wiki = []

    for tool_id, run_fn in sorted(registry.items()):
        if args.tool and tool_id != args.tool:
            continue

        wiki_path = WIKI_DIR / f"{tool_id}.md"
        if not wiki_path.exists():
            missing_wiki.append(tool_id)
            continue

        params = get_consultant_params(tool_id, run_fn)
        if not params:
            continue  # no consultant params to document

        new_section = build_params_section(params)
        result = update_wiki_params(wiki_path, new_section)

        if result is None:
            continue  # already in sync

        old_content, new_content = result
        changed.append(tool_id)

        if args.write:
            wiki_path.write_text(new_content, encoding="utf-8")
            print(f"[updated] {tool_id}")
        else:
            print(f"[drift]   {tool_id}")
            # Show old vs new params section
            old_params = re.search(r"Key parameters:(?:\n- `[^`]+`[^\n]*)*", old_content)
            if old_params:
                print(f"  OLD: {old_params.group(0)[:200]}")
            print(f"  NEW: {new_section[:200]}")
            print()

    if missing_wiki:
        print(f"\nNo wiki file found for: {missing_wiki}")
    if not changed:
        print("All wiki params are in sync with run() signatures.")
    elif not args.write:
        print(f"\n{len(changed)} tool(s) out of sync. Run with --write to apply.")


if __name__ == "__main__":
    main()
