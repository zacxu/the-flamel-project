#!/usr/bin/env python3
"""Full Flamel file-content snapshot, independent verification and safe restoration.

No Git ignore rules apply. No deletion or overwrite of existing snapshots is allowed.
Original hardlinks are materialized. Reparse points fail closed.
Content, relative paths, empty directories and modified times are preserved;
ACLs, alternate streams, creation times and original hardlink topology are not restored.
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import threading
import time

VERSION = "1.1.0"
CHUNK = 4 * 1024 * 1024
LOCK = threading.Lock()
PROGRESS = {"files": 0, "bytes": 0, "last": 0.0}

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def emit(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)

def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()

def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())

def json_new(path, value):
    write_new(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

def normalized(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))

def outside(first, second):
    first, second = normalized(first), normalized(second)
    try:
        common = os.path.commonpath([first, second])
    except ValueError:
        return
    if common in (first, second):
        raise RuntimeError("Source and destination must be separate, non-nested directories")

def safe_join(root, relative):
    if "\\" in relative or relative.startswith("/") or ":" in relative:
        raise RuntimeError("Unsafe relative path: " + relative)
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise RuntimeError("Unsafe relative path: " + relative)
    result = Path(root).joinpath(*parts)
    if os.path.commonpath([normalized(root), normalized(result)]) != normalized(root):
        raise RuntimeError("Path escapes expected root")
    return result

def meta(st):
    return {
        "bytes": st.st_size, "mtime_ns": st.st_mtime_ns,
        "atime_ns": st.st_atime_ns, "mode": st.st_mode,
        "file_attributes": getattr(st, "st_file_attributes", 0),
        "inode": st.st_ino, "device": st.st_dev, "hardlink_count": st.st_nlink,
    }

def identity(item):
    return (item["bytes"], item["mtime_ns"], item["mode"],
            item["file_attributes"], item["inode"], item["device"])

def scan(root):
    files, directories = {}, {}
    def visit(folder, relative):
        st = os.stat(folder, follow_symlinks=False)
        if stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & 0x400:
            raise RuntimeError("Reparse point requires explicit handling: " + str(folder))
        directories[relative] = meta(st)
        with os.scandir(folder) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            rel = (relative + "/" if relative else "") + entry.name
            est = os.stat(entry.path, follow_symlinks=False)
            if entry.is_symlink() or getattr(est, "st_file_attributes", 0) & 0x400:
                raise RuntimeError("Reparse point requires explicit handling: " + rel)
            if stat.S_ISDIR(est.st_mode):
                visit(entry.path, rel)
            elif stat.S_ISREG(est.st_mode):
                files[rel] = meta(est)
            else:
                raise RuntimeError("Unsupported filesystem object: " + rel)
    visit(root, "")
    folded = [relative.casefold() for relative in files]
    if len(set(folded)) != len(folded):
        raise RuntimeError("Case-insensitive path collision")
    return files, directories

def classify(relative, size):
    lower = relative.lower()
    parts = lower.split("/")
    name = parts[-1]
    if any(part in (".envs", ".runtime", ".cache", "node_modules", "__pycache__", ".tooling")
           for part in parts) or lower.endswith(".pyc"):
        return "recreate-for-git; original-bytes-retained-in-full-backup"
    if name in (".env", "id_rsa", "id_ed25519") or name.endswith((".pem", ".pfx", ".p12")):
        return "private-security-review; original-bytes-retained-in-full-backup"
    if lower.startswith("vendor/crystalformer/") and size <= 25 * 1024 * 1024:
        return "git-vendored-source-or-pinned-source; phase2-review"
    if (size > 25 * 1024 * 1024 or lower.startswith(("checkpoints/", "vendor/"))
        or name.endswith((".joblib", ".pkl", ".wfc1", ".dat"))
        or "/scratch/" in lower):
        return "checksummed-release-archive-or-pinned-download; phase2-review"
    if lower.startswith(("artifacts/", "data/", "website/reports/", "website/deployment/")):
        return "git-small-evidence-or-release-archive; phase2-review"
    return "git-source-config-documentation-or-small-asset; phase2-review"

def progress(action, size):
    with LOCK:
        PROGRESS["files"] += 1
        PROGRESS["bytes"] += size
        now = time.monotonic()
        if now - PROGRESS["last"] >= 10:
            PROGRESS["last"] = now
            emit({"stage": action, "files_processed": PROGRESS["files"],
                  "bytes_processed": PROGRESS["bytes"], "utc": utc()})

def reset_progress():
    with LOCK:
        PROGRESS.update(files=0, bytes=0, last=0.0)

def load_records(snapshot):
    snapshot = Path(snapshot)
    manifest = snapshot / "inventory.jsonl"
    sidecar = snapshot / "inventory.sha256"
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = sha(manifest)
    if actual != expected:
        raise RuntimeError("Inventory sidecar mismatch")
    records = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    files = [record for record in records if record["kind"] == "file"]
    dirs = [record for record in records if record["kind"] == "directory"]
    return files, dirs, actual

def compare_inventory(root, files, dirs, workers):
    reset_progress()
    current, current_dirs = scan(root)
    expected_files = {item["relative_path"]: item for item in files}
    expected_dirs = {item["relative_path"]: item for item in dirs}
    if set(current) != set(expected_files):
        raise RuntimeError("File set differs from inventory")
    if set(current_dirs) != set(expected_dirs):
        raise RuntimeError("Directory set differs from inventory")
    def check(item):
        rel, expected = item
        target = safe_join(root, rel)
        actual = current[rel]
        if actual["bytes"] != expected["bytes"]:
            raise RuntimeError("Length mismatch: " + rel)
        if actual["mtime_ns"] != expected["mtime_ns"]:
            raise RuntimeError("Modified-time mismatch: " + rel)
        if sha(target) != expected["sha256"]:
            raise RuntimeError("SHA256 mismatch: " + rel)
        after = meta(os.stat(target, follow_symlinks=False))
        if identity(after) != identity(actual):
            raise RuntimeError("File changed during verification: " + rel)
        progress("independent-content-verification", expected["bytes"])
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(check, expected_files.items()))
    return {"files": len(files), "directories_including_root": len(dirs),
            "bytes": sum(item["bytes"] for item in files),
            "all_content_sha256_match": True, "all_file_mtimes_match": True}

def capture(args):
    source, output = Path(args.source), Path(args.snapshot)
    if not source.is_dir():
        raise RuntimeError("Source directory does not exist")
    outside(source, output)
    if output.exists():
        raise RuntimeError("Snapshot destination already exists; refusing overwrite")
    started = utc()
    before, before_dirs = scan(source)
    total = sum(item["bytes"] for item in before.values())
    space_parent = output.parent
    while not space_parent.exists():
        space_parent = space_parent.parent
    free = shutil.disk_usage(space_parent).free
    if free < total + max(2 * 1024**3, total // 20):
        raise RuntimeError("Insufficient backup space")
    output.mkdir(parents=True, exist_ok=False)
    tree = output / "bears"
    tree.mkdir()
    json_new(output / "capture-start.json", {
        "tool_version": VERSION, "source": str(source), "started_utc": started,
        "expected_files": len(before), "expected_bytes": total,
        "expected_directories_including_root": len(before_dirs), "exclusions": [],
    })
    for rel in sorted(before_dirs, key=lambda item: (item.count("/"), item)):
        if rel:
            safe_join(tree, rel).mkdir(exist_ok=False)
    reset_progress()
    def copy(item):
        rel, original = item
        source_path = safe_join(source, rel)
        target = safe_join(tree, rel)
        if identity(meta(os.stat(source_path, follow_symlinks=False))) != identity(original):
            raise RuntimeError("Source changed before copying: " + rel)
        digest = hashlib.sha256()
        size = 0
        with open(source_path, "rb") as incoming, open(target, "xb") as outgoing:
            for block in iter(lambda: incoming.read(CHUNK), b""):
                outgoing.write(block)
                digest.update(block)
                size += len(block)
        after = meta(os.stat(source_path, follow_symlinks=False))
        if identity(after) != identity(original) or size != original["bytes"]:
            raise RuntimeError("Source changed while copying: " + rel)
        shutil.copystat(source_path, target, follow_symlinks=False)
        progress("copy-and-source-sha256", size)
        return {
            "kind": "file", "relative_path": rel, **original,
            "sha256": digest.hexdigest(), "backup_relative_path": "bears/" + rel,
            "intended_storage_location": classify(rel, size),
        }
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(copy, sorted(before.items())))
    after, after_dirs = scan(source)
    if set(before) != set(after) or set(before_dirs) != set(after_dirs):
        raise RuntimeError("Source paths changed during capture")
    changes = [rel for rel in before if identity(before[rel]) != identity(after[rel])]
    if changes:
        raise RuntimeError("Source metadata changed during capture: " + repr(changes[:10]))
    for rel in sorted(before_dirs, key=lambda item: (-item.count("/"), item), reverse=False):
        target = safe_join(tree, rel) if rel else tree
        stamp = before_dirs[rel]
        os.utime(target, ns=(stamp["atime_ns"], stamp["mtime_ns"]))
    dir_records = [
        {"kind": "directory", "relative_path": rel, **value,
         "backup_relative_path": "bears/" + rel if rel else "bears",
         "intended_storage_location": "full-backup-directory; phase2-review"}
        for rel, value in sorted(before_dirs.items())
    ]
    inventory = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                        for item in dir_records + records).encode("utf-8")
    write_new(output / "inventory.jsonl", inventory)
    inventory_sha = sha(output / "inventory.jsonl")
    write_new(output / "inventory.sha256", (inventory_sha + "  inventory.jsonl\n").encode("ascii"))
    verification = compare_inventory(tree, records, dir_records, args.workers)
    final_source, final_source_dirs = scan(source)
    if (set(final_source) != set(before) or set(final_source_dirs) != set(before_dirs)
        or any(identity(before[rel]) != identity(final_source[rel]) for rel in before)):
        raise RuntimeError("Source changed before final acceptance")
    summary = {
        "status": "VERIFIED", "tool_version": VERSION, "source": str(source),
        "snapshot": str(output), "started_utc": started, "completed_utc": utc(),
        "inventory_sha256": inventory_sha, **verification,
        "source_stability_checked_before_during_after": True,
        "exclusions": [], "reparse_points": 0,
        "original_hardlinks_materialized": True,
        "metadata_scope": "File contents/relative paths/empty directories/file mtimes; original timestamps and attributes inventoried. ACLs/ADS/creation times/hardlink topology not restored.",
    }
    json_new(output / "verification.json", summary)
    emit(summary)

def verify(args):
    files, dirs, digest = load_records(args.snapshot)
    root = Path(args.root) if args.root else Path(args.snapshot) / "bears"
    result = compare_inventory(root, files, dirs, args.workers)
    summary = {"status": "VERIFIED", "root": str(root), "inventory_sha256": digest,
               "completed_utc": utc(), **result}
    if args.report:
        json_new(args.report, summary)
    emit(summary)

def restore(args):
    snapshot, destination = Path(args.snapshot), Path(args.destination)
    outside(snapshot, destination)
    files, dirs, digest = load_records(snapshot)
    if destination.exists():
        raise RuntimeError("Restore destination exists; refusing overwrite")
    original_source = json.loads((snapshot / "capture-start.json").read_text())["source"]
    if normalized(original_source) != normalized(destination):
        outside(original_source, destination)
    free = shutil.disk_usage(destination.parent).free
    total = sum(item["bytes"] for item in files)
    if free < total + max(2 * 1024**3, total // 20):
        raise RuntimeError("Insufficient restoration space")
    destination.mkdir(parents=True, exist_ok=False)
    for item in sorted(dirs, key=lambda item: (item["relative_path"].count("/"), item["relative_path"])):
        if item["relative_path"]:
            safe_join(destination, item["relative_path"]).mkdir(exist_ok=False)
    reset_progress()
    def copy(record):
        rel = record["relative_path"]
        source = safe_join(snapshot / "bears", rel)
        target = safe_join(destination, rel)
        digest = hashlib.sha256()
        with open(source, "rb") as incoming, open(target, "xb") as outgoing:
            for block in iter(lambda: incoming.read(CHUNK), b""):
                outgoing.write(block)
                digest.update(block)
        if digest.hexdigest() != record["sha256"]:
            raise RuntimeError("Backup content mismatch while restoring: " + rel)
        shutil.copystat(source, target, follow_symlinks=False)
        progress("restore-copy", record["bytes"])
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(copy, files))
    for item in sorted(dirs, key=lambda item: -item["relative_path"].count("/")):
        target = safe_join(destination, item["relative_path"]) if item["relative_path"] else destination
        os.utime(target, ns=(item["atime_ns"], item["mtime_ns"]))
    result = compare_inventory(destination, files, dirs, args.workers)
    report = {"status": "VERIFIED", "restoration_root": str(destination),
              "inventory_sha256": digest, "completed_utc": utc(), **result,
              "uses_git_or_network": False}
    json_new(args.report, report)
    emit(report)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "verify", "restore"):
        command = sub.add_parser(name)
        command.add_argument("--snapshot", required=True)
        command.add_argument("--workers", type=int, default=4)
        if name == "capture":
            command.add_argument("--source", required=True)
        elif name == "verify":
            command.add_argument("--root")
            command.add_argument("--report")
        else:
            command.add_argument("--destination", required=True)
            command.add_argument("--report", required=True)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        parser.error("workers must be between 1 and 16")
    {"capture": capture, "verify": verify, "restore": restore}[args.command](args)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc), "utc": utc()})
        raise