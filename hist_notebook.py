"""History notebook — tracks optimization steps and provides compressed context."""
import json
import os
from typing import Optional, Any, Dict, List

import textgrad as tg

from hist_notebook_prompts import (
    NOTEBOOK_PROMPT,
    NOTEBOOK_QUERY,
    NOTE_CLEAN_SYS_PROMPT,
    NOTE_SUMMARIZE_SYS_PROMPT,
)
from multieval_types import StepRecord


class NoteBook:
    """Tracks optimization history for evaluator context."""

    def __init__(self, engine_name: str, task: str, notes_dir: str):
        self.engine = tg.get_engine(engine_name, max_tokens=2500)
        self.task = task
        self.records: List[StepRecord] = []
        self.notes: List[Dict] = []
        self.keep_full = 2
        self.clean_threshold = 10
        self.notes_path = os.path.join(notes_dir, "history.jsonl")
        open(self.notes_path, "w").close()

    def record_step(self, record: StepRecord) -> None:
        self.records.append(record)
        with open(self.notes_path, "a") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")

    def create_note(
        self, script: str, cur_code: str, prev_code: str,
        step: int, metric_value: Optional[float], gain: Optional[float],
    ) -> str:
        query = NOTEBOOK_QUERY.format(
            task_description=self.task, code_role=script,
            cur_step=step, cur_code=cur_code,
            prev_step=max(0, step - 1), prev_code=prev_code or "<none>",
        )
        try:
            note = self.engine.generate(content=query, system_prompt=NOTEBOOK_PROMPT, temperature=0.2)
        except Exception:
            note = f"Step {step}: {script} updated."
        note += f"\nMetric: {metric_value}, Gain: {gain}"
        self.notes.append({"step": step, "content": note, "is_summary": False})
        self._compress()
        return note

    def get_context(self, keep_last: int = 5) -> str:
        if not self.records:
            return "<empty>"
        lines = ["[Recent Steps]"]
        for r in self.records[-keep_last:]:
            lines.append(
                f"step={r.step} action={r.action} success={r.run_success} "
                f"ari={r.metric_value} gain={r.gain} stagnation={r.stagnation} "
                f"targets={','.join(r.optimized_scripts) or 'none'}"
            )
        if self.notes:
            lines.append("\n[Notes]")
            for n in self.notes[-keep_last:]:
                prefix = "curated" if n.get("is_summary") else f"step_{n['step']}"
                lines.append(f"[{prefix}] {n['content']}")
        return "\n".join(lines)

    def _compress(self):
        if len(self.notes) <= self.keep_full:
            return
        for i in range(len(self.notes) - self.keep_full):
            if not self.notes[i]["is_summary"]:
                try:
                    s = self.engine.generate(
                        content=f"Note:\n{self.notes[i]['content']}",
                        system_prompt=NOTE_SUMMARIZE_SYS_PROMPT, temperature=0.2,
                    )
                    self.notes[i] = {"step": self.notes[i]["step"], "content": s, "is_summary": True}
                except Exception:
                    pass
        summarized = [n for n in self.notes if n["is_summary"]]
        if len(summarized) > self.clean_threshold:
            combined = "\n".join(n["content"] for n in summarized)
            try:
                cleaned = self.engine.generate(
                    content=f"Notes:\n{combined}",
                    system_prompt=NOTE_CLEAN_SYS_PROMPT, temperature=0.2,
                )
                self.notes = [{"step": -1, "content": cleaned, "is_summary": True}] + self.notes[-self.keep_full:]
            except Exception:
                pass