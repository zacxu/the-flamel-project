"""Focused tamper checks for the read-only saved-evidence audit."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

SCRIPT = pathlib.Path(__file__).with_name("audit_saved_evidence.py")
spec = importlib.util.spec_from_file_location("saved_audit", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SOURCE = pathlib.Path(__file__).resolve().parents[2]

class EvidenceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="saved-evidence-tests-", dir=SCRATCH)
        cls.root = pathlib.Path(cls.temp.name) / "source"
        cls.root.mkdir()
        export = json.loads((SOURCE / "website/reports/W1_EXPORT.json").read_text())
        manifest_rel = "website/" + export["manifestPath"].replace("\\", "/")
        manifest = json.loads((SOURCE / manifest_rel).read_text())
        required = set(export["baseline"]) | set(export["inputAllowlist"]) | {
            "website/reports/W1_EXPORT.json", manifest_rel, "website/public/research/manifest.json",
            "artifacts/phase6/audit.json", "artifacts/phase6/readiness.json",
        } | {"website/public/research/" + row["path"] for row in manifest["files"]}
        for rel in required:
            target = cls.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / rel, target)
        cls.before = {rel: module.sha(cls.root / rel) for rel in required}
        cls.input_name = next(iter(export["inputAllowlist"]))
        cls.payload_name = "website/public/research/" + manifest["files"][0]["path"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def fail_after_change(self, relative):
        path = self.root / relative
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n")
            with self.assertRaises(ValueError):
                module.audit(self.root)
        finally:
            path.write_bytes(original)

    def test_public_inputs_work_without_environments_or_large_archives(self):
        result = module.audit(self.root)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["source_inputs_verified"], 103)
        self.assertEqual(result["public_payloads_verified"], 75)
        self.assertFalse((self.root / ".envs").exists())
        self.assertFalse((self.root / "checkpoints").exists())

    def test_curated_input_tamper_fails(self):
        self.fail_after_change(self.input_name)

    def test_payload_tamper_fails(self):
        self.fail_after_change(self.payload_name)

    def test_budget_tamper_fails(self):
        self.fail_after_change("artifacts/budget_ledger.json")

    def test_nested_historical_audit_tamper_fails(self):
        self.fail_after_change("artifacts/phase6/audit.json")

    def test_rewriting_authority_record_is_rejected(self):
        self.fail_after_change("website/reports/W1_EXPORT.json")

    def test_historical_count_is_not_claimed_as_new_execution(self):
        result = module.audit(self.root)
        self.assertFalse(result["historical_checks_reexecuted"])
        self.assertEqual(result["new_experiments"], 0)
        self.assertEqual(result["models_deserialized"], 0)

    def test_output_cannot_overwrite_existing_file(self):
        report = pathlib.Path(self.temp.name) / "existing.json"
        report.write_text("keep")
        result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(self.root),
                                 "--report", str(report)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report.read_text(), "keep")

    def test_output_cannot_write_to_source(self):
        report = self.root / "new.json"
        result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(self.root),
                                 "--report", str(report)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report.exists())

    def test_new_report_rejects_reparse_parent(self):
        parent = pathlib.Path(self.temp.name)
        original = pathlib.Path.lstat
        def mocked_lstat(path):
            if path == parent:
                return SimpleNamespace(st_mode=module.stat.S_IFDIR, st_file_attributes=0x400)
            return original(path)
        with mock.patch.object(pathlib.Path, "lstat", mocked_lstat):
            with self.assertRaises(ValueError):
                module.no_reparse_existing_ancestors(parent)

    def test_source_bytes_remain_unchanged(self):
        module.audit(self.root)
        self.assertEqual(self.before, {rel: module.sha(self.root / rel) for rel in self.before})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, default=SOURCE)
    parser.add_argument("--scratch", type=pathlib.Path, required=True)
    args, remaining = parser.parse_known_args()
    SOURCE, SCRATCH = args.source, args.scratch
    if not SCRATCH.is_dir():
        parser.error("--scratch must already exist")
    unittest.main(argv=[sys.argv[0], *remaining])
