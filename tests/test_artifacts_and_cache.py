from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.artifacts.cleanup import collect_cleanup_candidates
from backend.artifacts.manifest import ArtifactManifest
from backend.cache.step_cache import StepCache


class ArtifactAndCacheTests(unittest.TestCase):
    def test_manifest_records_file_and_cleanup_reports_ephemeral_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ephemeral = root / "path_000" / "00_stage" / "output.h5ad"
            metadata = root / "path_000" / "00_stage" / "result.json"
            ephemeral.parent.mkdir(parents=True)
            ephemeral.write_text("large", encoding="utf-8")
            metadata.write_text("{}", encoding="utf-8")

            manifest = ArtifactManifest(root)
            manifest.record_file(ephemeral, kind="h5ad", tier="ephemeral", stage="stage", path_index=0)
            manifest.record_file(metadata, kind="json", tier="metadata", stage="stage", path_index=0, protected=True)
            manifest.write()

            report = collect_cleanup_candidates(root)

        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["candidates"][0]["path"], str(ephemeral))
        self.assertEqual(report["reclaimable_bytes"], len("large"))

    def test_step_cache_stores_single_output_and_restores_stage_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = StepCache(Path(tmpdir) / "cache")
            stage_dir = Path(tmpdir) / "stage"
            stage_dir.mkdir()
            (stage_dir / "output.h5ad").write_text("payload", encoding="utf-8")
            (stage_dir / "result.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")

            cache.put_dir("a" * 64, stage_dir)
            slot = cache.cache_dir / "aa" / ("a" * 64)

            restored = Path(tmpdir) / "restored"
            cache.restore_dir_to("a" * 64, restored)

            self.assertTrue((slot / "output.h5ad").exists())
            self.assertFalse((slot / "stage_dir" / "output.h5ad").exists())
            self.assertEqual((restored / "output.h5ad").read_text(encoding="utf-8"), "payload")
            self.assertEqual(json.loads((restored / "result.json").read_text(encoding="utf-8"))["status"], "ok")


if __name__ == "__main__":
    unittest.main()
