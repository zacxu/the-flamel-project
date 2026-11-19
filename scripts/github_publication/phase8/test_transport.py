"""Deployment boundaries and recovery from a partially completed publication."""
import ftplib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location("phase8_transport", Path(__file__).with_name("transport.py"))
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


class TransportTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.state = Path(tmp.name)
        self.old_build = "ui-w6-" + "b" * 20
        pointer = json.dumps({"studyId": "flamel-frozen-study-20261022", "revision": 1}).encode()
        self.old = {
            "index.html": b'<title>The Flamel Project</title><script src="./assets/index-old.js"></script>',
            "assets/index-old.js": self.old_build.encode(),
            "research/manifest.json": pointer,
            ".htaccess": (transport.ROOT / "website/deployment/root-image-adapter/.htaccess").read_bytes(),
        }
        rows = [{"path": k, "bytes": len(v), "sha256": transport.digest(v)}
                for k, v in self.old.items() if k != ".htaccess"]
        self.old["release-manifests/" + self.old_build + ".json"] = json.dumps({
            "uiBuildId": self.old_build, "studyId": "flamel-frozen-study-20261022",
            "files": rows, "exportManifestSha256": transport.digest(pointer)}).encode()
        self.old["assets/unrelated.js"] = b"keep"
        self.remote = transport.RehearsalHost(self.old)
        self.desired = {
            "assets/index-new.js": b"new js",
            "ui/figures/overview.new.webp": b"fixture image",
            "research/manifest.json": pointer.replace(b"1}", b"2}"),
            ".htaccess": (transport.ROOT / "website/deployment/cache-fix/.htaccess").read_bytes(),
            "index.html": self.old["index.html"].replace(b"index-old.js", b"index-new.js"),
        }
        self.verified = {"source_commit": "a" * 40, "payload_sha256": "b" * 64, "ui_build_id": "current"}
        self.expected = transport.digest(self.old["index.html"])

    def snapshot(self):
        return transport.snapshot(self.remote, self.verified, self.desired, self.expected, self.state)

    def apply(self, rollback=False):
        return transport.apply(self.remote, self.verified, self.desired, self.state, rollback, self.expected)

    def test_snapshot_uses_original_entry_and_atomic_order_with_idempotent_rollback(self):
        record = self.snapshot()
        self.assertEqual(self.remote.files, self.old)
        self.assertEqual(record["previous_sha256"]["index.html"], self.expected)
        self.assertEqual(self.apply()["written_paths"][-3:], list(transport.MUTABLE))
        self.assertEqual(self.apply()["written_paths"], [])
        self.assertEqual(self.apply(rollback=True)["written_paths"], list(transport.MUTABLE))
        for k, v in self.old.items():
            self.assertEqual(self.remote.read(k), v)
        self.assertEqual(self.apply(rollback=True)["written_paths"], [])
        self.assertEqual(self.remote.read("assets/index-new.js"), b"new js")

    def test_wrong_existing_entry_rejected_before_upload_or_snapshot(self):
        self.expected = "f" * 64
        with self.assertRaisesRegex(ValueError, "expected live entry"):
            self.snapshot()
        self.assertFalse((self.state / "snapshot.json").exists())
        self.assertEqual(self.remote.files, self.old)

    def test_immutable_collision_fails_before_any_write(self):
        self.remote.files["assets/index-new.js"] = b"somebody else's bytes"
        before = self.remote.files.copy()
        with self.assertRaisesRegex(ValueError, "versioned file differs"):
            self.snapshot()
        self.assertEqual(self.remote.files, before)

    def test_existing_effective_sidecar_preserves_host_original(self):
        image = "ui/figures/overview.new.webp"
        self.remote.files[image] = b"provider image representation"
        self.remote.files[image + ".bin"] = self.desired[image]
        record = self.snapshot()
        self.assertNotIn(image, record["new_immutable_files"])
        self.apply()
        self.assertEqual(self.remote.read(image), b"provider image representation")
        self.assertEqual(transport.effective(self.remote, image), self.desired[image])

    def test_rollback_validates_entire_previous_release_before_writes(self):
        self.snapshot()
        self.apply()
        self.remote.files["assets/index-old.js"] = b"missing previous application"
        before = self.remote.files.copy()
        with self.assertRaisesRegex(ValueError, "versioned file differs"):
            self.apply(rollback=True)
        self.assertEqual(self.remote.files, before)

    def test_rollback_recovers_missing_prior_asset_from_durable_snapshot(self):
        self.snapshot()
        self.apply()
        del self.remote.files['assets/index-old.js']
        self.assertIn('assets/index-old.js', self.apply(rollback=True)['written_paths'])
        self.assertEqual(self.remote.files['assets/index-old.js'], self.old['assets/index-old.js'])

    def test_unexpected_edit_preserved_on_rollback(self):
        self.snapshot()
        self.apply()
        self.remote.files[".htaccess"] = b"operator update"
        before = self.remote.files.copy()
        with self.assertRaisesRegex(ValueError, "diverged"):
            self.apply(rollback=True)
        self.assertEqual(self.remote.files, before)

    def test_partial_deploy_can_be_rolled_back(self):
        self.snapshot()
        original = self.remote.replace

        def interrupted(path, data, before):
            if path == ".htaccess":
                raise OSError("connection lost")
            original(path, data, before)

        self.remote.replace = interrupted
        with self.assertRaisesRegex(OSError, "connection lost"):
            self.apply()
        self.assertEqual(self.remote.read("index.html"), self.old["index.html"])
        self.remote.replace = original
        self.assertEqual(self.apply(rollback=True)["written_paths"], ["research/manifest.json"])

    def test_tampered_backup_and_foreign_account_fail_without_writes(self):
        self.snapshot()
        self.remote.binding = "another-account"
        with self.assertRaisesRegex(ValueError, "different account"):
            self.apply()
        self.remote.binding = "local-rehearsal"
        (self.state / "rollback/index.html").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "inventory mismatch"):
            self.apply()
        self.assertEqual(self.remote.files, self.old)

    def test_ambiguous_550_is_not_missing(self):
        client = transport.FTPS.__new__(transport.FTPS)
        client.ftp = Mock()
        client.ftp.retrbinary.side_effect = ftplib.error_perm("550 Permission denied")
        client.ftp.mlsd.return_value = [("index.html", {"type": "file"})]
        with self.assertRaises(ftplib.error_perm):
            client.read("index.html")
        client.ftp.mlsd.return_value = []
        self.assertIsNone(client.read("index.html"))

    def test_server_rejecting_overwrite_never_deletes_live_destination(self):
        client = transport.FTPS.__new__(transport.FTPS)
        client.ftp = Mock()
        client.ftp.rename.side_effect = ftplib.error_perm("550 Destination already exists")
        client.kind = lambda path: None
        client.read = lambda name: b"old" if name == "index.html" else b"new"
        with self.assertRaises(ftplib.error_perm):
            client.replace("index.html", b"new", transport.digest(b"old"))
        deleted = client.ftp.delete.call_args[0][0]
        self.assertRegex(deleted, r"^/htdocs/flamel-upload-[a-f0-9]{32}\.bin$")


if __name__ == "__main__":
    unittest.main()
