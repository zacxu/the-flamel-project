"""Record Phase 5 MLIP handoff lineage and within-composition structure matches."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/phase5/chgnet"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    summary_path = OUT / "summary.json"
    summary = load(summary_path)
    matcher = StructureMatcher(ltol=.05, stol=.1, angle_tol=5, primitive_cell=True, scale=True, attempt_supercell=False)
    additions = []
    for entry in summary["results"]:
        selected, result = entry["selection"], entry["result"]
        parent_path = (ROOT / entry["result_path"]).parent / "parent_result.json"
        parent = load(parent_path)
        entry.update(candidate_id=selected["candidate_id"], role=selected["category"],
                     control=selected.get("control"), arm=selected.get("arm"), cached=selected["cached"],
                     source_path=selected["source_structure"], source_sha256=selected["source_structure_sha256"],
                     parent_result_path=parent_path.relative_to(ROOT).as_posix(), parent_result_sha256=sha(parent_path),
                     converged=result["converged"], final_filter_fmax_eV_A=result["final_filter_fmax_eV_A"],
                     energy_eV_per_atom=result["energy_eV_per_atom"], final_spacegroup=result["final_spacegroup"],
                     DFT_dispatch_authorized=False)
        additions.append({"check": selected["candidate_id"] + ":parent_result_identity", "passed": parent["result"] == result})
        additions.append({"check": selected["candidate_id"] + ":no_new_DFT_authorization", "passed": entry["DFT_dispatch_authorized"] is False})
    references = [r for r in summary["results"] if r["role"] == "same_composition_reference"]
    reference_comparisons = []
    for entry in [r for r in summary["results"] if r["role"] == "symmetry"]:
        structure = Structure.from_dict(load(ROOT / entry["result"]["final_structure"]))
        for reference in references:
            other = Structure.from_dict(load(ROOT / reference["result"]["final_structure"]))
            if structure.composition.reduced_composition != other.composition.reduced_composition:
                continue
            reference_comparisons.append({"candidate_id": entry["candidate_id"], "reference_id": reference["candidate_id"],
                                          "reference_phase": reference["selection"]["reference_phase"],
                                          "reduced_formula": structure.composition.reduced_formula,
                                          "candidate_minus_reference_eV_atom": entry["energy_eV_per_atom"] - reference["energy_eV_per_atom"],
                                          "relaxed_structures_match": bool(matcher.fit(structure, other)),
                                          "scope": "Within-composition CHGNet energies and tolerant structure matching, not DFT stability"})
    summary["within_composition_reference_comparisons"] = reference_comparisons
    summary["category_summary"] = {
        role: {"selections": sum(r["role"] == role for r in summary["results"]),
               "new_launches": sum(r["role"] == role and not r["cached"] for r in summary["results"]),
               "cached_reuses": sum(r["role"] == role and r["cached"] for r in summary["results"]),
               "converged": sum(r["role"] == role and r["converged"] for r in summary["results"])}
        for role in ["symmetry", "prototype", "same_composition_reference"]}
    summary["handoff_schema_annotation"] = {"created_utc": datetime.now(timezone.utc).isoformat(),
                                             "script": Path(__file__).relative_to(ROOT).as_posix(),
                                             "script_sha256": sha(Path(__file__)),
                                             "new_model_inferences": 0, "new_relaxations": 0}
    dump(summary_path, summary)
    audit_path = OUT / "audit.json"
    audit = load(audit_path)
    check_names = {r["check"] for r in audit["checks"]}
    audit["checks"].extend(r for r in additions if r["check"] not in check_names)
    audit["checks_count"] = len(audit["checks"])
    audit["failures"] = [r for r in audit["checks"] if not r["passed"]]
    audit["status"] = "passed" if not audit["failures"] else "failed"
    audit["handoff_schema_annotation"] = summary["handoff_schema_annotation"]
    dump(audit_path, audit)
    print(json.dumps({"status": audit["status"], "checks": audit["checks_count"],
                      "category_summary": summary["category_summary"], "within_composition_comparisons": len(reference_comparisons)}))
    if audit["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
