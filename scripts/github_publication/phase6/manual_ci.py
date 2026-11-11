"""Exact source-bound CI package checks. No model execution or hosting writes."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile

REPO = "zacxu/the-flamel-project"
POLICY = "cfec2cddb8cbbf215fbe2ee17593a20f8b470d80071648ddb6d79004a8bbd149"
FILES = frozenset({"payload.zip", "package-record.json", "upload-plan.json", "host/.htaccess", "entry-last/index.html"})

def require(value, message):
    if not value:
        raise ValueError(message)

def sha(value):
    return hashlib.sha256(value).hexdigest()

def pairs(items):
    out = {}
    for key,value in items:
        require(key not in out, "Duplicate JSON key")
        out[key] = value
    return out

def regular(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,
                    "Link/reparse path rejected")
    require(path.is_file(), "Expected regular file")
    return path

def read(path):
    return json.loads(regular(path).read_text(encoding="utf-8-sig"),object_pairs_hook=pairs)

def relative(name):
    require(isinstance(name,str) and re.fullmatch(r"[A-Za-z0-9_./-]+",name), "Unsafe relative path")
    require(all(part not in ("",".","..") for part in name.split("/")), "Unsafe path segment")
    for part in name.split("/"):
        require(not part.endswith(".") and part.split(".")[0].upper() not in
                {"CON","PRN","AUX","NUL",*("COM"+str(n) for n in range(1,10)),*("LPT"+str(n) for n in range(1,10))},
                "Unsafe Windows path")
    return name

def under(root,name):
    return Path(root).absolute().joinpath(*relative(name).split("/"))

def commit(value):
    require(isinstance(value,str) and re.fullmatch(r"[a-f0-9]{40}",value), "Use a full lowercase immutable commit SHA")
    return value

def git(root,*args):
    return subprocess.run(["git","-C",str(root),*args],check=True,capture_output=True,text=True).stdout.strip()

def write_new(path,value):
    path=Path(path).absolute()
    for parent in path.parents:
        if parent.exists():
            info=parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,
                    "Linked output parent")
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(value,stream,indent=2,sort_keys=True)
        stream.write("\n")

def new_directory(path, source):
    path=Path(path).absolute()
    for item in (path,*path.parents):
        if item.exists() or item.is_symlink():
            info=item.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,
                    "Linked output parent")
    require(not path.exists() and not path.is_relative_to(Path(source).absolute()),
            "Output directory must be new and outside source")
    path.mkdir(parents=True)
    return path

def row(root,name):
    data=regular(under(root,name)).read_bytes()
    return {"path":name,"bytes":len(data),"sha256":sha(data)}

def inventory(rows):
    require(isinstance(rows,list) and 0<len(rows)<=4096,"Invalid payload inventory")
    found={}
    folded=set()
    total=0
    for item in rows:
        name=relative(item["path"])
        require(name.casefold() not in folded,"Duplicate/colliding payload path")
        folded.add(name.casefold())
        require(type(item["bytes"]) is int and 0<=item["bytes"]<=10*1024*1024,"Invalid payload size")
        require(isinstance(item["sha256"],str) and re.fullmatch(r"[a-f0-9]{64}",item["sha256"]),"Invalid payload SHA")
        require(name=="index.html" or re.fullmatch(r"assets/[A-Za-z0-9_-]+\.(?:js|css)",name)
                or (name.startswith("research/") and Path(name).suffix in (".json",".csv",".png",".webp",".svg",".txt",".cif"))
                or re.fullmatch(r"ui/figures/[A-Za-z0-9_.-]+\.(?:png|webp|svg)",name)
                or re.fullmatch(r"release-manifests/ui-w6-[a-f0-9]{20}(?:\.files\.csv|\.json)",name),
                "Non-public payload path")
        cap=1_000_000 if Path(name).suffix in (".html",".js") else 10_000_000
        require(item["bytes"]<cap,"Provider per-file size bound exceeded")
        require(not re.search(r"\.(?:py|exe|dll|pkl|pickle|pt|pth|zip|map)$",name,re.I),"Private executable/model payload")
        found[name]={"path":name,"bytes":item["bytes"],"sha256":item["sha256"]}
        total+=item["bytes"]
    require(total<=100*1024*1024,"Payload exceeds bound")
    return found

def verify_zip(archive,record):
    archive=regular(archive)
    require(archive.stat().st_size<=50*1024*1024,"Archive exceeds safety bound")
    require(archive.stat().st_size==record["archive"]["bytes"] and
            sha(archive.read_bytes())==record["archive"]["sha256"],"Archive digest/size mismatch")
    rows=inventory(record["files"])
    require(record["fileCount"]==len(rows) and record["totalBytes"]==sum(r["bytes"] for r in rows.values()),"Package totals mismatch")
    require(record["payload"]=="dist/" and re.fullmatch(r"ui-w6-[a-f0-9]{20}",record["uiBuildId"]),"Invalid package/UI identity")
    with zipfile.ZipFile(archive) as stream:
        entries=stream.infolist()
        require(len(entries)==len(rows),"ZIP member count mismatch")
        folded=set()
        for entry in entries:
            name=relative(entry.filename)
            require(name in rows and name.casefold() not in folded,"Unexpected/colliding ZIP member")
            folded.add(name.casefold())
            require(stat.S_IFMT(entry.external_attr>>16) in (0,stat.S_IFREG) and
                    not entry.is_dir() and not entry.flag_bits&1,"ZIP links/directories/encryption rejected")
            require(entry.file_size==rows[name]["bytes"],"ZIP member size mismatch")
            require(sha(stream.read(entry))==rows[name]["sha256"],"ZIP member hash mismatch")
        name="release-manifests/"+record["uiBuildId"]+".json"
        require(record["manifestPath"]==name and name in rows,"Manifest identity mismatch")
        raw=stream.read(name)
        require(sha(raw)==record["manifestSha256"],"Manifest hash mismatch")
        manifest=json.loads(raw,object_pairs_hook=pairs)
        for key in ("uiBuildId","sourceFingerprint","dataReleaseId","exportManifestSha256"):
            require(manifest[key]==record[key],"Release/package identity mismatch")
        require(inventory(manifest["files"])=={n:r for n,r in rows.items() if n!=name},"Manifest member inventory mismatch")
        entry=stream.read("index.html")
    return rows,entry

def file_set(root):
    result=[]
    for directory,dirs,names in os.walk(root,followlinks=False):
        for name in [*dirs,*names]:
            info=(Path(directory)/name).lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,"Artifact link rejected")
        for name in names:
            result.append((Path(directory)/name).relative_to(root).as_posix())
    return sorted(result)

def verify_package(directory,source_commit,producer_run_id=None):
    directory=Path(directory).absolute()
    require(set(file_set(directory))==FILES|{"provenance.json","SHA256SUMS"},"Artifact has extra/missing files")
    provenance=read(directory/"provenance.json")
    require(provenance["kind"]=="flamel-ci-package-v1" and provenance["repository"]==REPO and
            provenance["source_commit"]==commit(source_commit) and
            provenance["producer_workflow"]==".github/workflows/release-packaging.yml" and
            provenance["status"]=="VERIFIED_PACKAGE_NOT_DEPLOYED" and provenance["hosting_deployed"] is False,
            "Artifact source/provenance mismatch")
    if producer_run_id is not None:
        require(str(provenance["producer_run_id"])==str(producer_run_id),"Producer run mismatch")
    require(provenance["files"]==[row(directory,n) for n in sorted(FILES)],"Artifact file integrity mismatch")
    sums="".join(r["sha256"]+"  "+r["path"]+"\n" for r in
                 [row(directory,n) for n in sorted([*FILES,"provenance.json"])])
    require(regular(directory/"SHA256SUMS").read_text(encoding="ascii")==sums,"Checksum sidecar mismatch")
    record=read(directory/"package-record.json")
    rows,entry=verify_zip(directory/"payload.zip",record)
    plan=read(directory/"upload-plan.json")
    require(plan["packageSha256"]==sha((directory/"package-record.json").read_bytes()) and
            plan["uiBuildId"]==record["uiBuildId"]==provenance["ui_build_id"] and
            plan["entryTarget"]=="index.html" and plan["stableUrl"]=="https://theflamelproject.42web.io/refresh" and
            plan["policy"]["sha256"]==POLICY and
            regular(directory/"entry-last/index.html").read_bytes()==entry and
            sha(regular(directory/"host/.htaccess").read_bytes())==POLICY,"Staged entry/policy mismatch")
    require(inventory(plan["filesBeforeEntry"])=={n:r for n,r in rows.items() if n!="index.html"},
            "Upload inventory differs from payload")
    return {"status":"VERIFIED_PACKAGE_NOT_DEPLOYED","source_commit":source_commit,"ui_build_id":record["uiBuildId"],
            "payload_files":len(rows),"payload_sha256":sha((directory/"payload.zip").read_bytes()),
            "hosting_deployed":False,"github_release_published":False}

def record_package(root,destination,source_commit,stage_root):
    root=Path(root).absolute()
    require(git(root,"rev-parse","HEAD")==commit(source_commit),"Candidate source commit mismatch")
    destination=Path(destination).absolute()
    # Reject all existing reparse ancestors before creating any output.
    for parent in (destination,*destination.parents):
        if parent.exists() or parent.is_symlink():
            info=parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,"Linked output parent")
    require(not destination.exists() and not destination.is_relative_to(root),"Artifact output must be new and outside source")
    website=root/"website"
    record=read(website/"reports/W6_RELEASE_PACKAGE.json")
    verify_zip(under(website,record["archive"]["path"]),record)
    stage=Path(stage_root).absolute()/("deployment/latest-link/staged/"+record["uiBuildId"])
    inputs={"payload.zip":under(website,record["archive"]["path"]),
            "package-record.json":website/"reports/W6_RELEASE_PACKAGE.json",
            "upload-plan.json":stage/"upload-plan.json","host/.htaccess":stage/"host/.htaccess",
            "entry-last/index.html":stage/"entry-last/index.html"}
    destination.mkdir(parents=True)
    for name,original in inputs.items():
        target=under(destination,name)
        target.parent.mkdir(parents=True,exist_ok=True)
        with regular(original).open("rb") as incoming,target.open("xb") as outgoing:
            shutil.copyfileobj(incoming,outgoing)
    provenance={"schema_version":1,"kind":"flamel-ci-package-v1","repository":REPO,
                "source_commit":source_commit,"source_tree":git(root,"rev-parse","HEAD^{tree}"),
                "producer_workflow":".github/workflows/release-packaging.yml",
                "producer_run_id":os.environ.get("GITHUB_RUN_ID","local"),
                "producer_workflow_commit":os.environ.get("GITHUB_SHA","local"),
                "ui_build_id":record["uiBuildId"],"status":"VERIFIED_PACKAGE_NOT_DEPLOYED",
                "new_scientific_experiments":0,"github_release_published":False,"hosting_deployed":False,
                "files":[row(destination,n) for n in sorted(FILES)],
                "limits":"Phase 6 static/package gates. Predecessor-cache reconstruction, fresh browser acceptance and GitHub Release publication remain Phase 7."}
    write_new(destination/"provenance.json",provenance)
    sums="".join(r["sha256"]+"  "+r["path"]+"\n" for r in
                 [row(destination,n) for n in sorted([*FILES,"provenance.json"])])
    with (destination/"SHA256SUMS").open("x",encoding="ascii",newline="\n") as stream:
        stream.write(sums)
    return verify_package(destination,source_commit)

def resolve_source(root,source_commit):
    source_commit=commit(source_commit)
    git(root,"cat-file","-e",source_commit+"^{commit}")
    # The one-off acceptance caller can package its own exact trusted branch head.
    acceptance=(os.environ.get("GITHUB_REF")=="refs/heads/ci/phase6" and
                os.environ.get("GITHUB_SHA")==source_commit and os.environ.get("GITHUB_EVENT_NAME")=="push")
    if not acceptance:
        subprocess.run(["git","-C",str(root),"merge-base","--is-ancestor",source_commit,"origin/main"],check=True)
    return {"source_commit":source_commit,"accepted_scope":"phase6-acceptance-head" if acceptance else "main-history"}

def validate_producer_run(record,run_id):
    require(type(run_id) is int and run_id>0,"Invalid producing run ID")
    require(record.get("id")==run_id and record.get("repository",{}).get("full_name")==REPO and
            record.get("path")==".github/workflows/release-packaging.yml" and
            record.get("head_branch")=="main" and record.get("event")=="workflow_dispatch" and
            record.get("status")=="completed" and record.get("conclusion")=="success",
            "Only successful manual release-packaging runs from main in this repository are accepted")
    return {"run_id":run_id,"workflow":record["path"],"head_commit":record["head_sha"],"conclusion":"success"}

def check_run(run_id):
    require(type(run_id) is int and run_id>0,"Invalid run ID")
    token=os.environ.get("GH_TOKEN")
    require(token,"Read-only Actions token is required")
    request=urllib.request.Request("https://api.github.com/repos/"+REPO+"/actions/runs/"+str(run_id),
          headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(request,timeout=45) as response:
        data=json.load(response,object_pairs_hook=pairs)
    return validate_producer_run(data,run_id)

def evidence(root,destination,download_public=False,upstream_upfs=False):
    root=Path(root).absolute()
    destination=new_directory(destination,root)
    spec=importlib.util.spec_from_file_location("_flamel_saved_evidence",root/"scripts/github_publication/audit_saved_evidence.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    saved=module.audit(root)
    write_new(destination/"saved-evidence.json",saved)
    tool=root/"scripts/github_publication/public_assets.py"
    if download_public:
        assets=destination/"public-assets"
        # Existing downloader rejects unpublished URLs before any network request.
        subprocess.run([sys.executable,"-I","-B",str(tool),"download","--manifest",str(root/"publication/phase4/public-assets.json"),
                        "--destination",str(assets)],check=True)
        subprocess.run([sys.executable,"-I","-B",str(tool),"verify","--manifest",str(root/"publication/phase4/public-assets.json"),
                        "--asset-dir",str(assets),"--notice-dir",str(assets),"--scope","all",
                        "--report",str(destination/"public-assets-verification.json")],check=True)
    if upstream_upfs:
        subprocess.run([sys.executable,"-I","-B",str(tool),"upfs","--manifest",str(root/"publication/phase4/upstream-upfs.json"),
                        "--cache-dir",str(destination/"upstream-cache"),"--destination",str(destination/"upstream-upfs"),
                        "--restore-recorded-paths","--report",str(destination/"upstream-upfs-verification.json")],check=True)
    result={"status":"PASS","saved_evidence":saved,"public_archives_retrieved":download_public,
            "exact_upstream_upfs_retrieved":upstream_upfs,"models_deserialized":0,"new_scientific_experiments":0,"hosting_deployed":False}
    write_new(destination/"audit-summary.json",result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest="command",required=True)
    p=subs.add_parser("resolve-source")
    p.add_argument("--root",required=True,type=Path); p.add_argument("--source-commit",required=True)
    p=subs.add_parser("evidence")
    p.add_argument("--root",required=True,type=Path); p.add_argument("--output",required=True,type=Path)
    p.add_argument("--download-public",action="store_true"); p.add_argument("--upstream-upfs",action="store_true")
    p=subs.add_parser("record-package")
    p.add_argument("--root",required=True,type=Path); p.add_argument("--output",required=True,type=Path); p.add_argument("--source-commit",required=True)
    p.add_argument("--stage-root",required=True,type=Path)
    p=subs.add_parser("verify-package")
    p.add_argument("--package-dir",required=True,type=Path); p.add_argument("--source-commit",required=True)
    p.add_argument("--producer-run-id"); p.add_argument("--report",type=Path)
    p=subs.add_parser("check-run")
    p.add_argument("--run-id",required=True,type=int); p.add_argument("--report",required=True,type=Path)
    args=parser.parse_args()
    try:
        if args.command=="resolve-source": result=resolve_source(args.root,args.source_commit)
        elif args.command=="evidence": result=evidence(args.root,args.output,args.download_public,args.upstream_upfs)
        elif args.command=="record-package": result=record_package(args.root,args.output,args.source_commit,args.stage_root)
        elif args.command=="check-run":
            result=check_run(args.run_id); write_new(args.report,result)
        else:
            result=verify_package(args.package_dir,args.source_commit,args.producer_run_id)
            if args.report: write_new(args.report,result)
        print(json.dumps(result,indent=2))
        return 0
    except (ValueError,OSError,KeyError,TypeError,subprocess.CalledProcessError,zipfile.BadZipFile) as error:
        print("Manual CI gate rejected: "+str(error),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
