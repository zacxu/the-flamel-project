"""Real Git fixtures for exact path, byte, newline and clean-tree checks."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("git_publication", Path(__file__).with_name("verify_git_publication.py"))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

class GitPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="flamel-git-fixture-")
        self.root = Path(self.temporary.name)
        self.run_git("init", "-q", "-b", "main")
        self.run_git("config", "core.autocrlf", "true")
        self.run_git("config", "core.longpaths", "true")
        self.run_git("config", "user.name", "Fixture")
        self.run_git("config", "user.email", "fixture@example.invalid")
        self.data = {".gitattributes": b"* -text\n", "mixed.txt": b"one\r\ntwo\n",
                     "name with spaces.bin": bytes(range(256)), "crlf.txt": b"one\r\ntwo\r\n"}
        for name, content in self.data.items():
            (self.root / name).write_bytes(content)
        self.run_git("add", "--all")

    def tearDown(self):
        self.temporary.cleanup()

    def run_git(self, *arguments):
        return subprocess.run(["git", "-C", str(self.root), *arguments], check=True, capture_output=True)

    def test_index_preserves_mixed_binary_and_crlf_bytes(self):
        self.assertTrue(tool.verify_git_bytes(self.root, list(self.data), index=True)["passed"])

    def test_committed_tree_matches_and_is_clean(self):
        self.run_git("commit", "-qm", "Fixture")
        self.assertTrue(tool.verify_git_bytes(self.root, list(self.data), require_clean=True)["passed"])

    def test_source_change_after_staging_fails(self):
        (self.root / "mixed.txt").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            tool.verify_git_bytes(self.root, list(self.data), index=True)

    def test_unexpected_staged_private_path_fails(self):
        (self.root / ".env").write_text("fixture\n", encoding="utf-8")
        self.run_git("add", ".env")
        with self.assertRaises(ValueError):
            tool.verify_git_bytes(self.root, list(self.data), index=True)

    def test_missing_index_path_fails(self):
        self.run_git("rm", "--cached", "crlf.txt")
        with self.assertRaises(ValueError):
            tool.verify_git_bytes(self.root, list(self.data), index=True)

    def test_text_normalization_policy_rejected(self):
        (self.root / ".gitattributes").write_bytes(b"* text=auto\n")
        self.run_git("add", "--all")
        with self.assertRaises(ValueError):
            tool.verify_git_bytes(self.root, list(self.data), index=True)

    def test_untracked_unpublished_source_rejected(self):
        self.run_git("commit", "-qm", "Fixture")
        (self.root / "forgotten.py").write_text("pass\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            tool.verify_git_bytes(self.root, list(self.data), require_clean=True)

if __name__ == "__main__":
    unittest.main(verbosity=2)
