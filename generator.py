"""Code generator — produces and fixes stage scripts."""
import json
import os
import re
from typing import Optional, Any, Dict

import textgrad as tg

from config import Config
from multieval_types import STAGE_FILES, STAGE_FILENAMES, STAGE_TAG_BY_FILE
from generator_prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    DATA_SYSTEM_PROMPT,
    FIX_QUERY,
    FIX_SYSTEM_PROMPT,
    MODEL_SYSTEM_PROMPT,
    PRIOR_SYSTEM_PROMPT,
    STAGE_QUERY,
)

_SYSTEM_PROMPTS = {
    "prior_construction.py": PRIOR_SYSTEM_PROMPT,
    "data_preprocess.py": DATA_SYSTEM_PROMPT,
    "model_training.py": MODEL_SYSTEM_PROMPT,
    "downstream_analysis.py": ANALYSIS_SYSTEM_PROMPT,
}


class Generator:
    """Generates and fixes pipeline stage scripts."""

    def __init__(self, config: Config, path_fields: Dict[str, str]):
        self.config = config
        self.engine = tg.get_engine(config.engine_name, max_tokens=12000)
        self.path_fields = path_fields

    def generate_bundle(
        self, task: str, background: str, main_plan: str, prior_plan: str,
    ) -> Dict[str, tg.Variable]:
        """Generate all 4 stage scripts with predecessor chain."""
        bundle: Dict[str, tg.Variable] = {}

        for item in STAGE_FILES:
            fn, tag = item["filename"], item["tag"]
            query = self._build_query(fn, tag, task, background, main_plan, prior_plan, bundle)
            sys_prompt = _SYSTEM_PROMPTS.get(fn, MODEL_SYSTEM_PROMPT)
            response = self.engine.generate(content=query, system_prompt=sys_prompt, temperature=0.2)
            code = self._extract_tag(response, tag)

            bundle[fn] = tg.Variable(
                code, requires_grad=True,
                role_description=f"generated code for {fn}",
            )

        # Predecessor chain: each stage depends on the previous
        for i in range(1, len(STAGE_FILENAMES)):
            bundle[STAGE_FILENAMES[i]].predecessors.add(bundle[STAGE_FILENAMES[i - 1]])

        return bundle

    def fix(
        self, code_var: tg.Variable, filename: str, error: str, task: str,
        bundle: Optional[Dict[str, tg.Variable]] = None,
        stdout: str = "",
    ) -> None:
        """Fix a broken script in-place."""
        upstream_code = "<none>"
        idx = STAGE_FILENAMES.index(filename)
        if bundle and idx > 0:
            prev_fn = STAGE_FILENAMES[idx - 1]
            if prev_fn in bundle:
                upstream_code = bundle[prev_fn].value

        full_error = error.strip()
        if stdout.strip():
            full_error = f"stdout (last 500 chars):\n{stdout.strip()[-500:]}\n\nstderr:\n{full_error}"

        query = FIX_QUERY.format(
            target_file=filename, target_tag=STAGE_TAG_BY_FILE[filename],
            task_description=task, stage_context=self._stage_context(filename),
            upstream_code=upstream_code,
            target_code=code_var.value, error=full_error,
        )
        response = self.engine.generate(content=query, system_prompt=FIX_SYSTEM_PROMPT, temperature=0.4)
        code_var.set_value(self._extract_tag(response, STAGE_TAG_BY_FILE[filename]))

    def save_bundle(self, bundle: Dict[str, tg.Variable], step: int) -> str:
        """Save all scripts to a step directory."""
        step_dir = os.path.join(self.config.code_dir, f"code_step_{step}")
        os.makedirs(step_dir, exist_ok=True)
        for fn in STAGE_FILENAMES:
            with open(os.path.join(step_dir, fn), "w") as f:
                f.write(bundle[fn].value)
        return step_dir

    @staticmethod
    def summarize_bundle(bundle: Optional[Dict[str, tg.Variable]], max_chars: int = 500) -> str:
        if not bundle:
            return "<none>"
        return json.dumps({
            fn: {"lines": len(bundle[fn].value.splitlines()), "head": bundle[fn].value[:max_chars]}
            for fn in STAGE_FILENAMES if fn in bundle
        })

    # ── Private ────────────────────────────────────────────────────

    def _build_query(self, fn, tag, task, background, main_plan, prior_plan, bundle):
        return STAGE_QUERY.format(
            target_file=fn, target_tag=tag,
            task_description=task, background=background,
            main_plan=main_plan if fn != "prior_construction.py" else "<none>",
            prior_plan=prior_plan if fn in {"prior_construction.py", "data_preprocess.py", "model_training.py"} else "<none>",
            prior_schema=json.dumps(self.config.prior_schema),
            stage_requirements=json.dumps(self.config.stage_requirements(fn)),
            stage_context=self._stage_context(fn),
            dataset_dir=self.config.dataset_dir,
            data_summary=self.config.data_summary,
            prior_resources=self.config.prior_resource_summary if fn == "prior_construction.py" else "<none>",
            metrics=self.config.metrics,
            time_budget=self.config.timeout,
            existing_code=bundle.get(fn, tg.Variable("<none>", requires_grad=False)).value
                          if isinstance(bundle.get(fn), tg.Variable) else "<none>",
        )

    def _stage_context(self, filename: str) -> str:
        return "\n".join(f"{k}: {v}" for k, v in self.path_fields.items() if v) or "<none>"

    def _extract_tag(self, response: str, tag: str) -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", response or "", re.DOTALL | re.IGNORECASE)
        if m:
            code = m.group(1).strip()
            m2 = re.search(r"```(?:python)?\n?(.*?)```", code, re.DOTALL)
            return m2.group(1).strip() if m2 else code
        m3 = re.search(r"```(?:python)?\n?(.*?)```", response or "", re.DOTALL)
        return m3.group(1).strip() if m3 else (response or "").strip()