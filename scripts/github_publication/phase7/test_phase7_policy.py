"""Protect the frozen Phase 6 evidence while permitting explicit Phase 7 source controls."""
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("phase7",Path(__file__).resolve().parents[1]/"verify_phase7.py")
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

class PolicyTests(unittest.TestCase):
    def test_current_ci_controls_allowed(self):
        names={"CI.md",".github/workflows/release-packaging.yml","README.md"}
        self.assertEqual(gate.validate_controls(names,{"paths":sorted(names)}),names)
    def test_active_source_edits_allowed(self):
        for name in ["website/src/app.tsx","website/scripts/verify-release.mjs","research_acquisition.py","scripts/phase4_gates.py","scripts/github_publication/phase6/manual_stage.mjs"]:
            with self.subTest(name=name):
                self.assertTrue(gate.mutable_baseline_path(name))
    def test_historical_artifacts_cannot_be_exempted(self):
        for name in ["artifacts/phase6/numerical_freeze.json","data/research.csv","config/run.json","website/contracts/core.json","website/reports/W6_BASELINE.json","requirements/analysis-lock.txt","vendor/CrystalFormer/main.py","publication/phase4/public-assets.json","publication/phase6/baseline-inputs.json","reports/GITHUB_PUBLICATION_PHASE6.md"]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    gate.validate_controls({name},{"paths":[name],"modified_frozen_input_paths":[name]})
    def test_withholding_published_history_rejected(self):
        with self.assertRaises(ValueError):
            gate.validate_controls({"README.md"},{"paths":["README.md"],"withheld_private_paths":["README.md"]})
    def test_secret_control_path_rejected(self):
        with self.assertRaises(ValueError):
            gate.validate_controls(set(),{"paths":["config/.env"]})

if __name__=="__main__":
    unittest.main(verbosity=2)
