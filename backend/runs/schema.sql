CREATE TABLE IF NOT EXISTS tasks (
    task_id       TEXT PRIMARY KEY,
    description   TEXT NOT NULL,
    objective     TEXT NOT NULL,
    dataset_path  TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trials (
    trial_id             TEXT PRIMARY KEY,
    task_id              TEXT NOT NULL,
    config               TEXT NOT NULL,
    metrics              TEXT NOT NULL DEFAULT '{}',
    status               TEXT NOT NULL,
    duration_s           REAL,
    error_message        TEXT,
    artifact_paths       TEXT NOT NULL DEFAULT '{}',
    optuna_study_name    TEXT,
    optuna_trial_number  INTEGER,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at         TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

CREATE INDEX IF NOT EXISTS idx_trials_task ON trials(task_id);
CREATE INDEX IF NOT EXISTS idx_trials_task_status ON trials(task_id, status);
