"""Remote research-release metadata boundary fixtures; no network/model execution."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("_phase7_research_assets", Path(__file__).with_name("research_assets.py"))
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)

class MetadataTests(unittest.TestCase):
    def setUp(self):
        selector, _ = tool.public.load_public(tool.ROOT / "publication/phase4/public-assets.json")
        self.selector = copy.deepcopy(selector)
        self.selector.update(publication_status="published", release_tag="v0.1.0")
        for row in self.selector["archives"]:
            row["download_url"] = "https://github.com/" + tool.REPOSITORY + "/releases/download/v0.1.0/" + row["name"]
        self.metadata = {"id": 1, "tag_name": "v0.1.0", "draft": False, "prerelease": False,
                         "target_commitish": "a"*40, "assets": [
                             {"id": i+1, "name": row["name"], "state": "uploaded", "size": row["bytes"],
                              "digest": "sha256:"+row["sha256"], "browser_download_url": row["download_url"]}
                             for i,row in enumerate(self.selector["archives"])]}
    def verify(self):
        return tool.validate_release(self.metadata, self.selector, "v0.1.0")
    def test_complete_exact_subset(self):
        result=self.verify()
        self.assertEqual(len(result["archives"]),12)
        self.assertEqual(result["private_archives_included"],0)
        self.assertFalse(result["downloaded_bytes_verified"])
    def test_separately_verified_production_and_inventory_assets_allowed(self):
        self.metadata["assets"].extend([{"name":"RELEASE.json"},{"name":"SHA256SUMS"},{"name":"flamel-website-v0.1.0.zip"}])
        self.assertEqual(len(self.verify()["archives"]),12)
    def test_draft_is_not_published(self):
        self.metadata["draft"]=True
        with self.assertRaises(ValueError): self.verify()
    def test_wrong_tag_rejected(self):
        self.metadata["tag_name"]="different"
        with self.assertRaises(ValueError): self.verify()
    def test_private_archive_anywhere_rejected(self):
        self.metadata["assets"].append({"name":"flamel-qe-scratch-001.zip"})
        with self.assertRaises(ValueError): self.verify()
    def test_raw_upf_rejected(self):
        self.metadata["assets"].append({"name":"O.UPF"})
        with self.assertRaises(ValueError): self.verify()
    def test_missing_notice_rejected(self):
        self.metadata["assets"].pop()
        with self.assertRaises(ValueError): self.verify()
    def test_case_colliding_asset_rejected(self):
        value=copy.deepcopy(self.metadata["assets"][0]);value["name"]=value["name"].upper()
        self.metadata["assets"].append(value)
        with self.assertRaises(ValueError): self.verify()
    def test_size_tampering_rejected(self):
        self.metadata["assets"][0]["size"]+=1
        with self.assertRaises(ValueError): self.verify()
    def test_server_hash_tampering_rejected(self):
        self.metadata["assets"][0]["digest"]="sha256:"+"0"*64
        with self.assertRaises(ValueError): self.verify()
    def test_incomplete_upload_rejected(self):
        self.metadata["assets"][0]["state"]="new"
        with self.assertRaises(ValueError): self.verify()
    def test_wrong_repository_url_rejected(self):
        self.metadata["assets"][0]["browser_download_url"]="https://github.com/elsewhere/file"
        with self.assertRaises(ValueError): self.verify()
    def test_missing_server_digest_still_requires_download_hash(self):
        self.metadata["assets"][0]["digest"]=None
        self.assertFalse(self.verify()["archives"][0]["github_digest_checked"])
    def test_unpublished_selector_rejected(self):
        self.selector["publication_status"]="unpublished"
        with self.assertRaises(ValueError): self.verify()
    def test_token_or_path_tag_rejected(self):
        for tag in ["../v1","v1?token=secret","v1/other",""," v1","v1#extra"]:
            with self.subTest(tag=tag), self.assertRaises(ValueError): tool.tag_name(tag)

if __name__ == "__main__":
    unittest.main()
