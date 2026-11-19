"""Stage the published Flamel website and bind it to the original release source."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
PUBLICATION = ROOT / "scripts/github_publication"
DEPLOYMENT_TARGET = "publication/phase8/deployment-target.json"

# The deployed v0.1.0 UI predates release packaging. Both original ZIPs are
# members of the separately published, hash-pinned website-builds release asset.
LIVE_SOURCE = "84115354ef9d1acad65401869ade392e9039da16"
LIVE_UI = "ui-w6-351e6182d7af3a9d062d"
LIVE_RECORD = "reports/CRYSTAL_LAB_RELEASE_PACKAGE.json"
LIVE_RECORD_SHA = "f7d9fdf1e162a4d906d09fadf3ea7507edc658df10d6fa8354ec53fd66575da0"
LIVE_PAYLOAD_SHA = "ccff9618e0c74d9c98ac3c378b7e361876e18befdd32640b7e64bf6cdec19ca5"
HISTORY_ASSET = "flamel-website-builds-001.zip"
HISTORY_SHA = "7eb744a319f6400406477408c5f1158103f609116429dc591efb10468dff70c9"
PRIOR_UI = "ui-w6-359b66f2fb63f90e993c"
PRIOR_PATH = f"website/deployment/workflow-visuals/releases/{PRIOR_UI}/{PRIOR_UI}.zip"
PRIOR_SHA = "8e06f5367cf0c97acff35f00b412e41b4c59d025f23aa22cecc77f2453e62e7d"



def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


package = module("manual_ci", PUBLICATION / "phase6/manual_ci.py")
transport = module("release_transport", PUBLICATION / "phase7/release_transport.py")


def release_at(controller):
    def committed_json(name):
        return json.loads(package.git(ROOT, "show", f"{controller}:{name}"), object_pairs_hook=package.pairs)
    name = package.relative(committed_json(DEPLOYMENT_TARGET)["release_state"])
    if not name.startswith("publication/") or not name.endswith("/release-state.json"):
        raise ValueError("Deployment target must reference a published release-state file")
    return committed_json(name)


def selected_release(rollback_run_id):
    if not rollback_run_id:
        # Local preparation supports testing a reviewed target before it is committed.
        name = package.relative(package.read(ROOT / DEPLOYMENT_TARGET)["release_state"])
        if not name.startswith("publication/") or not name.endswith("/release-state.json"):
            raise ValueError("Deployment target must reference a published release-state file")
        return package.read(ROOT / name)
    if not re.fullmatch(r"[1-9][0-9]{0,19}", rollback_run_id):
        raise ValueError("Invalid rollback run ID")
    run = github().api(f"repos/{package.REPO}/actions/runs/{rollback_run_id}")
    if not (run["repository"]["full_name"] == package.REPO and run["event"] == "workflow_dispatch"
            and run["head_branch"] == "main" and run["path"] == ".github/workflows/production-deployment.yml"
            and run["status"] == "completed"):
        raise ValueError("Snapshot must come from a completed production dispatch on main")
    controller = package.commit(run["head_sha"])
    package.git(ROOT, "merge-base", "--is-ancestor", controller, "HEAD")
    return release_at(controller)


def github():
    executable = shutil.which("gh")
    if not executable:
        raise ValueError("GitHub CLI is required for authenticated release retrieval")
    return transport.GitHub(Path(executable).resolve(strict=True))


def download_release(state, destination, name):
    gh = github()
    gh.repository()
    gh.tag(state["tag"], state["source_commit"])
    release = gh.release(state["tag"])
    if release["draft"] or release["prerelease"] or release["id"] != state["release_id"]:
        raise ValueError("Unexpected GitHub release")
    expected = {asset["name"]: asset for asset in state["assets"]}
    actual = transport.remote_assets(release["assets"], expected, complete=True)
    if actual[name]["id"] != expected[name]["id"]:
        raise ValueError("Published website asset identity changed")
    gh.command("release", "download", state["tag"], "--repo", package.REPO,
               "--pattern", name, "--output", str(destination))


def unpack(archive, destination, members):
    destination.mkdir()
    with zipfile.ZipFile(archive) as source:
        if sorted(source.namelist()) != sorted(members):
            raise ValueError("Unexpected or duplicate ZIP members")
        for member in source.infolist():
            if member.file_size > 100 * 1024 * 1024:
                raise ValueError("ZIP member exceeds package bounds")
            path = package.under(destination, member.filename)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as target, source.open(member) as data:
                shutil.copyfileobj(data, target)


def historical_member(archive, member_name, destination, size, digest):
    with zipfile.ZipFile(archive) as source:
        members = [info for info in source.infolist() if info.filename == member_name]
        if len(members) != 1 or members[0].file_size != size:
            raise ValueError("Historical release member size or identity mismatch")
        with source.open(members[0]) as data, destination.open("xb") as target:
            shutil.copyfileobj(data, target)
    if transport.digest(destination) != digest:
        raise ValueError("Historical release member digest mismatch")


def write_live_provenance(handoff, source, record):
    package.write_new(handoff / "provenance.json", {
        "kind": "flamel-live-package-v1", "repository": package.REPO,
        "source_commit": source, "ui_build_id": LIVE_UI, "source_release_asset": HISTORY_ASSET,
        "source_asset_sha256": HISTORY_SHA, "member": "website/" + record["archive"]["path"],
        "source_record": LIVE_RECORD, "source_record_sha256": LIVE_RECORD_SHA,
        "origin": "Historical Crystal Lab hosting ZIP carried in release v0.1.0",
        "preparation": "Published payload staged and verified without rebuilding",
        "files": [package.row(handoff, n) for n in sorted(package.FILES)]})
    sums = "".join(row["sha256"] + "  " + row["path"] + "\n" for row in
                   (package.row(handoff, n) for n in sorted(package.FILES | {"provenance.json"})))
    (handoff / "SHA256SUMS").write_text(sums, encoding="ascii", newline="\n")


def verify_handoff(directory, source_commit):
    directory = Path(directory)
    provenance = package.read(directory / "provenance.json")
    if provenance["kind"] != "flamel-live-package-v1":
        return package.verify_package(directory, source_commit)
    if set(package.file_set(directory)) != package.FILES | {"provenance.json", "SHA256SUMS"}:
        raise ValueError("Unexpected handoff files")
    record_path = directory / "package-record.json"
    record = package.read(record_path)
    if not (source_commit == provenance["source_commit"] == LIVE_SOURCE
            and provenance["repository"] == package.REPO and record["uiBuildId"] == provenance["ui_build_id"] == LIVE_UI
            and provenance["source_release_asset"] == HISTORY_ASSET and provenance["source_asset_sha256"] == HISTORY_SHA
            and provenance["source_record_sha256"] == transport.digest(record_path) == LIVE_RECORD_SHA
            and provenance["source_record"] == LIVE_RECORD and provenance["member"] == "website/" + record["archive"]["path"]
            and record["archive"]["sha256"] == LIVE_PAYLOAD_SHA):
        raise ValueError("Historical hosting handoff identity mismatch")
    rows, entry = package.verify_zip(directory / "payload.zip", record)
    plan = package.read(directory / "upload-plan.json")
    if not (plan["packagePath"] == LIVE_RECORD and plan["packageSha256"] == LIVE_RECORD_SHA
            and plan["uiBuildId"] == LIVE_UI and plan["entryTarget"] == "index.html"
            and plan["stableUrl"] == "https://theflamelproject.42web.io/refresh"
            and plan["policy"]["sha256"] == transport.digest(directory / "host/.htaccess") == package.POLICY
            and entry == (directory / "entry-last/index.html").read_bytes()
            and package.inventory(plan["filesBeforeEntry"]) == {k:v for k,v in rows.items() if k != "index.html"}):
        raise ValueError("Staged entry, hosting policy, or plan differs from the release")
    files = [package.row(directory, n) for n in sorted(package.FILES)]
    sums = "".join(row["sha256"] + "  " + row["path"] + "\n" for row in
                   (package.row(directory, n) for n in sorted(package.FILES | {"provenance.json"})))
    if files != provenance["files"] or (directory / "SHA256SUMS").read_bytes() != sums.encode("ascii"):
        raise ValueError("Historical handoff inventories differ")
    return {"source_commit": source_commit, "ui_build_id": LIVE_UI,
            "payload_sha256": LIVE_PAYLOAD_SHA, "payload_files": len(rows)}


def stage(args):
    state = selected_release(args.rollback_run_id)
    source = package.commit(state["source_commit"])
    if state["repository"] != package.REPO or not transport.TAG.fullmatch(state["tag"]):
        raise ValueError("Invalid recorded release identity")
    if package.git(ROOT, "rev-parse", f"{source}^{{tree}}") != state["source_tree"]:
        raise ValueError("Release tree differs from the pinned Git object")
    package.git(ROOT, "merge-base", "--is-ancestor", source, "HEAD")
    work = package.new_directory(args.work_dir, ROOT)
    historical = state["tag"] == "v0.1.0"
    if historical and (source != LIVE_SOURCE or state["ui_build_id"] != LIVE_UI):
        raise ValueError("Unexpected v0.1.0 historical source")
    asset_name = HISTORY_ASSET if historical else f"flamel-website-{state['tag']}.zip"
    asset = next(a for a in state["assets"] if a["name"] == asset_name)
    bundle = args.bundle
    if bundle is None:
        bundle = work / asset_name
        download_release(state, bundle, asset_name)
    if (package.regular(bundle).stat().st_size != asset["bytes"]
            or asset["sha256"] != (HISTORY_SHA if historical else state["production_bundle_sha256"])
            or transport.digest(bundle) != asset["sha256"]):
        raise ValueError("Published website bundle digest or size mismatch")
    handoff = work / "package"
    # Run the original guard with a disposable, byte-preserving checkout of its exact source.
    tagged = work / "source"
    git = ["git", "-c", "core.autocrlf=false", "-c", "core.longpaths=true"]
    child_env = {k: v for k, v in os.environ.items() if k not in {"GH_TOKEN", "GITHUB_TOKEN"}}
    subprocess.run([*git, "clone", "--config", "core.autocrlf=false", "--config", "core.longpaths=true", "--shared", "--no-checkout", "--quiet", str(ROOT), str(tagged)],
                   check=True, env=child_env)
    subprocess.run([*git, "-C", str(tagged), "checkout", "--quiet", "--detach", source],
                   check=True, env=child_env)
    verifier_dir = tagged / "scripts/github_publication"
    verifier = verifier_dir / "verify_phase8.py"
    if not verifier.exists():
        verifier = verifier_dir / "verify_phase7.py"
    subprocess.run([sys.executable, "-I", "-B", str(verifier), "--root", str(tagged), "--require-clean"],
                   cwd=tagged, check=True, env=child_env)
    website = tagged / "website"
    record_relative = LIVE_RECORD if historical else "reports/W6_RELEASE_PACKAGE.json"
    if historical:
        handoff.mkdir()
        original_record = package.regular(website / record_relative)
        if transport.digest(original_record) != LIVE_RECORD_SHA:
            raise ValueError("Tagged historical package record differs")
        shutil.copyfile(original_record, handoff / "package-record.json")
        record = package.read(original_record)
        archive = record["archive"]
        historical_member(bundle, "website/" + archive["path"], handoff / "payload.zip", archive["bytes"], LIVE_PAYLOAD_SHA)
        historical_member(bundle, PRIOR_PATH, work / "predecessor.zip", 3103132, PRIOR_SHA)
    else:
        unpack(bundle, handoff, package.FILES | {"SHA256SUMS", "provenance.json"})
        checked = package.verify_package(handoff, source)
        if checked["payload_sha256"] != state["production_payload_sha256"] or checked["ui_build_id"] != state["ui_build_id"]:
            raise ValueError("Release payload or UI identity mismatch")
        record = package.read(handoff / "package-record.json")
        shutil.copyfile(handoff / "package-record.json", website / record_relative)
    package.verify_zip(handoff / "payload.zip", record)
    unpack(handoff / "payload.zip", website / "dist", [r["path"] for r in record["files"]])
    # The source tag includes two historical stage files. Retain them separately
    # within this disposable checkout so the guard can create its three new files.
    staged = website / "deployment/latest-link/staged" / record["uiBuildId"]
    if staged.exists():
        staged.rename(work / "archived-tag-stage")
    guard = website / "deployment/latest-link/prepare-publication.mjs"
    node = args.node or shutil.which("node")
    if not node:
        raise ValueError("Node.js is required for the publication guard")
    guard_output = subprocess.check_output([str(node), str(guard), f"--package={record_relative}",
                                            "--stage"], cwd=website, env=child_env)
    result = json.loads(guard_output)
    if result.get("mode") != "staged" or result.get("uiBuildId") != record["uiBuildId"]:
        raise ValueError("Guard did not stage the expected UI")
    for name in ("upload-plan.json", "host/.htaccess", "entry-last/index.html"):
        if historical:
            (handoff / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package.regular(staged / name), handoff / name)
        elif package.regular(staged / name).read_bytes() != (handoff / name).read_bytes():
            raise ValueError(f"Guard stage differs from the published handoff: {name}")
    if historical:
        write_live_provenance(handoff, source, record)
    checked = verify_handoff(handoff, source)
    receipt = {"status": "VERIFIED_AND_STAGED", "source_commit": source, "source_tree": state["source_tree"],
               "tag": state["tag"], "release_id": state["release_id"], "asset_id": asset["id"],
               "asset_name": asset_name, "asset_sha256": asset["sha256"], "payload_sha256": checked["payload_sha256"],
               "guard": result, "input": "local verified bundle" if args.bundle else "published GitHub release"}
    package.write_new(work / "preparation.json", receipt)
    print(json.dumps(receipt, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--bundle", type=Path, help="Use a retained copy of the exact published ZIP")
    parser.add_argument("--node", type=Path, help="Path to Node.js")
    parser.add_argument("--rollback-run-id", default="", help="Use the release selected by this prior production run")
    args = parser.parse_args()
    try:
        stage(args)
    except (ValueError, OSError, KeyError, RuntimeError, StopIteration, subprocess.SubprocessError,
            zipfile.BadZipFile) as error:
        raise SystemExit(f"Release preparation failed: {error}")


if __name__ == "__main__":
    main()
