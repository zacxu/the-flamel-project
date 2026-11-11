"""Release inventory, no-clobber and fresh-clone bootstrap safety fixtures."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location("release_transport",Path(__file__).with_name("release_transport.py"))
tool=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(tool)
ROOT=Path(__file__).resolve().parents[3]
TAG="v0.1.0";SOURCE="a"*40

def hashed(data):
    return hashlib.sha256(data).hexdigest()

def fixture():
    real,_=tool.policy(ROOT)
    required={name:{"name":name,"bytes":1,"sha256":hashed(b"x")} for name in real}
    private={"withheld.zip":{"name":"withheld.zip","bytes":3,"sha256":hashed(b"bad")}}
    names=tool.expected_names(TAG,required)
    payloads={name:b"x" if name in required else b"{}" for name in names
              if name not in {"flamel-release-"+TAG+".json","SHA256SUMS"}}
    rows=[{"name":name,"bytes":len(data),"sha256":hashed(data)} for name,data in sorted(payloads.items())]
    record={"repository":tool.REPOSITORY,"tag":TAG,"source_commit":SOURCE,"assets":rows}
    record_name="flamel-release-"+TAG+".json"
    payloads[record_name]=(json.dumps(record,sort_keys=True)+"\n").encode()
    sums={name:hashed(data) for name,data in payloads.items()}
    payloads["SHA256SUMS"]="".join(sums[name]+"  "+name+"\n" for name in sorted(sums)).encode()
    inventory={"repository":tool.REPOSITORY,"tag":TAG,"source_commit":SOURCE,
               "assets":[{"name":name,"bytes":len(data),"sha256":hashed(data)}
                         for name,data in sorted(payloads.items())]}
    return required,private,payloads,inventory

def remote_rows(payloads):
    return [{"id":index+1,"name":name,"size":len(data),"digest":"sha256:"+hashed(data),"state":"uploaded"}
            for index,(name,data) in enumerate(sorted(payloads.items()))]

class FakeGH:
    def __init__(self,payloads,draft=False):
        self.payloads=payloads;self.calls=[];self.draft=draft
    def repository(self,write=False):
        self.calls.append(("repository",write))
    def tag(self,tag,source):
        if tag!=TAG or source!=SOURCE:raise ValueError("Wrong fake tag target")
    def release(self,tag,missing=False):
        return {"id":7,"tag_name":tag,"draft":self.draft,"immutable":False,"assets":remote_rows(self.payloads)}
    def command(self,*args):
        self.calls.append(args)
        if args[:2]==("release","download"):
            name=args[args.index("--pattern")+1]
            directory=Path(args[args.index("--dir")+1]);directory.mkdir(parents=True,exist_ok=True)
            (directory/name).write_bytes(self.payloads[name])
            return b""
        raise AssertionError("An unexpected mutation command reached the fake transport")

class ReleaseTransportTests(unittest.TestCase):
    def setUp(self):
        self.required,self.private,self.payloads,self.inventory=fixture()
    def validate(self,value=None):
        return tool.validate_inventory(value or self.inventory,self.required,self.private)
    def test_historical_policy_pins_exact_twelve_and_three(self):
        required,private=tool.policy(ROOT)
        self.assertEqual(len(required),12);self.assertEqual(len(private),3)
    def test_complete_seventeen_asset_inventory(self):
        self.assertEqual(len(self.validate()["assets"]),17)
    def test_missing_notice_rejected(self):
        value=copy.deepcopy(self.inventory)
        value["assets"]=[r for r in value["assets"] if "third-party-notices" not in r["name"]]
        with self.assertRaises(ValueError):self.validate(value)
    def test_private_archive_bytes_cannot_be_renamed(self):
        value=copy.deepcopy(self.inventory)
        row=next(r for r in value["assets"] if r["name"]=="flamel-website-"+TAG+".zip")
        row["sha256"]=self.private["withheld.zip"]["sha256"]
        with self.assertRaises(ValueError):self.validate(value)
    def test_reviewed_research_digest_cannot_change(self):
        value=copy.deepcopy(self.inventory)
        next(row for row in value["assets"] if row["name"] in self.required)["sha256"]="0"*64
        with self.assertRaises(ValueError):self.validate(value)
    def test_duplicate_and_traversal_names_rejected(self):
        for bad in [self.inventory["assets"][1]["name"],"../secret.zip","asset#label.zip","asset*.zip"]:
            value=copy.deepcopy(self.inventory);value["assets"][0]["name"]=bad
            with self.subTest(name=bad),self.assertRaises(ValueError):self.validate(value)
    def test_oversized_extra_rejected(self):
        value=copy.deepcopy(self.inventory)
        row=next(r for r in value["assets"] if r["name"]=="flamel-website-"+TAG+".zip")
        row["bytes"]=tool.MAX_EXTRA+1
        with self.assertRaises(ValueError):self.validate(value)
    def test_wrong_repository_or_mutable_source_rejected(self):
        for key,value in [("repository","other/repository"),("source_commit","main"),("tag","../../main")]:
            candidate=copy.deepcopy(self.inventory);candidate[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(candidate)
    def test_checksum_duplicates_and_unbound_names_rejected(self):
        with self.assertRaises(ValueError):tool.checksum_rows((("a"*64+"  file.zip\n")*2).encode())
        with self.assertRaises(ValueError):tool.checksum_rows(("a"*64+"  ../file.zip\n").encode())
    def test_remote_missing_extra_or_digest_changes_rejected(self):
        expected=self.validate()["assets"];valid=remote_rows(self.payloads)
        for changed in [valid[:-1],valid+[dict(valid[0],id=999,name="private.zip")],
                        [dict(valid[0],digest="sha256:"+"0"*64),*valid[1:]]]:
            with self.assertRaises(ValueError):tool.remote_assets(changed,expected,complete=True)
    def test_matching_partial_draft_inventory_is_safe_to_resume(self):
        expected=self.validate()["assets"];partial=remote_rows(self.payloads)[:1]
        self.assertEqual(len(tool.remote_assets(partial,expected,complete=False)),1)
    def test_existing_published_release_never_uploads(self):
        gh=FakeGH(self.payloads)
        with self.assertRaises(ValueError):
            tool.upload_draft(gh,self.validate(),ROOT/"README.md","Test")
        self.assertFalse(any(call[:2]==("release","upload") for call in gh.calls))
    def test_remote_annotated_tag_resolves_only_expected_commit(self):
        gh=object.__new__(tool.GitHub)
        def api(path,missing=False):
            return ({"object":{"type":"tag","sha":"b"*40}} if "/ref/" in path
                    else {"object":{"type":"commit","sha":SOURCE}})
        gh.api=api
        self.assertEqual(gh.tag(TAG,SOURCE),SOURCE)
        with self.assertRaises(ValueError):gh.tag(TAG,"c"*40)
    def test_published_release_download_bootstrap_checks_all_seventeen(self):
        gh=FakeGH(self.payloads)
        with tempfile.TemporaryDirectory() as parent:
            destination=Path(parent)/"downloads"
            with mock.patch.object(tool,"policy",return_value=(self.required,self.private)),contextlib.redirect_stdout(io.StringIO()):
                result=tool.bootstrap(gh,TAG,ROOT,destination,SOURCE)
            self.assertEqual(result["status"],"DOWNLOADED_VERIFIED")
            self.assertEqual(len(result["assets"]),17)
            self.assertEqual({p.name for p in destination.iterdir()},set(self.payloads))
            for name,data in self.payloads.items():self.assertEqual((destination/name).read_bytes(),data)
    def test_bootstrap_rejects_missing_canonical_record_checksum(self):
        changed=dict(self.payloads)
        changed["SHA256SUMS"]=b"".join(line for line in changed["SHA256SUMS"].splitlines(keepends=True)
                                       if b"flamel-release-" not in line)
        gh=FakeGH(changed)
        with tempfile.TemporaryDirectory() as parent,mock.patch.object(tool,"policy",return_value=(self.required,self.private)):
            with self.assertRaises(ValueError):tool.bootstrap(gh,TAG,ROOT,Path(parent)/"downloads",SOURCE)
    def test_bootstrap_rejects_draft_and_source_mismatch(self):
        with tempfile.TemporaryDirectory() as parent,mock.patch.object(tool,"policy",return_value=(self.required,self.private)):
            for gh,source in [(FakeGH(self.payloads,draft=True),SOURCE),(FakeGH(self.payloads),"f"*40)]:
                with self.subTest(draft=gh.draft),self.assertRaises(ValueError):
                    tool.bootstrap(gh,TAG,ROOT,Path(parent)/"downloads",source)
    def test_published_release_uses_normal_tag_endpoint_only(self):
        gh=object.__new__(tool.GitHub);calls=[]
        row={"id":7,"tag_name":TAG,"draft":False,"assets":[],
             "url":"https://api.github.com/repos/"+tool.REPOSITORY+"/releases/7"}
        def api(path,missing=False):
            calls.append(path);self.assertTrue(missing);return row
        gh.api=api
        self.assertEqual(gh.release(TAG),row)
        self.assertEqual(calls,["repos/"+tool.REPOSITORY+"/releases/tags/"+TAG])
    def test_tag_404_falls_back_to_unique_same_repository_draft(self):
        gh=object.__new__(tool.GitHub);calls=[]
        row={"id":7,"tag_name":TAG,"draft":True,"assets":[],
             "url":"https://api.github.com/repos/"+tool.REPOSITORY+"/releases/7"}
        def api(path,missing=False):
            calls.append(path)
            return None if "/tags/" in path else [row]
        gh.api=api
        self.assertEqual(gh.release(TAG),row)
        self.assertEqual(calls[-1],"repos/"+tool.REPOSITORY+"/releases?per_page=100")
    def test_fallback_rejects_ambiguous_wrong_scope_or_published_rows(self):
        row={"id":7,"tag_name":TAG,"draft":True,"assets":[],
             "url":"https://api.github.com/repos/"+tool.REPOSITORY+"/releases/7"}
        for rows in [[row,dict(row,id=8)],
                     [dict(row,url="https://api.github.com/repos/other/repository/releases/7")],
                     [dict(row,draft=False)],
                     [dict(row)]*101]:
            gh=object.__new__(tool.GitHub)
            gh.api=lambda path,missing=False: None if "/tags/" in path else rows
            with self.subTest(rows=len(rows)),self.assertRaises(ValueError):gh.release(TAG)
    def test_absent_release_is_optional_only_when_explicit(self):
        gh=object.__new__(tool.GitHub)
        gh.api=lambda path,missing=False: None if "/tags/" in path else []
        self.assertIsNone(gh.release(TAG,missing=True))
        with self.assertRaises(ValueError):gh.release(TAG)
    def test_new_output_never_reuses_or_writes_into_source(self):
        with self.assertRaises(ValueError):tool.new_output(ROOT/"new-download",ROOT)
        with tempfile.TemporaryDirectory() as parent:
            existing=Path(parent)/"old";existing.mkdir()
            with self.assertRaises(ValueError):tool.new_output(existing,ROOT)

if __name__=="__main__":
    unittest.main(verbosity=2)
