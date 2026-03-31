"""Shared types and constants."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

# ── Stage definitions ──────────────────────────────────────────────

STAGE_FILES: List[Dict[str, str]] = [
    {"filename": "prior_construction.py", "tag": "PRIOR_CONSTRUCTION_CODE"},
    {"filename": "data_preprocess.py",    "tag": "DATA_PREPROCESS_CODE"},
    {"filename": "model_training.py",     "tag": "MODEL_TRAINING_CODE"},
    {"filename": "downstream_analysis.py","tag": "DOWNSTREAM_ANALYSIS_CODE"},
]

STAGE_FILENAMES: List[str] = [s["filename"] for s in STAGE_FILES]
STAGE_TAG_BY_FILE: Dict[str, str] = {s["filename"]: s["tag"] for s in STAGE_FILES}
STAGE_ORDER_INDEX: Dict[str, int] = {s["filename"]: i for i, s in enumerate(STAGE_FILES)}

# Evaluator role ↔ script mapping
EVALUATOR_ROLES: Dict[str, str] = {
    "prior":        "prior_construction.py",
    "data_science": "data_preprocess.py",
    "model":        "model_training.py",
    "biology":      "downstream_analysis.py",
}
SCRIPT_TO_ROLE: Dict[str, str] = {v: k for k, v in EVALUATOR_ROLES.items()}


# ── Records ────────────────────────────────────────────────────────

@dataclass
class StepRecord:
    step: int
    action: str  # "exploit" or "reconsult"
    run_success: bool
    metric_value: Optional[float]
    gain: Optional[float]
    stagnation: int
    optimized_scripts: List[str] = field(default_factory=list)
    failure_script: Optional[str] = None
    error_message: str = ""
    critic_rationale: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class ConsultantPlanRecord:
    step: int
    source: str  # "initial" or "reconsult"
    task_description: str
    suggestion: str
    prior_schema_json: Dict[str, Any] = field(default_factory=dict)
    raw_output: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class GlobalBestState:
    best_ari: Optional[float] = None
    best_step: int = -1
    best_script_path: str = ""
    best_cluster_metrics: Dict[str, Any] = field(default_factory=dict)