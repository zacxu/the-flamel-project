"""Annotate legacy CHGNet worker fields without changing frozen numerics or queues."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase5/chgnet"


def annotate():
    path = OUT / "summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("scope_annotation"):
        print("Existing CHGNet scope annotation preserved")
        return
    archived = OUT / "summary_before_scope_annotation.json"
    if archived.exists():
        raise RuntimeError("Prior annotation archive exists; inspect before replacing evidence")
    shutil.copyfile(path, archived)
    summary["scope_annotation"] = {
        "annotated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "scripts/phase5_chgnet_scope.py",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "pre_annotation_summary": archived.relative_to(ROOT).as_posix(),
        "pre_annotation_summary_sha256": hashlib.sha256(archived.read_bytes()).hexdigest(),
        "reason": "Unchanged Phase 3 worker retains DFT_eligible as a geometry/workload result. It confers no Phase 5 DFT queue admission.",
        "new_numerical_jobs": 0,
        "changes_to_frozen_experimental_selection": 0,
    }
    summary["new_DFT_dispatches_authorized_by_CHGNet_results"] = 0
    summary["original_transformer_DFT_shortlist"] = []
    summary["DFT_queue_policy"] = "Preserve the frozen empty transformer primary shortlist and the previously selected known-MgO fallback. Symmetry, prototype and reference MLIP results do not authorize additional candidate DFT."
    for entry in summary["results"]:
        entry["DFT_dispatch_authorized"] = False
        entry["raw_worker_DFT_eligible_interpretation"] = "Geometry/workload gates only; not a stability label or queue selection"
        entry["previously_dispatched_known_MgO_control"] = bool(entry["selection"]["cached"])
        entry["experiment_role"] = {
            "symmetry": "Descriptive matched within-composition symmetry comparison",
            "prototype": "Predeclared deterministic prototype-substitution baseline, separate from transformer outputs",
            "same_composition_reference": "Known same-composition MLIP reference",
        }[entry["selection"]["category"]]
    path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"annotated": path.relative_to(ROOT).as_posix(), "new_DFT_queue_admissions": 0}))


if __name__ == "__main__":
    annotate()
