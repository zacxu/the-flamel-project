"""Fetch and verify pinned Phase 1 generator assets, without model execution.

Run from any directory with Python 3.11+. Existing verified assets are reused.
Changed archives, checkpoints, or original vendor files cause an error rather
than being overwritten. Extra vendor files produced by packaging are retained.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "31bb734a3fd006af49a021921839061e6184cbf1"
CHECKPOINT_REVISION = "b203f4273158d95b49b60a13433bf1dcc4ccf5d9"
ARCHIVE = ROOT / "vendor/CrystalFormer-31bb734a.tar.gz"
VENDOR = ROOT / "vendor/CrystalFormer"
CHECKPOINT = ROOT / "checkpoints/epoch_044000.pkl"
ARCHIVE_SHA = "1f440e96fd598139067c9d7eb2c4cbd8204a9bf79505e4fcdabe8dc2b372e975"
CHECKPOINT_SHA = "847e8f3962226d0539722c851bd615479d9c7fc2d5be9112898c1cdd2b7b700a"


def safe_path(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise RuntimeError(f"Path leaves this workspace: {path}")
    # Reject links even when they currently resolve inside the workspace.
    for candidate in (path, *path.parents):
        if candidate == ROOT:
            break
        if candidate.is_symlink():
            raise RuntimeError(f"Refusing symbolic-link path: {candidate}")
    return path


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url: str, destination: Path, expected_sha: str) -> str:
    safe_path(destination)
    if destination.exists():
        if not destination.is_file() or digest_file(destination) != expected_sha:
            raise RuntimeError(f"Existing asset differs; refusing overwrite: {destination}")
        return "reused_verified"
    safe_path(destination.parent).mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=destination.name + ".", suffix=".download",
                                         dir=destination.parent, delete=False) as output:
            temporary = Path(output.name)
            request = urllib.request.Request(url, headers={"User-Agent": "bears-phase1-setup/1"})
            with urllib.request.urlopen(request, timeout=60) as response:
                shutil.copyfileobj(response, output, length=1024 * 1024)
        if digest_file(temporary) != expected_sha:
            raise RuntimeError(f"Downloaded SHA256 mismatch: {url}")
        # Windows rename refuses an existing destination, preserving concurrent assets.
        if destination.exists():
            if digest_file(destination) != expected_sha:
                raise RuntimeError(f"Asset changed during download: {destination}")
            temporary.unlink()
            return "reused_concurrent_verified"
        temporary.rename(destination)
        return "downloaded_verified"
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def extract_verified_source() -> dict:
    safe_path(VENDOR)
    prefix = f"CrystalFormer-{SOURCE_REVISION}"
    entries = []
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        seen = set()
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            if (name.is_absolute() or ".." in name.parts or "\\" in member.name
                    or not name.parts or name.parts[0] != prefix):
                raise RuntimeError(f"Unsafe archive path: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise RuntimeError(f"Unsupported archive entry: {member.name}")
            relative = Path(*name.parts[1:])
            destination = safe_path(VENDOR / relative)
            if member.isdir():
                if destination.exists() and not destination.is_dir():
                    raise RuntimeError(f"Expected a directory: {destination}")
                continue
            if not name.parts[1:] or relative in seen:
                raise RuntimeError(f"Duplicate/empty archive entry: {member.name}")
            seen.add(relative)
            with archive.extractfile(member) as stream:
                expected = hashlib.file_digest(stream, "sha256").hexdigest()
            if destination.exists():
                if not destination.is_file() or digest_file(destination) != expected:
                    raise RuntimeError(f"Vendor source changed; refusing overwrite: {destination}")
            entries.append((member, destination, expected))
        # All original files are checked before any missing vendor file is written.
        written = 0
        for member, destination, expected in entries:
            if destination.exists():
                continue
            safe_path(destination.parent).mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, destination.open("xb") as output:
                shutil.copyfileobj(source, output)
            if digest_file(destination) != expected:
                raise RuntimeError(f"Extracted source hash mismatch: {destination}")
            written += 1
    return {"original_files_verified": len(entries), "missing_files_created": written}


def main():
    source = fetch(
        f"https://codeload.github.com/deepmodeling/CrystalFormer/tar.gz/{SOURCE_REVISION}",
        ARCHIVE, ARCHIVE_SHA)
    extraction = extract_verified_source()
    checkpoint = fetch(
        "https://huggingface.co/zdcao/CrystalFormer/resolve/"
        f"{CHECKPOINT_REVISION}/alex20s/multi/epoch_044000.pkl",
        CHECKPOINT, CHECKPOINT_SHA)
    print(json.dumps({"source_archive": source, "source_revision": SOURCE_REVISION,
                      "archive_sha256": ARCHIVE_SHA, **extraction,
                      "checkpoint": checkpoint, "checkpoint_sha256": CHECKPOINT_SHA,
                      "checkpoint_bytes": CHECKPOINT.stat().st_size,
                      "model_samples_generated": 0}, indent=2))


if __name__ == "__main__":
    main()
