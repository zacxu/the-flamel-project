"""Adversarial predecessor archive fixtures. Standard library, no models/network."""
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

spec=importlib.util.spec_from_file_location("_predecessor",Path(__file__).with_name("website_predecessor.py"))
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

class PredecessorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="flamel-predecessor-");self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/"source";self.root.mkdir()
        self.data={"index.html":b"old verified html","assets/old.js":b"old verified javascript"}
        self.rows={n:{"path":n,"bytes":len(b),"sha256":tool.hashlib.sha256(b).hexdigest()} for n,b in self.data.items()}
        self.patch=mock.patch.object(tool,"baseline",return_value=(self.root,self.rows));self.patch.start();self.addCleanup(self.patch.stop)
        self.archive=self.base/"predecessor.zip";self.write_zip(self.data)
    def write_zip(self,data,extra=None,mode=None):
        with zipfile.ZipFile(self.archive,"w") as z:
            for name,value in data.items():
                info=zipfile.ZipInfo(name);info.external_attr=(mode or (stat.S_IFREG|0o644))<<16;z.writestr(info,value)
            if extra:z.writestr(*extra)
    def test_valid_exact_archive_and_restore(self):
        rows,data=tool.payload(self.root,self.archive);self.assertEqual(data,self.data)
        result=tool.restore(self.root,self.archive);self.assertEqual(result["files"],2)
        self.assertEqual((self.root/"website/.cache/w6-previous-dist/index.html").read_bytes(),self.data["index.html"])
    def test_same_size_byte_tamper_rejected(self):
        changed=dict(self.data);changed["index.html"]=b"x"*len(changed["index.html"]);self.write_zip(changed)
        with self.assertRaises(ValueError):tool.payload(self.root,self.archive)
    def test_extra_file_rejected(self):
        self.write_zip(self.data,("extra.txt",b"extra"))
        with self.assertRaises(ValueError):tool.payload(self.root,self.archive)
    def test_traversal_rejected(self):
        changed=dict(self.data);changed["../escape"]=changed.pop("index.html");self.write_zip(changed)
        with self.assertRaises(ValueError):tool.payload(self.root,self.archive)
    def test_symlink_member_rejected(self):
        self.write_zip(self.data,mode=stat.S_IFLNK|0o777)
        with self.assertRaises(ValueError):tool.payload(self.root,self.archive)
    def test_duplicate_member_rejected(self):
        self.write_zip(self.data,("index.html",self.data["index.html"]))
        with self.assertRaises(ValueError):tool.payload(self.root,self.archive)
    def test_missing_member_rejected(self):
        self.write_zip({"index.html":self.data["index.html"]})
        with self.assertRaises(ValueError):tool.payload(self.root,self.archive)
    def test_existing_destination_is_never_overwritten(self):
        dest=self.root/"website/.cache/w6-previous-dist";dest.mkdir(parents=True);p=dest/"index.html";p.write_bytes(b"preserve me")
        with self.assertRaises(ValueError):tool.restore(self.root,self.archive)
        self.assertEqual(p.read_bytes(),b"preserve me")
    def test_existing_archive_is_never_overwritten(self):
        source=self.base/"old";source.mkdir()
        with self.assertRaises(ValueError):tool.pack(self.root,source,self.archive)
    def test_pack_cannot_write_inside_checkout(self):
        with self.assertRaises(ValueError):tool.pack(self.root,self.base/"old",self.root/"bad.zip")
    def test_actual_baseline_digest_is_not_replaceable(self):
        self.patch.stop()
        path=self.root/"website/reports/W6_BASELINE.json";path.parent.mkdir(parents=True);path.write_bytes(b"{}")
        with self.assertRaises(ValueError):tool.baseline(self.root)

if __name__=="__main__":unittest.main(verbosity=2)
