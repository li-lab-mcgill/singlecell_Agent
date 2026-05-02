"""Persistent trial registry backed by SQLite.

Shares its SQLite file with Optuna so the leaderboard and the study
internals are one canonical source of truth. Both survive restart.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._types import Task, Trial


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


class TrialRegistry:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        schema = (Path(__file__).parent / "schema.sql").read_text()
        with self._connect() as conn:
            conn.executescript(schema)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    def create_task(
        self,
        description: str,
        objective: Dict[str, Any],
        dataset_path: Optional[str] = None,
    ) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO tasks(task_id, description, objective, dataset_path, created_at) "
                "VALUES(?, ?, ?, ?, ?)",
                (task_id, description, json.dumps(objective), dataset_path, _now()),
            )
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            return None
        return Task(
            task_id=row["task_id"],
            description=row["description"],
            objective=json.loads(row["objective"]),
            dataset_path=row["dataset_path"],
            created_at=row["created_at"],
        )

    def list_tasks(self) -> List[Task]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [
            Task(
                task_id=r["task_id"],
                description=r["description"],
                objective=json.loads(r["objective"]),
                dataset_path=r["dataset_path"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Trials
    # ------------------------------------------------------------------
    def start_trial(
        self,
        task_id: str,
        config: Dict[str, Any],
        optuna_study_name: Optional[str] = None,
        optuna_trial_number: Optional[int] = None,
    ) -> str:
        trial_id = f"trial_{uuid.uuid4().hex[:12]}"
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO trials(trial_id, task_id, config, status, "
                "optuna_study_name, optuna_trial_number, created_at) "
                "VALUES(?, ?, ?, 'running', ?, ?, ?)",
                (trial_id, task_id, json.dumps(config), optuna_study_name, optuna_trial_number, _now()),
            )
        return trial_id

    def complete_trial(
        self,
        trial_id: str,
        *,
        metrics: Dict[str, float],
        duration_s: float,
        artifact_paths: Optional[Dict[str, str]] = None,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE trials SET status='completed', metrics=?, duration_s=?, "
                "artifact_paths=?, completed_at=? WHERE trial_id=?",
                (json.dumps(metrics), duration_s, json.dumps(artifact_paths or {}), _now(), trial_id),
            )

    def fail_trial(self, trial_id: str, error_message: str, duration_s: Optional[float] = None) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE trials SET status='failed', error_message=?, duration_s=?, completed_at=? "
                "WHERE trial_id=?",
                (error_message, duration_s, _now(), trial_id),
            )

    def prune_trial(self, trial_id: str, duration_s: Optional[float] = None) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE trials SET status='pruned', duration_s=?, completed_at=? WHERE trial_id=?",
                (duration_s, _now(), trial_id),
            )

    def get_trial(self, trial_id: str) -> Optional[Trial]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM trials WHERE trial_id=?", (trial_id,)).fetchone()
        return self._row_to_trial(row) if row else None

    def get_leaderboard(
        self,
        task_id: str,
        *,
        top_k: int = 5,
        sort_by: Optional[str] = None,
        order: str = "desc",
    ) -> List[Trial]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trials WHERE task_id=? AND status='completed'", (task_id,)
            ).fetchall()

        trials = [self._row_to_trial(r) for r in rows]

        # Resolve sort_by: explicit arg > task primary metric > first metric on any trial
        if sort_by is None:
            task = self.get_task(task_id)
            if task is not None:
                obj = task.objective
                if isinstance(obj, dict) and "metric" in obj:
                    sort_by = obj["metric"]
                elif isinstance(obj, list) and obj and "metric" in obj[0]:
                    sort_by = obj[0]["metric"]
        if sort_by is None and trials:
            for t in trials:
                if t.metrics:
                    sort_by = next(iter(t.metrics))
                    break

        reverse = order == "desc"
        if sort_by:
            trials = [t for t in trials if sort_by in t.metrics]
            trials.sort(key=lambda t: t.metrics[sort_by], reverse=reverse)
        return trials[:top_k]

    def _row_to_trial(self, row: sqlite3.Row) -> Trial:
        return Trial(
            trial_id=row["trial_id"],
            task_id=row["task_id"],
            config=json.loads(row["config"]),
            metrics=json.loads(row["metrics"] or "{}"),
            status=row["status"],
            duration_s=row["duration_s"],
            error_message=row["error_message"],
            artifact_paths=json.loads(row["artifact_paths"] or "{}"),
            optuna_study_name=row["optuna_study_name"],
            optuna_trial_number=row["optuna_trial_number"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )
