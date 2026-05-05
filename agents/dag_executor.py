from __future__ import annotations

import copy
import json
import re
import shutil
import time
from itertools import product
from pathlib import Path
from typing import Any, Dict, List

from agents.decision_schema import validate_dag_plan
from backend.artifacts import ArtifactManifest
from backend.tools.executor import build_wiki_executor_registry
from backend.cache import sha256_file
from backend.objectives import score_metrics


REF_RE = re.compile(r"^\$L(\d+)\.([A-Za-z_][A-Za-z0-9_]*)$")


class DagExecutor:
    """Execute ordered single-cell tool DAGs by enumerating variant paths."""

    def __init__(self, *, backend: Any, result_dir: str | Path):
        self.backend = backend
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.tool_executor = build_wiki_executor_registry()

    def execute(self, *, dag_plan: Dict[str, Any], session_tag: str = "dag") -> Dict[str, Any]:
        plan = validate_dag_plan(dag_plan, available_stages=self.tool_executor.keys())
        run_dir = self.result_dir / session_tag
        run_dir.mkdir(parents=True, exist_ok=True)
        if not plan.get("output_dir"):
            plan["output_dir"] = str(run_dir)

        paths = self._enumerate_paths(plan["layers"])
        task_id = self.backend.runs.create_task(
            description=f"DAG exploration: {session_tag}",
            objective={"name": plan.get("objective_name")},
            dataset_path=plan["input_h5ad_path"],
        )

        results: list[dict[str, Any]] = []
        for path_idx, path_config in enumerate(paths):
            results.append(
                self._execute_path(
                    plan=plan,
                    path_config=path_config,
                    path_idx=path_idx,
                    task_id=task_id,
                    run_dir=run_dir,
                )
            )

        result = self._format_result(results, plan, task_id, run_dir)
        manifest_path, retention_summary = self._apply_retention(results, result, run_dir)
        result["artifact_manifest_path"] = str(manifest_path)
        result["retention_summary"] = retention_summary
        result_path = run_dir / "dag_result.json"
        result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        result["result_path"] = str(result_path)
        return result

    def _enumerate_paths(self, layers: List[Dict[str, Any]]) -> list[list[dict[str, Any]]]:
        variant_lists = [layer["variants"] for layer in layers]
        stage_names = [layer["stage"] for layer in layers]
        paths: list[list[dict[str, Any]]] = []
        for combo in product(*variant_lists):
            path: list[dict[str, Any]] = []
            for stage, variant in zip(stage_names, combo):
                step = copy.deepcopy(variant)
                step["stage"] = stage
                path.append(step)
            paths.append(path)
        return paths

    def _execute_path(
        self,
        *,
        plan: Dict[str, Any],
        path_config: list[dict[str, Any]],
        path_idx: int,
        task_id: str,
        run_dir: Path,
    ) -> Dict[str, Any]:
        input_path = Path(plan["input_h5ad_path"])
        path_dir = run_dir / f"path_{path_idx:03d}"
        if path_dir.exists():
            shutil.rmtree(path_dir)
        path_dir.mkdir(parents=True, exist_ok=True)
        trial_id = self.backend.runs.start_trial(
            task_id=task_id,
            config={"path_index": path_idx, "stages": path_config},
        )

        t_start = time.time()
        cache_hits: list[str] = []

        try:
            current_input = input_path
            input_sha = sha256_file(current_input)
            stage_results: list[dict[str, Any]] = []

            for layer_idx, step in enumerate(path_config):
                stage = step["stage"]
                stage_params = {"method": step["method"], **(step.get("params") or {})}
                stage_params = _resolve_refs(stage_params, path_config, layer_idx)
                step["params"] = {key: value for key, value in stage_params.items() if key != "method"}

                if step.get("declared_outputs"):
                    step["declared_outputs"] = _resolve_refs(step["declared_outputs"], path_config, layer_idx)
                    step["resolved_outputs"] = dict(step["declared_outputs"])

                stage_dir = path_dir / f"{layer_idx:02d}_{stage}"
                stage_dir.mkdir(parents=True, exist_ok=True)
                cache_key = self.backend.cache.key(input_sha, stage, stage_params)
                output_h5ad_path = stage_dir / "output.h5ad"

                result: Any = None
                cache_usable = False
                if self.backend.cache.has_dir(cache_key):
                    self.backend.cache.restore_dir_to(cache_key, stage_dir)
                    cached_meta = self.backend.cache.get_meta(cache_key)
                    cached_outputs = cached_meta.get("resolved_outputs") if isinstance(cached_meta, dict) else {}
                    if isinstance(cached_outputs, dict):
                        step.setdefault("resolved_outputs", {})
                        step["resolved_outputs"].update(cached_outputs)
                    if output_h5ad_path.exists():
                        step.setdefault("resolved_outputs", {})
                        step["resolved_outputs"]["output_h5ad_path"] = str(output_h5ad_path)
                        cache_usable = True
                    cached_stage_result = cached_meta.get("stage_result") if isinstance(cached_meta, dict) else None
                    if cached_stage_result is None:
                        cached_stage_result = _read_stage_result(stage_dir)
                    if cached_stage_result is not None:
                        step["result"] = cached_stage_result
                        stage_results.append({"stage": stage, "method": step["method"], "result": cached_stage_result})
                        cache_usable = True
                    if cache_usable:
                        cache_hits.append(stage)
                if not cache_usable:
                    fn = self.tool_executor[stage]
                    result = fn(
                        input_h5ad_path=str(current_input),
                        output_h5ad_path=str(output_h5ad_path),
                        output_dir=str(stage_dir),
                        **stage_params,
                    )
                    stage_result = _json_safe(result)
                    if stage_result is not None:
                        step["result"] = stage_result
                        stage_results.append({"stage": stage, "method": step["method"], "result": stage_result})
                        _write_stage_result(stage_dir, stage_result)
                    output_h5ad = _extract_output_h5ad(result, stage_dir)
                    if output_h5ad is not None:
                        step.setdefault("resolved_outputs", {})
                        step["resolved_outputs"]["output_h5ad_path"] = str(output_h5ad)
                    self.backend.cache.put_dir(
                        cache_key,
                        stage_dir,
                        meta={
                            "stage": stage,
                            "params": stage_params,
                            "resolved_outputs": step.get("resolved_outputs", {}),
                            "stage_result": stage_result,
                        },
                    )

                outputs = step.get("resolved_outputs", {}) or step.get("declared_outputs", {})
                if outputs.get("output_h5ad_path"):
                    current_input = Path(outputs["output_h5ad_path"])
                    input_sha = sha256_file(current_input)

            resolved_eval = _resolve_refs(plan.get("evaluation", {}) or {}, path_config, len(path_config))
            eval_h5ad = _find_primary_h5ad(path_config, default=input_path)
            eval_result = self.backend.eval.evaluate(
                eval_h5ad,
                metrics=resolved_eval.get("metrics", []),
                embedding_key=resolved_eval.get("embedding_key"),
                cluster_key=resolved_eval.get("cluster_key"),
                label_key=resolved_eval.get("label_key"),
                batch_key=resolved_eval.get("batch_key"),
                objective_name=plan.get("objective_name"),
            )
            duration_s = time.time() - t_start
            artifacts = _collect_path_outputs(path_dir)
            self.backend.runs.complete_trial(
                trial_id,
                metrics=dict(eval_result.metrics),
                duration_s=duration_s,
                artifact_paths=artifacts,
            )
            return {
                "path_index": path_idx,
                "status": "completed",
                "config": path_config,
                "metrics": dict(eval_result.metrics),
                "warnings": list(getattr(eval_result, "warnings", [])),
                "duration_s": duration_s,
                "path_dir": str(path_dir),
                "artifacts": artifacts,
                "stage_results": stage_results,
                "cache_hits": cache_hits,
                "trial_id": trial_id,
            }
        except Exception as exc:
            duration_s = time.time() - t_start
            self.backend.runs.fail_trial(trial_id, str(exc), duration_s)
            return {
                "path_index": path_idx,
                "status": "failed",
                "config": path_config,
                "error": str(exc),
                "duration_s": duration_s,
                "path_dir": str(path_dir),
                "cache_hits": cache_hits,
                "trial_id": trial_id,
            }

    def _format_result(
        self,
        results: list[dict[str, Any]],
        plan: Dict[str, Any],
        task_id: str,
        run_dir: Path,
    ) -> Dict[str, Any]:
        completed = [result for result in results if result.get("status") == "completed"]
        failed = [result for result in results if result.get("status") == "failed"]
        if not completed:
            return {
                "status": "failed",
                "error": "All DAG paths failed",
                "failed_paths": failed,
                "artifact_dir": str(run_dir),
                "task_id": task_id,
            }

        objective_name = plan.get("objective_name")
        for result in completed:
            result["objective_score"] = score_metrics(objective_name, result.get("metrics", {})) if objective_name else None
        if objective_name:
            completed.sort(key=lambda item: (-(item.get("objective_score") if item.get("objective_score") is not None else float("-inf")), item["path_index"]))
        else:
            completed.sort(key=lambda item: item["path_index"])

        best = completed[0]
        resolved_outputs: dict[str, Any] = {}
        for step in best.get("config", []):
            resolved_outputs.update(step.get("declared_outputs", {}) or {})
            resolved_outputs.update(step.get("resolved_outputs", {}) or {})

        return {
            "status": "completed",
            "best_path": {
                "path_index": best["path_index"],
                "config": best["config"],
                "metrics": best.get("metrics", {}),
                "objective_score": best.get("objective_score"),
                "path_dir": best["path_dir"],
                "artifacts": best.get("artifacts", {}),
                "stage_results": best.get("stage_results", []),
                "cache_hits": best.get("cache_hits", []),
                "resolved_outputs": resolved_outputs,
            },
            "comparison_table": self._build_comparison_table(results) if len(results) > 1 else [],
            "paths_completed": len(completed),
            "paths_failed": len(failed),
            "objective_name": objective_name,
            "artifact_dir": str(run_dir),
            "task_id": task_id,
        }

    def _build_comparison_table(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        table: list[dict[str, Any]] = []
        for result in results:
            row: dict[str, Any] = {"path_index": result["path_index"], "status": result["status"]}
            for step in result.get("config", []):
                stage = step["stage"]
                row[f"{stage}_method"] = step.get("method")
                for param_name, param_value in (step.get("params") or {}).items():
                    row[f"{stage}_{param_name}"] = param_value
            for metric_name, metric_value in (result.get("metrics") or {}).items():
                row[metric_name] = metric_value
            if result.get("objective_score") is not None:
                row["objective_score"] = result["objective_score"]
            if result.get("error"):
                row["error"] = result["error"]
            table.append(row)
        table.sort(key=lambda row: (-(row.get("objective_score") if row.get("objective_score") is not None else float("-inf")), row["path_index"]))
        return table

    def _apply_retention(
        self,
        results: list[dict[str, Any]],
        formatted: dict[str, Any],
        run_dir: Path,
    ) -> tuple[Path, dict[str, Any]]:
        manifest = ArtifactManifest(run_dir)
        manifest.record_file(run_dir / "dag_result.json", kind="json", tier="metadata", protected=True)

        completed = [result for result in results if result.get("status") == "completed"]
        keep_intermediates = bool(getattr(getattr(self.backend, "config", None), "keep_intermediates", False))
        keep_top_k = int(getattr(getattr(self.backend, "config", None), "keep_top_k_paths", 3) or 0)
        if keep_top_k < 1:
            keep_top_k = 1

        ranked_indices = [row["path_index"] for row in formatted.get("comparison_table", []) if row.get("status") == "completed"]
        if not ranked_indices and formatted.get("best_path"):
            ranked_indices = [formatted["best_path"]["path_index"]]
        protected_indices = set(ranked_indices[:keep_top_k])
        best_index = formatted.get("best_path", {}).get("path_index")
        if best_index is not None:
            protected_indices.add(best_index)

        deleted_files = 0
        deleted_bytes = 0
        kept_h5ad = 0

        for result in results:
            path_index = result.get("path_index")
            path_dir = Path(result.get("path_dir", ""))
            final_h5ad = _final_h5ad_for_path(result)
            for item in sorted(path_dir.rglob("*")) if path_dir.exists() else []:
                if not item.is_file():
                    continue
                rel = str(item.relative_to(path_dir))
                stage = _stage_for_relative_artifact(rel)
                if item.suffix == ".h5ad":
                    is_protected_final = (
                        result.get("status") == "completed"
                        and path_index in protected_indices
                        and final_h5ad is not None
                        and item == final_h5ad
                    )
                    keep_file = bool(is_protected_final or keep_intermediates)
                    tier = "best" if is_protected_final and path_index == best_index else ("result" if is_protected_final else "ephemeral")
                    if keep_file:
                        kept_h5ad += 1
                        manifest.record_file(
                            item,
                            kind="h5ad",
                            tier=tier,
                            stage=stage,
                            path_index=path_index,
                            protected=is_protected_final,
                        )
                    else:
                        size = item.stat().st_size
                        item.unlink(missing_ok=True)
                        deleted_files += 1
                        deleted_bytes += size
                    continue
                manifest.record_file(
                    item,
                    kind=_artifact_kind(item),
                    tier="metadata",
                    stage=stage,
                    path_index=path_index,
                    protected=True,
                )

            if path_dir.exists():
                result["artifacts"] = _collect_path_outputs(path_dir)
                if best_index == path_index and formatted.get("best_path"):
                    formatted["best_path"]["artifacts"] = result["artifacts"]

        manifest_path = manifest.write()
        return manifest_path, {
            "policy": {
                "keep_intermediates": keep_intermediates,
                "keep_top_k_paths": keep_top_k,
            },
            "protected_path_indices": sorted(protected_indices),
            "deleted_files": deleted_files,
            "deleted_bytes": deleted_bytes,
            "kept_h5ad_files": kept_h5ad,
        }


def _resolve_refs(value: Any, path_config: list[dict[str, Any]], current_idx: int) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_refs(item, path_config, current_idx) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_refs(item, path_config, current_idx) for item in value]
    if not isinstance(value, str):
        return value
    match = REF_RE.match(value.strip())
    if not match:
        return value
    layer_idx = int(match.group(1))
    output_key = match.group(2)
    if layer_idx >= current_idx:
        raise ValueError(f"Reference {value}: layer {layer_idx} is not before current layer {current_idx}")
    source = path_config[layer_idx]
    outputs = {}
    outputs.update(source.get("declared_outputs", {}) or {})
    outputs.update(source.get("resolved_outputs", {}) or {})
    if output_key not in outputs:
        raise ValueError(f"Reference {value}: output {output_key!r} not found in layer {layer_idx}")
    return _resolve_refs(outputs[output_key], path_config, layer_idx)


def _extract_output_h5ad(result: Any, stage_dir: Path) -> Path | None:
    if isinstance(result, dict) and result.get("output_h5ad_path"):
        return Path(result["output_h5ad_path"])
    default = stage_dir / "output.h5ad"
    return default if default.exists() else None


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return {"value": str(value)}


def _write_stage_result(stage_dir: Path, result: Any) -> None:
    path = stage_dir / "result.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_stage_result(stage_dir: Path) -> Any | None:
    path = stage_dir / "result.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_primary_h5ad(path_config: list[dict[str, Any]], default: Path) -> Path:
    for step in reversed(path_config):
        outputs = {}
        outputs.update(step.get("declared_outputs", {}) or {})
        outputs.update(step.get("resolved_outputs", {}) or {})
        if outputs.get("output_h5ad_path"):
            return Path(outputs["output_h5ad_path"])
    return Path(default)


def _collect_path_outputs(path_dir: Path) -> Dict[str, str]:
    artifacts: dict[str, str] = {}
    for item in sorted(path_dir.rglob("*")):
        if item.is_file():
            artifacts[str(item.relative_to(path_dir))] = str(item)
    return artifacts


def _final_h5ad_for_path(result: dict[str, Any]) -> Path | None:
    config = result.get("config") or []
    if not isinstance(config, list):
        return None
    for step in reversed(config):
        outputs = {}
        outputs.update(step.get("declared_outputs", {}) or {})
        outputs.update(step.get("resolved_outputs", {}) or {})
        if outputs.get("output_h5ad_path"):
            return Path(outputs["output_h5ad_path"])
    return None


def _stage_for_relative_artifact(relative_path: str) -> str | None:
    first = Path(relative_path).parts[0] if relative_path else ""
    if "_" not in first:
        return None
    return first.split("_", 1)[1]


def _artifact_kind(path: Path) -> str:
    if path.suffix == ".json":
        return "json"
    if path.suffix in {".log", ".txt"}:
        return "log"
    if path.suffix in {".csv", ".tsv", ".parquet"}:
        return "table"
    if path.suffix in {".png", ".jpg", ".jpeg", ".svg", ".pdf"}:
        return "figure"
    return path.suffix.lstrip(".") or "file"
