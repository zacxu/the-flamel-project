"""Re-audit completed QE artifacts without dispatching jobs or rewriting geometry."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from phase3_qe_parser import parse_job

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "phase3" / "qe"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    checks = []
    for path in sorted(ART.glob("*/result.json")):
        original = json.loads(path.read_text())
        stage = original["provenance"]
        directory = path.parent
        actual = parse_job(directory, stage["settings"], return_code=original["return_code"],
                           timed_out=original["timed_out"], write_geometry=False)
        hashes = {"input": digest(directory / "pw.in") == stage["input_sha256"],
                  "source_geometry": digest(ROOT / stage["source_geometry"]) == stage["source_geometry_sha256"],
                  "executable": digest(Path(stage["executable"])) == stage["executable_sha256"],
                  "settings": digest(directory / "settings.json") == stage["settings_sha256"],
                  "output": digest(directory / "pw.out") == original["output_sha256"]}
        for element, filename in stage["pseudo_files"].items():
            hashes["pseudo_" + element] = digest(directory / "pseudo" / filename) == stage["pseudo_hashes"][element]
        if stage["selection_manifest"]:
            hashes["frozen_selection"] = digest(ROOT / stage["selection_manifest"]) == stage["selection_manifest_sha256"]
        checks.append({"job_id": original["job_id"], "elapsed_wall_seconds": original["elapsed_wall_seconds"],
                       "peak_working_set_bytes_observed": original["peak_working_set_bytes_observed"],
                       "hash_checks": hashes, "all_hash_checks_pass": all(hashes.values()),
                       "current_parser_result": actual, "settings": stage["settings"]})
    ledger = ROOT / "artifacts" / "phase1" / "qe" / "qe_jobs.jsonl"
    legacy = [json.loads(line) for line in ledger.read_text().splitlines()]
    canonical = json.loads((ROOT / "artifacts" / "budget_ledger.json").read_text())
    legacy_seconds = sum(row["elapsed_wall_seconds"] for row in legacy)
    audit = {"parser_sha256": digest(ROOT / "scripts" / "phase3_qe_parser.py"),
             "jobs": checks, "all_job_hash_checks_pass": all(row["all_hash_checks_pass"] for row in checks),
             "legacy_QE_job_count": len(legacy), "legacy_QE_wall_seconds": legacy_seconds,
             "canonical_QE_snapshot": canonical["qe"],
             "completed_budget_totals_match": abs(legacy_seconds - canonical["qe"]["charged_wall_seconds"]) < 1e-6,
             "scope": "SCF/ionic/force/stress and provenance audit; no cutoff/k convergence or stability inferred merely from a completed job"}
    (ART / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    summary = {"completed_phase3_jobs": len(checks), "hashes_pass": audit["all_job_hash_checks_pass"],
               "budget_totals_match": audit["completed_budget_totals_match"],
               "QE_charged_wall_seconds": legacy_seconds,
               "active_QE": canonical["qe"]["active_reservations"]}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
