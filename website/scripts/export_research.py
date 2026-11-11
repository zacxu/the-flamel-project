"""Create a content-addressed static bundle from the frozen, allowed study files.

Run from any directory using the existing analysis Python. No research writer,
model, optimizer or DFT dispatcher is imported by this export entry point.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from export_common import ExportContext, SCHEMA_VERSION, STUDY_ID, WEBSITE, json_bytes, sha_file
from export_content import export_content
from export_structures import export_structures
from export_tables import export_tables


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_exact(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError("Refusing to replace different immutable release bytes: " + str(path))
    else:
        path.write_bytes(content)


def main() -> None:
    ctx = ExportContext()
    export_tables(ctx)
    export_structures(ctx)
    export_content(ctx)

    # All dependency notices are text assets, never executable runtime tooling.
    notice = WEBSITE / "THIRD_PARTY_NOTICES.md"
    if not notice.is_file():
        raise ValueError("The reviewed third-party notice must exist before export")
    ctx.add_asset("notices/third-party.txt", notice.read_bytes())
    texts = []
    for path in sorted((WEBSITE / "licenses" / "dependencies").rglob("*")):
        if path.is_file():
            texts.append(("\n\n===== " + path.relative_to(WEBSITE / "licenses").as_posix()
                          + " =====\n").encode() + path.read_bytes())
    ctx.check(len(texts) > 0, "Dependency licence texts are present")
    ctx.add_asset("notices/dependency-licenses.txt", b"".join(texts))

    frozen = ctx.read_json("artifacts/phase6/numerical_freeze.json")
    ctx.add_json("provenance.json", {
        "sources": ctx.public_sources(),
        "studyFrozenAt": frozen["frozen_utc"],
        "sourceInventorySha256": ctx.inventory_sha256,
        "sourceIdentityMeaning": "Hashes bind saved evidence bytes; they do not imply scientific acceptance.",
        "units": {"energy": "eV/atom", "lattice": "angstrom", "force": "eV/angstrom",
                  "stress": "kbar", "cutoff": "Ry", "time": "seconds", "fraction": "0 to 1"},
        "newExperiments": 0,
        "scope": "Selected recorded research only. No complete oracle, evaluation-ID set, model binaries, credentials or local absolute paths.",
        "attributionDataset": "methods.json",
        "claimDataset": "claims.json",
    })
    ctx.verify_unchanged()

    contents = {name: (json_bytes(payload), "application/json") for name, payload in ctx.payloads.items()}
    contents.update({name: (data, "image/png" if name.endswith(".png") else "text/plain; charset=utf-8")
                     for name, data in ctx.assets.items()})
    for name, (content, media) in contents.items():
        if media == "application/json":
            ctx.check(len(content) < 500_000, "JSON shard below 500 kB: " + name, bytes=len(content))
    identities = [{"logicalName": name, "sha256": digest(content), "bytes": len(content)}
                  for name, (content, _) in sorted(contents.items())]
    release_id = "data-v1-" + digest(json_bytes({"schemaVersion": SCHEMA_VERSION,
                                             "studyId": STUDY_ID, "files": identities}))[:20]
    public = WEBSITE / "public" / "research"
    files = []
    for name, (content, media) in sorted(contents.items()):
        logical = Path(name)
        hashed_name = logical.stem + "." + digest(content)[:16] + logical.suffix
        relative = Path("releases") / release_id / logical.parent / hashed_name
        write_exact(public / relative, content)
        files.append({"logicalName": name, "path": relative.as_posix(), "sha256": digest(content),
                      "bytes": len(content), "mediaType": media})

    immutable = public / "releases" / release_id / "manifest.json"
    if immutable.exists():
        manifest = json.loads(immutable.read_text(encoding="utf-8"))
        ctx.check(manifest["files"] == files and manifest["sourceInventorySha256"] == ctx.inventory_sha256,
                  "An existing content release has identical provenance and files")
    else:
        manifest = {"schemaVersion": SCHEMA_VERSION, "studyId": STUDY_ID, "dataReleaseId": release_id,
                    "studyFrozenAt": frozen["frozen_utc"],
                    "generatedAt": datetime.now(timezone.utc).isoformat(),
                    "sourceInventorySha256": ctx.inventory_sha256, "files": files,
                    "uiBuildId": None,
                    "scope": "W1 data foundation; a UI build has a separate identity in W6."}
    manifest_bytes = json_bytes(manifest)
    write_exact(immutable, manifest_bytes)
    # Convenience discovery pointer. Application builds MUST use the immutable pin.
    (public / "manifest.json").write_bytes(manifest_bytes)
    pin = {"schemaVersion": SCHEMA_VERSION, "studyId": STUDY_ID, "dataReleaseId": release_id,
           "manifestPath": "research/" + immutable.relative_to(public).as_posix(),
           "manifestSha256": digest(manifest_bytes)}
    generated = "// Generated by scripts/export_research.py. Do not use the mutable discovery pointer.\n"
    generated += "export const DATA_RELEASE = " + json.dumps(pin, indent=2) + " as const;\n"
    (WEBSITE / "src" / "data").mkdir(parents=True, exist_ok=True)
    (WEBSITE / "src" / "data" / "release.ts").write_text(generated, encoding="utf-8")

    ctx.verify_unchanged()
    report = {"phase": "W1", "status": "passed", "generatedAt": datetime.now(timezone.utc).isoformat(),
              "schemaVersion": SCHEMA_VERSION, "studyId": STUDY_ID, "dataReleaseId": release_id,
              "manifestPath": str(immutable.relative_to(WEBSITE)), "manifestSha256": digest(manifest_bytes),
              "inventoryHashSha256": ctx.inventory_sha256,
              "inputAllowlist": ctx.inputs, "baseline": ctx.baseline,
              "counts": {"jsonDatasets": len(ctx.payloads), "assets": len(ctx.assets),
                         "sourceInputs": len(ctx.inputs), "checksPassed": len(ctx.checks)},
              "sizes": {"totalBytes": sum(row["bytes"] for row in files),
                        "largestJsonBytes": max(row["bytes"] for row in files if row["mediaType"] == "application/json"),
                        "imagesOver300kB": [row["logicalName"] for row in files
                                             if row["mediaType"] == "image/png" and row["bytes"] > 300_000]},
              "newExperiments": 0, "parentSourcesUnchanged": True,
              "licenceInputSha256": {str(p.relative_to(WEBSITE)): sha_file(p) for p in
                                      [notice, WEBSITE / "reports" / "W1_DEPENDENCY_LICENSES.json"]},
              "checks": ctx.checks}
    (WEBSITE / "reports").mkdir(exist_ok=True)
    (WEBSITE / "reports" / "W1_EXPORT.json").write_bytes(json_bytes(report))
    print(json.dumps({"status": "passed", "dataReleaseId": release_id, **report["counts"],
                      **report["sizes"], "parentSourcesUnchanged": True}, indent=2))


if __name__ == "__main__":
    main()
