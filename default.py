"""Pipeline orchestration — main optimization loop with proper TextGrad."""
import argparse
import json
import os
import shutil
import time
from typing import List, Optional, Any, Dict

import textgrad as tg

from config import Config
from consultant import Consultant
from evaluator import EvaluatorPanel
from executor import Executor
from generator import Generator
from hist_notebook import NoteBook
from mcp_utils import fetch_mcp_tools_text
from multieval_types import (
    STAGE_FILENAMES,
    SCRIPT_TO_ROLE,
    ConsultantPlanRecord,
    GlobalBestState,
    StepRecord,
)


# ── Helpers ────────────────────────────────────────────────────────

def _to_float(x) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except Exception:
        return None


def _read_json(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _build_path_fields(layout: Dict[str, Any]) -> Dict[str, str]:
    inputs = layout.get("runtime_inputs", {})
    outputs = layout.get("generated_outputs", {})
    return {
        "input_mod1": inputs.get("mod1", ""),
        "input_mod2": inputs.get("mod2", ""),
        "prior_output_dir": layout.get("prior_output_dir", ""),
        **{k: v for k, v in outputs.items()},
    }


def _build_background(mod1: str, mod2: Optional[str]) -> str:
    return (
        f"Data: Modality 1: {mod1}\n"
        f"Data: Modality 2: {mod2 or 'None'}\n"
        "DATA: Sparse, high-dimensional gene expression counts. Rows=cells, columns=genes.\n\n"
        "TASK: Prior-guided unsupervised deep learning for scRNA-seq representation learning.\n"
        "Pipeline: prior_construction.py → data_preprocess.py → model_training.py → downstream_analysis.py\n"
        "All scripts use fixed config-owned artifact paths.\n\n"
        "EVALUATION: Primary metric: ARI. Labels only for evaluation, never training.\n"
    )


def _execute_with_fixes(
    executor, generator, code_bundle, script_dir, layout, task, config, step,
):
    """Run pipeline with fix loop. Returns (result, start_from)."""
    start_from = STAGE_FILENAMES[0]
    result = {}
    for attempt in range(config.max_fix_steps + 1):
        result = executor.run_bundle(script_dir, layout, start_from=start_from)
        if result["success"]:
            return result, start_from
        failed = result.get("failed_script", STAGE_FILENAMES[0])
        error = result.get("error", "Unknown error")
        if attempt == config.max_fix_steps:
            return result, start_from
        print(f"  Fix {attempt+1}/{config.max_fix_steps}: {failed}")
        generator.fix(code_bundle[failed], failed, error, task)
        script_dir = generator.save_bundle(code_bundle, step)
        start_from = failed
    return result, start_from


# ── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_mod1", required=True)
    parser.add_argument("--input_mod2", default=None)
    parser.add_argument("--engine", default="gpt-5")
    parser.add_argument("--dataset-dir", default=None)
    parser.add_argument("--api-dir", default=None)
    parser.add_argument("--opt-step", type=int, default=5)
    parser.add_argument("--max-fix-step", type=int, default=3)
    parser.add_argument("--time-budget", type=int, default=3600)
    parser.add_argument("--stagnation_steps_limit", type=int, default=5)
    parser.add_argument("--delta-min", type=float, default=0.005)
    args = parser.parse_args()

    # ── Setup ──────────────────────────────────────────────────────
    config = Config(
        mod1_path=args.input_mod1, mod2_path=args.input_mod2,
        engine_name=args.engine, dataset_dir=args.dataset_dir,
        api_dir=args.api_dir, opt_steps=args.opt_step,
        max_fix_steps=args.max_fix_step, timeout=args.time_budget,
        stagnation_limit=args.stagnation_steps_limit, delta_min=args.delta_min,
    )

    background = _build_background(config.mod1_path, config.mod2_path)
    background += f"\nFixed downstream requirements:\n{json.dumps(config.downstream_requirements(), indent=2)}"

    global_engine = tg.get_engine(engine_name=args.engine)
    tg.set_backward_engine(global_engine, override=True)

    # ── Consultation ───────────────────────────────────────────────
    print("=== Prior Consultation ===")
    prior_consultant = Consultant(config, "prior")
    prior_plan = prior_consultant.consult(background)
    config.prior_schema = prior_plan.get("prior_schema", {})

    print("=== Main Consultation ===")
    main_consultant = Consultant(config, "main")
    plan = main_consultant.consult(
        background,
        prior_plan=prior_plan["suggestion"],
        prior_output_summary=json.dumps(prior_plan.get("prior_schema", {})),
    )

    # ── State ──────────────────────────────────────────────────────
    task = plan["task_description"]
    suggestion = plan["suggestion"]
    prior_suggestion = prior_plan["suggestion"]

    panel = EvaluatorPanel(config, task)
    notebook = NoteBook(args.engine, task, config.notes_dir)
    executor = Executor(config)

    global_best = GlobalBestState()
    best_ari: Optional[float] = None
    stagnation = 0
    code_bundle: Optional[Dict[str, tg.Variable]] = None
    optimizers: Dict[str, tg.TextualGradientDescent] = {}
    generator: Optional[Generator] = None
    prev_code: Dict[str, str] = {}

    # ── Optimization Loop ──────────────────────────────────────────
    for step in range(config.opt_steps + 1):
        t0 = time.perf_counter()
        print(f"\n{'='*60}\nStep {step}\n{'='*60}")

        # 1. Resolve artifact paths
        layout = config.resolve_step_paths(step)
        path_fields = _build_path_fields(layout)

        # 2. Generate code bundle (first step or after reconsult)
        if code_bundle is None:
            generator = Generator(config, path_fields)
            code_bundle = generator.generate_bundle(task, background, suggestion, prior_suggestion)
            optimizers = {
                fn: tg.TextualGradientDescent(
                    engine=global_engine, parameters=[code_bundle[fn]],
                    constraints=[
                        f"Return ONLY valid executable Python for {fn}.",
                        "No argparse, sys.argv, or environment variables.",
                        "Use only fixed config-owned artifact paths.",
                    ],
                )
                for fn in STAGE_FILENAMES
            }

        # 3. Execute with fix loop
        script_dir = generator.save_bundle(code_bundle, step)
        run_result, _ = _execute_with_fixes(
            executor, generator, code_bundle, script_dir, layout, task, config, step,
        )

        if not run_result["success"]:
            print(f"FAILED: {run_result['error'][:200]}")
            notebook.record_step(StepRecord(
                step=step, action="exploit", run_success=False,
                metric_value=None, gain=None, stagnation=stagnation,
                failure_script=run_result.get("failed_script"),
                error_message=run_result.get("error", "")[:500],
            ))
            continue

        # 4. Collect metrics
        cluster_metrics = run_result.get("cluster_metrics", {})
        cur_ari = _to_float(cluster_metrics.get("ari"))
        gain = (cur_ari - best_ari) if cur_ari is not None and best_ari is not None else None

        if cur_ari is None or (gain is not None and gain <= config.delta_min):
            stagnation += 1
        else:
            stagnation = 0
        if cur_ari is not None:
            best_ari = max(best_ari, cur_ari) if best_ari is not None else cur_ari

        print(f"ARI={cur_ari}  gain={gain}  stagnation={stagnation}/{config.stagnation_limit}")

        # 5. Update global best
        if cur_ari is not None and (global_best.best_ari is None or cur_ari >= global_best.best_ari):
            global_best.best_ari = cur_ari
            global_best.best_step = step
            global_best.best_cluster_metrics = cluster_metrics
            best_dir = os.path.join(config.code_dir, "code_best_ari")
            shutil.rmtree(best_dir, ignore_errors=True)
            shutil.copytree(script_dir, best_dir)
            global_best.best_script_path = best_dir
            with open(os.path.join(config.final_dir, "global_best.json"), "w") as f:
                json.dump({"step": step, "ari": cur_ari, "metrics": cluster_metrics}, f, indent=2)

        # 6. Build evaluator context
        perf_json = _read_json(layout["generated_outputs"].get("model_performance", ""))
        context = {
            "suggestion": suggestion,
            "performance": json.dumps({"ari": cur_ari, "gain": gain, "stagnation": stagnation, "perf": perf_json}),
            "prior_schema": json.dumps(config.prior_schema),
            "prior_resources": config.prior_resource_summary,
            "data_summary": config.data_summary,
            "preprocess_meta": json.dumps(_read_json(layout["generated_outputs"].get("preprocess_metadata", ""))),
            "cluster_summary": json.dumps(run_result.get("cluster_summary", {})),
            "training_logs": json.dumps(run_result.get("training_logs", {})),
            "pipeline_summary": json.dumps(run_result.get("pipeline_summary", {})),
            "script_summaries": Generator.summarize_bundle(code_bundle),
            "notes": notebook.get_context(),
        }

        # 7. Evaluator meeting: 4 specialists → critic
        print("Evaluating...")
        eval_outputs, parsed, critic_out = panel.run_meeting(code_bundle, step, context)
        critic = parsed.get("critic", {})

        with open(os.path.join(config.feedback_dir, f"step_{step}.json"), "w") as f:
            json.dump({"step": step, "parsed": {k: str(v) for k, v in parsed.items()}, "ari": cur_ari}, f, indent=2)

        # 8. Decide: exploit or reconsult
        action = "reconsult" if stagnation >= config.stagnation_limit else "exploit"
        targets: List[str] = []

        if action == "exploit":
            targets = [
                fn for fn, payload in critic.get("targets", {}).items()
                if str(payload.get("feedback", "")).strip()
            ]
            if targets:
                print(f"Optimizing: {targets}")

                # ── CORRECT TEXTGRAD FLOW ──────────────────────────
                for fn in targets:
                    optimizers[fn].zero_grad()

                # backward() on each evaluator whose script is targeted
                # EVALUATOR_ROLES: role → script (e.g. "model" → "model_training.py")
                from multieval_types import EVALUATOR_ROLES
                for role, eval_out in eval_outputs.items():
                    script = EVALUATOR_ROLES.get(role)
                    if script and script in targets:
                        eval_out.backward()

                for fn in targets:
                    optimizers[fn].step()
                # ── END TEXTGRAD FLOW ──────────────────────────────

        elif action == "reconsult":
            print("=== Reconsulting ===")
            result = main_consultant.reconsult(
                task_description=task, background=background,
                current_suggestion=suggestion,
                current_results=json.dumps({"ari": cur_ari, "metrics": cluster_metrics}),
                failure_analysis=str(critic.get("global_rationale", "")),
                history=notebook.get_context(),
            )
            task = result["task_description"]
            suggestion = result["suggestion"]

            # Reset
            panel = EvaluatorPanel(config, task)
            code_bundle = None
            optimizers = {}
            best_ari = None
            stagnation = 0
            prev_code = {}

        # 9. Record
        notebook.record_step(StepRecord(
            step=step, action=action, run_success=True,
            metric_value=cur_ari, gain=gain, stagnation=stagnation,
            optimized_scripts=targets,
            critic_rationale=str(critic.get("global_rationale", "")),
        ))
        for fn in STAGE_FILENAMES:
            cur = code_bundle[fn].value if code_bundle and fn in code_bundle else ""
            notebook.create_note(fn, cur, prev_code.get(fn, ""), step, cur_ari, gain)
        if code_bundle:
            prev_code = {fn: code_bundle[fn].value for fn in STAGE_FILENAMES}

        print(f"Step {step}: {time.perf_counter() - t0:.1f}s")

    # ── Done ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Best ARI: {global_best.best_ari} at step {global_best.best_step}")
    print(f"Scripts: {global_best.best_script_path}")


if __name__ == "__main__":
    main()