from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import textgrad as tg


@dataclass
class PipelineBundle:
    pipeline_code: tg.Variable

    def as_text_dict(self) -> Dict[str, str]:
        return {"pipeline": self.pipeline_code.value}


@dataclass
class ValidationFailure:
    stage: str
    error_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class StepRunContract:
    step: int
    run_dir: str
    contract_path: str
    artifact_paths: Dict[str, str]
    required_script: str
    required_functions: List[str]
    section_order: List[str]
    section_output_contracts: Dict[str, List[str]]
    component_contract_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "run_dir": self.run_dir,
            "contract_path": self.contract_path,
            "component_contract_path": self.component_contract_path,
            "artifact_paths": self.artifact_paths,
            "required_script": self.required_script,
            "required_functions": self.required_functions,
            "section_order": self.section_order,
            "section_output_contracts": self.section_output_contracts,
        }

    def write(self) -> None:
        Path(self.run_dir).mkdir(parents=True, exist_ok=True)
        with open(self.contract_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def build_env(self) -> Dict[str, str]:
        contract_env_path = self.component_contract_path or self.contract_path
        return {
            "SCANPY_AGENT_RUN_DIR": self.run_dir,
            "SCANPY_AGENT_CONTRACT_PATH": contract_env_path,
            "SCANPY_AGENT_STEP": str(self.step),
        }


@dataclass
class HistoryNoteRecord:
    step: int
    action: str
    context_mode: str
    attempts_used: int
    run_success: bool
    failed_stage: str | None
    architecture_fingerprint: str
    design_summary: str
    decision_rationale: str
    primary_metric: str
    metric_value: float | None
    gain: float | None
    stagnation: int
    failure_phase: str | None
    failure_fingerprint: str | None
    root_cause: str
    fix_outcome: str
    evaluator_diagnosis: str
    script_plan: Dict[str, Any]
    open_issues: List[str]
    exploit_applied: bool = False
    optimized_scripts: List[str] = field(default_factory=list)
    exploit_change_types: Dict[str, str] = field(default_factory=dict)
    exploit_summary: Dict[str, str] = field(default_factory=dict)
    previous_exploit_context: Dict[str, Any] = field(default_factory=dict)
    do_not_repeat: bool = False
    do_not_repeat_reason: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "action": self.action,
            "context_mode": self.context_mode,
            "attempts_used": self.attempts_used,
            "run_success": self.run_success,
            "failed_stage": self.failed_stage,
            "architecture_fingerprint": self.architecture_fingerprint,
            "design_summary": self.design_summary,
            "decision_rationale": self.decision_rationale,
            "primary_metric": self.primary_metric,
            "metric_value": self.metric_value,
            "gain": self.gain,
            "stagnation": self.stagnation,
            "failure_phase": self.failure_phase,
            "failure_fingerprint": self.failure_fingerprint,
            "root_cause": self.root_cause,
            "fix_outcome": self.fix_outcome,
            "evaluator_diagnosis": self.evaluator_diagnosis,
            "script_plan": self.script_plan,
            "open_issues": self.open_issues,
            "exploit_applied": self.exploit_applied,
            "optimized_scripts": self.optimized_scripts,
            "exploit_change_types": self.exploit_change_types,
            "exploit_summary": self.exploit_summary,
            "previous_exploit_context": self.previous_exploit_context,
            "do_not_repeat": self.do_not_repeat,
            "do_not_repeat_reason": self.do_not_repeat_reason,
            "created_at": self.created_at,
        }


@dataclass
class DecisionLedgerRecord:
    step: int
    architecture_fingerprint: str
    design_summary: str
    decision_rationale: str
    primary_metric: str
    metric_value: float | None
    metric_gain: float | None
    result: str
    action: str
    failed_stage: str | None
    failure_fingerprint: str | None
    do_not_repeat: bool = False
    do_not_repeat_reason: str = ""
    exploit_applied: bool = False
    optimized_scripts: List[str] = field(default_factory=list)
    exploit_change_types: Dict[str, str] = field(default_factory=dict)
    exploit_summary: Dict[str, str] = field(default_factory=dict)
    rejected_design_labels: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "architecture_fingerprint": self.architecture_fingerprint,
            "design_summary": self.design_summary,
            "decision_rationale": self.decision_rationale,
            "primary_metric": self.primary_metric,
            "metric_value": self.metric_value,
            "metric_gain": self.metric_gain,
            "result": self.result,
            "action": self.action,
            "failed_stage": self.failed_stage,
            "failure_fingerprint": self.failure_fingerprint,
            "exploit_applied": self.exploit_applied,
            "optimized_scripts": self.optimized_scripts,
            "exploit_change_types": self.exploit_change_types,
            "exploit_summary": self.exploit_summary,
            "do_not_repeat": self.do_not_repeat,
            "do_not_repeat_reason": self.do_not_repeat_reason,
            "rejected_design_labels": self.rejected_design_labels,
            "created_at": self.created_at,
        }


@dataclass
class ConsultantPlanRecord:
    step: int
    source: str
    task_description: str
    suggestion: str
    prior_plan_json: Dict[str, Any]
    raw_output: str
    plan_fingerprint: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "source": self.source,
            "task_description": self.task_description,
            "suggestion": self.suggestion,
            "prior_plan_json": self.prior_plan_json,
            "raw_output": self.raw_output,
            "plan_fingerprint": self.plan_fingerprint,
            "created_at": self.created_at,
        }


@dataclass
class OuterLoopState:
    best_ari: float | None = None
    best_sil: float | None = None
    stagnation_steps: int = 0
    note_records: List[HistoryNoteRecord] = field(default_factory=list)

    def reset(self) -> None:
        self.best_ari = None
        self.best_sil = None
        self.stagnation_steps = 0
        self.note_records = []


@dataclass
class GlobalBestState:
    best_ari: float | None = None
    best_silhouette: float | None = None
    best_step: int = -1
    best_script_path: str = ""
    best_perf: Dict[str, Any] = field(default_factory=dict)
    best_cluster_metrics: Dict[str, Any] = field(default_factory=dict)
