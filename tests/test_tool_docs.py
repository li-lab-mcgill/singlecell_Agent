import unittest

from agents.decision_schema import summarize_tool_specs


class ToolDocSummaryTests(unittest.TestCase):
    def test_summarize_tool_specs_includes_schema_details(self):
        docs = summarize_tool_specs(
            [
                {
                    "name": "rna_dimensionality_reduction",
                    "description": "Compute a latent embedding.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "string",
                                "enum": ["pca", "scvi", "seurat_pca", "scanvi"],
                            },
                            "n_pcs": {"type": "integer", "minimum": 1, "default": 50},
                            "output_h5ad_path": {"type": "string"},
                        },
                        "required": ["method", "output_h5ad_path"],
                    },
                }
            ]
        )

        self.assertIn("method* (string, enum=[pca, scvi, seurat_pca, scanvi])", docs)
        self.assertIn("n_pcs (integer, min=1, default=50)", docs)
        self.assertIn("output_h5ad_path* (string)", docs)


if __name__ == "__main__":
    unittest.main()
