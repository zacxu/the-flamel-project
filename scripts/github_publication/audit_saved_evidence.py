"""Verify frozen scientific inputs and browser payloads without executing research."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import re
import stat

EXPORT_RECORD_SHA256 = "a65fa0195bac44436581085025eaf697a20d35cb6a94ab791997cbadcaee34d6"
ROOT = pathlib.Path(__file__).resolve().parents[2]

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result

def no_reparse_existing_ancestors(path):
    for parent in (path, *path.parents):
        if parent.exists():
            info = parent.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("Report ancestor is a reparse point")

def safe_file(root, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative or any(ord(c) < 32 for c in relative):
        raise ValueError("Unsafe relative path")
    parts = relative.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError("Unsafe relative path")
    for parent in (root, *root.parents):
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Reparse point")
    path = root
    for part in parts:
        path = path / part
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Reparse point")
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Expected contained regular file")
    return path

def read(root, relative):
    return json.loads(safe_file(root, relative).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs)

def require(condition, message):
    if not condition:
        raise ValueError(message)

def match(root, relative, digest, size=None):
    require(isinstance(digest, str) and bool(re.fullmatch("[0-9a-f]{64}", digest)), "Invalid SHA256")
    path = safe_file(root, relative)
    require(size is None or path.stat().st_size == size, "Byte length mismatch: " + relative)
    require(sha(path) == digest, "Checksum mismatch: " + relative)

def audit(root):
    root = root.absolute()
    record = "website/reports/W1_EXPORT.json"
    match(root, record, EXPORT_RECORD_SHA256)
    export = read(root, record)
    require(export["status"] == "passed" and export["newExperiments"] == 0
            and export["parentSourcesUnchanged"] is True, "Export record is not accepted")
    for relative, digest in export["baseline"].items():
        match(root, relative, digest)
    inputs = export["inputAllowlist"]
    require(len(inputs) == export["counts"]["sourceInputs"], "Input count mismatch")
    for relative, row in inputs.items():
        require(row["path"] == relative, "Input key/path mismatch")
        match(root, relative, row["sha256"], row["bytes"])
    manifest_name = "website/" + export["manifestPath"].replace("\\", "/")
    match(root, manifest_name, export["manifestSha256"])
    match(root, "website/public/research/manifest.json", export["manifestSha256"])
    manifest = read(root, manifest_name)
    require(manifest["dataReleaseId"] == export["dataReleaseId"]
            and manifest["sourceInventorySha256"] == export["inventoryHashSha256"], "Release identity mismatch")
    names = set()
    for row in manifest["files"]:
        relative = row["path"]
        require(relative.startswith("releases/" + export["dataReleaseId"] + "/"), "Payload outside recorded release")
        require(relative.casefold() not in names, "Duplicate/colliding payload")
        names.add(relative.casefold())
        match(root, "website/public/research/" + relative, row["sha256"], row["bytes"])
    require(len(names) == export["counts"]["assets"] + export["counts"]["jsonDatasets"], "Payload count mismatch")
    # The frozen manifest authenticates the saved historical audit; do not re-run its finalizer.
    historical = read(root, "artifacts/phase6/manifest.json")
    rows = {row["path"]: row for row in historical["files"]}
    for relative in ("artifacts/phase6/audit.json", "artifacts/phase6/readiness.json"):
        row = rows[relative]
        match(root, relative, row["sha256"], row["bytes"])
    saved_audit = read(root, "artifacts/phase6/audit.json")
    require(saved_audit["status"] == "passed" and not saved_audit["failed_checks"]
            and saved_audit["checks_passed"] == saved_audit["checks_total"] == len(saved_audit["checks"])
            and all(item["passed"] for item in saved_audit["checks"]), "Historical audit is not complete")
    freeze = read(root, "artifacts/phase6/numerical_freeze.json")
    require(freeze["status"] == "frozen" and freeze["new_phase6_experiments"] == 0
            and freeze["canonical_budget_writes"] == 0, "Numerical freeze changed")
    match(root, "artifacts/budget_ledger.json", freeze["budget_ledger_sha256"])
    match(root, "artifacts/runtime_budget_events.jsonl", freeze["runtime_events_sha256"])
    budget = read(root, "artifacts/budget_ledger.json")
    require(budget == freeze["budget_ledger"], "Frozen budget content differs")
    require(all(not budget[lane]["active_reservations"] for lane in ("generation", "chgnet", "qe")), "Active reservation")
    ready = read(root, "artifacts/phase6/readiness.json")
    require(ready["numerical_evidence_frozen"] is True
            and ready["new_stable_material_established"] is False
            and ready["complete_hull_established"] is False, "Frozen scientific scope differs")
    return {"result": "PASS", "mode": "read-only-saved-evidence-integrity",
            "source_inputs_verified": len(inputs), "baseline_hashes_verified": len(export["baseline"]),
            "public_payloads_verified": len(names), "historical_audit_checks_recorded": saved_audit["checks_total"],
            "historical_checks_reexecuted": False, "new_experiments": 0, "models_deserialized": 0,
            "data_release": export["dataReleaseId"],
            "scope": "Authenticates retained inputs, public payloads, saved audit and numerical freeze. Does not recompute metrics, repeat experiments, establish model validity or inspect private scratch history."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--report", type=pathlib.Path, help="Optional new report outside the project")
    args = parser.parse_args()
    try:
        root = args.root.absolute()
        if args.report:
            destination = args.report.absolute()
            no_reparse_existing_ancestors(destination.parent)
            safe_file(destination.parent, destination.name) if destination.exists() else None
            require(not destination.exists() and not destination.resolve().is_relative_to(root.resolve()),
                    "Report must be new and outside the project")
        result = audit(root)
        if args.report:
            with args.report.open("x", encoding="utf-8") as report:
                report.write(json.dumps(result, indent=2) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"result": "FAIL", "error_type": type(error).__name__, "detail": str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
