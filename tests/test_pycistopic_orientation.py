from __future__ import annotations

import types
import unittest

import numpy as np
import pandas as pd
from anndata import AnnData

from backend.tools.atac.topic.pycisTopic import _align_first_axis, _write_topic_outputs


class AlignFirstAxisTests(unittest.TestCase):
    """Unit tests for the orientation-robust alignment helper used when
    extracting model.cell_topic / model.topic_region into AnnData.

    pycisTopic is not installed in this environment, so these tests exercise
    only the shape-alignment logic directly with fake arrays standing in for
    the (possibly transposed) matrices pycisTopic's CistopicLDAModel returns.
    """

    def test_returns_array_unchanged_when_already_aligned(self):
        # cell_topic already (n_obs, n_topics)
        arr = np.zeros((10, 4))

        result = _align_first_axis(arr, target_len=10, name="model.cell_topic")

        self.assertEqual(result.shape, (10, 4))
        self.assertIs(result, arr)

    def test_transposes_when_first_axis_does_not_match(self):
        # Simulates pycisTopic returning cell_topic as topics x cells
        n_obs, n_topics = 10, 4
        transposed = np.arange(n_topics * n_obs).reshape(n_topics, n_obs)

        result = _align_first_axis(transposed, target_len=n_obs, name="model.cell_topic")

        self.assertEqual(result.shape, (n_obs, n_topics))
        np.testing.assert_array_equal(result, transposed.T)

    def test_topic_region_already_aligned_left_untouched(self):
        # Simulates pycisTopic returning topic_region as regions x topics
        # (the opposite of the topics x regions the current code assumes).
        n_vars, n_topics = 7, 3
        regions_by_topics = np.arange(n_vars * n_topics).reshape(n_vars, n_topics)

        result = _align_first_axis(regions_by_topics, target_len=n_vars, name="model.topic_region")

        # Already aligned (first axis == n_vars) -> returned as-is.
        self.assertEqual(result.shape, (n_vars, n_topics))
        np.testing.assert_array_equal(result, regions_by_topics)

    def test_topic_region_transposes_topics_x_regions_to_match_n_vars(self):
        n_vars, n_topics = 7, 3
        topics_by_regions = np.arange(n_topics * n_vars).reshape(n_topics, n_vars)

        result = _align_first_axis(topics_by_regions, target_len=n_vars, name="model.topic_region")

        self.assertEqual(result.shape, (n_vars, n_topics))
        np.testing.assert_array_equal(result, topics_by_regions.T)

    def test_ambiguous_square_case_left_untouched(self):
        # n_obs == n_topics: cannot disambiguate from shape alone.
        arr = np.arange(16).reshape(4, 4)

        result = _align_first_axis(arr, target_len=4, name="model.cell_topic")

        self.assertIs(result, arr)

    def test_raises_when_neither_dimension_matches(self):
        arr = np.zeros((5, 3))

        with self.assertRaisesRegex(ValueError, "Cannot determine orientation"):
            _align_first_axis(arr, target_len=10, name="model.cell_topic")

    def test_raises_on_non_2d_array(self):
        arr = np.zeros(5)

        with self.assertRaisesRegex(ValueError, "must be 2D"):
            _align_first_axis(arr, target_len=5, name="model.cell_topic")


class WriteTopicOutputsTests(unittest.TestCase):
    """Exercises _write_topic_outputs end-to-end: DataFrame .values
    extraction, obsm/varm assignment, the post-assignment asserts, and
    top-peaks DataFrame construction — the wiring _align_first_axis's own
    unit tests above don't touch.

    Uses a real (tiny) AnnData rather than a stand-in, and a fake model
    whose cell_topic/topic_region are pandas DataFrames in the orientation
    the original (pre-fix) code got backwards: cell_topic as topics x cells
    (needs a transpose to align with adata.n_obs) and topic_region as
    regions x topics (already aligned with adata.n_vars — the old code's
    unconditional `.T` would have broken this case). n_obs, n_vars, and
    n_topics are all distinct so shape mismatches can't hide behind
    coincidental equality.
    """

    def setUp(self):
        self.n_obs = 5
        self.n_vars = 8
        self.n_topics = 3

    def _build_adata_and_model(self):
        adata = AnnData(X=np.zeros((self.n_obs, self.n_vars), dtype=np.float32))
        adata.obs_names = [f"barcode_{i}" for i in range(self.n_obs)]
        adata.var_names = [f"chr1:{100 * i}-{100 * i + 50}" for i in range(self.n_vars)]

        # topics x cells (transposed relative to adata.n_obs) -> must transpose
        cell_topic_vals = np.arange(self.n_topics * self.n_obs).reshape(
            self.n_topics, self.n_obs
        )
        cell_topic_df = pd.DataFrame(
            cell_topic_vals,
            index=[f"Topic{i+1}" for i in range(self.n_topics)],
            columns=list(adata.obs_names),
        )

        # regions x topics (already aligned with adata.n_vars) -> no transpose
        topic_region_vals = np.arange(self.n_vars * self.n_topics).reshape(
            self.n_vars, self.n_topics
        )
        topic_region_df = pd.DataFrame(
            topic_region_vals,
            index=list(adata.var_names),
            columns=[f"Topic{i+1}" for i in range(self.n_topics)],
        )

        model = types.SimpleNamespace(cell_topic=cell_topic_df, topic_region=topic_region_df)
        return adata, model, cell_topic_vals, topic_region_vals

    def test_write_topic_outputs_aligns_and_writes_correct_shapes_and_values(self):
        adata, model, cell_topic_vals, topic_region_vals = self._build_adata_and_model()

        topic_region_sets = _write_topic_outputs(adata, model, n_top_peaks=4)

        # obsm["X_topic"] must be (n_obs, n_topics) and equal to the transpose
        # of the topics x cells input — not just shape-compatible.
        self.assertEqual(adata.obsm["X_topic"].shape, (self.n_obs, self.n_topics))
        np.testing.assert_array_equal(adata.obsm["X_topic"], cell_topic_vals.T)

        # varm["topic_peak_weights"] must be (n_vars, n_topics) and equal to
        # the (already-aligned) regions x topics input, untransposed.
        self.assertEqual(
            adata.varm["topic_peak_weights"].shape, (self.n_vars, self.n_topics)
        )
        np.testing.assert_array_equal(
            adata.varm["topic_peak_weights"], topic_region_vals
        )

        # The top-peaks DataFrame (reconstructed from the same array written
        # to varm) must index by adata.var_names with one column per topic.
        recovered_df = pd.DataFrame(
            adata.varm["topic_peak_weights"],
            index=adata.var_names,
            columns=[f"Topic{i+1}" for i in range(self.n_topics)],
        )
        self.assertEqual(list(recovered_df.index), list(adata.var_names))
        self.assertEqual(recovered_df.shape[1], self.n_topics)

        # topic_region_sets: one key per topic, values drawn from var_names,
        # and attached to adata.uns (not just returned).
        self.assertIs(adata.uns["topic_region_sets"], topic_region_sets)
        self.assertEqual(
            set(topic_region_sets.keys()),
            {f"Topic{i+1}" for i in range(self.n_topics)},
        )
        var_names_set = set(adata.var_names)
        for peaks in topic_region_sets.values():
            self.assertEqual(len(peaks), 4)
            self.assertTrue(all(p in var_names_set for p in peaks))

    def test_write_topic_outputs_would_catch_a_dropped_transpose_or_axis_swap(self):
        # Sanity-check the fixture itself is non-vacuous: if a regression
        # dropped the alignment (assigning cell_topic straight into obsm
        # without transposing, or swapping cell_topic/topic_region between
        # obsm/varm), something fails loudly — either AnnData's own obsm/varm
        # shape validation (real AnnData rejects mismatched first dims
        # outright) or, for a subtler bug that fools AnnData's validation,
        # the internal shape asserts inside _write_topic_outputs.
        adata, model, _, _ = self._build_adata_and_model()

        def _broken_write_topic_outputs(adata, model):
            # Mimics the pre-fix bug: assumes cell_topic is already
            # cell x topic (no alignment) — wrong here, since the fixture's
            # cell_topic is topics x cells (3, 5) vs adata.n_obs == 5.
            adata.obsm["X_topic"] = model.cell_topic.values.astype(np.float32)
            assert adata.obsm["X_topic"].shape[0] == adata.n_obs, (
                f"X_topic first dim {adata.obsm['X_topic'].shape[0]} != "
                f"adata.n_obs {adata.n_obs}"
            )

        with self.assertRaises((AssertionError, ValueError)):
            _broken_write_topic_outputs(adata, model)


if __name__ == "__main__":
    unittest.main()
