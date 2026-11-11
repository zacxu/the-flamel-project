"""Download, verify, and stage the bounded Phase 1 QE lane in this workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "quantum_espresso"
PSEUDOS = ROOT / "data" / "pseudopotentials"
ART = ROOT / "artifacts" / "phase1" / "qe"
QE_HASH = "e50ec7368a5b7a964eb5084e0a13464ba2628d4e147c16227e876002ea34fdf7"
QE_URL = "https://github.com/QMatSuite/quantum-espresso-windows-exe/releases/download/qe-7.5-win-oneapi-msmpi/qe-7.5-win-oneapi-msmpi.zip"
SSSP_BASE = "https://archive.materialscloud.org/records/rcyfm-68h65/files/"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url, target, expected_hash=None, algorithm="sha256"):
    target.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    if not target.exists() or (expected_hash and digest(target, algorithm) != expected_hash):
        partial = target.with_suffix(target.suffix + ".partial")
        request = urllib.request.Request(url, headers={"User-Agent": "bears-research-phase1"})
        with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as output:
            for block in iter(lambda: response.read(1024 * 1024), b""):
                output.write(block)
        partial.replace(target)
    actual = digest(target, algorithm)
    if expected_hash and actual != expected_hash:
        raise RuntimeError(f"Checksum mismatch for {target.name}: {actual}")
    record = {"source": url, "path": str(target.relative_to(ROOT)), "bytes": target.stat().st_size,
              "sha256": digest(target), "verified_algorithm": algorithm if expected_hash else None,
              "expected_digest": expected_hash, "observed_digest": actual,
              "checked_at_utc": now(), "setup_elapsed_seconds": time.perf_counter() - started}
    print(json.dumps(record), flush=True)
    return record


def setup_qe():
    VENDOR.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    archive = VENDOR / "qe-7.5-win-oneapi-msmpi.zip"
    record = download(QE_URL, archive, QE_HASH)
    extracted = VENDOR / "qe-7.5-win-oneapi-msmpi"
    extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            resolved = (extracted / member.filename).resolve()
            if not resolved.is_relative_to(extracted.resolve()):
                raise RuntimeError("Unsafe zip member")
        bundle.extractall(extracted)
    files = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
              "sha256": digest(path)}
             for path in sorted(extracted.rglob("*")) if path.is_file()]
    manifest = {"setup_at_utc": now(), "distribution": "QMatSuite third-party QE 7.5 Windows build",
                "upstream_release": "qe-7.5-win-oneapi-msmpi", "archive": record, "files": files,
                "executables": [row for row in files if Path(row["path"]).name.lower() == "pw.exe"]}
    (ART / "qe_distribution_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"qe_staged": True, "file_count": len(files), "executables": manifest["executables"]}), flush=True)


def setup_pseudos():
    PSEUDOS.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    version = "SSSP_1.3.0_PBE_efficiency"
    query = "?download=1&phase1_nonce=" + str(time.time_ns())
    metadata_path = PSEUDOS / (version + ".json")
    meta_record = download(SSSP_BASE + version + ".json" + query, metadata_path,
                           "3153c4b20fc90a44fba0236627525644", "md5")
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    chosen = {element: data[element] for element in ("Mg", "O")}
    print(json.dumps({"chosen_metadata": chosen}), flush=True)
    archive = PSEUDOS / (version + ".tar.gz")
    archive_record = download(SSSP_BASE + version + ".tar.gz" + query, archive,
                              "a58f1b3373f330179fd0832c48bb9a52", "md5")
    records = []
    with tarfile.open(archive, "r:gz") as bundle:
        for element, info in chosen.items():
            name = info["filename"]
            matched = [member for member in bundle.getmembers() if Path(member.name).name == name]
            if len(matched) != 1 or not matched[0].isfile():
                raise RuntimeError(f"Cannot find unique pseudopotential: {name}")
            target = PSEUDOS / name
            stream = bundle.extractfile(matched[0])
            if stream is None:
                raise RuntimeError(f"Missing stream: {name}")
            target.write_bytes(stream.read())
            actual_md5 = digest(target, "md5")
            expected = info.get("md5")
            if expected and actual_md5 != expected:
                raise RuntimeError(f"Pseudopotential MD5 mismatch: {name}")
            records.append({"element": element, "filename": name,
                            "path": str(target.relative_to(ROOT)), "bytes": target.stat().st_size,
                            "sha256": digest(target), "md5": actual_md5, "sssp_metadata": info})
    manifest = {"setup_at_utc": now(), "library": version,
                "official_record": "https://archive.materialscloud.org/record/2023.65",
                "metadata_archive": meta_record, "pseudopotential_archive": archive_record,
                "pseudopotentials": records}
    (ART / "pseudopotential_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"pseudopotentials_staged": records}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("component", choices=("qe", "pseudos"))
    args = parser.parse_args()
    {"qe": setup_qe, "pseudos": setup_pseudos}[args.component]()
