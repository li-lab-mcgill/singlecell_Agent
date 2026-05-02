import sys
import types
import unittest


if "textgrad" not in sys.modules:
    fake_textgrad = types.ModuleType("textgrad")
    fake_textgrad.get_engine = lambda *args, **kwargs: None
    sys.modules["textgrad"] = fake_textgrad

if "dotenv" not in sys.modules:
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["dotenv"] = fake_dotenv

if "pandas" not in sys.modules:
    sys.modules["pandas"] = types.ModuleType("pandas")
sys.modules["pandas"].DataFrame = type("DataFrame", (), {})

if "numpy" not in sys.modules:
    sys.modules["numpy"] = types.ModuleType("numpy")

from agents.consultant import validate_prior_decision_payload


class ConsultantSchemaTests(unittest.TestCase):
    def test_validate_prior_decision_accepts_empty_shape_for_json_report(self):
        parsed = validate_prior_decision_payload(
            {
                "use_priors": True,
                "decision_reason": "priors help",
                "selected_resource_names": ["CellMarker"],
                "prior_schema": {
                    "output_files": [
                        {
                            "file_name": "priors/prior_coverage_report.json",
                            "description": "Summary statistics on prior coverage and filtering",
                            "dtype": "json",
                            "shape": [],
                        }
                    ]
                },
            }
        )
        output_files = parsed["prior_schema"]["output_files"]
        self.assertEqual(len(output_files), 1)
        self.assertEqual(output_files[0]["file_name"], "priors/prior_coverage_report.json")
        self.assertEqual(output_files[0]["dtype"], "json")
        self.assertNotIn("shape", output_files[0])


if __name__ == "__main__":
    unittest.main()
