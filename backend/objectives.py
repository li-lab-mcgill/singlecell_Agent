from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable


@dataclass(frozen=True)
class ObjectiveSpec:
    name: str
    task: str
    direction: str
    metrics: tuple[str, ...]
    available: bool = True
    description: str = ""


CELLTYPE_OBJECTIVE = "cell_type_annotation_default"


OBJECTIVES: Dict[str, ObjectiveSpec] = {
    CELLTYPE_OBJECTIVE: ObjectiveSpec(
        name=CELLTYPE_OBJECTIVE,
        task="cell_type_annotation",
        direction="maximize",
        metrics=("ari", "nmi", "silhouette"),
        description="Combined cell-type annotation objective: 0.4*ARI + 0.4*NMI + 0.2*normalized_ASW.",
    ),
    "clustering_default": ObjectiveSpec(
        name="clustering_default",
        task="clustering",
        direction="maximize",
        metrics=("ari", "nmi", "silhouette"),
        available=False,
        description="Placeholder. Do not select until the objective is implemented.",
    ),
    "integration_default": ObjectiveSpec(
        name="integration_default",
        task="integration",
        direction="maximize",
        metrics=("batch_lisi", "bio_lisi"),
        available=False,
        description="Placeholder. Do not select until the objective is implemented.",
    ),
}


def list_objectives(*, include_unavailable: bool = True) -> list[dict[str, Any]]:
    specs: Iterable[ObjectiveSpec] = OBJECTIVES.values()
    if not include_unavailable:
        specs = [spec for spec in specs if spec.available]
    return [
        {
            "name": spec.name,
            "task": spec.task,
            "direction": spec.direction,
            "metrics": list(spec.metrics),
            "available": spec.available,
            "description": spec.description,
        }
        for spec in specs
    ]


def get_objective(name: str | None) -> ObjectiveSpec | None:
    if not name:
        return None
    return OBJECTIVES.get(str(name).strip())


def default_objective_for_task(task: str | None) -> ObjectiveSpec | None:
    normalized = str(task or "").strip().lower()
    for spec in OBJECTIVES.values():
        if spec.task == normalized and spec.available:
            return spec
    return None


def score_metrics(objective_name: str | None, metrics: Dict[str, Any]) -> float | None:
    """Compute an implemented objective from raw metric values."""
    if not objective_name:
        return None
    objective_name = str(objective_name).strip()
    if objective_name != CELLTYPE_OBJECTIVE:
        return None
    ari = _to_float(metrics.get("ari"))
    nmi = _to_float(metrics.get("nmi"))
    silhouette = _to_float(metrics.get("silhouette"))
    if ari is None or nmi is None or silhouette is None:
        return None
    normalized_asw = (silhouette + 1.0) / 2.0
    return 0.4 * ari + 0.4 * nmi + 0.2 * normalized_asw


def add_objective_score(metrics: Dict[str, Any], objective_name: str | None) -> Dict[str, Any]:
    out = dict(metrics or {})
    score = score_metrics(objective_name, out)
    if score is not None and objective_name:
        out[str(objective_name)] = float(score)
    return out


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
