#!/usr/bin/env python3
"""Small independent safety fixtures for the Phase 2 artifact verifier/hydrator."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import warnings
import zipfile
from unittest import mock

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--tool",type=Path,default=Path(__file__).with_name("artifact_io.py"),
                    help="Artifact verifier/hydrator to test; defaults to the sibling artifact_io.py")
parser.add_argument("--output-root",type=Path,required=True,
                    help="Fresh directory for retained fixtures and validation.json; must not exist")
args=parser.parse_args()
TOOL=Path(os.path.abspath(args.tool))
ROOT=Path(os.path.abspath(args.output_root))
if not TOOL.is_file():
    parser.error("--tool must identify an existing Python file")
if ROOT == Path(ROOT.anchor) or os.path.lexists(ROOT):
    parser.error("--output-root must be a fresh, non-root path that does not exist")
ROOT.mkdir(parents=True,exist_ok=False)
TEST_ROOT=ROOT/"fixtures"
RESULT=ROOT/"validation.json"
spec=importlib.util.spec_from_file_location("artifact_io",TOOL)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
TEST_ROOT.mkdir(parents=True,exist_ok=False)
results=[]
def digest(data): return hashlib.sha256(data).hexdigest()
def file_sha(path): return digest(path.read_bytes())
def write_json(path,data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def manifest_for(archives):
    return {"schema_version":1,"publication_status":module.PUBLICATION_STATUS,
    "repository":"zacxu/the-flamel-project","asset_limit_bytes":module.ASSET_LIMIT_BYTES,"archives":archives}
def new_case(name):
    folder=TEST_ROOT/name; folder.mkdir(); assets=folder/"assets"; assets.mkdir()
    return folder,assets
def archive_record(assets,name,entries,scope="project",zip_entries=None):
    path=assets/name
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",UserWarning)
        with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_STORED) as archive:
            for item in zip_entries if zip_entries is not None else entries.items():
                key,value=item
                archive.writestr(key,value)
    members=[{"archive_path":key,"restore_path":key,"bytes":len(value),"sha256":digest(value)}
             for key,value in entries.items()]
    return {"name":name,"group":"fixture","bytes":path.stat().st_size,"sha256":file_sha(path),
            "availability":"local-only","download_url":None,
            "planned_download_url":"https://127.0.0.1:1/never-request-this.zip",
            "restore_scope":scope,"members":members}
def save(folder,archives):
    path=folder/"artifacts.json"; write_json(path,manifest_for(archives)); return path
def check(name,action):
    action(); results.append({"test":name,"status":"PASSED"})
def rejects(action):
    try: action()
    except (module.ArtifactError,zipfile.BadZipFile,FileExistsError,OSError,ValueError): return
    raise AssertionError("Unsafe fixture was unexpectedly accepted")
def snapshot(folder):
    return {p.relative_to(folder).as_posix():p.read_bytes() for p in folder.rglob("*") if p.is_file()}

folder,assets=new_case("happy")
entries={"data/reference.txt":b"exact\r\nbytes\r\n","models/checkpoint.bin":bytes(range(256)),
         "empty.zero":b"","unicode/Delta-\u0394.txt":"\u03b1\u03b2\u03b3\n".encode()}
project=archive_record(assets,"project.zip",entries)
production=archive_record(assets,"production.zip",{"htdocs/index.html":b"<h1>saved</h1>\n"},"production")
manifest=save(folder,[project,production])
def happy_verify():
    with mock.patch.object(socket,"socket",side_effect=AssertionError("Network fetch attempted")) as mocked:
        value=module.verify(manifest,assets)
        assert value["status"]=="VERIFIED" and value["archives"]==2 and value["members"]==5
        assert value["network_fetches"]==0 and not mocked.called
check("valid mixed-scope archives and planned URLs are verified without network access",happy_verify)
def happy_restore():
    dest=folder/"hydrated"
    value=module.hydrate(manifest,assets,dest)
    assert value["status"]=="HYDRATED_VERIFIED" and value["created_files"]==4
    assert snapshot(dest)==entries and not (dest/"htdocs").exists()
check("project hydration preserves CRLF, Unicode, binary and zero-length content",happy_restore)
def production_restore():
    dest=folder/"production-hydrated"
    value=module.hydrate(manifest,assets,dest,scope="production")
    assert value["members"]==1 and snapshot(dest)=={"htdocs/index.html":b"<h1>saved</h1>\n"}
check("production scope hydrates only production members",production_restore)
def scope_does_not_read_other_assets():
    only=folder/"project-only-assets"; only.mkdir()
    (only/"project.zip").write_bytes((assets/"project.zip").read_bytes())
    assert module.verify(manifest,only,scope="project")["members"]==4
check("project verification does not require unrelated production archive bytes",scope_does_not_read_other_assets)

def cli_report():
    report=folder/"cli-verified.json"
    run=subprocess.run([sys.executable,"-I","-B",str(TOOL),"verify","--manifest",str(manifest),
                       "--asset-dir",str(assets),"--report",str(report)],capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
    assert json.loads(report.read_text())["status"]=="VERIFIED"
    before=report.read_bytes()
    run=subprocess.run([sys.executable,"-I","-B",str(TOOL),"verify","--manifest",str(manifest),
                       "--asset-dir",str(assets),"--report",str(report)],capture_output=True,text=True)
    assert run.returncode!=0 and report.read_bytes()==before
check("CLI success receipt is created once and an existing receipt is never overwritten",cli_report)

def existing_default():
    dest=folder/"existing"; dest.mkdir(); (dest/"marker.txt").write_bytes(b"keep")
    before=snapshot(dest)
    rejects(lambda:module.hydrate(manifest,assets,dest))
    assert snapshot(dest)==before
check("default hydration refuses an existing destination without writes",existing_default)
def merge_success():
    dest=folder/"merge"; (dest/"data").mkdir(parents=True)
    (dest/"data/reference.txt").write_bytes(entries["data/reference.txt"])
    (dest/"unrelated.txt").write_bytes(b"unrelated")
    value=module.hydrate(manifest,assets,dest,merge_existing=True)
    assert value["reused_matching_files"]==1 and value["created_files"]==3
    assert snapshot(dest)=={**entries,"unrelated.txt":b"unrelated"}
check("explicit merge reuses identical files and preserves unrelated files",merge_success)
def merge_conflict():
    dest=folder/"conflict"; (dest/"unicode").mkdir(parents=True)
    (dest/"unicode/Delta-\u0394.txt").write_bytes(b"different")
    (dest/"untouched.txt").write_bytes(b"keep")
    before=snapshot(dest)
    rejects(lambda:module.hydrate(manifest,assets,dest,merge_existing=True))
    assert snapshot(dest)==before and not (dest/"data").exists()
check("all merge conflicts are preflighted before any new member is written",merge_conflict)

def asset_corruption():
    f,a=new_case("archive-corruption"); record=archive_record(a,"bad.zip",{"data.txt":b"abc"})
    m=save(f,[record]); content=bytearray((a/"bad.zip").read_bytes()); content[0]^=1
    (a/"bad.zip").write_bytes(content)
    report=f/"should-not-exist.json"; dest=f/"target"
    run=subprocess.run([sys.executable,"-I","-B",str(TOOL),"hydrate","--manifest",str(m),
                       "--asset-dir",str(a),"--destination",str(dest),"--report",str(report)],
                       capture_output=True,text=True)
    assert run.returncode!=0 and not dest.exists() and not report.exists()
check("corrupt archive digest is rejected before destination creation or success receipt",asset_corruption)
def member_corruption():
    f,a=new_case("member-hash"); record=archive_record(a,"bad.zip",{"data.txt":b"abc"})
    record["members"][0]["sha256"]=digest(b"xyz"); m=save(f,[record])
    rejects(lambda:module.hydrate(m,a,f/"target"))
    assert not (f/"target").exists()
check("member hash mismatch is rejected even when archive checksum matches",member_corruption)

def manifest_traversal():
    for index,unsafe in enumerate(("../escape.txt","/absolute.txt","C:/drive.txt",
                                   r"folder\backslash.txt","folder/../up.txt","a//b.txt",
                                   "NUL.txt","file:stream.txt","trail./file.txt","a/.git/config")):
        f,a=new_case("unsafe-manifest-"+str(index)); record=archive_record(a,"bad.zip",{"safe.txt":b"abc"})
        record["members"][0]["archive_path"]=record["members"][0]["restore_path"]=unsafe
        m=save(f,[record]); rejects(lambda:module.hydrate(m,a,f/"target"))
        assert not (f/"target").exists()
check("manifest traversal, absolute/drive/backslash/ADS/reserved/noncanonical/Git-metadata paths are rejected",manifest_traversal)
def zip_traversal():
    f,a=new_case("zip-traversal")
    record=archive_record(a,"bad.zip",{"safe.txt":b"abc"},zip_entries=[("../escape.txt",b"abc")])
    m=save(f,[record]); rejects(lambda:module.hydrate(m,a,f/"target"))
    assert not (f/"escape.txt").exists() and not (f/"target").exists()
check("unsafe ZIP path is rejected independently of a safe declared manifest",zip_traversal)
def zip_symlink():
    f,a=new_case("zip-symlink")
    link=zipfile.ZipInfo("safe.txt"); link.create_system=3; link.external_attr=(stat.S_IFLNK|0o777)<<16
    record=archive_record(a,"bad.zip",{"safe.txt":b"outside.txt"},zip_entries=[(link,b"outside.txt")])
    m=save(f,[record]); rejects(lambda:module.hydrate(m,a,f/"target"))
    assert not (f/"target").exists()
check("ZIP symbolic links are rejected",zip_symlink)
def zip_duplicate():
    f,a=new_case("zip-duplicate")
    record=archive_record(a,"bad.zip",{"safe.txt":b"abc"},
                          zip_entries=[("safe.txt",b"abc"),("safe.txt",b"abc")])
    m=save(f,[record]); rejects(lambda:module.verify(m,a))
check("duplicate physical ZIP members are rejected",zip_duplicate)
def zip_case_collision():
    f,a=new_case("zip-case")
    record=archive_record(a,"bad.zip",{"A.txt":b"abc"},
                          zip_entries=[("A.txt",b"abc"),("a.txt",b"abc")])
    m=save(f,[record]); rejects(lambda:module.verify(m,a))
check("case-colliding physical ZIP members are rejected",zip_case_collision)
def across_archive_duplicate():
    f,a=new_case("cross-duplicate")
    records=[archive_record(a,"one.zip",{"same.txt":b"abc"}),
             archive_record(a,"two.zip",{"same.txt":b"abc"})]
    m=save(f,records); rejects(lambda:module.verify(m,a))
check("duplicate restoration paths across same-scope archives are rejected",across_archive_duplicate)
def cross_scope_allowed():
    f,a=new_case("cross-scope")
    records=[archive_record(a,"one.zip",{"same.txt":b"abc"}),
             archive_record(a,"two.zip",{"same.txt":b"xyz"},"production")]
    m=save(f,records); assert module.verify(m,a)["members"]==2
check("identical relative paths are allowed only across separate restore scopes",cross_scope_allowed)
def prefix_collision():
    f,a=new_case("prefix-collision")
    record=archive_record(a,"bad.zip",{"root":b"abc","root/child.txt":b"xyz"})
    m=save(f,[record]); rejects(lambda:module.verify(m,a))
check("file-versus-directory prefix conflicts are rejected",prefix_collision)
def parent_case_collision():
    f,a=new_case("parent-case")
    record=archive_record(a,"bad.zip",{"Directory/a.txt":b"abc","directory/b.txt":b"xyz"})
    m=save(f,[record]); rejects(lambda:module.verify(m,a))
check("case-colliding directory prefixes are rejected",parent_case_collision)
def unexpected_member():
    f,a=new_case("unexpected-member")
    record=archive_record(a,"bad.zip",{"safe.txt":b"abc"},
                          zip_entries=[("safe.txt",b"abc"),("extra.txt",b"extra")])
    m=save(f,[record]); rejects(lambda:module.verify(m,a))
check("unexpected archive members are rejected",unexpected_member)
def too_large():
    f,a=new_case("oversize"); record=archive_record(a,"bad.zip",{"safe.txt":b"abc"})
    record["bytes"]=module.ASSET_LIMIT_BYTES+1; m=save(f,[record]); rejects(lambda:module.verify(m,a))
check("declared archive over 1 GiB is rejected without allocating a large fixture",too_large)

def make_directory_link(link,target):
    try:
        os.symlink(target,link,target_is_directory=True)
    except OSError:
        assert os.name=="nt"
        quote=lambda s:"'"+str(s).replace("'","''")+"'"
        command="New-Item -ItemType Junction -Path "+quote(link)+" -Target "+quote(target)+" | Out-Null"
        run=subprocess.run([str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"),
                            "-NoProfile","-Command",command],capture_output=True,text=True)
        assert run.returncode==0,run.stdout+run.stderr
    assert module._is_reparse(os.lstat(link))
def reparse_destination():
    f,a=new_case("reparse-parent")
    record=archive_record(a,"one.zip",{"linked/data.txt":b"abc"})
    m=save(f,[record]); target=f/"target"; target.mkdir(); outside=f/"outside"; outside.mkdir()
    (outside/"sentinel.txt").write_bytes(b"keep"); make_directory_link(target/"linked",outside)
    before=snapshot(outside)
    rejects(lambda:module.hydrate(m,a,target,merge_existing=True))
    assert snapshot(outside)==before and not (outside/"data.txt").exists()
check("existing junction/symlink parent is rejected before writes outside the target",reparse_destination)
def existing_wrong_case():
    f,a=new_case("existing-case")
    record=archive_record(a,"one.zip",{"Directory/data.txt":b"abc"})
    m=save(f,[record]); target=f/"target"; (target/"directory").mkdir(parents=True)
    rejects(lambda:module.hydrate(m,a,target,merge_existing=True))
    assert not list((target/"directory").iterdir())
check("existing directory case conflicts are rejected without writes",existing_wrong_case)
def directory_entry():
    f,a=new_case("zip-directory")
    directory=zipfile.ZipInfo("unused/")
    record=archive_record(a,"one.zip",{"safe.txt":b"abc"},
                          zip_entries=[("safe.txt",b"abc"),(directory,b"")])
    m=save(f,[record]); rejects(lambda:module.verify(m,a))
check("explicit ZIP directory entries are rejected by the regular-files-only schema",directory_entry)

receipt={"status":"PASSED","tool_version":module.VERSION,"tool_sha256":file_sha(TOOL),
         "tests_passed":len(results),"checks":results,"fixture_root":str(TEST_ROOT),
         "tool_path":str(TOOL),"output_root":str(ROOT),"report_path":str(RESULT),
         "source_project_modified":False,"phase1_backup_modified":False,"network_requests":0}
with open(RESULT,"x",encoding="utf-8") as stream: json.dump(receipt,stream,indent=2); stream.write("\n")
print(json.dumps(receipt),flush=True)