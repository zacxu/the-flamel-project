#!/usr/bin/env python3
"""Small deterministic safety tests for public asset retrieval; no real network."""
import argparse
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import stat
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

spec = importlib.util.spec_from_file_location("public_assets", Path(__file__).with_name("public_assets.py"))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
OUTPUT = None

def digest(content):
    return hashlib.sha256(content).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="public-assets-case-", dir=OUTPUT)
        self.root = Path(self.temporary.name)
        self.assets = self.root / "assets"
        self.notices = self.root / "notices"
        self.assets.mkdir()
        self.notices.mkdir()
        self.manifest = self.root / "publication/phase4/public-assets.json"
        self.policy_path = self.root / "publication/phase3/release-selection.json"
        self.notice_path = self.root / "publication/phase3/notice-bundle.json"
        self.archives = []
        for index in range(11):
            scope = "production" if index == 0 else "project"
            entry = ("htdocs/index.html" if index == 0 else "data/input-%02d.bin" % index)
            content = b"frozen\r\n" + bytes(range(index + 1))
            self.archives.append(self.make_zip(self.assets, "flamel-fixture-%02d.zip" % index,
                                               {entry: content}, scope))
        self.notice = self.make_zip(self.notices, "flamel-notices.zip",
                                    {"THIRD_PARTY_NOTICES.md": b"fixture notice\n"}, "project")
        self.notice["group"] = "third-party-notices"
        self.data = {"schema_version": 1, "kind": tool.PUBLIC_KIND, "publication_status": "unpublished",
                     "repository": "zacxu/the-flamel-project", "asset_limit_bytes": tool.legacy.ASSET_LIMIT_BYTES,
                     "notice_archive_name": self.notice["name"],
                     "artifact_io_sha256": tool.sha256(Path(tool.__file__).with_name("artifact_io.py")),
                     "archives": copy.deepcopy(self.archives + [self.notice])}
        self.save_manifests()

    def tearDown(self):
        self.temporary.cleanup()

    def make_zip(self, folder, name, entries, scope, extra=None):
        path = folder / name
        with zipfile.ZipFile(path, "w") as archive:
            for key, value in entries.items():
                archive.writestr(key, value)
            if extra:
                archive.writestr(*extra)
        return {"name": name, "group": "fixture", "bytes": path.stat().st_size,
                "sha256": tool.sha256(path), "restore_scope": scope,
                "availability": "local-only", "download_url": None,
                "planned_download_url": "https://github.com/zacxu/the-flamel-project/releases/download/UNPUBLISHED/" + name,
                "members": [{"archive_path": key, "restore_path": key, "bytes": len(value),
                             "sha256": digest(value)} for key, value in entries.items()]}

    def save_manifests(self):
        historical_path = self.root / "publication/artifacts.json"
        save(historical_path, {"archives": self.archives})
        policy = {"historical_manifest_sha256": tool.sha256(historical_path),
                  "archives": [dict(record, publication_disposition="candidate-for-later-release")
                               for record in self.archives]}
        save(self.policy_path, policy)
        notice_source = copy.deepcopy(self.notice)
        for member in notice_source["members"]:
            member["source_path"] = member["restore_path"]
        save(self.notice_path, notice_source)
        self.data["phase3_selection_sha256"] = tool.sha256(self.policy_path)
        self.data["notice_record_sha256"] = tool.sha256(self.notice_path)
        save(self.manifest, self.data)

    def verify(self, scope="all"):
        return tool.verify(self.manifest, self.assets, self.notices, scope, self.root)

    def test_exact_public_subset_and_notices_verify_without_network(self):
        with mock.patch.object(socket, "socket", side_effect=AssertionError("unexpected network")):
            result = self.verify()
        self.assertEqual(result["archives"], 12)
        self.assertEqual(result["members"], 12)
        self.assertEqual(result["private_archives_included"], 0)

    def test_project_scope_always_includes_notice(self):
        result = self.verify("project")
        self.assertEqual(result["archives"], 11)
        self.assertTrue(result["required_notice_archive_included"])

    def test_production_scope_always_includes_notice(self):
        result = self.verify("production")
        self.assertEqual(result["archives"], 2)

    def test_hydration_preserves_bytes(self):
        target = self.root / "fresh"
        result = tool.hydrate(self.manifest, self.assets, target, self.notices, scratch_dir=self.root)
        self.assertEqual(result["created_files"], 11)
        self.assertEqual((target / "data/input-01.bin").read_bytes(), b"frozen\r\n" + bytes(range(2)))
        self.assertFalse((target / "htdocs/index.html").exists())

    def test_existing_destination_requires_explicit_merge(self):
        target = self.root / "existing"
        target.mkdir()
        with self.assertRaises(tool.ArtifactError):
            tool.hydrate(self.manifest, self.assets, target, self.notices, scratch_dir=self.root)

    def test_identical_merge_reuses_and_never_overwrites(self):
        target = self.root / "fresh"
        tool.hydrate(self.manifest, self.assets, target, self.notices, scratch_dir=self.root)
        result = tool.hydrate(self.manifest, self.assets, target, self.notices,
                              merge_existing=True, scratch_dir=self.root)
        self.assertEqual(result["created_files"], 0)
        self.assertEqual(result["reused_matching_files"], 11)

    def test_different_merge_preflights_without_new_writes(self):
        target = self.root / "existing"
        (target / "data").mkdir(parents=True)
        existing = target / "data/input-01.bin"
        existing.write_bytes(b"changed")
        before = list(target.rglob("*"))
        with self.assertRaises(tool.ArtifactError):
            tool.hydrate(self.manifest, self.assets, target, self.notices,
                         merge_existing=True, scratch_dir=self.root)
        self.assertEqual(list(target.rglob("*")), before)
        self.assertEqual(existing.read_bytes(), b"changed")

    def test_corrupt_archive_is_rejected(self):
        (self.assets / self.archives[1]["name"]).write_bytes(b"bad")
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_extra_zip_member_is_rejected(self):
        record = self.make_zip(self.assets, self.archives[1]["name"],
                               {"data/input-01.bin": b"exact"}, "project",
                               extra=("unlisted.txt", b"no"))
        self.archives[1] = record
        self.data["archives"][1] = copy.deepcopy(record)
        self.save_manifests()
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_traversal_member_is_rejected(self):
        member = self.data["archives"][1]["members"][0]
        member["archive_path"] = member["restore_path"] = "../escape.txt"
        save(self.manifest, self.data)
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_private_archive_name_is_never_allowed(self):
        name = sorted(tool.PRIVATE_ARCHIVES)[0]
        self.archives[1]["name"] = self.data["archives"][1]["name"] = name
        self.save_manifests()
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_notice_namespace_cannot_exclude_it_from_project_scope(self):
        self.data["archives"][-1]["restore_scope"] = "production"
        save(self.manifest, self.data)
        with self.assertRaises(tool.ArtifactError):
            self.verify("project")

    def test_production_archive_cannot_be_relabelled_as_project(self):
        self.data["archives"][0]["restore_scope"] = "project"
        save(self.manifest, self.data)
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_notice_cannot_be_omitted(self):
        self.data["archives"].pop()
        save(self.manifest, self.data)
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_notice_cannot_be_changed(self):
        self.data["archives"][-1]["sha256"] = "0" * 64
        save(self.manifest, self.data)
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_source_policy_hash_must_match(self):
        self.data["phase3_selection_sha256"] = "0" * 64
        save(self.manifest, self.data)
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_duplicate_json_keys_rejected(self):
        self.manifest.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_duplicate_archive_names_rejected(self):
        self.data["archives"][1] = copy.deepcopy(self.data["archives"][2])
        save(self.manifest, self.data)
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_raw_upf_member_never_enters_public_release(self):
        member = self.data["archives"][1]["members"][0]
        member["archive_path"] = member["restore_path"] = "data/forbidden.UPF"
        save(self.manifest, self.data)
        with self.assertRaises(tool.ArtifactError):
            self.verify()

    def test_unpublished_download_fails_before_network_or_target_creation(self):
        target = self.root / "should-not-exist"
        with mock.patch.object(tool, "download_one") as fetch:
            with self.assertRaises(tool.ArtifactError):
                tool.download_public(self.manifest, target)
        fetch.assert_not_called()
        self.assertFalse(target.exists())

    def test_authentication_http_and_untrusted_urls_rejected(self):
        for url in ("http://github.com/a", "file:///tmp/a", "https://127.0.0.1/a",
                    "https://u:p@github.com/a", "https://github.com:444/a",
                    "https://untrusted.example/a"):
            with self.subTest(url=url):
                with self.assertRaises(tool.ArtifactError):
                    tool.safe_url(url)

    def test_redirect_host_cannot_escape_trusted_endpoints(self):
        with self.assertRaises(tool.ArtifactError):
            tool.SafeRedirects().redirect_request(None, None, 302, "", {}, "http://127.0.0.1/a")

    def download_fixture(self, payload=b"exact", expected=b"exact"):
        response = io.BytesIO(payload)
        response.headers = {"Content-Length": str(len(payload))}
        response.geturl = lambda: "https://archive.materialscloud.org/public"
        opener = mock.Mock()
        opener.open.return_value = response
        record = {"name": "file.bin", "bytes": len(expected), "sha256": digest(expected),
                  "url": "https://archive.materialscloud.org/public"}
        return record, opener

    def test_bounded_download_commits_only_verified_bytes(self):
        record, opener = self.download_fixture()
        with mock.patch.object(tool, "build_opener", return_value=opener):
            result = tool.download_one(record, self.root / "cache")
        self.assertEqual(result["network_fetches"], 1)
        self.assertEqual((self.root / "cache/file.bin").read_bytes(), b"exact")

    def test_bad_download_hash_leaves_no_committed_file(self):
        record, opener = self.download_fixture(payload=b"wrong")
        with mock.patch.object(tool, "build_opener", return_value=opener):
            with self.assertRaises(tool.ArtifactError):
                tool.download_one(record, self.root / "cache")
        self.assertEqual(list((self.root / "cache").iterdir()), [])

    def test_oversized_download_rejected(self):
        record, opener = self.download_fixture(payload=b"too-long")
        with mock.patch.object(tool, "build_opener", return_value=opener):
            with self.assertRaises(tool.ArtifactError):
                tool.download_one(record, self.root / "cache")
        self.assertEqual(list((self.root / "cache").iterdir()), [])

    def test_existing_download_never_overwritten(self):
        cache = self.root / "cache"
        cache.mkdir()
        output = cache / "file.bin"
        output.write_bytes(b"old")
        record, opener = self.download_fixture()
        with mock.patch.object(tool, "build_opener", return_value=opener):
            with self.assertRaises(tool.ArtifactError):
                tool.download_one(record, cache)
        self.assertEqual(output.read_bytes(), b"old")
        opener.open.assert_not_called()

    def test_verified_existing_download_reused_without_network(self):
        cache = self.root / "cache"
        cache.mkdir()
        (cache / "file.bin").write_bytes(b"exact")
        record, opener = self.download_fixture()
        with mock.patch.object(tool, "build_opener", return_value=opener):
            result = tool.download_one(record, cache)
        self.assertEqual(result["network_fetches"], 0)
        opener.open.assert_not_called()

    def test_reparse_asset_ancestor_rejected(self):
        original = tool.legacy.os.lstat
        asset_absolute = tool.legacy._absolute(self.assets)
        def guarded(path, *args, **kwargs):
            # POSIX TemporaryDirectory cleanup calls lstat with dir_fd.
            if not args and kwargs.get("dir_fd") is None and tool.legacy._absolute(path) == asset_absolute:
                return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_file_attributes=0x400)
            return original(path, *args, **kwargs)
        with mock.patch.object(tool.legacy.os, "lstat", side_effect=guarded):
            with self.assertRaises(tool.ArtifactError):
                self.verify()

    def make_upfs(self, bad_path=None, wrong_hash=False, link=False):
        folder = self.root / "upstream"
        folder.mkdir()
        names = ["Ca.UPF", "Mg.UPF", "O.UPF"]
        payloads = {name: ("upstream-" + name).encode() for name in names}
        archive_path = folder / "SSSP_1.3.0_PBE_efficiency.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            directory = tarfile.TarInfo(".")
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)
            for name, payload in payloads.items():
                entry = tarfile.TarInfo("./" + name)
                entry.size = len(payload)
                archive.addfile(entry, io.BytesIO(payload))
            if bad_path:
                entry = tarfile.TarInfo(bad_path)
                entry.size = 1
                archive.addfile(entry, io.BytesIO(b"x"))
            if link:
                entry = tarfile.TarInfo("symlink")
                entry.type = tarfile.SYMTYPE
                entry.linkname = "../../elsewhere"
                archive.addfile(entry)
        files = []
        for index, name in enumerate(names):
            copies = ["data/pseudopotentials/" + name] + [
                "artifacts/input-%02d/%s" % (n, name) for n in range(13 if index < 2 else 12)]
            files.append({"filename": name, "bytes": len(payloads[name]), "sha256": digest(payloads[name]),
                          "licence": "GPL-3.0" if index == 0 else "GPL-2.0-or-later",
                          "restore_paths": copies})
        if wrong_hash:
            files[0]["sha256"] = "0" * 64
        serialized = [{"path": "artifacts/old-%02d/scratch/run.save/Ca.UPF" % n,
                       "bytes": 1, "sha256": digest(b"x")} for n in range(36)]
        data = {"schema_version": 1, "kind": tool.UPF_KIND,
                "upstream_archive": {"name": archive_path.name, "bytes": archive_path.stat().st_size,
                                     "sha256": tool.sha256(archive_path),
                                     "url": "https://archive.materialscloud.org/public"},
                "files": files, "nonreconstructible_serialized_scratch_members": serialized}
        path = self.root / "upfs.json"
        save(path, data)
        return path, archive_path, payloads

    def retrieve_fixture(self, manifest, archive, destination, recorded=False):
        with mock.patch.object(tool, "download_one", return_value={
                "path": str(archive), "network_fetches": 0, "reused_verified": True}):
            return tool.retrieve_upfs(manifest, archive.parent, destination, recorded)

    def test_canonical_upfs_preserve_exact_three_inputs(self):
        manifest, archive, payloads = self.make_upfs()
        target = self.root / "upfs-canonical"
        result = self.retrieve_fixture(manifest, archive, target)
        self.assertEqual(result["placed_files"], 3)
        for name, payload in payloads.items():
            self.assertEqual((target / "data/pseudopotentials" / name).read_bytes(), payload)

    def test_recorded_inputs_restore_41_and_never_serialized_scratch(self):
        manifest, archive, _ = self.make_upfs()
        target = self.root / "upfs-inputs"
        result = self.retrieve_fixture(manifest, archive, target, recorded=True)
        self.assertEqual(result["placed_files"], 41)
        self.assertEqual(result["serialized_scratch_members_not_reconstructed"], 36)
        self.assertFalse(any("/scratch/" in p.as_posix() for p in target.rglob("*")))

    def test_wrong_upf_content_fails_before_destination_creation(self):
        manifest, archive, _ = self.make_upfs(wrong_hash=True)
        target = self.root / "no-upfs"
        with self.assertRaises(tool.ArtifactError):
            self.retrieve_fixture(manifest, archive, target)
        self.assertFalse(target.exists())

    def test_tar_traversal_is_rejected(self):
        manifest, archive, _ = self.make_upfs(bad_path="../escape.UPF")
        with self.assertRaises(tool.ArtifactError):
            self.retrieve_fixture(manifest, archive, self.root / "no-upfs")

    def test_cached_upstream_mutation_rejected_before_writes(self):
        manifest, archive, _ = self.make_upfs()
        with archive.open("ab") as stream:
            stream.write(b"changed")
        target = self.root / "no-upfs"
        with self.assertRaises(tool.ArtifactError):
            self.retrieve_fixture(manifest, archive, target)
        self.assertFalse(target.exists())

    def test_tar_links_are_rejected(self):
        manifest, archive, _ = self.make_upfs(link=True)
        with self.assertRaises(tool.ArtifactError):
            self.retrieve_fixture(manifest, archive, self.root / "no-upfs")

def main():
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    if args.output_root:
        OUTPUT = args.output_root.absolute()
        if OUTPUT.exists():
            parser.error("Output root must be new")
        OUTPUT.mkdir(parents=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SafetyTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = {"tests": result.testsRun, "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
              "failed": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
              "real_network_fetches": 0, "fixtures_removed_after_each_test": True,
              "public_assets_sha256": tool.sha256(Path(tool.__file__))}
    if OUTPUT:
        save(OUTPUT / "validation.json", record)
    print(json.dumps(record))
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    raise SystemExit(main())
