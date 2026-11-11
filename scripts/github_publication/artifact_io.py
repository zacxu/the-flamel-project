#!/usr/bin/env python3
"""Verify and hydrate local Flamel release archives without network access.

Only regular-file ZIP members declared by a strict manifest are accepted.
Hydration verifies every selected archive before preflighting/writing a target.
Existing files are never overwritten. Merge mode accepts matching collisions and
leaves unrelated existing files untouched. Destination directories must not be
mutated concurrently by other processes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import zipfile

VERSION = "1.0.0"
ASSET_LIMIT_BYTES = 1024 * 1024 * 1024
CHUNK = 4 * 1024 * 1024
PUBLICATION_STATUS = "local_prepared_unpublished_pending_phase3"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_RESERVED = {"con", "prn", "aux", "nul"} | {
    prefix + str(number) for prefix in ("com", "lpt") for number in range(1, 10)
}

class ArtifactError(RuntimeError):
    """A manifest, archive, or destination failed a safety/integrity check."""

def _fail(message):
    raise ArtifactError(message)

def _absolute(path):
    return Path(os.path.abspath(os.fspath(path)))

def _is_reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)

def _lstat(path):
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None

def _check_directory_ancestors(path, allow_missing=False):
    absolute = _absolute(path)
    for part in list(reversed(absolute.parents)) + [absolute]:
        info = _lstat(part)
        if info is None:
            if allow_missing:
                continue
            _fail("Required directory is missing: " + str(part))
        if _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            _fail("Directory or ancestor is a link/reparse point or not a directory: " + str(part))
    return absolute

def _regular_file(path):
    info = _lstat(path)
    if info is None or _is_reparse(info) or not stat.S_ISREG(info.st_mode):
        _fail("Required regular file is missing or is a link: " + str(path))
    return info

def _stamp(info):
    return (info.st_size, info.st_mtime_ns, info.st_ino, info.st_dev)

def _digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            value.update(block)
    return value.hexdigest()

def _safe_relative(value):
    if not isinstance(value, str) or not value:
        _fail("A member path must be a nonempty string")
    if "\\" in value or ":" in value or value.startswith("/"):
        _fail("Absolute, drive, stream, or backslash member path is forbidden: " + repr(value))
    parts = value.split("/")
    for part in parts:
        if part in ("", ".", "..") or part.endswith((" ", ".")):
            _fail("Noncanonical or traversing member path is forbidden: " + repr(value))
        if any(ord(char) < 32 or char in '<>"|?*' for char in part):
            _fail("Unsafe Windows member name: " + repr(value))
        if part.split(".", 1)[0].casefold() in _RESERVED:
            _fail("Reserved Windows member name: " + repr(value))
        if part.casefold() == ".git":
            _fail("Git metadata is not an allowed hydrated artifact: " + repr(value))
    return value

def _safe_basename(value):
    result = _safe_relative(value)
    if "/" in result or not result.lower().endswith(".zip"):
        _fail("An archive name must be a ZIP basename: " + repr(value))
    return result

def _integer(value, label):
    if type(value) is not int or value < 0:
        _fail(label + " must be a nonnegative integer")
    return value

def _hash_value(value, label):
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail(label + " must be a lowercase SHA-256 hex digest")
    return value

def _read_plan(manifest_path, asset_dir, scope):
    if scope not in ("project", "production", "all"):
        _fail("Scope must be project, production, or all")
    manifest = _absolute(manifest_path)
    _check_directory_ancestors(manifest.parent)
    before = _regular_file(manifest)
    raw = manifest.read_bytes()
    if _stamp(_regular_file(manifest)) != _stamp(before):
        _fail("Manifest changed while reading")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        _fail("Manifest is not valid JSON: " + str(exc))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        _fail("Unsupported manifest schema")
    if data.get("publication_status") != PUBLICATION_STATUS:
        _fail("This tool requires locally prepared, unpublished Phase 2 assets")
    if not isinstance(data.get("repository"), str) or not data["repository"]:
        _fail("Repository is missing")
    if type(data.get("asset_limit_bytes")) is not int or data["asset_limit_bytes"] != ASSET_LIMIT_BYTES:
        _fail("Manifest asset limit must be exactly 1 GiB")
    archives = data.get("archives")
    if not isinstance(archives, list) or not archives:
        _fail("Manifest must declare at least one archive")
    names = set()
    scope_paths = {"project": {}, "production": {}}
    scope_prefixes = {"project": {}, "production": {}}
    selected = []
    for archive in archives:
        if not isinstance(archive, dict):
            _fail("Archive record must be an object")
        name = _safe_basename(archive.get("name"))
        if name.casefold() in names:
            _fail("Duplicate or case-colliding archive name: " + name)
        names.add(name.casefold())
        archive_scope = archive.get("restore_scope")
        if archive_scope not in scope_paths:
            _fail("Archive restore_scope must be project or production")
        size = _integer(archive.get("bytes"), "Archive bytes")
        if size > ASSET_LIMIT_BYTES:
            _fail("Archive exceeds the 1 GiB limit: " + name)
        _hash_value(archive.get("sha256"), "Archive sha256")
        if not isinstance(archive.get("group"), str) or not archive["group"]:
            _fail("Archive group is missing: " + name)
        if archive.get("availability") != "local-only" or archive.get("download_url") is not None:
            _fail("Phase 2 archive availability must remain local-only and unpublished")
        if not isinstance(archive.get("planned_download_url"), str) or not archive["planned_download_url"]:
            _fail("A planned download URL must be documented without being fetched")
        members = archive.get("members")
        if not isinstance(members, list) or not members:
            _fail("Each archive must declare regular-file members: " + name)
        member_names = set()
        for member in members:
            if not isinstance(member, dict):
                _fail("Member record must be an object")
            archive_path = _safe_relative(member.get("archive_path"))
            restore_path = _safe_relative(member.get("restore_path"))
            if archive_path != restore_path:
                _fail("Archive and restoration relative paths must be identical")
            folded = archive_path.casefold()
            if folded in member_names:
                _fail("Duplicate or case-colliding manifest member: " + archive_path)
            member_names.add(folded)
            _integer(member.get("bytes"), "Member bytes")
            _hash_value(member.get("sha256"), "Member sha256")
            prior = scope_paths[archive_scope].get(folded)
            if prior is not None:
                _fail("Member occurs more than once in a restore scope: " + restore_path)
            scope_paths[archive_scope][folded] = restore_path
            parts = restore_path.split("/")
            for count in range(1, len(parts) + 1):
                prefix = "/".join(parts[:count])
                prior_prefix = scope_prefixes[archive_scope].get(prefix.casefold())
                if prior_prefix is not None and prior_prefix != prefix:
                    _fail("Case-colliding directory or file path: " + prefix)
                scope_prefixes[archive_scope][prefix.casefold()] = prefix
        if scope == "all" or archive_scope == scope:
            selected.append(archive)
    for archive_scope, paths in scope_paths.items():
        for folded, value in paths.items():
            parts = value.split("/")
            for count in range(1, len(parts)):
                if "/".join(parts[:count]).casefold() in paths:
                    _fail("A declared file is also a parent directory: " + value)
    if not selected:
        _fail("No archives are declared for the requested scope")
    assets = _check_directory_ancestors(asset_dir)
    return {
        "data": data, "manifest": manifest, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "asset_dir": assets, "scope": scope, "archives": selected,
    }

def _zip_members(archive, expected):
    actual = {}
    folded = set()
    for info in archive.infolist():
        name = _safe_relative(info.filename)
        if getattr(info, "orig_filename", name) != name:
            _fail("ZIP member name contains a truncated/NUL name")
        mode = (info.external_attr >> 16) & 0xFFFF
        kind = stat.S_IFMT(mode)
        if info.is_dir() or kind not in (0, stat.S_IFREG):
            _fail("ZIP contains a directory, link, or nonregular member: " + name)
        if info.flag_bits & 1:
            _fail("Encrypted members are not supported: " + name)
        if name in actual or name.casefold() in folded:
            _fail("ZIP contains duplicate or case-colliding members: " + name)
        folded.add(name.casefold())
        actual[name] = info
    if set(actual) != set(expected):
        _fail("ZIP member set differs from the manifest")
    for name, info in actual.items():
        if info.file_size != expected[name]["bytes"]:
            _fail("ZIP member length differs from the manifest: " + name)
    return actual

def _read_member(archive, info, expected, outgoing=None):
    digest = hashlib.sha256()
    count = 0
    with archive.open(info, "r") as incoming:
        for block in iter(lambda: incoming.read(CHUNK), b""):
            count += len(block)
            if count > expected["bytes"]:
                _fail("Member exceeds its declared size: " + info.filename)
            digest.update(block)
            if outgoing is not None:
                outgoing.write(block)
    if count != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
        _fail("ZIP member content hash or length mismatch: " + info.filename)

def _verify_plan(plan, progress=None):
    count = 0
    total = 0
    asset_bytes = 0
    for spec in plan["archives"]:
        path = plan["asset_dir"] / spec["name"]
        before = _regular_file(path)
        if before.st_size != spec["bytes"] or before.st_size > ASSET_LIMIT_BYTES:
            _fail("Archive file length mismatch: " + spec["name"])
        if _digest(path) != spec["sha256"]:
            _fail("Archive SHA-256 mismatch: " + spec["name"])
        expected = {member["archive_path"]: member for member in spec["members"]}
        with zipfile.ZipFile(path, "r") as archive:
            infos = _zip_members(archive, expected)
            for name, info in infos.items():
                _read_member(archive, info, expected[name])
        if _stamp(_regular_file(path)) != _stamp(before):
            _fail("Archive changed during verification: " + spec["name"])
        count += len(expected)
        total += sum(member["bytes"] for member in expected.values())
        asset_bytes += spec["bytes"]
        if progress is not None:
            progress({"stage": "archive-verified", "archive": spec["name"], "members": len(expected)})
    return {
        "status": "VERIFIED", "tool_version": VERSION, "scope": plan["scope"],
        "manifest_sha256": plan["manifest_sha256"], "archives": len(plan["archives"]),
        "members": count, "member_bytes": total, "asset_bytes": asset_bytes,
        "network_fetches": 0, "publication_status": PUBLICATION_STATUS,
    }

def verify(manifest_path, asset_dir, scope="all"):
    """Verify selected local archives and all member contents; never fetch URLs."""
    return _verify_plan(_read_plan(manifest_path, asset_dir, scope))

def _case_exact_child(parent, name, cache):
    key = str(parent)
    if key not in cache:
        names = {}
        with os.scandir(parent) as stream:
            for entry in stream:
                folded = entry.name.casefold()
                if folded in names and names[folded] != entry.name:
                    _fail("Existing directory contains case-colliding entries: " + str(parent))
                names[folded] = entry.name
        cache[key] = names
    actual = cache[key].get(name.casefold())
    if actual is not None and actual != name:
        _fail("Existing destination entry has conflicting case: " + str(parent / name))

def _target_members(plan):
    return [member for spec in plan["archives"] for member in spec["members"]]

def _preflight_destination(destination, members, merge_existing):
    target = _absolute(destination)
    if target == Path(target.anchor):
        _fail("A filesystem root is not an allowed hydration destination")
    _check_directory_ancestors(target.parent, allow_missing=True)
    root_info = _lstat(target)
    if root_info is not None:
        if not merge_existing:
            _fail("Destination exists; use a fresh directory or explicit --merge-existing")
        if _is_reparse(root_info) or not stat.S_ISDIR(root_info.st_mode):
            _fail("Merge destination is not a regular directory")
    reused = set()
    checked_dirs = set()
    case_cache = {}
    for member in members:
        parts = member["restore_path"].split("/")
        parent = target
        missing = root_info is None
        for name in parts[:-1]:
            child = parent / name
            if not missing:
                _case_exact_child(parent, name, case_cache)
                if str(child) not in checked_dirs:
                    info = _lstat(child)
                    if info is None:
                        missing = True
                    elif _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
                        _fail("Selected destination parent is a link or non-directory: " + str(child))
                    checked_dirs.add(str(child))
                elif not child.exists():
                    missing = True
            parent = child
        final = parent / parts[-1]
        if not missing:
            _case_exact_child(parent, parts[-1], case_cache)
            info = _lstat(final)
            if info is not None:
                if _is_reparse(info) or not stat.S_ISREG(info.st_mode):
                    _fail("Selected existing destination is not a regular file: " + str(final))
                if info.st_size != member["bytes"] or _digest(final) != member["sha256"]:
                    _fail("Existing destination file differs; no files have been written: " + str(final))
                reused.add(member["restore_path"])
    return target, reused

def _ensure_directories(path):
    _check_directory_ancestors(path, allow_missing=True)
    path.mkdir(parents=True, exist_ok=True)
    _check_directory_ancestors(path)

def _hydrate_plan(plan, destination, merge_existing=False, progress=None):
    verification = _verify_plan(plan, progress)
    members = _target_members(plan)
    target, reused = _preflight_destination(destination, members, merge_existing)
    _ensure_directories(target)
    created = 0
    for spec in plan["archives"]:
        asset = plan["asset_dir"] / spec["name"]
        before = _regular_file(asset)
        if before.st_size != spec["bytes"] or _digest(asset) != spec["sha256"]:
            _fail("Verified archive changed before hydration: " + spec["name"])
        expected = {member["archive_path"]: member for member in spec["members"]}
        with zipfile.ZipFile(asset, "r") as archive:
            infos = _zip_members(archive, expected)
            for name, member in expected.items():
                if member["restore_path"] in reused:
                    continue
                output = target.joinpath(*member["restore_path"].split("/"))
                _ensure_directories(output.parent)
                descriptor, temporary_name = tempfile.mkstemp(prefix=".flamel-hydrate-", dir=output.parent)
                temporary = Path(temporary_name)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        _read_member(archive, infos[name], member, stream)
                        stream.flush()
                    _check_directory_ancestors(output.parent)
                    # link() atomically fails if the final name already exists; unlike
                    # rename/replace it never overwrites an existing destination.
                    os.link(temporary, output)
                    created += 1
                finally:
                    temporary.unlink(missing_ok=True)
        if _stamp(_regular_file(asset)) != _stamp(before):
            _fail("Archive changed during hydration: " + spec["name"])
        if progress is not None:
            progress({"stage": "archive-hydrated", "archive": spec["name"], "created_files": created})
    for member in members:
        output = target.joinpath(*member["restore_path"].split("/"))
        _check_directory_ancestors(output.parent)
        info = _regular_file(output)
        if info.st_size != member["bytes"] or _digest(output) != member["sha256"]:
            _fail("Final destination verification failed: " + str(output))
    return {
        **verification, "status": "HYDRATED_VERIFIED", "destination": str(target),
        "created_files": created, "reused_matching_files": len(reused),
        "merge_existing": bool(merge_existing), "existing_files_overwritten": 0,
        "selected_destination_files_independently_hashed": len(members),
    }

def hydrate(manifest_path, asset_dir, destination, scope="project", merge_existing=False):
    """Verify, preflight and hydrate selected archives without overwriting files."""
    if scope not in ("project", "production"):
        _fail("Hydration scope must be project or production")
    return _hydrate_plan(_read_plan(manifest_path, asset_dir, scope), destination, merge_existing)

def _report_preflight(report):
    if report is None:
        return None
    result = _absolute(report)
    _check_directory_ancestors(result.parent, allow_missing=True)
    if _lstat(result) is not None:
        _fail("Report already exists; refusing overwrite: " + str(result))
    return result

def _write_report(report, value):
    if report is None:
        return
    _ensure_directories(report.parent)
    with open(report, "x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify", "hydrate"):
        command = sub.add_parser(name)
        command.add_argument("--manifest", required=True)
        command.add_argument("--asset-dir", required=True)
        command.add_argument("--scope", choices=("project", "production", "all") if name == "verify" else ("project", "production"),
                             default="all" if name == "verify" else "project")
        command.add_argument("--report")
        if name == "hydrate":
            command.add_argument("--destination", required=True)
            command.add_argument("--merge-existing", action="store_true")
    args = parser.parse_args()
    report = _report_preflight(args.report)
    plan = _read_plan(args.manifest, args.asset_dir, args.scope)
    progress = lambda value: print(json.dumps(value, ensure_ascii=True), flush=True)
    if args.command == "verify":
        result = _verify_plan(plan, progress)
    else:
        result = _hydrate_plan(plan, args.destination, args.merge_existing, progress)
    _write_report(report, result)
    print(json.dumps(result, ensure_ascii=True), flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)},
                         ensure_ascii=True), flush=True)
        sys.exit(1)