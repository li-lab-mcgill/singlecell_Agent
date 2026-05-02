from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Task:
    task_id: str
    description: str
    objective: Dict[str, Any]
    dataset_path: Optional[str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "objective": self.objective,
            "dataset_path": self.dataset_path,
            "created_at": self.created_at,
        }


@dataclass
class Trial:
    trial_id: str
    task_id: str
    config: Dict[str, Any]
    metrics: Dict[str, float]
    status: str
    duration_s: Optional[float]
    error_message: Optional[str]
    artifact_paths: Dict[str, str]
    optuna_study_name: Optional[str]
    optuna_trial_number: Optional[int]
    created_at: str
    completed_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "task_id": self.task_id,
            "config": self.config,
            "metrics": self.metrics,
            "status": self.status,
            "duration_s": self.duration_s,
            "error_message": self.error_message,
            "artifact_paths": self.artifact_paths,
            "optuna_study_name": self.optuna_study_name,
            "optuna_trial_number": self.optuna_trial_number,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
