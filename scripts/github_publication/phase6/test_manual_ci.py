"""Adversarial exact-package/source/provenance fixtures; no network or models."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

SPEC=importlib.util.spec_from_file_location("_manual_ci",Path(__file__).with_name("manual_ci.py"))
tool=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)
ROOT=Path(__file__).resolve().parents[3]
SOURCE="1"*40
UI="ui-w6-"+"a"*20

def dumps(value):
    return (json.dumps(value,sort_keys=True,indent=2)+"\n").encode()

def make_bundle(root):
    root.mkdir()
    runtime={"index.html":b'<script src="./assets/main.js"></script><link href="./assets/main.css">',
             "assets/main.js":UI.encode(),"assets/main.css":b"body{}"}
    rows=[{"path":n,"bytes":len(v),"sha256":tool.sha(v)} for n,v in sorted(runtime.items())]
    identity={"uiBuildId":UI,"sourceFingerprint":"a"*64,"dataReleaseId":"data-v1-test",
              "exportManifestSha256":"b"*64}
    manifest_path="release-manifests/"+UI+".json"
    manifest={**identity,"files":rows}
    runtime[manifest_path]=dumps(manifest)
    rows=[{"path":n,"bytes":len(v),"sha256":tool.sha(v)} for n,v in sorted(runtime.items())]
    with zipfile.ZipFile(root/"payload.zip","w",compression=zipfile.ZIP_DEFLATED) as stream:
        for name,value in sorted(runtime.items()):
            stream.writestr(name,value)
    archive=(root/"payload.zip").read_bytes()
    record={**identity,"payload":"dist/","fileCount":len(rows),"totalBytes":sum(r["bytes"] for r in rows),
            "files":rows,"manifestPath":manifest_path,"manifestSha256":tool.sha(runtime[manifest_path]),
            "archive":{"path":"releases/test.zip","bytes":len(archive),"sha256":tool.sha(archive)}}
    (root/"package-record.json").write_bytes(dumps(record))
    plan={"packageSha256":tool.sha((root/"package-record.json").read_bytes()),"uiBuildId":UI,
          "entryTarget":"index.html","stableUrl":"https://theflamelproject.42web.io/refresh",
          "policy":{"sha256":tool.POLICY},"filesBeforeEntry":[r for r in rows if r["path"]!="index.html"]}
    (root/"upload-plan.json").write_bytes(dumps(plan))
    (root/"host").mkdir(); (root/"entry-last").mkdir()
    (root/"host/.htaccess").write_bytes((ROOT/"website/deployment/cache-fix/.htaccess").read_bytes())
    (root/"entry-last/index.html").write_bytes(runtime["index.html"])
    provenance={"kind":"flamel-ci-package-v1","repository":tool.REPO,"source_commit":SOURCE,
                "producer_workflow":".github/workflows/release-packaging.yml","producer_run_id":"7",
                "status":"VERIFIED_PACKAGE_NOT_DEPLOYED","hosting_deployed":False,"ui_build_id":UI}
    (root/"provenance.json").write_bytes(dumps(provenance))
    reseal(root)
    return root

def reseal(root):
    provenance=tool.read(root/"provenance.json")
    provenance["files"]=[tool.row(root,n) for n in sorted(tool.FILES)]
    (root/"provenance.json").write_bytes(dumps(provenance))
    rows=[tool.row(root,n) for n in sorted([*tool.FILES,"provenance.json"])]
    (root/"SHA256SUMS").write_text("".join(r["sha256"]+"  "+r["path"]+"\n" for r in rows),encoding="ascii",newline="\n")

class ManualTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="flamel-manual-ci-")
        self.addCleanup(self.tmp.cleanup)
        self.root=make_bundle(Path(self.tmp.name)/"package")
    def verify(self):
        return tool.verify_package(self.root,SOURCE,"7")
    def test_valid_source_bound_package(self):
        self.assertEqual(self.verify()["status"],"VERIFIED_PACKAGE_NOT_DEPLOYED")
    def test_wrong_source_sha_rejected(self):
        with self.assertRaises(ValueError): tool.verify_package(self.root,"2"*40,"7")
    def test_wrong_producer_run_rejected(self):
        with self.assertRaises(ValueError): tool.verify_package(self.root,SOURCE,"8")
    def test_extra_private_file_rejected(self):
        (self.root/".env").write_text("fixture",encoding="ascii")
        with self.assertRaises(ValueError): self.verify()
    def test_missing_staged_entry_rejected(self):
        (self.root/"entry-last/index.html").unlink()
        with self.assertRaises(ValueError): self.verify()
    def test_corrupt_archive_rejected(self):
        with (self.root/"payload.zip").open("ab") as stream: stream.write(b"corrupt")
        reseal(self.root)
        with self.assertRaises(ValueError): self.verify()
    def test_resealed_wrong_entry_rejected(self):
        (self.root/"entry-last/index.html").write_bytes(b"stale entry")
        reseal(self.root)
        with self.assertRaises(ValueError): self.verify()
    def test_resealed_wrong_host_policy_rejected(self):
        (self.root/"host/.htaccess").write_bytes(b"stale host policy")
        reseal(self.root)
        with self.assertRaises(ValueError): self.verify()
    def test_payload_case_collision_rejected(self):
        row={"path":"assets/Main.js","bytes":1,"sha256":"a"*64}
        with self.assertRaises(ValueError): tool.inventory([row,{**row,"path":"assets/main.js"}])
    def test_path_traversal_and_windows_names_rejected(self):
        for name in ("../private","assets/../../secret","/index.html","C:/secret","a\\b","research/CON.json","assets/end."):
            with self.subTest(name=name),self.assertRaises(ValueError): tool.relative(name)
    def test_duplicate_json_key_rejected(self):
        (self.root/"duplicate.json").write_text('{"key":1,"key":2}',encoding="ascii")
        with self.assertRaises(ValueError): tool.read(self.root/"duplicate.json")
    def test_linked_bundle_file_rejected(self):
        target=self.root/"outside"
        target.write_bytes(b"fixture")
        linked=self.root/"linked"
        try: linked.symlink_to(target)
        except OSError: self.skipTest("OS does not permit unprivileged symlink creation")
        with self.assertRaises(ValueError): tool.regular(linked)
    def test_new_output_rejects_linked_parent_before_write(self):
        parent=Path(self.tmp.name)/"parent"
        parent.mkdir()
        link=Path(self.tmp.name)/"link"
        try: link.symlink_to(parent,target_is_directory=True)
        except OSError: self.skipTest("OS does not permit unprivileged symlink creation")
        with self.assertRaises(ValueError): tool.new_directory(link/"output",self.root)
        self.assertFalse((parent/"output").exists())
    def test_successful_run_metadata(self):
        value={"id":7,"repository":{"full_name":tool.REPO},"path":".github/workflows/release-packaging.yml",
               "head_branch":"main","event":"workflow_dispatch","status":"completed","conclusion":"success","head_sha":SOURCE}
        self.assertEqual(tool.validate_producer_run(value,7)["conclusion"],"success")
        for key,wrong in (("head_branch","feature"),("conclusion","failure"),("path",".github/workflows/untrusted.yml")):
            with self.subTest(key=key),self.assertRaises(ValueError):
                tool.validate_producer_run({**value,key:wrong},7)
    def test_mutable_or_injected_commit_rejected(self):
        for value in ("main","abc","1"*40+"; echo secret","A"*40):
            with self.subTest(value=value),self.assertRaises(ValueError): tool.commit(value)

if __name__=="__main__":
    unittest.main(verbosity=2)
