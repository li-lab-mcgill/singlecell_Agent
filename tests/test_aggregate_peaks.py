"""Tests for backend.tools.multi.velocity.aggregate_peaks.

MultiVelo itself is not importable in this environment, so these tests
inject a fake ``multivelo`` module into sys.modules and monkeypatch
``aggregate_peaks_10x`` to exercise both return conventions the real
package is known to use across versions:

1. Returns a brand-new gene-level AnnData (peak-level ``adata_atac`` is
   left untouched).
2. Mutates ``adata_atac`` in place and returns ``None``.

The test also implicitly guards against the original keyword-argument bug
(``peaks_annot_path=``/``linkage_path=``/``verbose=``): the fake
``aggregate_peaks_10x`` below only accepts ``(adata_atac, peaks_annot,
linkage, use_gene_id=...)``, so calling it with any of those stale keyword
names would raise ``TypeError`` before the assertions even run.
"""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path

import anndata as ad
import numpy as np

from backend.tools.multi.velocity import aggregate_peaks


class AggregatePeaksReturnHandlingTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(self._tmpdir.name)

        # Dummy Cell Ranger ARC files -- only their existence is checked by
        # the code under test; contents are irrelevant since the fake
        # aggregate_peaks_10x never parses them.
        self.peaks_annot_path = tmp / "atac_peak_annotation.tsv"
        self.linkage_path = tmp / "feature_linkage.bedpe"
        self.peaks_annot_path.write_text("dummy\n")
        self.linkage_path.write_text("dummy\n")

        self.atac_path = tmp / "atac.h5ad"
        peak_names = ["chr1:100-200", "chr1:300-400", "chr2:50-150"]
        n_obs = 4
        X = np.arange(n_obs * len(peak_names), dtype=float).reshape(n_obs, len(peak_names))
        adata_atac = ad.AnnData(X=X)
        adata_atac.var_names = peak_names
        adata_atac.obs_names = [f"cell{i}" for i in range(n_obs)]
        adata_atac.write_h5ad(self.atac_path)

        self.rna_adata = types.SimpleNamespace(
            var_names=["GENE_A", "GENE_B", "GENE_C"],
            n_vars=3,
            uns={},
        )

    def tearDown(self):
        self._tmpdir.cleanup()
        sys.modules.pop("multivelo", None)

    def _install_fake_multivelo(self, aggregate_fn):
        fake = types.ModuleType("multivelo")
        fake.aggregate_peaks_10x = aggregate_fn
        fake.tfidf_norm = lambda adata, scale_factor=1e4: None
        sys.modules["multivelo"] = fake

    def _run(self):
        return aggregate_peaks._run_aggregate_peaks(
            self.rna_adata,
            atac_path=self.atac_path,
            peaks_annot_path=self.peaks_annot_path,
            linkage_path=self.linkage_path,
            use_gene_id=False,
            tfidf_scale_factor=1e4,
        )

    def test_new_gene_level_adata_return_is_captured_downstream(self):
        """Version that returns a NEW gene-level AnnData (does not mutate input)."""
        gene_var_names = ["GENE_A", "GENE_B"]
        calls = []

        def fake_aggregate(adata_atac, peaks_annot, linkage, use_gene_id=False):
            calls.append((peaks_annot, linkage, use_gene_id))
            assert isinstance(peaks_annot, str) and isinstance(linkage, str)
            new_adata = ad.AnnData(X=np.ones((adata_atac.n_obs, len(gene_var_names))))
            new_adata.var_names = gene_var_names
            new_adata.obs_names = adata_atac.obs_names
            return new_adata

        self._install_fake_multivelo(fake_aggregate)

        result = self._run()

        self.assertEqual(len(calls), 1)
        meta = result.uns["velocity_aggregate_peaks"]
        # If the code failed to capture the returned object, these would
        # reflect the stale 3-peak object and the shared-gene check would
        # raise ValueError (peak coords never overlap RNA gene symbols).
        self.assertEqual(meta["n_atac_peaks_before"], 3)
        self.assertEqual(meta["n_atac_genes_after"], 2)
        self.assertEqual(meta["n_shared_genes"], 2)

        saved = ad.read_h5ad(self.atac_path)
        self.assertEqual(list(saved.var_names), gene_var_names)

    def test_in_place_mutation_returning_none_still_works(self):
        """Version that mutates adata_atac in place and returns None."""

        def fake_aggregate(adata_atac, peaks_annot, linkage, use_gene_id=False):
            assert isinstance(peaks_annot, str) and isinstance(linkage, str)
            adata_atac.var_names = ["GENE_A", "GENE_B", "GENE_C"]
            return None

        self._install_fake_multivelo(fake_aggregate)

        result = self._run()

        meta = result.uns["velocity_aggregate_peaks"]
        self.assertEqual(meta["n_atac_genes_after"], 3)
        self.assertEqual(meta["n_shared_genes"], 3)

        saved = ad.read_h5ad(self.atac_path)
        self.assertEqual(list(saved.var_names), ["GENE_A", "GENE_B", "GENE_C"])


if __name__ == "__main__":
    unittest.main()
