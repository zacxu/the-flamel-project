"""Compare every staged/committed blob with the exact publication path set and source bytes."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

spec = importlib.util.spec_from_file_location("phase5_integrity", Path(__file__).with_name("verify_phase3.py"))
integrity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integrity)

def git(root, *arguments):
    environment = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    run = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, env=environment)
    if run.returncode:
        raise ValueError("Read-only Git command failed: " + arguments[0])
    return run.stdout

def entries(root, index):
    raw = git(root, "ls-files", "--stage", "-z") if index else git(root, "ls-tree", "-r", "-z", "--full-tree", "HEAD")
    result, seen = {}, set()
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, name = item.split(b"\t", 1)
        fields = metadata.decode("ascii").split()
        if index:
            mode, oid, stage = fields
            if stage != "0":
                raise ValueError("Unmerged index entry")
        else:
            mode, kind, oid = fields
            if kind != "blob":
                raise ValueError("Submodule/non-blob entry")
        path = name.decode("utf-8")
        integrity.checked_name(path)
        if mode not in ("100644", "100755") or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid):
            raise ValueError("Nonregular Git entry")
        if path.casefold() in seen:
            raise ValueError("Duplicate/case-colliding Git path")
        seen.add(path.casefold())
        result[path] = (mode, oid)
    return result

def blob_hashes(root, oids):
    process = subprocess.Popen(["git", "-C", str(root), "cat-file", "--batch"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = {}
    try:
        for oid in dict.fromkeys(oids):
            process.stdin.write((oid + "\n").encode("ascii"))
            process.stdin.flush()
            header = process.stdout.readline(1024).decode("ascii").strip().split()
            if len(header) != 3 or header[0] != oid or header[1] != "blob":
                raise ValueError("Missing/non-blob Git object")
            remaining = size = int(header[2])
            if not 0 <= size <= integrity.MAX_GIT_BYTES:
                raise ValueError("Git blob exceeds publication limit")
            digest = hashlib.sha256()
            while remaining:
                block = process.stdout.read(min(1024 * 1024, remaining))
                if not block:
                    raise ValueError("Truncated Git object")
                digest.update(block)
                remaining -= len(block)
            if process.stdout.read(1) != b"\n":
                raise ValueError("Invalid Git object framing")
            result[oid] = (size, digest.hexdigest())
        process.stdin.close()
        if process.wait(timeout=15):
            raise ValueError("Git object reader failed")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()
    return result

def verify_git_bytes(root, selected, *, index=False, require_clean=False):
    selected = integrity.checked_names(list(selected), "Expected Git paths", secrets=True)
    actual = entries(root, index)
    if set(actual) != set(selected):
        raise ValueError("Git path set differs from the exact publication allowlist")
    # Keep the per-path text attribute check independent of core.autocrlf.
    raw = subprocess.run(["git", "-C", str(root), "check-attr", "--stdin", "-z", "text"],
                         input=b"".join(p.encode("utf-8") + b"\0" for p in selected), capture_output=True)
    if raw.returncode:
        raise ValueError("Git attributes unavailable")
    fields = raw.stdout.split(b"\0")
    if len(fields) != 3 * len(selected) + 1 or any(fields[i + 2] != b"unset" for i in range(0, len(fields) - 1, 3)):
        raise ValueError("Every publication input must have text unset")
    objects = blob_hashes(root, [row[1] for row in actual.values()])
    total = 0
    for name in selected:
        path = integrity.checked_file(root, name)
        size, digest = objects[actual[name][1]]
        if path.stat().st_size != size or integrity.sha256(path) != digest:
            raise ValueError("Git/source bytes differ: " + name)
        total += size
    if require_clean and git(root, "status", "--porcelain=v1", "-z", "--untracked-files=normal"):
        raise ValueError("Working tree/index contains unpublished changes")
    return {"passed": True, "git_scope": "index" if index else "HEAD", "paths_verified": len(selected),
            "unique_blobs_verified": len(objects), "source_bytes_verified": total,
            "require_clean": require_clean, "source_mutations": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--seal", type=Path)
    parser.add_argument("--seal-sha256")
    args = parser.parse_args()
    try:
        root = args.root.absolute()
        overlay = integrity.verify(root, args.seal, args.seal_sha256, metadata_dir="publication/phase5")
        selected = integrity.checked_file(root, "publication/git-files.txt").read_text(encoding="utf-8").splitlines()
        result = verify_git_bytes(root, selected, index=args.index, require_clean=args.require_clean)
        result["overlay_mode"] = overlay["mode"]
        result["controls_unsealed_without_external_seal"] = overlay["controls_unsealed"]
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
