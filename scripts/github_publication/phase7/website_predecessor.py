"""Create/verify/restore the exact W5 static predecessor required by W6 release QA.

Only the 84 bytes-and-path records in the immutable W6 baseline are eligible.
No source extraction, scientific models, hosting write or bulk archive access.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import zipfile

BASELINE_SHA256 = "1ff35e05aaceb42f5a38293fd296e5b7a50d7774d010f6991062f8c32716f893"
PREVIOUS_ID = "w5-ui-61310ee383dfae8b9003"
MAX_ARCHIVE = 20 * 1024 * 1024
SPEC = importlib.util.spec_from_file_location("_predecessor_integrity", Path(__file__).resolve().parents[1] / "verify_phase3.py")
integrity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(integrity)

def no_links(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Predecessor paths cannot traverse links or reparse points")
    return path

def baseline(root):
    root = no_links(root)
    path = integrity.checked_file(root, "website/reports/W6_BASELINE.json")
    if integrity.sha256(path) != BASELINE_SHA256:
        raise ValueError("The frozen W6 predecessor baseline changed")
    saved = integrity.load_json(path)
    if saved["previousUiBuildId"] != PREVIOUS_ID:
        raise ValueError("Unexpected predecessor identity")
    rows = integrity.records(saved["previousBuildFiles"], "Frozen W5 files")
    if len(rows) != 84 or any(row["bytes"] > 10_000_000 for row in rows.values()):
        raise ValueError("Unexpected predecessor inventory bounds")
    return root, rows

def bytes_checked(data, row):
    if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise ValueError("Predecessor bytes differ: " + row["path"])

def payload(root, archive):
    root, rows = baseline(root)
    archive = no_links(archive)
    if not archive.is_file() or archive.stat().st_size > MAX_ARCHIVE:
        raise ValueError("Expected bounded regular predecessor ZIP")
    result = {}
    with zipfile.ZipFile(archive) as stream:
        entries = stream.infolist()
        if len(entries) != len(rows) or {entry.filename for entry in entries} != set(rows):
            raise ValueError("Predecessor ZIP has extra/missing/duplicate paths")
        for entry in entries:
            name = integrity.checked_name(entry.filename)
            if name in result or entry.is_dir() or entry.flag_bits & 1 or stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError("Predecessor ZIP must contain unique regular unencrypted files")
            if entry.file_size != rows[name]["bytes"]:
                raise ValueError("Predecessor ZIP size mismatch")
            data = stream.read(entry)
            bytes_checked(data, rows[name])
            result[name] = data
    return rows, result

def pack(root, source, archive):
    root, rows = baseline(root)
    source = no_links(source)
    archive = no_links(archive)
    if archive.exists() or archive.resolve().is_relative_to(root):
        raise ValueError("New support ZIP must be outside the source checkout")
    originals = {}
    for name, row in rows.items():
        path = integrity.checked_file(source, name)
        data = path.read_bytes()
        bytes_checked(data, row)
        originals[name] = data
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
        for name, data in sorted(originals.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 10, 22, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            stream.writestr(entry, data, compresslevel=9)
    payload(root, archive)
    return summary(archive, rows, "PACKED_EXACT_PREDECESSOR")

def restore(root, archive):
    rows, files = payload(root, archive)
    root = no_links(root)
    destination = no_links(root / "website/.cache/w6-previous-dist")
    if destination.exists():
        raise ValueError("Predecessor destination must be new; previous data is never overwritten")
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        target = destination.joinpath(*name.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    for name, row in rows.items():
        bytes_checked(integrity.checked_file(destination, name).read_bytes(), row)
    return {**summary(archive, rows, "RESTORED_EXACT_PREDECESSOR"), "destination": str(destination)}

def summary(archive, rows, status):
    archive = Path(archive)
    return {"status": status, "predecessor_ui_build_id": PREVIOUS_ID,
            "baseline_sha256": BASELINE_SHA256, "files": len(rows),
            "file_bytes": sum(row["bytes"] for row in rows.values()),
            "archive_bytes": archive.stat().st_size, "archive_sha256": integrity.sha256(archive),
            "new_scientific_experiments": 0, "hosting_changed": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for command in ("pack", "verify", "restore"):
        p = subs.add_parser(command)
        p.add_argument("--root", type=Path, required=True)
        p.add_argument("--archive", type=Path, required=True)
        p.add_argument("--report", type=Path)
        if command == "pack":
            p.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "pack":
            result = pack(args.root, args.source, args.archive)
        elif args.command == "restore":
            result = restore(args.root, args.archive)
        else:
            rows, _ = payload(args.root, args.archive)
            result = summary(args.archive, rows, "VERIFIED_EXACT_PREDECESSOR")
        if args.report:
            report = no_links(args.report)
            if report.resolve().is_relative_to(args.root.resolve()):
                raise ValueError("Verification report must be outside the checkout")
            report.parent.mkdir(parents=True, exist_ok=True)
            with report.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2)
                stream.write("\n")
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
