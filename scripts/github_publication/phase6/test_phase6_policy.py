"""Exercise the Phase 6 mutable-source boundary without editing any project file."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "phase6_policy_under_test", ROOT / "scripts/github_publication/verify_phase6.py")
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)

FROZEN = (
    "artifacts/budget_ledger.json",
    "artifacts/runtime_budget_events.jsonl",
    "artifacts/phase6/numerical_freeze.json",
    "data/provenance.json",
    "data/pseudopotentials/manifest.json",
    "config/phase2_protocol.json",
    "requirements/analysis-lock.txt",
    "requirements/phase4/analysis-historical-lock.txt",
    "requirements/phase4/bootstrap.json",
    "vendor/CrystalFormer/data/atoms.json",
    "vendor/CrystalFormer/.gitignore",
    "website/contracts/research-contract.json",
    "website/reports/W1_EXPORT.json",
    "website/reports/W6_INTEGRATION_VALIDATION.json",
    "website/public/research/manifest.json",
    "reports/GITHUB_PUBLICATION_PHASE5.md",
    "publication/phase5/baseline-inputs.json",
)
APPLICATION = (
    "website/src/App.tsx",
    "website/src/styles.css",
    "website/src/logo.svg",
    "website/scripts/validate.mjs",
    "website/scripts/validate.js",
    "website/scripts/validate.py",
    "website/scripts/validate.ps1",
    "website/scripts/types.ts",
)
RESEARCH = (
    "research_acquisition.py",
    "research_budget.py",
    "scripts/phase4_gates.py",
    "scripts/phase2_json_columns.py",
    "scripts/github_publication/verify_phase6.py",
    "scripts/github_publication/install_website.ps1",
    "scripts/github_publication/phase6/test_research_ci.py",
)


def controls(paths, *, modified=None, withheld=None):
    return {
        "paths": list(paths),
        "modified_frozen_input_paths": list(paths if modified is None else modified),
        "withheld_private_paths": list(withheld or []),
    }


class MutableSourceBoundary(unittest.TestCase):
    def test_legitimate_application_sources_are_mutable(self):
        for name in APPLICATION:
            with self.subTest(path=name):
                self.assertTrue(POLICY.mutable_baseline_path(name))

    def test_legitimate_research_and_publication_sources_are_mutable(self):
        for name in RESEARCH:
            with self.subTest(path=name):
                self.assertTrue(POLICY.mutable_baseline_path(name))

    def test_only_exact_reviewed_website_configuration_is_mutable(self):
        for name in ("package.json", "package-lock.json", "tsconfig.json", "vite.config.ts"):
            with self.subTest(path=name):
                self.assertTrue(POLICY.mutable_baseline_path("website/" + name))
        for name in ("website/.npmrc", "website/other-config.json",
                     "website/tsconfig-unreviewed.json", "website/public/config.json"):
            with self.subTest(path=name):
                self.assertFalse(POLICY.mutable_baseline_path(name))

    def test_frozen_evidence_dependencies_contracts_and_vendor_stay_frozen(self):
        for name in FROZEN:
            with self.subTest(path=name):
                self.assertFalse(POLICY.mutable_baseline_path(name))

    def test_similar_prefixes_and_non_source_extensions_do_not_expand_scope(self):
        for name in (
            "website/src-other/App.tsx",
            "website/scripts-old/validate.py",
            "website/src/accepted-evidence.json",
            "website/scripts/saved-results.csv",
            "website/scripts/installer.exe",
            "research_budget.py.backup",
            "research_archive/model.joblib",
            "scripts/phase4_results.json",
            "scripts/github_publication-old/check.py",
            "scripts/github_publication/secrets.key",
        ):
            with self.subTest(path=name):
                self.assertFalse(POLICY.mutable_baseline_path(name))

    def test_normal_pr_controls_allow_source_edits_and_a_new_workflow(self):
        existing = list(APPLICATION) + list(RESEARCH) + ["README.md"]
        new_workflow = ".github/workflows/research-ci.yml"
        baseline = set(existing) | set(FROZEN)
        document = controls(existing + [new_workflow], modified=existing)
        POLICY.validate_controls(baseline, document)

    def test_control_metadata_cannot_exempt_a_frozen_baseline_file(self):
        # This mirrors the actual bypass: declare both a control and modified
        # frozen path so the older generic overlay checker would skip its hash.
        for victim in FROZEN:
            with self.subTest(victim=victim):
                baseline = {victim, "research_budget.py"}
                document = controls(["research_budget.py", victim])
                with self.assertRaises(ValueError):
                    POLICY.validate_controls(baseline, document)

    def test_withholding_cannot_remove_historical_or_mutable_baseline_inputs(self):
        for victim in ("artifacts/budget_ledger.json", "research_budget.py"):
            with self.subTest(victim=victim):
                document = controls([], withheld=[victim])
                with self.assertRaises(ValueError):
                    POLICY.validate_controls({victim}, document)

    def test_current_root_controls_do_not_authorize_arbitrary_historical_docs(self):
        self.assertTrue(POLICY.mutable_baseline_path("README.md"))
        self.assertTrue(POLICY.mutable_baseline_path(".github/workflows/initial-ci.yml"))
        for name in ("reports/GITHUB_PUBLICATION_PHASE4.md",
                     "publication/phase4/baseline-inputs.json",
                     "publication/phase3/THIRD_PARTY_NOTICES.md"):
            with self.subTest(path=name):
                self.assertFalse(POLICY.mutable_baseline_path(name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
