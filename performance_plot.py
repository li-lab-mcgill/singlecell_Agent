import argparse
import json
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def natural_step_key(path: Path):
    m = re.search(r"step_(\d+)", path.name)
    return int(m.group(1)) if m else math.inf


def load_json(path: Path):
    with open(path, "r") as f:
        return json.load(f)


def load_jsonl(path: Path):
    rows = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results_dir", required=True, help="Path to results folder")
    parser.add_argument("--notes_dir", required=True, help="Path to notes folder")
    parser.add_argument("--output", default="single_plan_plot.png")
    parser.add_argument("--line_mode", choices=["per_step", "cumulative"], default="per_step")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    notes_dir = Path(args.notes_dir)

    step_root = results_dir / "intermediate_output"
    step_dirs = sorted(
        [p for p in step_root.iterdir() if p.is_dir() and re.match(r"step_\d+", p.name)],
        key=natural_step_key
    )

    history_path = notes_dir / "history_notes.jsonl"
    history_rows = load_jsonl(history_path)
    attempts_by_step = {
        int(row["step"]): float(row.get("attempts_used", np.nan))
        for row in history_rows if "step" in row
    }

    iterations = []
    aris = []
    attempts = []

    for step_dir in step_dirs:
        step_num = natural_step_key(step_dir)
        metrics_path = step_dir / "cluster_metrics.json"

        ari = np.nan
        if metrics_path.exists():
            data = load_json(metrics_path)
            ari = float(data["ari"]) if "ari" in data else np.nan

        iterations.append(step_num + 1)
        aris.append(ari)
        attempts.append(attempts_by_step.get(step_num, np.nan))

    iterations = np.array(iterations)
    aris = np.array(aris, dtype=float)
    attempts = np.array(attempts, dtype=float)

    if args.line_mode == "cumulative":
        attempts = np.nancumsum(attempts)

    best_ari = np.nanmax(aris)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(iterations, aris, alpha=0.5)
    ax.set_xlabel("Iterations")
    ax.set_ylabel("ARI")
    ax.set_ylim(0, 1.0)
    ax.set_xticks(iterations)
    ax.set_title(f"Best ARI: {best_ari:.3f}", fontweight="bold")

    ax2 = ax.twinx()
    ax2.plot(iterations, attempts, marker="o")
    ymax = max(10, int(np.nanmax(attempts)) + 1) if not np.all(np.isnan(attempts)) else 1
    ax2.set_ylim(0, ymax)
    ax2.set_ylabel("Number of Attempts")

    plt.tight_layout()
    plt.savefig(args.output, dpi=300, bbox_inches="tight")
    print(f"Saved plot to {args.output}")


if __name__ == "__main__":
    main()