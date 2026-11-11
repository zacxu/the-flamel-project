"""Audit frozen Phase 2 artifacts without fitting, querying, sampling or relaxing."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np

OUT = ROOT / "artifacts/phase2"
CHECKS = []


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8-sig"))


def rows(relative):
    with (ROOT / relative).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(condition, description):
    CHECKS.append({"passed": bool(condition), "check": description})


def file_check(item):
    path = ROOT / item["path"]
    check(path.is_file() and sha(path) == item["sha256"], f"Hash: {item['path']}")


def signature(counts):
    return tuple(sorted((str(k), int(v)) for k, v in counts.items()))


def main():
    created = datetime.now(timezone.utc).isoformat()
    phase1 = load("artifacts/phase1/readiness.json")
    check(phase1["status"] == "complete", "Phase 1 prerequisites complete")
    population = rows("artifacts/phase1/data/eligible_population.csv")
    population_by_id = {row["material_id"]: row for row in population}
    feature_manifest = load("artifacts/phase2/features/feature_manifest.json")
    for item in feature_manifest["outputs"].values():
        file_check(item)
    file_check({"path": "research_features.py", "sha256": feature_manifest["implementation"]["module_sha256"]})
    for item in feature_manifest["input_sources"].values():
        file_check(item)
    with np.load(OUT / "features/features.npz", allow_pickle=False) as archive:
        X, ids, names = archive["X"], archive["material_ids"].astype(str), archive["feature_names"].astype(str)
        check(set(archive.files) == {"X", "material_ids", "feature_names"}, "Feature archive contains descriptors/IDs/schema only, without target labels")
    check(X.shape == (8294, 408) and X.dtype == np.float32 and np.isfinite(X).all(), "All 8294x408 descriptors are finite float32")
    check(set(ids) == set(population_by_id) and len(set(ids)) == 8294, "Feature IDs exactly cover the eligible population")
    from research_features import FEATURE_NAMES
    check(list(names) == list(FEATURE_NAMES), "Archive feature order matches the shared descriptor implementation")
    check(not feature_manifest["summary_csv_read"] and feature_manifest["structural_failures"] == 0 and feature_manifest["symmetry_fallback_rows"] == 0, "Features use initial geometry, without summary CSV or dropped/fallback rows")
    feature_tests = load("artifacts/phase2/features/validation_report.json")
    check(feature_tests["passed"], "Feature invariance, initial-only lineage and shared-function checks pass")
    split_manifest = load("artifacts/phase2/splits/manifest.json")
    for item in split_manifest["files"]:
        file_check(item)
    reservations = load("artifacts/phase2/splits/reserved_systems.json")
    reserve = set(reservations["chemical_systems"])
    check(len(reserve) == 78 and reservations["eligible_reserved_rows"] == 476 and reservations["available_rows"] == 7818, "All palette systems reserved; exactly 476 eligible rows excluded")
    for seed in split_manifest["seeds"]:
        split = load(f"artifacts/phase2/splits/seed_{seed}.json")
        subsets = split["material_ids"]
        check([len(subsets[k]) for k in ["train", "calibration", "pool", "unused", "fresh_reserved"]] == [2000, 400, 2000, 3418, 476], f"Exact split/evaluation/reserve sizes for seed {seed}")
        all_ids = [mid for values in subsets.values() for mid in values]
        check(len(all_ids) == len(set(all_ids)) == 8294 and set(all_ids) == set(ids), f"Every eligible ID assigned once for seed {seed}")
        group_sets = {part: {population_by_id[mid]["chemical_system"] for mid in mids} for part, mids in subsets.items()}
        check(all(not group_sets[a] & group_sets[b] for a, b in itertools.combinations(group_sets, 2)), f"Complete chemical systems stay disjoint for seed {seed}")
        check(not set.union(*(group_sets[k] for k in ["train", "calibration", "pool", "unused"])) & reserve, f"No reserved chemistry in any predictor partition for seed {seed}")
        training_elements = set.union(*(set(g.split("-")) for g in group_sets["train"]))
        evaluation_elements = set.union(*(set(g.split("-")) for g in group_sets["pool"] | group_sets["unused"]))
        check(evaluation_elements <= training_elements and len(training_elements) == 68, f"Held-out combinations use individually seen elements for seed {seed}")
    oracle = {r["material_id"]: float(r["e_above_hull_mp2020_corrected_ppd_mp"]) for r in rows("artifacts/phase2/splits/oracle_labels.csv")}
    original_labels = {}
    with gzip.open(ROOT / "data/wbm/2023-12-13-wbm-summary.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["material_id"] in population_by_id:
                original_labels[row["material_id"]] = float(row["e_above_hull_mp2020_corrected_ppd_mp"])
    check(oracle == original_labels and len(oracle) == 8294 and np.isfinite(list(oracle.values())).all(), "Separate oracle exactly preserves all signed original labels and ID joins")
    protocol = load("config/phase2_protocol.json")
    protocol_manifest = load("artifacts/phase2/protocol/manifest.json")
    file_check(protocol_manifest["protocol"])
    file_check(protocol_manifest["acquisition_module"])
    check(protocol["population"]["fixed_untouched_evaluation"] == 3418 and protocol["population"]["evaluation_partition_key_in_split_files"] == "unused", "Predictor metrics use a fixed untouched evaluation cohort")
    check(protocol["fresh_selector_seed"] == split_manifest["fresh_selector_seed"] == 20261022, "Fresh selector seed fixed before replay")
    check(protocol["calibration"]["rank_for_400"] == 361 and protocol["calibration"]["uncertainty_floor_eV_atom"] == .01, "Uncertainty calibration rank and floor predeclared")
    check(load("artifacts/phase2/protocol/synthetic_checks.json")["status"] == "passed", "Five-policy selection and calibration synthetic checks passed")
    catalogs = load("artifacts/phase2/catalogs/catalog_manifest.json")
    for item in catalogs["files"].values():
        file_check(item)
    sets = {}
    for name in ["mp", "wbm"]:
        path = ROOT / f"data/catalogs/{name}_full_compositions.jsonl"
        with path.open(encoding="utf-8") as stream:
            values = [json.loads(line) for line in stream]
        sets[name] = {signature(row["counts"]) for row in values}
        check(len(values) == catalogs[f"{name}_rows"] and len(sets[name]) == catalogs[f"{name}_unique_compositions"], f"Full {name} composition catalog coverage reproduced")
    catalog_union = sets["mp"] | sets["wbm"]
    selected = load("artifacts/phase2/compositions/selection.json")
    with (OUT / "compositions/enumerated_and_screened.jsonl").open(encoding="utf-8") as stream:
        enumeration = [json.loads(line) for line in stream]
    check(len(enumeration) == len({signature(r["counts"]) for r in enumeration}) == 1372, "1372 distinct reduced formulas enumerated")
    check(all(sum(r["counts"].values()) <= 20 and all(sum(r["counts"][e] * oxidation for e, oxidation in witness.items()) == 0 for witness in r["oxidation_state_witnesses"]) for r in enumeration), "All formulas fit 20 atoms and supplied charge-balance witnesses")
    check(all((signature(r["counts"]) in sets["mp"]) == r["present_in_mp_snapshot"] and (signature(r["counts"]) in sets["wbm"]) == r["present_in_full_wbm"] for r in enumeration), "All 1372 composition presence/absence flags independently reproduced")
    check(sum(signature(r["counts"]) not in catalog_union for r in enumeration) == selected["new_to_both_count"] == 1135, "1135 formulas absent from both complete checked snapshots")
    proposals = selected["selected"]
    all_prospective = proposals + selected["reserves"] + selected["stretch"]
    check(len(proposals) == 6 and all(r["chemical_system"] in reserve and signature(r["counts"]) not in catalog_union for r in all_prospective), "Six selected formulas and every reserve/stretch are catalog-absent and pre-reserved")
    check(len({r["chemical_system"] for r in proposals}) == 6, "Default proposals cover six distinct chemical systems")
    controls = load("artifacts/phase2/controls/matched_protocol.json")
    check([(c["evaluated_formula"], c["nontrivial_spacegroup"], c["evaluated_n_atoms"]) for c in controls["controls"]] == [("Mg4O4", 225, 8), ("Ti2O4", 136, 6)], "Matched controls frozen with exact evaluated cells")
    check(controls["seed"] == 20261022 and controls["temperature"] == controls["top_p"] == 1.0 and controls["primary_attempts_per_arm_per_formula"] == 8, "Control sampling matches the Phase 1 production pilot")
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    for control in controls["controls"]:
        geometry = Structure.from_dict(load(control["reference_json"]))
        check(len(geometry) == control["evaluated_n_atoms"] and SpacegroupAnalyzer(geometry, symprec=.01, angle_tolerance=5).get_space_group_number() == control["nontrivial_spacegroup"], f"Catalog control geometry/group verified: {control['label']}")
    generation_protocol = load("artifacts/phase2/compositions/generation_protocol.json")
    check(bool(generation_protocol), "New-formula exact cells, compatible group and seed protocol frozen")
    witness_checks = []
    for formula in generation_protocol["formulas"]:
        counts = {}
        for site in formula["count_compatibility_witness"]:
            counts[site["element"]] = counts.get(site["element"], 0) + site["multiplicity"]
        witness_checks.append(counts == formula["exact_expanded_counts"] and formula["spacegroup"] == 2 and sum(counts.values()) <= 20)
    check(len(witness_checks) == 14 and all(witness_checks), "All 14 selected/reserve formula cells have explicit SG2 count witnesses")
    catalog_audit = load("artifacts/phase2/catalogs/audit.json")
    check(catalog_audit["checks_passed"] and catalog_audit["eligible_prototype_baselines"] == 4, "Catalog audit and four frozen exact-count prototype baselines pass")
    prototype_plan = load("artifacts/phase2/compositions/prototype_plan.json")
    check(sum(len(row.get("geometry_rejections", [])) for row in prototype_plan["plans"]) == 0, "No rejected prototype instantiations omitted from the four-attempt count")
    with (OUT / "budgets/prototype_attempts.jsonl").open(encoding="utf-8") as stream:
        prototype_events = [json.loads(line) for line in stream]
    check(len(prototype_events) == sum(row["attempts_charged"] for row in prototype_events) == 4, "Four distinct deterministic prototype candidates ledgered once")
    for row in prototype_events:
        file_check({"path": row["candidate_path"], "sha256": row["candidate_sha256"]})
    for item in load("artifacts/phase2/catalogs/artifact_inventory.json")["files"]:
        file_check(item)
    dft = load("artifacts/phase2/dft/reference_plan.json")
    numerical = load("artifacts/phase2/dft/numerical_protocol.json")
    check(bool(dft) and bool(numerical), "Reference inventory and concrete numerical acceptance protocol present")
    check(dft["formula_selection_sha256"] == sha(ROOT / dft["formula_selection_manifest"]), "DFT composition selection bound to final frozen proposal manifest")
    check(any(r["formula"] == "CaMg2O3" for r in proposals), "Primary six-atom DFT composition is a selected new-to-reference proposal")
    primary_inventory = load("artifacts/phase2/dft/primary_reference_plan.json")
    check(primary_inventory["system"] == "Ca-Mg-O" and len(primary_inventory["records"]) == 161, "All 161 primary-system catalog entries retained")
    fallback_inventory = load("artifacts/phase2/dft/fallback_Mg-O_reference_plan.json")
    check(len(fallback_inventory["records"]) == 57, "All 57 fallback-system catalog entries retained")
    for row in primary_inventory["records"] + fallback_inventory["records"]:
        file_check({"path": row["primitive_geometry"], "sha256": row["geometry_sha256"]})
        file_check({"path": row["execution_geometry_path"], "sha256": row["execution_geometry_sha256"]})
        check(row["execution_geometry_path"] == row["source_geometry"] and row["execution_n_sites"] == row["source_n_sites"], f"Execution retains original source cell: {row['material_id']}")
        check((ROOT / row["source_geometry"]).is_file() and (ROOT / row["primitive_cif"]).is_file() and (ROOT / row["input_template"]).is_file(), f"Source/reference/input files retained: {row['material_id']}")
    dft_audit = load("artifacts/phase2/dft/phase2_dft_audit.json")
    check(dft_audit["template_count"] == 221 and dft_audit["all_template_parses_passed"] and dft_audit["all_geometry_files_exist_and_hash_match"], "All 221 reference/molecular input templates parsed and geometry checks passed")
    check(dft_audit["all_reference_template_geometries_match_original_source_cells"], "No approximate primitive reduction changes the executed reference geometries")
    for item in dft_audit["template_checks"]:
        file_check({"path": item["template"], "sha256": item["sha256"]})
    budget = load("artifacts/budget_ledger.json")
    check(budget["generation"]["charged_attempts"] == 12 and budget["generation"]["CrystalFormer_sample_attempts"] == 8 and budget["generation"]["deterministic_prototype_attempts"] == 4, "Eight CrystalFormer samples plus four prepared prototype candidates charged once")
    check(budget["chgnet"]["charged_attempts"] == 8 and budget["qe"]["completed_jobs"] == 1, "No CHGNet or QE jobs added in Phase 2")
    allocation = protocol["chgnet_reallocation"]
    check(sum(allocation[k] for k in ["symmetry_max", "new_composition_shortlist_and_DFT_prerelax_max", "prototype_substitution_max", "same_composition_reference_max", "explicit_retry_contingency_max"]) == 32, "Rebalanced future CHGNet suballocations fit all 32 remaining launches")
    model_paths = list((ROOT / "artifacts/phase3").rglob("*")) if (ROOT / "artifacts/phase3").exists() else []
    check(not model_paths, "No Phase 3 models, replay histories or query outcomes exist yet")
    errors = [r["check"] for r in CHECKS if not r["passed"]]
    audit = {"created_utc": created, "status": "passed" if not errors else "failed", "checks": CHECKS,
             "errors": errors, "new_numerical_jobs": 0, "actual_model_fits": 0, "actual_pool_queries_revealed": 0,
             "evaluation_label_reads": "Audit integrity comparison only, never passed to model fitting/acquisition"}
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2)+"\n", encoding="utf-8")
    readiness = {"phase": 2, "status": "complete" if not errors else "failed", "completed_utc": created,
                 "ready_for_phase3": not errors, "descriptor_shape": [8294, 408],
                 "splits_per_seed": {"train": 2000, "calibration": 400, "query_pool": 2000, "fixed_untouched_evaluation": 3418, "reserved_fresh": 476},
                 "seeds": split_manifest["seeds"], "fresh_selector_seed": 20261022,
                 "selected_formulas": [r["formula"] for r in proposals], "new_formulas_qualified": 6,
                 "primary_DFT_composition": "CaMg2O3", "primary_DFT_chemical_system": "Ca-Mg-O",
                 "DFT_evidence_scope": "Same-composition polymorph and explicit CaO+2MgO decomposition comparisons first; no complete-hull stability claim from anchor phases alone",
                 "protocol_path": "config/phase2_protocol.json", "protocol_sha256": sha(ROOT / "config/phase2_protocol.json"),
                 "budget_ceilings_unchanged": True, "phase2_prototype_candidates_charged": 4,
                 "remaining_generation_attempts": 116, "remaining_chgnet_launches": 32,
                 "future_phase3_requirements": [
                     "Fit/calibrate initial seed20261022 snapshot and freeze it before any replay pool-label reveal.",
                     "Evaluate prediction error and uncertainty coverage only on fixed untouched unused-partition IDs; evaluator labels cannot affect decisions.",
                     "Complete one50-query replay using the frozen five-policy protocol and retain every decision before oracle reveal.",
                     "Generate the early CaMg2O3 pool under frozen SG2 settings; rank using the initial fresh-selector snapshot, not an adapted or best-seed model.",
                     "Charge every new sample, relaxation and QE job to registered cumulative ledgers; keep all failed jobs and numerical cutoffs.",
                     "Launch candidate/reference QE only after its budget/selection record is saved; force/stress/electronic and sensitivity checks are required for the stated evidence level."]}
    (OUT / "readiness.json").write_text(json.dumps(readiness, indent=2)+"\n", encoding="utf-8")
    budget_copy = dict(budget, workflow_phase_completed=2, phase2_CrystalFormer_attempts_added=0,
                       phase2_prototype_attempts_added=4,
                       remaining_chgnet_reallocation=allocation)
    (OUT / "budget_snapshot.json").write_text(json.dumps(budget_copy, indent=2)+"\n", encoding="utf-8")
    inventory = []
    for folder in [OUT, ROOT / "config"]:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.name != "artifact_inventory.json":
                inventory.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    for path in [ROOT / "research_features.py", ROOT / "research_acquisition.py", ROOT / "scripts/phase1_finalize.py"] + sorted((ROOT / "scripts").glob("phase2*.py")):
        inventory.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
    for filename in ["reports/phase2_report.md", "one_day_research_proposal.md", "README.md"]:
        path = ROOT / filename
        inventory.append({"path": filename, "bytes": path.stat().st_size, "sha256": sha(path)})
    (OUT / "artifact_inventory.json").write_text(json.dumps({"created_utc": created, "files": inventory}, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "checks": len(CHECKS), "errors": errors,
                      "ready_for_phase3": readiness["ready_for_phase3"], "selected": readiness["selected_formulas"]}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
