"""Focused guards for the Phase 4 environment installer and checkpoint verifier."""
from __future__ import annotations
import base64,hashlib,importlib.util,json,pathlib,subprocess,sys,tempfile,unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location("verify_python_environment",ROOT/"scripts/github_publication/verify_python_environment.py")
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)

class Safety(unittest.TestCase):
    def test_bad_checkpoint_record_rejected_before_load(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=pathlib.Path(temp);checkpoint=folder/"checkpoint";checkpoint.write_bytes(b"saved bytes")
            class Distribution:
                def read_text(self,name):return "checkpoint,sha256="+base64.urlsafe_b64encode(hashlib.sha256(b"different bytes").digest()).rstrip(b"=").decode()+",11\n"
                def locate_file(self,name):return folder/name
            with mock.patch.object(MODULE.md,"distribution",return_value=Distribution()):
                with self.assertRaises(RuntimeError):MODULE.verify_record_file(checkpoint,"fixture")

    def test_good_checkpoint_record_matches_sha256(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=pathlib.Path(temp);checkpoint=folder/"checkpoint";checkpoint.write_bytes(b"saved bytes");digest=hashlib.sha256(checkpoint.read_bytes()).digest()
            class Distribution:
                def read_text(self,name):return "checkpoint,sha256="+base64.urlsafe_b64encode(digest).rstrip(b"=").decode()+",11\n"
                def locate_file(self,name):return folder/name
            with mock.patch.object(MODULE.md,"distribution",return_value=Distribution()):
                self.assertEqual(MODULE.verify_record_file(checkpoint,"fixture"),digest.hex())

    def test_record_matching_arbitrary_checkpoint_still_rejected_by_fixed_pin(self):
        with tempfile.TemporaryDirectory() as temp:
            checkpoint=pathlib.Path(temp)/"checkpoint";checkpoint.write_bytes(b"arbitrary model data")
            with mock.patch.object(MODULE,"verify_record_file",return_value=hashlib.sha256(checkpoint.read_bytes()).hexdigest()):
                with self.assertRaises(RuntimeError):MODULE.verify_packaged_chgnet_checkpoint(checkpoint)

    def test_missing_checkpoint_record_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            checkpoint=pathlib.Path(temp)/"checkpoint";checkpoint.write_bytes(b"x")
            class Distribution:
                def read_text(self,name):return None
            with mock.patch.object(MODULE.md,"distribution",return_value=Distribution()):
                with self.assertRaises(RuntimeError):MODULE.verify_record_file(checkpoint,"fixture")

    def test_wrong_package_version_rejected_before_imports(self):
        with tempfile.TemporaryDirectory() as temp:
            spec=pathlib.Path(temp)/"requirements.txt";spec.write_text("numpy==0.0.0\n")
            with mock.patch.object(MODULE.md,"distributions",return_value=[]):
                with self.assertRaises(RuntimeError):MODULE.verify(spec,"analysis-maintenance-cpu")

    def test_powershell_existing_destination_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            destination=pathlib.Path(temp);marker=destination/"marker";marker.write_bytes(b"retain")
            result=subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT/"scripts/github_publication/install_python.ps1"),"-Destination",str(destination)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(marker.read_bytes(),b"retain")
            self.assertEqual(sorted(p.name for p in destination.iterdir()),["marker"])

    def test_powershell_source_destination_rejected(self):
        destination=ROOT/"_phase4_guard_must_not_create"
        self.assertFalse(destination.exists())
        result=subprocess.run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",str(ROOT/"scripts/github_publication/install_python.ps1"),"-Destination",str(destination)],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(destination.exists())

    def test_report_in_source_rejected_before_imports(self):
        target=ROOT/"_phase4_report_must_not_create.json"
        result=subprocess.run([sys.executable,"-I","-B",str(ROOT/"scripts/github_publication/verify_python_environment.py"),"--spec",str(ROOT/"requirements/phase4/analysis-maintenance-cpu.txt"),"--environment","analysis-maintenance-cpu","--report",str(target)],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(target.exists())

    def test_existing_report_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            report=pathlib.Path(temp)/"report.json";report.write_bytes(b"keep original")
            result=subprocess.run([sys.executable,"-I","-B",str(ROOT/"scripts/github_publication/verify_python_environment.py"),"--spec",str(ROOT/"requirements/phase4/analysis-maintenance-cpu.txt"),"--environment","analysis-maintenance-cpu","--report",str(report)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(report.read_bytes(),b"keep original")

if __name__=="__main__":unittest.main(verbosity=2)
