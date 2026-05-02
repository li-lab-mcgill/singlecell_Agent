from __future__ import annotations

import types
import unittest
import gzip
import tempfile
from pathlib import Path

from backend.atac import _celltype_annotation, _peak_calling
from backend.atac._utils import parse_peak_coordinates, peak_coordinate_schema


class AtacUtilsTests(unittest.TestCase):
    def test_peak_coordinate_schema_accepts_var_columns(self):
        adata = types.SimpleNamespace(
            var={"chrom": ["chr1"], "start": [10], "end": [50]},
            var_names=["peak_1"],
        )

        self.assertEqual(peak_coordinate_schema(adata), {"schema": "var_columns", "n_peaks": 1})
        self.assertEqual(parse_peak_coordinates(adata), [("chr1", 10, 50, "peak_1")])

    def test_peak_coordinate_schema_accepts_var_names(self):
        adata = types.SimpleNamespace(var={}, var_names=["chr1:10-50", "chr2:5-20"])

        self.assertEqual(
            peak_coordinate_schema(adata),
            {"schema": "var_names_chr_start_end", "n_peaks": 2},
        )
        self.assertEqual(
            parse_peak_coordinates(adata),
            [("chr1", 10, 50, "chr1:10-50"), ("chr2", 5, 20, "chr2:5-20")],
        )

    def test_peak_coordinate_schema_rejects_missing_coordinates(self):
        adata = types.SimpleNamespace(var={}, var_names=["geneA"])

        with self.assertRaisesRegex(ValueError, "ATAC peak coordinates"):
            peak_coordinate_schema(adata)

    def test_macs_input_conversion_handles_gz_fragments_and_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fragments = Path(tmpdir) / "fragments.tsv.gz"
            output_bed = Path(tmpdir) / "macs_input.bed"
            with gzip.open(fragments, "wt", encoding="utf-8") as handle:
                handle.write("chr1\t10\t20\tAAAC-1\t2\n")
                handle.write("chr2\t30\t50\tAAAG-1\t1\n")

            n_written = _peak_calling._write_macs_bed_input(fragments, output_bed)

            self.assertEqual(n_written, 3)
            self.assertEqual(
                output_bed.read_text(encoding="utf-8").splitlines(),
                ["chr1\t10\t20", "chr1\t10\t20", "chr2\t30\t50"],
            )

    def test_marker_peaks_overlap_intervals_not_only_exact_names(self):
        peaks = [("chr1", 100, 200, "peak_a"), ("chr1", 300, 350, "peak_b")]
        peak_index = _celltype_annotation._peak_index(peaks)

        self.assertEqual(_celltype_annotation._marker_indices("chr1:150-250", peaks, peak_index), [0])
        self.assertEqual(_celltype_annotation._marker_indices({"chrom": "chr1", "start": 320, "end": 330}, peaks, peak_index), [1])
        self.assertEqual(_celltype_annotation._marker_indices("peak_b", peaks, peak_index), [1])

    def test_tfidf_v3_source_uses_log_tf_times_log_idf(self):
        source = Path("backend/atac/_tfidf_lsi.py").read_text(encoding="utf-8")
        v3_block = source.split('if method == "tfidf_lsi_v3":', 1)[1].split("else:", 1)[0]

        self.assertIn("Signac method 3", v3_block)
        self.assertIn("tf.data = np.log1p(tf.data)", v3_block)
        self.assertIn("tf.multiply(np.log1p(idf))", v3_block)

    def test_da_source_requires_peak_coordinates_and_binarizes_by_default(self):
        source = Path("backend/atac/_differential_accessibility.py").read_text(encoding="utf-8")

        self.assertIn("coordinate_schema = peak_coordinate_schema(adata)", source)
        self.assertNotIn('"schema": "unvalidated"', source)
        self.assertIn("binarize: bool = True", source)
        self.assertIn("use_raw=False", source)

    def test_peak2gene_source_defaults_to_positive_links_and_returns_links(self):
        source = Path("backend/atac/_peak_to_gene_linking.py").read_text(encoding="utf-8")

        self.assertIn("allow_negative: bool = False", source)
        self.assertIn("elif corr < min_correlation", source)
        self.assertIn('"links": rows[:max_links_in_result]', source)


if __name__ == "__main__":
    unittest.main()
