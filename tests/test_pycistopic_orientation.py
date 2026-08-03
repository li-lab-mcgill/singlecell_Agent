from __future__ import annotations

import unittest

import numpy as np

from backend.tools.atac.topic.pycisTopic import _align_first_axis


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

    def test_topic_region_transposes_regions_x_topics_to_match_n_vars(self):
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


if __name__ == "__main__":
    unittest.main()
