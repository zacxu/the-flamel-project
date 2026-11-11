#!/usr/bin/env python3
"""Verify/retrieve the permitted public subset without publishing private archives.

Requires only the Python standard library and the retained sibling artifact_io.py.
Scientific pickle/joblib contents are verified as bytes and never deserialized.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

VERSION = "1.0.0"
PRIVATE_ARCHIVES = frozenset({
    "flamel-qe-scratch-001.zip", "flamel-qe-scratch-002.zip", "flamel-research-inputs-001.zip"
})
PUBLIC_KIND = "flamel-public-assets-v1"
UPF_KIND = "flamel-upstream-upfs-v1"
CHUNK = 1024 * 1024
TRUSTED_HOSTS = frozenset({
    "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com",
    "archive.materialscloud.org", "rgw.cscs.ch"
})
module_spec = importlib.util.spec_from_file_location(
    "_flamel_artifact_io", Path(__file__).with_name("artifact_io.py"))
legacy = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(legacy)
ArtifactError = legacy.ArtifactError

def fail(message):
    raise ArtifactError(message)

def sha256(path):
    return legacy._digest(path)

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("Duplicate JSON object key")
        result[key] = value
    return result

def read_json(path):
    path = legacy._absolute(path)
    legacy._check_directory_ancestors(path.parent)
    before = legacy._regular_file(path)
    if before.st_size > 10 * 1024 * 1024:
        fail("Manifest exceeds 10 MiB")
    raw = path.read_bytes()
    if legacy._stamp(legacy._regular_file(path)) != legacy._stamp(before):
        fail("Manifest changed while reading")
    try:
        result = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError):
        fail("Invalid JSON manifest")
    return result, hashlib.sha256(raw).hexdigest()

def safe_url(value):
    if not isinstance(value, str):
        fail("Missing published HTTPS URL")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname not in TRUSTED_HOSTS
            or parsed.username or parsed.password or parsed.fragment
            or parsed.port not in (None, 443)):
        fail("Download URL must use an explicitly trusted HTTPS host")
    return value

class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(request, fp, code, message, headers, newurl)

def download_one(record, directory):
    """Bounded anonymous HTTPS download, verified before atomic no-overwrite commit."""
    directory = legacy._absolute(directory)
    if directory == Path(directory.anchor):
        fail("A filesystem root is not a download destination")
    legacy._ensure_directories(directory)
    name = legacy._safe_relative(record["name"])
    if "/" in name:
        fail("Download name must have one basename")
    size = legacy._integer(record["bytes"], "Download bytes")
    expected_hash = legacy._hash_value(record["sha256"], "Download SHA256")
    url = safe_url(record["url"])
    output = directory / name
    existing = legacy._lstat(output)
    if existing is not None:
        legacy._regular_file(output)
        if existing.st_size != size or sha256(output) != expected_hash:
            fail("Existing download differs; it will not be overwritten")
        return {"path": str(output), "network_fetches": 0, "reused_verified": True}
    descriptor, temporary_name = tempfile.mkstemp(prefix=".flamel-download-", dir=directory)
    temporary = Path(temporary_name)
    try:
        opener = build_opener(SafeRedirects())
        request = Request(url, headers={"User-Agent": "TheFlamelProject-reproduction/1.0"})
        digest = hashlib.sha256()
        total = 0
        with opener.open(request, timeout=60) as response, os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            safe_url(response.geturl())
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) != size:
                fail("Server Content-Length differs from pinned size")
            for block in iter(lambda: response.read(CHUNK), b""):
                total += len(block)
                if total > size:
                    fail("Download exceeds pinned size")
                stream.write(block)
                digest.update(block)
            stream.flush()
        if total != size or digest.hexdigest() != expected_hash:
            fail("Downloaded bytes do not match pinned size/SHA256")
        legacy._check_directory_ancestors(directory)
        os.link(temporary, output)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    return {"path": str(output), "network_fetches": 1, "reused_verified": False}

def load_public(manifest_path):
    path = legacy._absolute(manifest_path)
    data, digest = read_json(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("kind") != PUBLIC_KIND:
        fail("Unsupported public-asset manifest")
    if data.get("publication_status") not in ("unpublished", "published"):
        fail("Unknown publication status")
    if type(data.get("asset_limit_bytes")) is not int or data["asset_limit_bytes"] != legacy.ASSET_LIMIT_BYTES:
        fail("Public asset limit must remain exactly 1 GiB")
    if data.get("repository") != "zacxu/the-flamel-project":
        fail("Unexpected source repository")
    # These source-policy files are committed beside the manifest in a fresh checkout.
    publication = path.parent.parent
    policy, policy_digest = read_json(publication / "phase3/release-selection.json")
    notice, notice_digest = read_json(publication / "phase3/notice-bundle.json")
    historical, historical_digest = read_json(publication / "artifacts.json")
    if policy.get("historical_manifest_sha256") != historical_digest:
        fail("Historical member inventory differs from the Phase 3 source identity")
    historical_by_name = {row["name"]: row for row in historical["archives"]}
    if data.get("phase3_selection_sha256") != policy_digest or data.get("notice_record_sha256") != notice_digest:
        fail("Public scope differs from the retained Phase 3 policy")
    helper = Path(__file__).with_name("artifact_io.py")
    if data.get("artifact_io_sha256") != sha256(helper):
        fail("Archive-verifier implementation differs from the audited dependency")
    allowed = {x["name"]: x for x in policy["archives"]
               if x["publication_disposition"] == "candidate-for-later-release"}
    private_folded = {name.casefold() for name in PRIVATE_ARCHIVES}
    if len(allowed) != 11 or private_folded & {name.casefold() for name in allowed}:
        fail("Phase 3 candidate policy must contain exactly eleven permitted originals")
    archives = data.get("archives")
    if not isinstance(archives, list) or len(archives) != 12:
        fail("Public scope requires eleven originals plus one notice bundle")
    names = set()
    for archive in archives:
        if not isinstance(archive, dict):
            fail("Archive entry must be an object")
        name = legacy._safe_basename(archive.get("name"))
        if name.casefold() in names or name.casefold() in private_folded:
            fail("Duplicate/private archive in public manifest")
        names.add(name.casefold())
        if name == notice["name"]:
            original = notice
            if archive.get("group") != "third-party-notices" or archive.get("restore_scope") != "project":
                fail("Notice archive identity/namespace is missing")
            expected_members = [{"archive_path": row["archive_path"], "restore_path": row["source_path"],
                                 "bytes": row["bytes"], "sha256": row["sha256"]} for row in notice["members"]]
            if archive.get("members") != expected_members:
                fail("Notice member inventory differs from the required pack")
        elif name in allowed:
            original = allowed[name]
            historical_record = historical_by_name.get(name)
            if historical_record is None or any(archive.get(key) != historical_record[key]
                                                 for key in ("group", "restore_scope", "members")):
                fail("Public member inventory or restoration namespace changed")
        else:
            fail("Archive is not a Phase 3 permitted candidate")
        if any(archive.get(key) != original[key] for key in ("bytes", "sha256")):
            fail("Public archive identity changed from Phase 3")
        if not isinstance(archive.get("members"), list) or not archive["members"]:
            fail("Archive member inventory missing")
        if any(str(member.get("archive_path", "")).lower().endswith(".upf")
               for member in archive["members"]):
            fail("Raw UPFs are retrieved upstream, never public release members")
        if data["publication_status"] == "unpublished" and archive.get("download_url") is not None:
            fail("Unpublished assets cannot have active download URLs")
    if names != {name.casefold() for name in allowed} | {notice["name"].casefold()}:
        fail("Public candidate/notice scope is incomplete")
    if data.get("notice_archive_name") != notice["name"]:
        fail("Required notice archive is not identified")
    return data, digest

class AssetRoots:
    def __init__(self, assets, notices, notice_name):
        self.assets = legacy._check_directory_ancestors(assets)
        self.notices = legacy._check_directory_ancestors(notices)
        self.notice_name = notice_name
    def __truediv__(self, name):
        legacy._safe_basename(name)
        return (self.notices if name == self.notice_name else self.assets) / name

def public_plan(manifest_path, asset_dir, notice_dir=None, scope="all", scratch_dir=None):
    if scope not in ("project", "production", "all"):
        fail("Invalid verification scope")
    data, digest = load_public(manifest_path)
    adapted = {
        "schema_version": 1, "publication_status": legacy.PUBLICATION_STATUS,
        "repository": data["repository"], "asset_limit_bytes": legacy.ASSET_LIMIT_BYTES,
        "archives": []
    }
    for item in data["archives"]:
        record = dict(item)
        record["availability"] = "local-only"
        record["download_url"] = None
        record["planned_download_url"] = item.get("planned_download_url") or (
            "https://github.com/zacxu/the-flamel-project/releases/download/UNPUBLISHED/" + item["name"])
        if record["name"] == data["notice_archive_name"] and scope == "production":
            record["restore_scope"] = "production"
        adapted["archives"].append(record)
    if scratch_dir is not None:
        legacy._check_directory_ancestors(scratch_dir)
    with tempfile.TemporaryDirectory(prefix="flamel-public-manifest-", dir=scratch_dir) as tmp:
        adapter_path = Path(tmp) / "adapter.json"
        adapter_path.write_text(json.dumps(adapted), encoding="utf-8")
        plan = legacy._read_plan(adapter_path, asset_dir, scope)
    plan["asset_dir"] = AssetRoots(asset_dir, notice_dir or asset_dir, data["notice_archive_name"])
    plan["manifest_sha256"] = digest
    plan["manifest"] = legacy._absolute(manifest_path)
    plan["public_data"] = data
    return plan

def public_result(result, plan):
    return {**result, "tool_version": VERSION, "manifest_kind": PUBLIC_KIND,
            "publication_status": plan["public_data"]["publication_status"],
            "private_archives_included": 0, "required_notice_archive_included": True,
            "scope_statement": "Permitted public subset; withheld scratch/restart history is not restored."}

def verify(manifest_path, asset_dir, notice_dir=None, scope="all", scratch_dir=None):
    plan = public_plan(manifest_path, asset_dir, notice_dir, scope, scratch_dir)
    return public_result(legacy._verify_plan(plan), plan)

def hydrate(manifest_path, asset_dir, destination, notice_dir=None, scope="project",
            merge_existing=False, scratch_dir=None):
    if scope not in ("project", "production"):
        fail("Hydrate one namespace at a time")
    plan = public_plan(manifest_path, asset_dir, notice_dir, scope, scratch_dir)
    return public_result(legacy._hydrate_plan(plan, destination, merge_existing), plan)

def download_public(manifest_path, destination):
    data, digest = load_public(manifest_path)
    # Never infer URLs from plans or attempt an unpublished/private GitHub release.
    if data["publication_status"] != "published":
        fail("No public assets are published; use verified local files until a later release exists")
    records = []
    for archive in data["archives"]:
        url = safe_url(archive.get("download_url"))
        prefix = "https://github.com/" + data["repository"] + "/releases/download/"
        if not url.startswith(prefix) or urlsplit(url).query:
            fail("Published release URLs must identify the intended GitHub repository")
        records.append({"name": archive["name"], "bytes": archive["bytes"],
                        "sha256": archive["sha256"], "url": url})
    fetched = [download_one(record, destination) for record in records]
    return {"status": "DOWNLOADED_VERIFIED", "archives": len(fetched),
            "network_fetches": sum(x["network_fetches"] for x in fetched),
            "manifest_sha256": digest, "anonymous_https_only": True}

def load_upfs(manifest_path):
    data, digest = read_json(manifest_path)
    if data.get("schema_version") != 1 or data.get("kind") != UPF_KIND:
        fail("Unsupported UPF retrieval manifest")
    archive = data.get("upstream_archive", {})
    if archive.get("name") != "SSSP_1.3.0_PBE_efficiency.tar.gz":
        fail("Unexpected upstream archive")
    safe_url(archive.get("url"))
    legacy._integer(archive.get("bytes"), "UPF archive bytes")
    legacy._hash_value(archive.get("sha256"), "UPF archive hash")
    files = data.get("files")
    if not isinstance(files, list) or len(files) != 3:
        fail("Exactly the three used UPFs must be declared")
    names, paths = set(), set()
    for record in files:
        name = legacy._safe_relative(record.get("filename"))
        if "/" in name or not name.lower().endswith(".upf") or name.casefold() in names:
            fail("Invalid/duplicate UPF filename")
        names.add(name.casefold())
        legacy._integer(record.get("bytes"), "UPF bytes")
        legacy._hash_value(record.get("sha256"), "UPF hash")
        if record.get("licence") not in ("GPL-3.0", "GPL-2.0-or-later"):
            fail("Exact UPF family licence must remain visible")
        copies = record.get("restore_paths")
        if not isinstance(copies, list) or not copies:
            fail("Recorded UPF copy paths missing")
        canonical = "data/pseudopotentials/" + name
        if canonical not in copies:
            fail("Canonical UPF placement missing")
        for path in copies:
            legacy._safe_relative(path)
            if Path(path).name != name or path.casefold() in paths:
                fail("Duplicate/inconsistent UPF copy path")
            paths.add(path.casefold())
    if len(paths) != 41:
        fail("Recorded upstream reconstruction scope must contain exactly 41 exact input copies")
    serialized = data.get("nonreconstructible_serialized_scratch_members")
    if not isinstance(serialized, list) or len(serialized) != 36:
        fail("The 36 QE-serialized scratch UPFs must remain explicitly private")
    for record in serialized:
        path = legacy._safe_relative(record.get("path"))
        if path.casefold() in paths or "/scratch/" not in path or ".save/" not in path:
            fail("Unexpected or duplicate serialized scratch member")
        paths.add(path.casefold())
        legacy._integer(record.get("bytes"), "Scratch member bytes")
        legacy._hash_value(record.get("sha256"), "Scratch member SHA256")
    if len(paths) != 77:
        fail("All 77 original UPF-containing members must be accounted for")
    return data, digest

def _tar_name(name):
    while name.startswith("./"):
        name = name[2:]
    return name

def retrieve_upfs(manifest_path, cache_dir, destination, recorded_paths=False, merge_existing=False):
    data, digest = load_upfs(manifest_path)
    download = download_one(data["upstream_archive"], cache_dir)
    archive_path = Path(download["path"])
    archive_before = legacy._regular_file(archive_path)
    if archive_before.st_size != data["upstream_archive"]["bytes"] or sha256(archive_path) != data["upstream_archive"]["sha256"]:
        fail("Cached upstream archive changed before extraction")
    selected = {row["filename"]: row for row in data["files"]}
    extracted = {}
    total_declared = 0
    count = 0
    with tarfile.open(archive_path, "r:gz") as archive:
        seen = set()
        for entry in archive:
            count += 1
            if count > 1000:
                fail("Upstream tar member bound exceeded")
            name = _tar_name(entry.name)
            if name in ("", ".") and entry.isdir():
                continue
            legacy._safe_relative(name)
            if name.casefold() in seen:
                fail("Duplicate/case-colliding tar member")
            seen.add(name.casefold())
            if not entry.isfile():
                fail("Upstream tar has a link or unexpected nonregular member")
            total_declared += entry.size
            if total_declared > 512 * 1024 * 1024 or entry.size > 64 * 1024 * 1024:
                fail("Upstream tar expansion bound exceeded")
            if name in selected:
                row = selected[name]
                if entry.size != row["bytes"]:
                    fail("UPF member size differs")
                stream = archive.extractfile(entry)
                content = stream.read(row["bytes"] + 1)
                if len(content) != row["bytes"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
                    fail("UPF member hash differs")
                extracted[name] = content
    if legacy._stamp(legacy._regular_file(archive_path)) != legacy._stamp(archive_before) or sha256(archive_path) != data["upstream_archive"]["sha256"]:
        fail("Pinned upstream archive changed during extraction")
    if set(extracted) != set(selected):
        fail("Pinned archive lacks one of the exact used UPFs")
    members = []
    for name, row in selected.items():
        paths = row["restore_paths"] if recorded_paths else ["data/pseudopotentials/" + name]
        members.extend({"restore_path": path, "bytes": row["bytes"], "sha256": row["sha256"],
                        "filename": name} for path in paths)
    target, reused = legacy._preflight_destination(destination, members, merge_existing)
    legacy._ensure_directories(target)
    created = 0
    for row in members:
        if row["restore_path"] in reused:
            continue
        output = target / row["restore_path"]
        legacy._ensure_directories(output.parent)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".flamel-upf-", dir=output.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(extracted[row["filename"]])
            legacy._check_directory_ancestors(output.parent)
            os.link(temporary, output)
            created += 1
        finally:
            temporary.unlink(missing_ok=True)
    for row in members:
        output = target / row["restore_path"]
        legacy._check_directory_ancestors(output.parent)
        legacy._regular_file(output)
        if sha256(output) != row["sha256"]:
            fail("Final UPF copy hash differs")
    return {"status": "UPSTREAM_UPFS_RETRIEVED_VERIFIED", "manifest_sha256": digest,
            "network_fetches": download["network_fetches"], "canonical_upfs": 3, "serialized_scratch_members_not_reconstructed": 36,
            "placed_files": len(members), "created_files": created,
            "reused_matching_files": len(reused), "archive_members_inspected": count,
            "tar_declared_bytes": total_declared, "existing_files_overwritten": 0,
            "source": data["upstream_archive"]["url"],
            "licences": {row["filename"]: row["licence"] for row in data["files"]},
            "scope_statement": "Exact upstream UPF inputs only; withheld scratch/restart outputs are not reconstructed."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify", "hydrate"):
        command = sub.add_parser(name)
        command.add_argument("--manifest", required=True, type=Path)
        command.add_argument("--asset-dir", required=True, type=Path)
        command.add_argument("--notice-dir", type=Path)
        command.add_argument("--scope", choices=("project", "production", "all") if name == "verify" else ("project", "production"),
                             default="all" if name == "verify" else "project")
        command.add_argument("--scratch-dir", type=Path)
        command.add_argument("--report", type=Path)
        if name == "hydrate":
            command.add_argument("--destination", required=True, type=Path)
            command.add_argument("--merge-existing", action="store_true")
    command = sub.add_parser("download")
    command.add_argument("--manifest", required=True, type=Path)
    command.add_argument("--destination", required=True, type=Path)
    command.add_argument("--report", type=Path)
    command = sub.add_parser("upfs")
    command.add_argument("--manifest", required=True, type=Path)
    command.add_argument("--cache-dir", required=True, type=Path)
    command.add_argument("--destination", required=True, type=Path)
    command.add_argument("--restore-recorded-paths", action="store_true")
    command.add_argument("--merge-existing", action="store_true")
    command.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = legacy._report_preflight(args.report)
    if args.command == "verify":
        result = verify(args.manifest, args.asset_dir, args.notice_dir, args.scope, args.scratch_dir)
    elif args.command == "hydrate":
        result = hydrate(args.manifest, args.asset_dir, args.destination, args.notice_dir,
                         args.scope, args.merge_existing, args.scratch_dir)
    elif args.command == "download":
        result = download_public(args.manifest, args.destination)
    else:
        result = retrieve_upfs(args.manifest, args.cache_dir, args.destination,
                               args.restore_recorded_paths, args.merge_existing)
    legacy._write_report(report, result)
    print(json.dumps(result, ensure_ascii=True))

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__, "error": str(error)}))
        raise SystemExit(1)
